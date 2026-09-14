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

    def head(self, path, expected="", **kwargs):
        return allure_request("HEAD", self._url(path), expected=expected, session=self.session, headers=kwargs.pop("headers", {}), **kwargs)

    def options(self, path, expected="", **kwargs):
        return allure_request("OPTIONS", self._url(path), expected=expected, session=self.session, headers=kwargs.pop("headers", {}), **kwargs)
