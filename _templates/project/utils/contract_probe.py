#!/usr/bin/env python3
"""Safely inspect one API response before writing contract assertions.

The program loads project-local .env at runtime and sends requests through
AuthSession. Stdout contains the method/path, status code, Content-Type, and a
sanitized response preview capped at 2000 characters for recording in MEMORY.md.
Recognized credential fields and configured token/password values are redacted.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

from dotenv import load_dotenv

from utils.request_helper import AuthSession, _is_secret_key, _render


METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")
STATIC_AUTH_MODES = {"none", "bearer", "header", "query", "cookie", "basic"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="安全探测一个 API 的状态码和脱敏实际响应")
    parser.add_argument("--method", required=True, choices=METHODS)
    parser.add_argument("--path", required=True, help="不含凭据的接口路径")
    params = parser.add_mutually_exclusive_group()
    params.add_argument("--params-json", help="非敏感查询参数 JSON 对象")
    params.add_argument("--params-file", help="项目内非敏感查询参数 JSON 文件")
    body = parser.add_mutually_exclusive_group()
    body.add_argument("--json-body", help="非敏感请求体 JSON")
    body.add_argument("--json-body-file", help="项目内非敏感请求体 JSON 文件")
    return parser.parse_args()


def parse_json(raw: str, option: str, *, object_only: bool) -> Any:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{option} 不是有效 JSON") from exc
    if object_only and not isinstance(value, dict):
        raise ValueError(f"{option} 必须是 JSON 对象")
    return value


def read_project_json(raw: str, option: str) -> str:
    project = Path.cwd().resolve()
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = project / candidate
    if candidate.is_symlink():
        raise ValueError(f"{option} 不能是符号链接")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(project)
    except ValueError as exc:
        raise ValueError(f"{option} 必须位于项目目录内") from exc
    if not resolved.is_file():
        raise ValueError(f"{option} 文件不存在")
    try:
        return resolved.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"{option} 无法按 UTF-8 读取") from exc


def configured_auth() -> tuple[str, dict[str, str]]:
    mode = os.environ.get("API_AUTH_MODE", "").strip().lower()
    token = os.environ.get("API_TOKEN", "").strip()
    username = os.environ.get("API_USERNAME", "").strip()
    password = os.environ.get("API_PASSWORD", "").strip()
    location = os.environ.get("API_AUTH_LOCATION", "header").strip().lower()
    name = os.environ.get("API_AUTH_NAME", "").strip()
    legacy_header = os.environ.get("API_AUTH_HEADER", "").strip()
    legacy_query = os.environ.get("API_AUTH_QUERY_PARAM", "").strip()
    legacy_cookie = os.environ.get("API_AUTH_COOKIE", "").strip()
    scheme = os.environ.get("API_AUTH_SCHEME", "").strip()

    if not mode:
        if username or password:
            mode = "basic"
        elif token:
            mode = location if location in {"query", "cookie"} else (
                "bearer" if (
                    (not legacy_header or legacy_header.lower() == "authorization")
                    and (not scheme or scheme.lower() == "bearer")
                ) else "header"
            )
        else:
            mode = "none"

    return mode, {
        "token": token,
        "username": username,
        "password": password,
        "location": location,
        "header": legacy_header or name or ("Authorization" if mode == "bearer" else ""),
        "query": legacy_query or name,
        "cookie": legacy_cookie or name,
        "scheme": scheme,
    }


def credentials_ready(mode: str, values: dict[str, str]) -> bool:
    if mode == "none":
        return True
    if mode in {"bearer", "header", "query", "cookie"}:
        return bool(values["token"])
    if mode == "basic":
        return bool(values["username"] and values["password"])
    return False


def contains_secret_field(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            _is_secret_key(key) or contains_secret_field(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(contains_secret_field(item) for item in value)
    return False


def main() -> int:
    args = parse_args()
    try:
        params_raw = (
            read_project_json(args.params_file, "--params-file")
            if args.params_file else (args.params_json or "{}")
        )
        body_raw = (
            read_project_json(args.json_body_file, "--json-body-file")
            if args.json_body_file else args.json_body
        )
        params = parse_json(params_raw, "查询参数", object_only=True)
        body = parse_json(body_raw, "JSON 请求体", object_only=False) if body_raw else None
    except ValueError as exc:
        print(f"PROBE: FAIL\n- {exc}")
        return 2

    if (
        not args.path.startswith("/")
        or "://" in args.path
        or any(char in args.path for char in ("?", "#", "{", "}"))
    ):
        print(
            "PROBE: FAIL\n"
            "- --path 必须是已替换路径参数的具体相对路径；查询参数只允许使用 --params-json"
        )
        return 2
    if contains_secret_field(params) or contains_secret_field(body):
        print("PROBE: FAIL\n- 探测参数不得包含认证凭据字段")
        return 2

    load_dotenv()
    base_url = os.environ.get("API_BASE_URL", "").strip()
    mode, values = configured_auth()
    if mode == "dynamic":
        print("PROBE: BLOCKED\n- dynamic 认证必须先按已确认契约实现项目专用 fixture")
        return 3
    if mode not in STATIC_AUTH_MODES:
        print("PROBE: FAIL\n- API_AUTH_MODE 不受支持")
        return 2
    if not base_url.startswith(("http://", "https://")):
        print("PROBE: BLOCKED\n- API_BASE_URL 未配置为完整 HTTP(S) 地址")
        return 3
    if not credentials_ready(mode, values):
        print("PROBE: BLOCKED\n- 本地认证凭据尚未配置")
        return 3
    argument_blob = json.dumps(
        {"path": args.path, "params": params, "body": body},
        ensure_ascii=False,
        default=str,
    )
    if any(
        secret and secret in argument_blob
        for secret in (values["token"], values["password"])
    ):
        print("PROBE: FAIL\n- 探测参数不得包含已配置的认证凭据值")
        return 2

    try:
        session = AuthSession(
            base_url,
            values["token"],
            values["location"],
            values["header"],
            values["query"],
            values["scheme"],
            auth_mode=mode,
            auth_cookie=values["cookie"],
            username=values["username"],
            password=values["password"],
        )
        kwargs: dict[str, Any] = {"params": params}
        if body is not None:
            kwargs["json"] = body
        response = getattr(session, args.method.lower())(
            args.path,
            expected="安全探测：记录状态码与脱敏后的实际响应，不记录凭据",
            **kwargs,
        )
        try:
            payload = response.json()
            body_preview = _render(payload, limit=2000)
        except ValueError:
            body_preview = _render(response.text, limit=2000)
    except Exception as exc:  # 请求异常不得回显可能含 URL 或凭据的原文。
        print(f"PROBE: FAIL\n- 请求失败: {type(exc).__name__}")
        return 1

    print("PROBE: PASS")
    print(json.dumps({
        "method": args.method,
        "path": args.path,
        "status": response.status_code,
        "content_type": response.headers.get("Content-Type", "").split(";", 1)[0],
        "body_preview": body_preview,
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
