#!/usr/bin/env python3
"""Safely merge confirmed non-secret API settings into a project-local .env.

Existing credential values are preserved and never printed.  The script only
reports key names and whether each key was created, updated, or preserved.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit


AUTH_MODES = {"none", "bearer", "header", "query", "cookie", "basic", "dynamic"}
ENV_KEY = re.compile(r"^[A-Z][A-Z0-9_]*$")
LINE_KEY = re.compile(r"^[ \t]*(?:export[ \t]+)?([A-Za-z_][A-Za-z0-9_]*)[ \t]*=")
SKILL_ROOT = Path(__file__).resolve().parent.parent


class ConfigurationError(ValueError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="写入已确认的非敏感配置，并保留已有凭据值。",
    )
    parser.add_argument("--project", required=True, help="用户已确认的项目绝对路径")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--auth-mode", required=True, choices=sorted(AUTH_MODES))
    parser.add_argument("--auth-name", default="")
    parser.add_argument("--auth-scheme", default="")
    parser.add_argument(
        "--secret-env",
        default="",
        help="dynamic 模式使用的凭据变量名，多个名称用逗号分隔",
    )
    return parser.parse_args()


def safe_scalar(value: str, option: str) -> str:
    if any(char in value for char in ("\x00", "\r", "\n")):
        raise ConfigurationError(f"{option} 不能包含换行或 NUL")
    return value


def project_dir(raw: str) -> Path:
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        raise ConfigurationError("--project 必须是绝对路径")
    project = candidate.resolve()
    if project in {Path(project.anchor).resolve(), Path.home().resolve()}:
        raise ConfigurationError("--project 不能是文件系统根目录或用户主目录")
    if project == SKILL_ROOT or SKILL_ROOT in project.parents:
        raise ConfigurationError("禁止把生成项目放在 skill 目录内")
    if not project.is_dir():
        raise ConfigurationError("项目目录不存在")
    return project


def credential_keys(mode: str, custom: str) -> list[str]:
    if mode in {"bearer", "header", "query", "cookie"}:
        return ["API_TOKEN"]
    if mode == "basic":
        return ["API_USERNAME", "API_PASSWORD"]
    if mode == "dynamic":
        keys = [item.strip() for item in custom.split(",") if item.strip()]
        if not keys:
            raise ConfigurationError("dynamic 模式必须用 --secret-env 指定凭据变量名")
        if any(not ENV_KEY.fullmatch(key) for key in keys):
            raise ConfigurationError("--secret-env 只能包含大写环境变量名")
        return list(dict.fromkeys(keys))
    if custom.strip():
        raise ConfigurationError("AUTH_MODE=none 时不得声明凭据变量")
    return []


def merge_env(path: Path, confirmed: dict[str, str], credentials: list[str]) -> list[str]:
    if path.exists() and (not path.is_file() or path.is_symlink()):
        raise ConfigurationError(".env 必须是项目内普通文件，不能是符号链接")

    original = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = original.splitlines()
    positions: dict[str, int] = {}
    duplicate_keys: set[str] = set()
    for index, line in enumerate(lines):
        match = LINE_KEY.match(line)
        if not match:
            continue
        key = match.group(1)
        if key in positions:
            duplicate_keys.add(key)
        else:
            positions[key] = index

    managed_keys = set(confirmed) | set(credentials)
    duplicated_managed = sorted(duplicate_keys & managed_keys)
    if duplicated_managed:
        raise ConfigurationError(
            ".env 的受管变量重复，请用户在本地合并重复项: "
            + ", ".join(duplicated_managed)
        )

    events: list[str] = []
    for key, value in confirmed.items():
        rendered = f"{key}={value}"
        if key in positions:
            state = "UNCHANGED" if lines[positions[key]] == rendered else "UPDATED"
            lines[positions[key]] = rendered
        else:
            lines.append(rendered)
            state = "CREATED"
        events.append(f"- {state} {key}")

    for key in credentials:
        if key in positions:
            events.append(f"- PRESERVED {key}")
        else:
            lines.append(f"{key}=")
            events.append(f"- CREATED {key}")

    rendered_text = "\n".join(lines).rstrip("\n") + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".env.", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(rendered_text)
        if path.exists():
            os.chmod(temporary, path.stat().st_mode & 0o777)
        else:
            os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return events


def main() -> int:
    args = parse_args()
    try:
        project = project_dir(args.project)
        base_url = safe_scalar(args.base_url.strip(), "--base-url")
        parsed = urlsplit(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ConfigurationError("--base-url 必须是完整 HTTP(S) 地址")
        if parsed.username or parsed.password:
            raise ConfigurationError("--base-url 不得包含用户名或密码")
        auth_name = safe_scalar(args.auth_name.strip(), "--auth-name")
        auth_scheme = safe_scalar(args.auth_scheme.strip(), "--auth-scheme")
        credentials = credential_keys(args.auth_mode, args.secret_env)
        events = merge_env(
            project / ".env",
            {
                "API_BASE_URL": base_url,
                "API_AUTH_MODE": args.auth_mode,
                "API_AUTH_NAME": auth_name,
                "API_AUTH_SCHEME": auth_scheme,
            },
            credentials,
        )
    except (ConfigurationError, OSError, UnicodeError) as exc:
        print("ENV CONFIGURATION: FAIL")
        print(f"- {exc}")
        return 1

    print("ENV CONFIGURATION: PASS")
    for event in events:
        print(event)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
