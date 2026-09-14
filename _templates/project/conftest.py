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
