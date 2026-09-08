# 实现规范

## conftest.py 完整代码

用 `save_file` 保存为 `<PROJECT_DIR>/conftest.py`：

```python
import os
import pytest
import allure
from dotenv import load_dotenv
from utils.request_helper import AuthSession, allure_request

load_dotenv()

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8080")
API_TOKEN = os.environ.get("API_TOKEN", "")


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL


@pytest.fixture(scope="session")
def auth_session():
    session = AuthSession(BASE_URL, API_TOKEN)
    return session


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
        if "auth" in item.nodeid or "need_auth" in item.keywords:
            if not API_TOKEN:
                item.add_marker(pytest.mark.skip(reason="无 API_TOKEN，跳过认证测试"))


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
import allure
import requests

logging.getLogger("urllib3").setLevel(logging.WARNING)

_request_counter = 0


def allure_request(method, url, expected="", session=None, **kwargs):
    global _request_counter
    _request_counter += 1
    seq = _request_counter

    headers = kwargs.pop("headers", None) or {}
    auth_header = headers.get("Authorization", "")
    if auth_header and len(auth_header) > 25:
        display_auth = auth_header[:25] + "..."
    else:
        display_auth = auth_header

    # 记录请求日志
    logging.info(f"[请求 #{seq}] {method} {url}")
    logging.debug(f"[请求 #{seq}] Headers: {headers}")
    logging.debug(f"[请求 #{seq}] Body: {kwargs.get('json', kwargs.get('data', ''))}")

    body_val = kwargs.get("json", kwargs.get("data", ""))
    try:
        body_display = json.dumps(body_val, ensure_ascii=False)[:500] if isinstance(body_val, (dict, list)) else str(body_val)[:500]
    except Exception:
        body_display = str(body_val)[:500]

    with allure.step(f"请求 #{seq}: {method} {url}"):
        allure.attach(
            f"方法: {method}\nURL: {url}\nHeaders: {display_auth}\n"
            f"Body: {body_display}",
            name="📤 请求",
            attachment_type=allure.attachment_type.TEXT,
        )
        if expected:
            allure.attach(expected, name="📋 预期", attachment_type=allure.attachment_type.TEXT)

    requester = session if session is not None else requests
    resp = requester.request(method, url, headers=headers, **kwargs)

    # 记录响应日志
    logging.info(f"[响应 #{seq}] Status: {resp.status_code}")
    logging.debug(f"[响应 #{seq}] Body: {resp.text[:500]}")

    body_text = resp.text[:500] if len(resp.text) > 500 else resp.text
    with allure.step(f"响应 #{seq}: {resp.status_code}"):
        allure.attach(
            f"状态码: {resp.status_code}\nBody: {body_text}",
            name="📥 响应",
            attachment_type=allure.attachment_type.TEXT,
        )

    return resp


class AuthSession:
    def __init__(self, base_url, token=""):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.session = requests.Session()
        if self.token:
            self.session.headers["Authorization"] = f"Bearer {self.token}"

    def _url(self, path):
        return f"{self.base_url}{path}"

    def _request(self, method, path, expected="", **kwargs):
        headers = kwargs.pop("headers", {})
        if self.token and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {self.token}"
        return allure_request(method, self._url(path), expected=expected, session=self.session, headers=headers, **kwargs)

    def get(self, path, expected="", **kwargs):
        return self._request("GET", path, expected=expected, **kwargs)

    def post(self, path, expected="", **kwargs):
        return self._request("POST", path, expected=expected, **kwargs)

    def put(self, path, expected="", **kwargs):
        return self._request("PUT", path, expected=expected, **kwargs)

    def patch(self, path, expected="", **kwargs):
        return self._request("PATCH", path, expected=expected, **kwargs)

    def delete(self, path, expected="", **kwargs):
        return self._request("DELETE", path, expected=expected, **kwargs)
```

## report_generator.py

完整代码在 `_templates/report_generator.py`。**仅当 ALLURE=无 时需要**，用 `read_file` 读取后用 `save_file` 保存到 `<PROJECT_DIR>/utils/report_generator.py`。

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
    smoke: 冒烟测试（核心路径）
    regression: 回归测试（全量覆盖）

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

```
API_BASE_URL=https://api.example.com
API_TOKEN=your_token_here
```

## tests/__init__.py

用 `save_file` 保存为 `<PROJECT_DIR>/tests/__init__.py`（空文件，用于初始化 `tests/` 用例包目录，所有自动化测试用例文件必须且只能存放在 `tests/` 目录下）。

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

按阶段记录：每阶段写日期+做了什么+发现什么+决策什么。阶段三写覆盖矩阵（接口 × 9 维度）。

## 频率限制

429 → 等 Retry-After 重试。大量 401 → token 被风控，重新获取。
