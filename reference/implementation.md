# 实现规范

## conftest.py 完整代码

用 `save_file` 保存为 `<PROJECT_DIR>/conftest.py`：

```python
import os
import pytest
import allure
from dotenv import load_dotenv

load_dotenv()

from utils.request_helper import AuthSession, allure_request

BASE_URL = os.environ.get("API_BASE_URL", "").strip()
API_TOKEN = os.environ.get("API_TOKEN", "").strip()
API_USERNAME = os.environ.get("API_USERNAME", "").strip()
API_PASSWORD = os.environ.get("API_PASSWORD", "").strip()
API_AUTH_MODE = os.environ.get("API_AUTH_MODE", "").strip().lower()
API_AUTH_LOCATION = os.environ.get("API_AUTH_LOCATION", "header").strip().lower()
API_AUTH_NAME = os.environ.get("API_AUTH_NAME", "").strip()
LEGACY_AUTH_HEADER = os.environ.get("API_AUTH_HEADER", "").strip()
LEGACY_AUTH_QUERY_PARAM = os.environ.get("API_AUTH_QUERY_PARAM", "").strip()
LEGACY_AUTH_COOKIE = os.environ.get("API_AUTH_COOKIE", "").strip()
API_AUTH_SCHEME = os.environ.get("API_AUTH_SCHEME", "").strip()

# 兼容旧项目：未配置 API_AUTH_MODE 时，沿用原 API_TOKEN + LOCATION 语义。
if not API_AUTH_MODE:
    if API_USERNAME or API_PASSWORD:
        API_AUTH_MODE = "basic"
    elif API_TOKEN:
        API_AUTH_MODE = API_AUTH_LOCATION if API_AUTH_LOCATION in {"query", "cookie"} else (
            "bearer" if (
                (not LEGACY_AUTH_HEADER or LEGACY_AUTH_HEADER.lower() == "authorization")
                and (not API_AUTH_SCHEME or API_AUTH_SCHEME.lower() == "bearer")
            )
            else "header"
        )
    else:
        API_AUTH_MODE = "none"

ALLOWED_AUTH_MODES = {"none", "bearer", "header", "query", "cookie", "basic", "dynamic"}
if API_AUTH_MODE not in ALLOWED_AUTH_MODES:
    raise pytest.UsageError("API_AUTH_MODE 只允许 none/bearer/header/query/cookie/basic/dynamic")

API_AUTH_HEADER = LEGACY_AUTH_HEADER or API_AUTH_NAME or (
    "Authorization" if API_AUTH_MODE == "bearer" else ""
)
API_AUTH_QUERY_PARAM = LEGACY_AUTH_QUERY_PARAM or API_AUTH_NAME
API_AUTH_COOKIE = LEGACY_AUTH_COOKIE or API_AUTH_NAME

AUTH_READY = (
    API_AUTH_MODE == "none"
    or (API_AUTH_MODE in {"bearer", "header", "query", "cookie"} and bool(API_TOKEN))
    or (API_AUTH_MODE == "basic" and bool(API_USERNAME and API_PASSWORD))
)


@pytest.fixture(scope="session")
def base_url():
    """向不使用认证会话的契约用例提供统一 Base URL。"""
    if not BASE_URL.startswith(("http://", "https://")):
        pytest.fail("API_BASE_URL 未配置为完整的 HTTP(S) 地址")
    return BASE_URL


@pytest.fixture(scope="session")
def auth_session():
    if API_AUTH_MODE != "none" and not AUTH_READY:
        pytest.skip("认证凭据尚未由用户在本地配置")
    return AuthSession(BASE_URL, API_TOKEN, API_AUTH_LOCATION,
                       API_AUTH_HEADER, API_AUTH_QUERY_PARAM, API_AUTH_SCHEME,
                       auth_mode=API_AUTH_MODE, auth_cookie=API_AUTH_COOKIE,
                       username=API_USERNAME, password=API_PASSWORD)


@pytest.fixture(autouse=True)
def reset_request_counter():
    from utils import request_helper
    request_helper._request_counter = 0


def pytest_runtest_makereport(item, call):
    if call.when == "call":
        outcome = call.excinfo is None
        if outcome:
            status = "✅ PASSED"
        elif call.excinfo.errisinstance(pytest.skip.Exception):
            status = "⏭️ SKIPPED"
        else:
            tb_lines = str(call.excinfo.value).split("\n")[:8]
            status = f"❌ FAILED\n┌─ Error ─┐\n" + "\n".join(f"│ {l}" for l in tb_lines) + "\n└─────────┘"
        print(f"\n  {status}")


def pytest_collection_modifyitems(items):
    for item in items:
        if "need_auth" in item.keywords and not AUTH_READY:
            item.add_marker(pytest.mark.skip(reason="认证凭据尚未由用户在本地配置"))


def pytest_sessionfinish(session, exitstatus):
    """测试会话结束时，将日志附加到 Allure 报告"""
    from pathlib import Path

    log_file = Path("logs/test.log")
    if log_file.exists():
        content = log_file.read_text(encoding="utf-8")
        if content.strip():
            try:
                allure.attach(content, name="📄 测试日志", attachment_type=allure.attachment_type.TEXT)
            except (KeyError, RuntimeError):
                pass  # 会话结束时 allure 上下文可能已关闭
```

## request_helper.py 完整代码

用 `save_file` 保存为 `<PROJECT_DIR>/utils/request_helper.py`：

```python
import json
import logging
import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import allure
import requests

logging.getLogger("urllib3").setLevel(logging.WARNING)

_request_counter = 0

_COMMON_SECRET_KEYS = {
    "authorization", "token", "accesstoken", "refreshtoken", "idtoken",
    "apikey", "password", "passwd", "secret", "clientsecret", "cookie",
    "setcookie", "session", "sessionid",
}


def _key_id(value):
    return "".join(ch for ch in str(value).lower() if ch.isalnum())


def _configured_secret_keys():
    names = {
        os.environ.get("API_AUTH_HEADER", ""),
        os.environ.get("API_AUTH_QUERY_PARAM", ""),
        os.environ.get("API_AUTH_COOKIE", ""),
        os.environ.get("API_AUTH_NAME", ""),
    }
    return {_key_id(name) for name in names if name}


def _is_secret_key(key):
    normalized = _key_id(key)
    return normalized in _COMMON_SECRET_KEYS or normalized in _configured_secret_keys()


def _known_secret_values():
    return tuple(
        value for value in (
            os.environ.get("API_TOKEN", ""),
            os.environ.get("API_PASSWORD", ""),
        ) if value
    )


def _sanitize_text(value):
    text = str(value)
    for secret in _known_secret_values():
        text = text.replace(secret, "***REDACTED***")
    return text


def _sanitize(value, parent_key=""):
    if parent_key and _is_secret_key(parent_key):
        return "***REDACTED***"
    if isinstance(value, dict):
        return {key: _sanitize(item, key) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return _sanitize_text(value)
        return _sanitize(parsed)
    return value


def _render(value, limit=500):
    sanitized = _sanitize(value)
    if isinstance(sanitized, str):
        text = sanitized
    else:
        text = json.dumps(sanitized, ensure_ascii=False, default=str)
    return text[:limit]


def _sanitize_url(url):
    try:
        parts = urlsplit(str(url))
        hostname = parts.hostname or ""
        if parts.port:
            hostname = f"{hostname}:{parts.port}"
        if parts.username or parts.password:
            hostname = f"***REDACTED***@{hostname}"
        query = urlencode([
            (key, "***REDACTED***" if _is_secret_key(key) else _sanitize_text(value))
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
        ])
        return _sanitize_text(urlunsplit((parts.scheme, hostname, parts.path, query, parts.fragment)))
    except (TypeError, ValueError):
        return _sanitize_text(url)


def allure_request(method, url, expected="", session=None, **kwargs):
    global _request_counter
    _request_counter += 1
    seq = _request_counter

    headers = kwargs.pop("headers", {})
    session_headers = dict(getattr(session, "headers", {}) or {})
    display_headers = _sanitize({**session_headers, **headers})
    display_url = _sanitize_url(url)
    display_params = _render(kwargs.get("params", {}))
    display_body = _render(kwargs.get("json", kwargs.get("data", "")))

    # 日志和 Allure 只接收脱敏副本；原值仅传给 requests。
    logging.info(f"[请求 #{seq}] {method} {display_url}")
    logging.debug(f"[请求 #{seq}] Headers: {display_headers}")
    logging.debug(f"[请求 #{seq}] Params: {display_params}")
    logging.debug(f"[请求 #{seq}] Body: {display_body}")

    with allure.step(f"请求 #{seq}: {method} {display_url}"):
        allure.attach(
            f"方法: {method}\nURL: {display_url}\nHeaders: {_render(display_headers)}\n"
            f"Params: {display_params}\nBody: {display_body}",
            name="📤 请求",
            attachment_type=allure.attachment_type.TEXT,
        )
        if expected:
            allure.attach(expected, name="📋 预期", attachment_type=allure.attachment_type.TEXT)

    client = session or requests
    resp = client.request(method, url, headers=headers, **kwargs)

    try:
        response_body = resp.json()
    except (ValueError, TypeError):
        response_body = resp.text
    display_response = _render(response_body)

    # 响应日志和附件同样只使用脱敏副本。
    logging.info(f"[响应 #{seq}] Status: {resp.status_code}")
    logging.debug(f"[响应 #{seq}] Body: {display_response}")

    with allure.step(f"响应 #{seq}: {resp.status_code}"):
        allure.attach(
            f"状态码: {resp.status_code}\nBody: {display_response}",
            name="📥 响应",
            attachment_type=allure.attachment_type.TEXT,
        )

    return resp


class AuthSession:
    def __init__(self, base_url, token="", auth_location="header",
                 auth_header="Authorization", auth_query_param="", auth_scheme="Bearer",
                 auth_mode="", auth_cookie="", username="", password="", session=None):
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("API_BASE_URL 必须是完整的 HTTP(S) 地址")
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.session = session or requests.Session()

        mode = (auth_mode or "").strip().lower()
        if not mode:
            mode = auth_location if auth_location in {"query", "cookie"} and token else (
                "bearer" if token and (auth_header or "Authorization").lower() == "authorization"
                and auth_scheme.lower() == "bearer" else ("header" if token else "none")
            )
        if mode not in {"none", "bearer", "header", "query", "cookie", "basic", "dynamic"}:
            raise ValueError("API_AUTH_MODE 只允许 none/bearer/header/query/cookie/basic/dynamic")

        if mode == "bearer" and token:
            self.session.headers[auth_header or "Authorization"] = f"Bearer {token}"
        elif mode == "header" and token:
            if not auth_header:
                raise ValueError("Header 认证必须配置 API_AUTH_NAME")
            credential = f"{auth_scheme} {token}".strip()
            self.session.headers[auth_header] = credential
        elif mode == "query" and token:
            if not auth_query_param:
                raise ValueError("Query 认证必须配置 API_AUTH_QUERY_PARAM")
            self.session.params[auth_query_param] = f"{auth_scheme} {token}".strip()
        elif mode == "cookie" and token:
            if not auth_cookie:
                raise ValueError("Cookie 认证必须配置 API_AUTH_NAME")
            self.session.cookies.set(auth_cookie, token)
        elif mode == "basic":
            if username and password:
                self.session.auth = (username, password)
        # dynamic 不猜测登录/OAuth；项目专用 fixture 传入已配置的 session。

    def _url(self, path):
        return f"{self.base_url}/{str(path).lstrip('/')}"

    def get(self, path, expected="", **kwargs):
        return allure_request("GET", self._url(path), expected=expected, session=self.session, headers=kwargs.pop("headers", {}), **kwargs)

    def post(self, path, expected="", **kwargs):
        return allure_request("POST", self._url(path), expected=expected, session=self.session, headers=kwargs.pop("headers", {}), **kwargs)

    def put(self, path, expected="", **kwargs):
        return allure_request("PUT", self._url(path), expected=expected, session=self.session, headers=kwargs.pop("headers", {}), **kwargs)

    def patch(self, path, expected="", **kwargs):
        return allure_request("PATCH", self._url(path), expected=expected, session=self.session, headers=kwargs.pop("headers", {}), **kwargs)

    def delete(self, path, expected="", **kwargs):
        return allure_request("DELETE", self._url(path), expected=expected, session=self.session, headers=kwargs.pop("headers", {}), **kwargs)
```

## report_generator.py

完整代码在 `_templates/report_generator.py`，用 `read_file` 完整读取后保存到 `<PROJECT_DIR>/utils/report_generator.py`。无论当前是否有 Allure CLI 都要交付该回退工具，不用固定行数或文件大小判断完整性。

## pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Allure配置
addopts = -v --tb=short --alluredir=allure-results

markers =
    need_auth: 需要认证的测试

# 日志配置 - 控制台输出
log_cli = true
log_cli_level = INFO
log_cli_format = %(asctime)s - %(name)s - %(levelname)s - %(message)s
log_cli_date_format = %Y-%m-%d %H:%M:%S

# 日志配置 - 文件输出
log_file = logs/test.log
log_file_level = INFO
log_file_format = %(asctime)s - %(name)s - %(levelname)s - %(message)s
log_file_date_format = %Y-%m-%d %H:%M:%S
```

## requirements.txt

```
pytest>=7.4
allure-pytest>=2.13
requests>=2.31
python-dotenv>=1.0
```

## .env 模板

此处只定义变量结构。Agent 必须在 `.gitignore` 已包含 `.env` 后调用 `configure_env` 写入非敏感值和空凭据槽；不得用 `save_file`/`edit_file` 写 `.env`，也不得读取它。`API_TOKEN` 保留为旧项目兼容别名，同时承载 bearer/header/query/cookie 的静态凭据。

新项目统一把 header/query/cookie 名称写到非敏感变量 `API_AUTH_NAME`；旧项目的 `API_AUTH_HEADER`、`API_AUTH_QUERY_PARAM`、`API_AUTH_COOKIE` 继续兼容。`basic` 使用 `API_USERNAME` + `API_PASSWORD`。动态登录/OAuth 使用 `API_AUTH_MODE=dynamic`，不套用通用猜测：按已确认契约定制 `auth_session` fixture（包括就绪判断），登录后把已配置的 `requests.Session` 传给 `AuthSession(..., auth_mode="dynamic", session=session)`。

```
API_BASE_URL=
API_AUTH_MODE=none
API_AUTH_NAME=
API_TOKEN=
API_AUTH_LOCATION=header
API_AUTH_HEADER=
API_AUTH_QUERY_PARAM=
API_AUTH_COOKIE=
API_AUTH_SCHEME=
API_USERNAME=
API_PASSWORD=
REPORT_TITLE=
```

## .gitignore

```
__pycache__/
*.pyc
.env
allure-results/
allure-report/
*.egg-info/
dist/
build/
```

## MEMORY.md 格式

固定保存为 `<PROJECT_DIR>/MEMORY.md`，必须用文件写入工具创建或追加，作为用户可见交付物。禁止保存到 Agent 工作区、project-memory 或 skill 目录；`memory_save`/数据库只能额外保存副本，不能替代本文件。

文件开头维护一个稳定的“项目配置”段，至少包含：`PROJECT_KIND`、`API_BASE_URL`、`AUTH_MODE`、`AUTH_NAME`、`AUTH_SCHEME`、`AUTH_SECRET_ENV`、`PYTHON`、`OS_TYPE`、`ALLURE`。只记录凭据变量名，不记录值。

其后按阶段记录：每阶段写日期+做了什么+发现什么+决策什么。阶段三写覆盖矩阵（接口 × 9 维度）和按参数化展开后的用例计数表。

## 频率限制

429 → 等 Retry-After 重试。大量 401 → token 被风控，重新获取。
