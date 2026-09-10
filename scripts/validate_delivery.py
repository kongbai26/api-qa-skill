#!/usr/bin/env python3
"""Validate API-test deliverables without modifying the generated project.

The validator deliberately treats .env as opaque: it checks file metadata only
and never reads or prints its contents.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


COMMON_FILES = (
    "conftest.py",
    "utils/request_helper.py",
    "utils/report_generator.py",
    "utils/__init__.py",
    "pytest.ini",
    "requirements.txt",
    ".env",
    ".gitignore",
    "MEMORY.md",
)

NONEMPTY_FILES = (
    "conftest.py",
    "utils/request_helper.py",
    "utils/report_generator.py",
    "pytest.ini",
    "requirements.txt",
    ".env",
    ".gitignore",
    "MEMORY.md",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验 API 测试项目交付物")
    parser.add_argument("--project", required=True, help="测试项目绝对路径")
    parser.add_argument("--mode", required=True, choices=("full", "quick"))
    parser.add_argument("--os", dest="os_type", required=True,
                        choices=("Darwin", "Linux", "Windows"))
    parser.add_argument("--report", required=True,
                        choices=("official", "fallback"))
    parser.add_argument("--project-kind", required=True,
                        choices=("new", "existing"))
    return parser.parse_args()


def relative(project: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project))
    except ValueError:
        return str(path)


def check_python_syntax(project: Path, paths: list[Path], errors: list[str]) -> None:
    for path in paths:
        try:
            source = path.read_bytes()
            compile(source, str(path), "exec")
        except (OSError, SyntaxError, ValueError) as exc:
            errors.append(f"Python 语法无效: {relative(project, path)} ({exc})")


def main() -> int:
    args = parse_args()
    project = Path(args.project).expanduser().resolve()
    errors: list[str] = []

    if not project.is_dir():
        print(f"FAIL: 项目目录不存在: {project}")
        return 1

    for item in COMMON_FILES:
        path = project / item
        if not path.is_file():
            errors.append(f"缺少必需文件: {item}")

    for item in NONEMPTY_FILES:
        path = project / item
        if path.is_file() and path.stat().st_size == 0:
            errors.append(f"必需文件为空: {item}")

    gitignore = project / ".gitignore"
    if gitignore.is_file():
        ignored = {
            line.strip() for line in gitignore.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        if not ({".env", "/.env", ".env*"} & ignored):
            errors.append(".gitignore 未排除 .env")

    test_dir = project / "tests"
    test_files = sorted(
        path for path in test_dir.rglob("test_*.py")
        if path.is_file() and path.stat().st_size > 0
    ) if test_dir.is_dir() else []
    if not test_files:
        errors.append("tests/ 下没有非空的 test_*.py")

    result_files = sorted((project / "allure-results").glob("*-result.json"))
    if not result_files:
        errors.append("allure-results/ 下没有 *-result.json")
    else:
        for path in result_files:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("根节点不是对象")
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
                errors.append(f"Allure 结果无效: {relative(project, path)} ({exc})")

    official = project / "allure-report/index.html"
    fallback = project / "allure-report/report.html"
    selected, unexpected = (
        (official, fallback) if args.report == "official" else (fallback, official)
    )
    if not selected.is_file() or selected.stat().st_size == 0:
        errors.append(f"所选报告缺失或为空: {relative(project, selected)}")
    if unexpected.exists():
        errors.append(f"存在冲突的第二报告入口: {relative(project, unexpected)}")

    expected_runner = "run.bat" if args.os_type == "Windows" else "run.sh"
    other_runner = "run.sh" if expected_runner == "run.bat" else "run.bat"
    runner = project / expected_runner
    if not runner.is_file() or runner.stat().st_size == 0:
        errors.append(f"当前 OS 运行脚本缺失或为空: {expected_runner}")
    elif expected_runner == "run.sh" and not os.access(runner, os.X_OK):
        errors.append("run.sh 没有执行权限")
    else:
        try:
            runner_text = runner.read_text(encoding="ascii" if expected_runner == "run.bat" else "utf-8")
        except (OSError, UnicodeDecodeError):
            errors.append("run.bat 必须是纯 ASCII" if expected_runner == "run.bat" else "run.sh 必须是有效 UTF-8")
            runner_text = ""
        if runner_text:
            lowered = runner_text.lower()
            normalized = lowered.replace("\\", "/")
            required_fragments = (
                "pytest", "--clean-alluredir", "allure generate",
                "report_generator.py", "allure-report/index.html",
                "allure-report/report.html",
            )
            for fragment in required_fragments:
                if fragment not in normalized:
                    errors.append(f"{expected_runner} 缺少一键测试/单报告逻辑: {fragment}")
            if re.search(r"\ballure\s+(?:serve|open)\b", lowered):
                errors.append(f"{expected_runner} 含自动打开 Allure 的命令")
            if re.search(r"(?m)^\s*(?:open|xdg-open|start)\s+", lowered):
                errors.append(f"{expected_runner} 含自动打开报告的命令")
            if expected_runner == "run.bat" and "cd /d" not in lowered:
                errors.append("run.bat 必须用 cd /d 进入项目目录")
            if expected_runner == "run.sh" and 'cd "$(dirname "$0")"' not in runner_text:
                errors.append("run.sh 必须进入脚本所在项目目录")

    if args.project_kind == "new" and (project / other_runner).exists():
        errors.append(f"新项目不应同时生成另一平台脚本: {other_runner}")

    if args.mode == "full":
        test_doc = project / "docs/test_cases.md"
        if not test_doc.is_file() or test_doc.stat().st_size == 0:
            errors.append("完整流程缺少非空的 docs/test_cases.md")

    syntax_paths = [
        path for path in (
            project / "conftest.py",
            project / "utils/request_helper.py",
            project / "utils/report_generator.py",
            *test_files,
        ) if path.is_file()
    ]
    check_python_syntax(project, syntax_paths, errors)

    if errors:
        print("DELIVERY AUDIT: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("DELIVERY AUDIT: PASS")
    print(f"- mode={args.mode}, os={args.os_type}, report={args.report}")
    print(f"- tests={len(test_files)}, allure_results={len(result_files)}")
    print(f"- runner={expected_runner}, memory=MEMORY.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
