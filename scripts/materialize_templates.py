#!/usr/bin/env python3
"""Copy project assets without exposing their contents to the model context."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_ROOT = SKILL_ROOT / "_templates"
CORE_TEMPLATES = (
    (Path("project/.gitignore"), Path(".gitignore")),
    (Path("project/conftest.py"), Path("conftest.py")),
    (Path("project/utils/contract_probe.py"), Path("utils/contract_probe.py")),
    (Path("project/utils/request_helper.py"), Path("utils/request_helper.py")),
    (Path("project/utils/__init__.py"), Path("utils/__init__.py")),
    (Path("project/pytest.ini"), Path("pytest.ini")),
    (Path("project/requirements.txt"), Path("requirements.txt")),
)
REPORT_TEMPLATE = (Path("report_generator.py"), Path("utils/report_generator.py"))
WINDOWS_PYTHON = re.compile(r"^[A-Za-z0-9_ .:\\/()+-]+$")


class MaterializeError(ValueError):
    pass


def detect_report_mode() -> str:
    """Select the only report branch supported by the current host.

    ``which`` alone is not sufficient: an unusable or stale executable must
    not make a project appear to have official Allure support.
    """
    allure = shutil.which("allure")
    if not allure:
        return "fallback"
    try:
        completed = subprocess.run(
            [allure, "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "fallback"
    return "official" if completed.returncode == 0 else "fallback"


def lock_report_mode(args: argparse.Namespace) -> str | None:
    """Refuse a model-provided report branch that contradicts the host."""
    if args.component not in {"report", "runner"}:
        return None
    if not args.report:
        raise MaterializeError(f"{args.component} 需要 --report")
    actual = detect_report_mode()
    if args.report != actual:
        raise MaterializeError(
            "--report 与本机实际 Allure 检测不一致："
            f"requested={args.report}, detected={actual}。"
            "请返回 ENV_LOCK，按 `allure --version` 的结果重新锁定后再物化。"
        )
    return actual


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="按分支把 api-qa-skill 模板安全落盘到已确认的项目目录。",
    )
    parser.add_argument("--project", required=True, help="已由用户确认的项目绝对路径")
    parser.add_argument("--component", required=True, choices=("core", "report", "runner"))
    parser.add_argument("--project-kind", required=True, choices=("new", "existing"))
    parser.add_argument("--os", dest="os_type", choices=("Darwin", "Linux", "Windows"))
    parser.add_argument("--python-command")
    parser.add_argument("--report", choices=("official", "fallback"))
    return parser.parse_args()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def project_path(raw: str) -> Path:
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        raise MaterializeError("--project 必须是用户已确认的绝对路径")
    project = candidate.resolve()
    protected_roots = {Path(project.anchor).resolve(), Path.home().resolve()}
    desktop = Path.home() / "Desktop"
    if desktop.exists():
        protected_roots.add(desktop.resolve())
    if project in protected_roots:
        raise MaterializeError("--project 不能是文件系统根目录、用户主目录或桌面根目录")
    if project == SKILL_ROOT or SKILL_ROOT in project.parents:
        raise MaterializeError("禁止把生成项目放在 skill 目录内")
    project.mkdir(parents=True, exist_ok=True)
    if not project.is_dir():
        raise MaterializeError("项目路径不是目录")
    return project


def safe_target(project: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise MaterializeError(f"非法目标路径: {relative}")
    current = project
    for part in relative.parts[:-1]:
        current = current / part
        if current.exists() and current.is_symlink():
            raise MaterializeError(f"目标父目录不能是符号链接: {relative}")
    target = project / relative
    if target.exists() and target.is_symlink():
        raise MaterializeError(f"目标文件不能是符号链接: {relative}")
    return target


def read_asset(relative: Path) -> bytes:
    asset = (TEMPLATE_ROOT / relative).resolve()
    try:
        asset.relative_to(TEMPLATE_ROOT.resolve())
    except ValueError as exc:
        raise MaterializeError(f"模板路径越界: {relative}") from exc
    if not asset.is_file():
        raise MaterializeError(f"模板不存在: {relative}")
    return asset.read_bytes()


def render_runner(os_type: str, python_command: str, report: str) -> tuple[Path, Path, bytes]:
    if any(char in python_command for char in ("\x00", "\r", "\n")):
        raise MaterializeError("Python 命令不能包含换行或 NUL")
    if not python_command.strip():
        raise MaterializeError("--python-command 不能为空")
    python_command = python_command.strip()
    if any(char in python_command for char in ('"', "'")):
        raise MaterializeError("--python-command 传原始可执行文件名或路径，不要包含 Shell 引号")
    if any(char.isspace() for char in python_command) and not any(
        separator in python_command for separator in ("/", "\\")
    ):
        raise MaterializeError("--python-command 不能包含启动参数；请传单个可执行文件名或路径")

    if os_type == "Windows":
        try:
            python_command.encode("ascii")
        except UnicodeEncodeError as exc:
            raise MaterializeError("Windows Python 命令必须是纯 ASCII") from exc
        if not WINDOWS_PYTHON.fullmatch(python_command) or any(
            char in python_command for char in ('"', "%", "&", "|", "<", ">", "^")
        ):
            raise MaterializeError("Windows Python 命令含不安全字符")
        source, target = Path("run.bat"), Path("run.bat")
        encoding = "ascii"
    else:
        escaped = (
            python_command.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("$", "\\$")
            .replace("`", "\\`")
        )
        python_command = escaped
        source, target = Path("run.sh"), Path("run.sh")
        encoding = "utf-8"

    template = read_asset(source).decode(encoding)
    if template.count("__PYTHON_COMMAND__") != 1 or template.count("__REPORT_MODE__") != 1:
        raise MaterializeError(f"运行模板占位符数量异常: {source}")
    rendered = template.replace("__PYTHON_COMMAND__", python_command).replace(
        "__REPORT_MODE__", report
    )
    if "__PYTHON_COMMAND__" in rendered or "__REPORT_MODE__" in rendered:
        raise MaterializeError(f"运行模板仍含占位符: {source}")
    return source, target, rendered.encode(encoding)


def build_plan(args: argparse.Namespace) -> list[tuple[Path, Path, bytes, int | None]]:
    if args.component == "core":
        return [
            (source, target, read_asset(source), None)
            for source, target in CORE_TEMPLATES
        ]
    if args.component == "report":
        if args.report != "fallback":
            raise MaterializeError("报告生成器只允许在 --report fallback 时复制")
        source, target = REPORT_TEMPLATE
        return [(source, target, read_asset(source), None)]
    if not args.os_type or not args.python_command or not args.report:
        raise MaterializeError("runner 需要 --os、--python-command 和 --report")
    source, target, data = render_runner(args.os_type, args.python_command, args.report)
    return [(source, target, data, 0o755 if target.name == "run.sh" else None)]


def materialize(args: argparse.Namespace) -> int:
    # Validate the locked branch and the requested asset before project_path(),
    # so any invalid request fails without creating an empty candidate directory.
    locked_report = lock_report_mode(args)
    plan = build_plan(args)
    if locked_report:
        print(f"- REPORT MODE CHECK: PASS ({locked_report})")
    project = project_path(args.project)
    prepared: list[tuple[Path, Path, bytes, int | None, str]] = []

    if args.component == "runner" and args.project_kind == "new":
        expected = "run.bat" if args.os_type == "Windows" else "run.sh"
        other = safe_target(project, Path("run.sh" if expected == "run.bat" else "run.bat"))
        if other.exists():
            print("TEMPLATE MATERIALIZATION: FAIL")
            print(f"- new 项目已存在另一平台脚本: {other.name}；未写入当前脚本")
            return 2

    for source, relative, data, mode in plan:
        target = safe_target(project, relative)
        state = "CREATE"
        if target.exists():
            if not target.is_file():
                raise MaterializeError(f"目标不是普通文件: {relative}")
            state = "UNCHANGED" if target.read_bytes() == data else "PRESERVED"
        prepared.append((source, target, data, mode, state))

    conflicts = [item for item in prepared if item[4] == "PRESERVED"]
    if args.project_kind == "new" and conflicts:
        print("TEMPLATE MATERIALIZATION: FAIL")
        for _, target, data, _, _ in conflicts:
            print(
                f"- CONFLICT {target.relative_to(project)} "
                f"expected_sha256={sha256(data)} actual_sha256={sha256(target.read_bytes())}"
            )
        print("- new 项目存在冲突文件；未写入任何模板")
        return 2

    for source, target, data, mode, state in prepared:
        relative = target.relative_to(project)
        if state == "CREATE":
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as stream:
                stream.write(data)
            if mode is not None:
                os.chmod(target, mode)
            print(f"- CREATED {relative} sha256={sha256(data)} source={source}")
        elif state == "UNCHANGED":
            if mode is not None:
                os.chmod(target, mode)
            print(f"- UNCHANGED {relative} sha256={sha256(data)}")
        else:
            print(
                f"- PRESERVED {relative} expected_sha256={sha256(data)} "
                f"actual_sha256={sha256(target.read_bytes())}"
            )

    if conflicts:
        print("TEMPLATE MATERIALIZATION: REVIEW")
        print("- 只读取并最小修正上面列出的既有冲突文件；脚本未覆盖它们")
    else:
        print("TEMPLATE MATERIALIZATION: PASS")
    return 0


def main() -> int:
    try:
        return materialize(parse_args())
    except (MaterializeError, OSError, UnicodeError) as exc:
        print("TEMPLATE MATERIALIZATION: FAIL")
        print(f"- {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
