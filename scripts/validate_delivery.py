#!/usr/bin/env python3
"""Validate API QA deliverables without modifying the generated project.

The validator deliberately treats .env as opaque: it checks file metadata only
and never reads or prints its contents.
"""

from __future__ import annotations

import argparse
import ast
import base64
import binascii
from collections import Counter
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit


COMMON_FILES = (
    "conftest.py",
    "utils/contract_probe.py",
    "utils/request_helper.py",
    "utils/__init__.py",
    "pytest.ini",
    "requirements.txt",
    ".env",
    ".gitignore",
    "MEMORY.md",
)

NONEMPTY_FILES = (
    "conftest.py",
    "utils/contract_probe.py",
    "utils/request_helper.py",
    "pytest.ini",
    "requirements.txt",
    ".env",
    ".gitignore",
    "MEMORY.md",
)

MEMORY_KEYS = (
    "PROJECT_DIR",
    "PROJECT_KIND",
    "API_BASE_URL",
    "AUTH_MODE",
    "AUTH_NAME",
    "AUTH_SCHEME",
    "AUTH_SECRET_ENV",
    "PYTHON",
    "OS_TYPE",
    "ALLURE",
)

AUTH_MODES = {"none", "bearer", "header", "query", "cookie", "basic", "dynamic"}
HTTP_METHODS = "GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS"
HTTP_METHOD_SET = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
ENDPOINT_ROW = re.compile(
    rf"^\s*\|\s*({HTTP_METHODS})\s*\|\s*([^|]+?)\s*\|",
    re.IGNORECASE,
)
COUNT_ROW = re.compile(
    rf"^\s*\|\s*({HTTP_METHODS})\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|",
    re.IGNORECASE,
)
PLACEHOLDER = re.compile(r"<[^>\n]+>|待确认|(?:^|\W)(?:todo|tbd)(?:$|\W)", re.IGNORECASE)
VALID_ALLURE_STATUSES = {"passed", "failed", "broken", "skipped"}
HTTP_VERB_NAMES = {"get", "post", "put", "patch", "delete", "head", "options"}
CHINESE_TEXT = re.compile(r"[\u3400-\u9fff]")
CREDENTIAL_SKIP = re.compile(
    r"(?:"
    r"(?:认证|鉴权|凭据|token|api[_ -]?key|password|cookie).{0,50}"
    r"(?:未配置|未设置|缺失|无效|missing|not configured|unset|required)"
    r"|(?:missing|not configured|unset|required).{0,50}"
    r"(?:credential|token|api[_ -]?key|password|cookie)"
    r")",
    re.IGNORECASE,
)
DATE_TEXT = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
SECRET_KEY = re.compile(
    r"(?:authorization|api[_-]?key|access[_-]?token|refresh[_-]?token|token|password|passwd|secret|cookie|session[_-]?id)",
    re.IGNORECASE,
)
REPORT_TITLE = re.compile(r"<title\b[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
REPORT_SCAN_SUFFIXES = {".html", ".htm", ".md"}
REPORT_WORDS = {"report", "reports", "allure"}
TEST_CONTEXT_WORDS = {"api", "allure", "pytest", "test", "tests", "testing"}
REPORT_SCAN_EXCLUDED_PARTS = {
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "venv",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验 API 测试项目交付物")
    parser.add_argument("--project", required=True, help="测试项目绝对路径")
    parser.add_argument("--mode", choices=("full", "quick"))
    parser.add_argument("--os", dest="os_type",
                        choices=("Darwin", "Linux", "Windows"))
    parser.add_argument("--report", required=True,
                        choices=("official", "fallback"))
    parser.add_argument("--project-kind",
                        choices=("new", "existing"))
    parser.add_argument(
        "--report-artifacts-only",
        action="store_true",
        help="生成报告前只检查是否已有冲突报告；不要求其他交付物就绪",
    )
    args = parser.parse_args()
    if not args.report_artifacts_only:
        missing = [
            option
            for option, value in (
                ("--mode", args.mode),
                ("--os", args.os_type),
                ("--project-kind", args.project_kind),
            )
            if value is None
        ]
        if missing:
            parser.error("完整交付审计缺少参数: " + ", ".join(missing))
    return args


def detect_report_mode() -> str:
    """Return the currently executable report branch without changing it."""
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


def relative(project: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project))
    except ValueError:
        return str(path)


def is_below(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def is_official_allure_root(directory: Path) -> bool:
    """Recognize an Allure report by structure instead of its directory name."""
    return all(
        path.is_file()
        for path in (
            directory / "index.html",
            directory / "app.js",
            directory / "styles.css",
            directory / "widgets/summary.json",
        )
    )


def report_name_semantics(value: str) -> tuple[bool, bool]:
    """Return exact report/test signals without substring false positives."""
    lowered = value.casefold()
    words = set(re.findall(r"[a-z0-9]+", lowered))
    has_report = bool(words & REPORT_WORDS) or "报告" in lowered
    has_test_context = bool(words & TEST_CONTEXT_WORDS) or "测试" in lowered
    return has_report, has_test_context


def html_declares_test_report(path: Path) -> bool:
    """Recognize standalone test-report HTML without depending on an old path."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as stream:
            head = stream.read(128 * 1024)
    except OSError:
        return False
    match = REPORT_TITLE.search(head)
    if not match:
        return False
    title = re.sub(r"\s+", " ", match.group(1)).strip()
    has_report, has_test_context = report_name_semantics(title)
    return has_report and has_test_context


def report_scan_files(project: Path) -> list[Path]:
    """Enumerate possible entry files while pruning caches and dependencies."""
    files: list[Path] = []
    for directory, child_dirs, child_files in os.walk(project, followlinks=False):
        child_dirs[:] = [
            name for name in child_dirs
            if name.casefold() not in REPORT_SCAN_EXCLUDED_PARTS
            and not (Path(directory) / name).is_symlink()
        ]
        for name in child_files:
            path = Path(directory) / name
            if path.suffix.casefold() in REPORT_SCAN_SUFFIXES:
                files.append(path)
    return files


def discover_report_entries(project: Path) -> list[Path]:
    """Return report entry candidates using structure and semantics, not aliases."""
    files = report_scan_files(project)

    official_roots = {
        path.parent
        for path in files
        if path.name.lower() == "index.html"
        and not path.is_symlink()
        and is_official_allure_root(path.parent)
    }
    candidates: set[Path] = {root / "index.html" for root in official_roots}

    for path in files:
        containing_roots = [root for root in official_roots if is_below(path, root)]
        if containing_roots:
            # Allure can contain nested HTML resources such as export/mail.html.
            # A second HTML directly beside index.html is another entry point;
            # Allure itself does not emit Markdown report entries.
            markdown_report = (
                path.suffix.casefold() == ".md"
                and all(report_name_semantics(path.stem))
            )
            if (
                markdown_report
                or (
                    path.suffix.casefold() in {".html", ".htm"}
                    and path.name.casefold() != "index.html"
                    and any(path.parent == root for root in containing_roots)
                )
            ):
                candidates.add(path)
            continue
        rel = path.relative_to(project)
        stem = path.stem
        parent_parts = rel.parts[:-1]
        has_report_name, has_test_context = report_name_semantics(stem)
        report_named = (
            has_report_name
            if path.suffix.casefold() in {".html", ".htm"}
            else has_report_name and has_test_context
        )
        report_index = (
            path.name.casefold() == "index.html"
            and any(report_name_semantics(part)[0] for part in parent_parts)
        )
        report_titled = (
            path.suffix.casefold() in {".html", ".htm"}
            and not path.is_symlink()
            and html_declares_test_report(path)
        )
        if report_named or report_index or report_titled:
            candidates.add(path)
    return sorted(candidates, key=lambda path: relative(project, path))


def conflicting_report_entries(project: Path, report_mode: str) -> list[Path]:
    selected = project / "allure-report" / (
        "index.html" if report_mode == "official" else "report.html"
    )
    return [
        path for path in discover_report_entries(project)
        if path != selected
    ]


def print_report_artifact_audit(project: Path, report_mode: str) -> int:
    conflicts = conflicting_report_entries(project, report_mode)
    if conflicts:
        print("REPORT ARTIFACT AUDIT: BLOCKED")
        for path in conflicts:
            print(f"- 冲突报告入口（已保留）: {relative(project, path)}")
        print("- 未删除或覆盖任何文件；请让用户明确处理后再生成报告")
        return 2
    selected = "allure-report/index.html" if report_mode == "official" else "allure-report/report.html"
    print("REPORT ARTIFACT AUDIT: PASS")
    print(f"- selected={selected}")
    return 0


def strip_markdown(value: str) -> str:
    value = value.strip().replace("**", "")
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "`\"'":
        value = value[1:-1].strip()
    return value


def parse_memory_config(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    keys = "|".join(re.escape(key) for key in MEMORY_KEYS)
    colon_pattern = re.compile(
        rf"^\s*(?:[-*]\s*)?({keys})\s*[:：]\s*(.*?)\s*$",
        re.IGNORECASE,
    )
    table_pattern = re.compile(
        rf"^\s*\|\s*({keys})\s*\|\s*([^|]*)\|",
        re.IGNORECASE,
    )
    for line in text.splitlines():
        match = colon_pattern.match(line) or table_pattern.match(line)
        if match:
            values[match.group(1).upper()] = strip_markdown(match.group(2))
    return values


def markdown_sections(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    headings: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^\s*#{1,6}\s+(.+?)\s*$", line)
        if match:
            headings.append((index, strip_markdown(match.group(1))))

    sections: list[tuple[str, str]] = []
    for position, (start, title) in enumerate(headings):
        end = headings[position + 1][0] if position + 1 < len(headings) else len(lines)
        sections.append((title, "\n".join(lines[start + 1:end])))
    return sections


def last_section(sections: list[tuple[str, str]], keyword: str) -> str:
    matches = [body for title, body in sections if keyword in title]
    return matches[-1] if matches else ""


def substantive_markdown(text: str) -> bool:
    for raw in text.splitlines():
        line = strip_markdown(raw).strip()
        if not line or re.fullmatch(r"[|:\-\s]+", line):
            continue
        if PLACEHOLDER.search(line):
            continue
        return True
    return False


def field_has_content(text: str, label: str) -> bool:
    escaped = re.escape(label)
    patterns = (
        rf"(?mi)^\s*[-*]?\s*\**{escaped}\**\s*[:：]\s*(.+?)\s*$",
        rf"(?mi)^\s*\|\s*\**{escaped}\**\s*\|\s*([^|]+?)\s*\|",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            value = strip_markdown(match.group(1))
            if value and not PLACEHOLDER.search(value) and value not in {"-", "—", "/"}:
                return True
    return False


def validate_stage_records(
    sections: list[tuple[str, str]], mode: str, errors: list[str]
) -> None:
    expected = (
        [f"阶段{number}" for number in "一二三四五"]
        if mode == "full" else ["快速阶段一", "快速阶段二"]
    )
    for stage in expected:
        matches = [
            (title, body) for title, body in sections
            if stage in title and DATE_TEXT.search(title)
        ]
        if not matches:
            errors.append(f"MEMORY.md 缺少带日期的阶段记录: {stage}")
            continue
        _, body = matches[-1]
        for field in ("完成", "发现", "决策"):
            if not field_has_content(body, field):
                errors.append(f"MEMORY.md 的 {stage} 记录缺少非空字段: {field}")


def potential_secret_lines(text: str) -> list[int]:
    findings: list[int] = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or "REDACTED" in line.upper():
            continue
        match = re.search(
            r"(?i)([A-Za-z_][A-Za-z0-9_-]*(?:authorization|api[_-]?key|token|password|passwd|secret|cookie|session[_-]?id)[A-Za-z0-9_-]*)\s*[:=]\s*([^\s|,;]+)",
            line,
        )
        if not match:
            match = re.search(r"(?i)\bAuthorization\s*:\s*(.+)$", line)
            if not match:
                continue
            key, value = "Authorization", match.group(1).strip()
        else:
            key, value = match.group(1), strip_markdown(match.group(2))
        if key.upper().endswith("_ENV"):
            continue
        if not value or value.lower() in {"none", "null", "empty", "未配置", "无"}:
            continue
        if re.fullmatch(r"[A-Z][A-Z0-9_]*", value):
            continue
        if PLACEHOLDER.search(value) or value.startswith("***"):
            continue
        findings.append(number)
    return findings


def scan_text_for_secrets(label: str, text: str, errors: list[str]) -> None:
    lines = potential_secret_lines(text)
    if lines:
        errors.append(f"{label} 疑似包含凭据值（行 {', '.join(map(str, lines[:5]))}）")


def scalar_looks_secret(value: object) -> bool:
    if value is None:
        return False
    rendered = strip_markdown(str(value)).strip()
    if not rendered or rendered.lower() in {"none", "null", "empty", "未配置", "无"}:
        return False
    if "REDACTED" in rendered.upper() or rendered.startswith("***"):
        return False
    if PLACEHOLDER.search(rendered) or re.fullmatch(r"[A-Z][A-Z0-9_]*", rendered):
        return False
    return True


def payload_secret_paths(value: object, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        parameter_name = str(value.get("name", ""))
        if SECRET_KEY.search(parameter_name) and scalar_looks_secret(value.get("value")):
            findings.append(f"{path}.value")
        for key, item in value.items():
            child_path = f"{path}.{key}"
            if SECRET_KEY.search(str(key)) and not isinstance(item, (dict, list)):
                if scalar_looks_secret(item):
                    findings.append(child_path)
                continue
            findings.extend(payload_secret_paths(item, child_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            findings.extend(payload_secret_paths(item, f"{path}[{index}]"))
    elif isinstance(value, str) and potential_secret_lines(value):
        findings.append(path)
    return findings


def validate_memory(project: Path, args: argparse.Namespace, errors: list[str]) -> tuple[str, dict[str, str], set[tuple[str, str]], dict[tuple[str, str], int]]:
    path = project / "MEMORY.md"
    if not path.is_file() or path.stat().st_size == 0:
        return "", {}, set(), {}

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"MEMORY.md 无法按 UTF-8 读取: {exc}")
        return "", {}, set(), {}

    scan_text_for_secrets("MEMORY.md", text, errors)

    values = parse_memory_config(text)
    for key in MEMORY_KEYS:
        if key not in values:
            errors.append(f"MEMORY.md 项目配置缺少字段: {key}")
        elif PLACEHOLDER.search(values[key]):
            errors.append(f"MEMORY.md 项目配置未确认: {key}")
        elif key not in {"AUTH_NAME", "AUTH_SCHEME", "AUTH_SECRET_ENV"} and not values[key]:
            errors.append(f"MEMORY.md 项目配置未确认: {key}")

    configured_dir = values.get("PROJECT_DIR", "")
    if configured_dir and not PLACEHOLDER.search(configured_dir):
        memory_project = Path(configured_dir).expanduser()
        if not memory_project.is_absolute() or memory_project.resolve() != project:
            errors.append("MEMORY.md 的 PROJECT_DIR 不是当前项目绝对路径")

    if values.get("PROJECT_KIND", "").lower() != args.project_kind:
        errors.append("MEMORY.md 的 PROJECT_KIND 与审计参数不一致")

    base_url = values.get("API_BASE_URL", "")
    if base_url and not PLACEHOLDER.search(base_url):
        parsed_url = urlsplit(base_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            errors.append("MEMORY.md 的 API_BASE_URL 不是完整的 HTTP(S) 地址")
        elif parsed_url.username or parsed_url.password:
            errors.append("MEMORY.md 的 API_BASE_URL 不得包含用户名或密码")

    auth_mode = values.get("AUTH_MODE", "").lower()
    if auth_mode and auth_mode not in AUTH_MODES:
        errors.append("MEMORY.md 的 AUTH_MODE 不受支持")
    if auth_mode in {"header", "query", "cookie"} and not values.get("AUTH_NAME", ""):
        errors.append(f"AUTH_MODE={auth_mode} 时 MEMORY.md 必须记录 AUTH_NAME")
    if auth_mode in AUTH_MODES - {"none"} and not values.get("AUTH_SECRET_ENV", ""):
        errors.append("认证 API 必须在 MEMORY.md 记录凭据环境变量名")

    if values.get("OS_TYPE", "") != args.os_type:
        errors.append("MEMORY.md 的 OS_TYPE 与审计参数不一致")
    expected_allure = "有" if args.report == "official" else "无"
    if values.get("ALLURE", "") != expected_allure:
        errors.append("MEMORY.md 的 ALLURE 与报告分支不一致")

    sections = markdown_sections(text)
    required_sections = ["项目配置", "接口清单", "差异", "用例计数", "修复记录"]
    required_sections.extend(
        ["覆盖矩阵", "最终结果", "交付物", "遗留"]
        if args.mode == "full" else ["结果统计"]
    )
    for keyword in required_sections:
        matching = [body for title, body in sections if keyword in title]
        if not matching:
            errors.append(f"MEMORY.md 缺少章节: {keyword}")
        elif not substantive_markdown(matching[-1]):
            errors.append(f"MEMORY.md 章节没有非空产出: {keyword}")

    validate_stage_records(sections, args.mode, errors)

    interface_section = last_section(sections, "接口清单")
    endpoints = {
        (match.group(1).upper(), strip_markdown(match.group(2)))
        for line in interface_section.splitlines()
        if (match := ENDPOINT_ROW.match(line))
    }
    if not endpoints:
        errors.append("MEMORY.md 的接口清单缺少“方法 | 路径”表格行")
    elif args.mode == "quick" and len(endpoints) > 5:
        errors.append(f"快速流程接口数超过 5: {len(endpoints)}")

    count_section = last_section(sections, "用例计数")
    endpoint_counts: dict[tuple[str, str], int] = {}
    for line in count_section.splitlines():
        match = COUNT_ROW.match(line)
        if not match:
            continue
        endpoint = (match.group(1).upper(), strip_markdown(match.group(2)))
        endpoint_counts[endpoint] = endpoint_counts.get(endpoint, 0) + int(match.group(3))
    if not endpoint_counts:
        errors.append("MEMORY.md 的用例计数缺少“方法 | 路径 | 展开后 node 数”表格行")
    elif endpoints and set(endpoint_counts) != endpoints:
        missing = sorted(endpoints - set(endpoint_counts))
        extra = sorted(set(endpoint_counts) - endpoints)
        if missing:
            errors.append(f"用例计数缺少接口: {missing}")
        if extra:
            errors.append(f"用例计数包含接口清单外项目: {extra}")

    for (method, endpoint), count in sorted(endpoint_counts.items()):
        if args.mode == "quick" and not 3 <= count <= 5:
            errors.append(f"快速流程用例数不在 3-5: {method} {endpoint} = {count}")
        if args.mode == "full" and method == "GET" and count < 8:
            errors.append(f"完整流程 GET 用例不足 8: {endpoint} = {count}")
        if args.mode == "full" and method == "POST" and count < 15:
            errors.append(f"完整流程 POST 用例不足 15: {endpoint} = {count}")

    if args.mode == "full" and endpoint_counts:
        average = sum(endpoint_counts.values()) / len(endpoint_counts)
        if average < 15:
            shortfall = last_section(sections, "用例不足说明")
            if not substantive_markdown(shortfall):
                errors.append(f"完整流程平均用例数低于 15 且没有有效“用例不足说明”: {average:.1f}")
            else:
                for endpoint, count in sorted(endpoint_counts.items()):
                    if count < 15 and not document_mentions_endpoint(shortfall, endpoint):
                        errors.append(
                            "用例不足说明未逐接口记录理由: "
                            f"{endpoint[0]} {endpoint[1]} = {count}"
                        )

    return text, values, endpoints, endpoint_counts


def collect_pytest_nodes(project: Path, errors: list[str]) -> tuple[int, list[str]] | None:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment.pop("PYTEST_ADDOPTS", None)
    command = [
        sys.executable, "-m", "pytest", "tests", "--collect-only", "-q",
        "-p", "no:cacheprovider", "-o", "addopts=",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=project,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        errors.append(f"pytest collect-only 执行失败: {exc}")
        return None
    if completed.returncode != 0:
        errors.append(f"pytest collect-only 未通过（退出码 {completed.returncode}）")
        return None
    output = f"{completed.stdout}\n{completed.stderr}"
    matches = re.findall(r"(\d+)\s+(?:tests?|items?)\s+collected", output, re.IGNORECASE)
    if not matches:
        errors.append("无法从 pytest collect-only 输出取得实际用例数")
        return None
    collected_count = int(matches[-1])
    nodes = [
        line.strip() for line in output.splitlines()
        if re.match(r"^tests/.+?\.py(?:::.+)+$", line.strip())
    ]
    if len(nodes) != collected_count:
        errors.append(
            "无法将 pytest collect-only 的 node 与实际用例数一一对应: "
            f"nodes={len(nodes)}, collected={collected_count}"
        )
    return collected_count, nodes


def memory_has_result_count(section: str, labels: tuple[str, ...], value: int) -> bool:
    plain = section.replace("**", "").replace("`", "")
    label_pattern = "|".join(re.escape(label) for label in labels)
    return bool(re.search(
        rf"(?:{label_pattern})\s*(?:\|\s*|[:：=]\s*){value}(?!\d)",
        plain,
        re.IGNORECASE,
    ))


def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    if isinstance(node, ast.Call):
        called = dotted_name(node.func)
        return f"{called}()" if called else ""
    return ""


def static_strings(node: ast.AST) -> str:
    return "".join(
        child.value
        for child in ast.walk(node)
        if isinstance(child, ast.Constant) and isinstance(child.value, str)
    )


def static_string(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def static_path_pattern(
    node: ast.AST | None, string_constants: dict[str, str] | None = None
) -> str | None:
    """Render a request path expression without evaluating runtime values."""
    if node is None:
        return None
    literal = static_string(node)
    if literal is not None:
        return literal
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif (
                isinstance(value, ast.FormattedValue)
                and isinstance(value.value, ast.Name)
                and string_constants
                and value.value.id in string_constants
            ):
                parts.append(string_constants[value.value.id])
            elif isinstance(value, ast.FormattedValue):
                parts.append("{}")
            else:
                return None
        return "".join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = static_path_pattern(node.left, string_constants)
        right = static_path_pattern(node.right, string_constants)
        if left is None or right is None:
            return None
        return left + right
    if isinstance(node, ast.Name):
        return (string_constants or {}).get(node.id, "{}")
    if isinstance(node, (ast.Attribute, ast.Subscript)):
        return "{}"
    return None


def call_argument(call: ast.Call, position: int, *names: str) -> ast.AST | None:
    for keyword in call.keywords:
        if keyword.arg in names:
            return keyword.value
    return call.args[position] if len(call.args) > position else None


def has_real_assertion(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Assert):
            continue
        try:
            ast.literal_eval(child.test)
        except (ValueError, TypeError):
            return True
        # `assert True`, `assert 1` and other constant-only assertions do not
        # evaluate an API observation and therefore are still empty shells.
    assertion_names = {
        "pytest.raises", "pytest.fail", "assertEqual", "assertNotEqual",
        "assertTrue", "assertFalse", "assertIn", "assertNotIn",
        "assertIs", "assertIsNot", "assertIsNone", "assertIsNotNone",
        "assertGreater", "assertGreaterEqual", "assertLess", "assertLessEqual",
        "assertRegex", "assertRaises",
    }
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        name = dotted_name(child.func)
        if name in assertion_names or name.split(".")[-1] in assertion_names:
            return True
    return False


def network_mock_reason(node: ast.AST) -> str | None:
    argument_names = {
        arg.arg.lower()
        for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
    } if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else set()
    if argument_names & {"requests_mock", "httpx_mock", "respx_mock"}:
        return "使用网络 mock fixture"

    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        called = dotted_name(child.func).lower()
        strings = static_strings(child).lower()
        if called.startswith(("responses.", "respx.", "requests_mock.", "vcr.")):
            return f"使用网络拦截器 {called}"
        if called.endswith(("patch", "patch.object")) and any(
            marker in strings
            for marker in ("requests", "httpx", "allure_request", "authsession", ".request")
        ):
            return "patch 了 HTTP 请求链路"
        if called.endswith("monkeypatch.setattr") and any(
            marker in strings
            for marker in ("requests", "httpx", "allure_request", "authsession", "request")
        ):
            return "monkeypatch 了 HTTP 请求链路"
    return None


def endpoint_marker(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    location: str,
    errors: list[str],
) -> tuple[str, str] | None:
    markers = [
        decorator for decorator in node.decorator_list
        if isinstance(decorator, ast.Call)
        and dotted_name(decorator.func) == "pytest.mark.api_endpoint"
    ]
    if len(markers) != 1:
        errors.append(f"测试必须恰好有一个 api_endpoint 标记: {location}")
        return None

    marker = markers[0]
    keyword_values = {item.arg: item.value for item in marker.keywords if item.arg}
    method_node = keyword_values.get("method") or (marker.args[0] if marker.args else None)
    path_node = keyword_values.get("path") or (marker.args[1] if len(marker.args) > 1 else None)
    method = static_string(method_node)
    path = static_string(path_node)
    if not method or method.upper() not in HTTP_METHOD_SET or not path or not path.startswith("/"):
        errors.append(f"api_endpoint 标记必须提供静态方法和 / 开头路径: {location}")
        return None
    return method.upper(), path


def contract_path_matches(contract_path: str, observed_path: str) -> bool:
    observed = observed_path.split("?", 1)[0]
    pattern = re.escape(contract_path)
    pattern = re.sub(r"\\\{[^{}]+\\\}", r"[^/]+", pattern)
    return bool(re.fullmatch(pattern, observed))


def static_request_endpoint(
    call: ast.Call,
    *,
    is_allure_request: bool,
    method: str,
    string_constants: dict[str, str] | None = None,
) -> tuple[str, str] | None:
    if is_allure_request:
        request_method = static_string(call_argument(call, 0, "method"))
        raw_path = static_path_pattern(
            call_argument(call, 1, "url", "path"), string_constants
        )
        if not request_method or request_method.upper() not in HTTP_METHOD_SET or not raw_path:
            return None
        parsed = urlsplit(raw_path)
        observed_path = parsed.path if parsed.scheme else raw_path.split("?", 1)[0]
        if observed_path.startswith("{}/"):
            observed_path = observed_path[2:]
        return request_method.upper(), observed_path

    raw_path = static_path_pattern(
        call_argument(call, 0, "path", "url"), string_constants
    )
    if method.upper() not in HTTP_METHOD_SET or not raw_path:
        return None
    return method.upper(), raw_path.split("?", 1)[0]


def check_test_semantics(
    project: Path,
    paths: list[Path],
    errors: list[str],
) -> dict[str, tuple[str, str] | None]:
    declarations: dict[str, tuple[str, str] | None] = {}
    for path in paths:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, UnicodeError, SyntaxError):
            continue  # 读取或语法错误由 check_python_syntax 统一报告。

        request_module_aliases = {"requests", "httpx"}
        request_function_aliases: set[str] = set()
        request_session_names: set[str] = set()
        unified_function_aliases = {"allure_request"}
        string_constants: dict[str, str] = {}
        for child in tree.body:
            if not isinstance(child, (ast.Assign, ast.AnnAssign)):
                continue
            literal = static_string(child.value)
            if literal is None:
                continue
            targets = child.targets if isinstance(child, ast.Assign) else [child.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    string_constants[target.id] = literal
        for child in ast.walk(tree):
            if isinstance(child, ast.Import):
                for alias in child.names:
                    if alias.name in {"requests", "httpx"}:
                        request_module_aliases.add((alias.asname or alias.name).lower())
            elif isinstance(child, ast.ImportFrom):
                module = child.module or ""
                for alias in child.names:
                    local_name = (alias.asname or alias.name).lower()
                    if module.startswith(("requests", "httpx")) and alias.name in HTTP_VERB_NAMES | {"request"}:
                        request_function_aliases.add(local_name)
                    if module.endswith("request_helper") and alias.name == "allure_request":
                        unified_function_aliases.add(local_name)
            elif isinstance(child, (ast.Assign, ast.AnnAssign)):
                value = child.value
                if not isinstance(value, ast.Call):
                    continue
                called = dotted_name(value.func).lower().split(".")
                if len(called) != 2 or called[0] not in request_module_aliases or called[1] not in {"session", "client"}:
                    continue
                targets = child.targets if isinstance(child, ast.Assign) else [child.target]
                request_session_names.update(
                    dotted_name(target).lower() for target in targets if dotted_name(target)
                )

        for child in tree.body:
            if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) or child.name != "auth_session":
                continue
            if any("fixture" in dotted_name(item) for item in child.decorator_list):
                errors.append(
                    f"测试文件不得定义同名 auth_session fixture: {relative(project, path)}:{child.lineno}"
                )

        def check_test(
            node: ast.FunctionDef | ast.AsyncFunctionDef,
            class_names: tuple[str, ...],
        ) -> None:
            rel_path = relative(project, path).replace(os.sep, "/")
            declaration_key = "::".join((rel_path, *class_names, node.name))
            location = f"{rel_path}:{node.lineno}"
            marker = endpoint_marker(node, location, errors)
            declarations[declaration_key] = marker

            if not has_real_assertion(node):
                errors.append(f"测试缺少真实断言或异常判断: {location} {node.name}")
            mock_reason = network_mock_reason(node)
            if mock_reason:
                errors.append(f"测试不得用 mock 替代目标 API: {location} ({mock_reason})")

            docstring = ast.get_docstring(node, clean=False) or ""
            if not docstring or not CHINESE_TEXT.search(docstring):
                errors.append(f"测试缺少中文 docstring: {location} {node.name}")

            title_call = next(
                (
                    decorator for decorator in node.decorator_list
                    if isinstance(decorator, ast.Call)
                    and dotted_name(decorator.func) == "allure.title"
                ),
                None,
            )
            if title_call is None or not title_call.args or not CHINESE_TEXT.search(
                static_strings(title_call.args[0])
            ):
                errors.append(f"测试缺少中文 allure.title: {location} {node.name}")

            unified_request_count = 0
            marker_match_count = 0
            for call in (child for child in ast.walk(node) if isinstance(child, ast.Call)):
                name = dotted_name(call.func)
                lowered = name.lower()
                parts = lowered.split(".")
                method = parts[-1] if parts else ""
                prefix = ".".join(parts[:-1])

                direct_requests_call = (
                    (parts and parts[0] in request_module_aliases and method in HTTP_VERB_NAMES | {"request"})
                    or lowered in request_function_aliases
                    or (prefix in request_session_names and method in HTTP_VERB_NAMES | {"request"})
                )
                if direct_requests_call:
                    errors.append(f"测试直接调用 requests/httpx，必须使用统一请求封装: {location}")
                    continue

                is_allure_request = method == "allure_request" or lowered in unified_function_aliases
                is_auth_session_call = (
                    method in HTTP_VERB_NAMES
                    and any(marker in prefix for marker in ("auth", "session"))
                )
                if not (is_allure_request or is_auth_session_call):
                    continue

                unified_request_count += 1

                expected = next(
                    (keyword.value for keyword in call.keywords if keyword.arg == "expected"),
                    None,
                )
                if expected is None:
                    errors.append(f"HTTP 调用缺少 expected 参数: {location}")
                elif isinstance(expected, (ast.Constant, ast.JoinedStr)) and not CHINESE_TEXT.search(
                    static_strings(expected)
                ):
                    errors.append(f"HTTP 调用的 expected 不是中文预期: {location}")

                observed = static_request_endpoint(
                    call,
                    is_allure_request=is_allure_request,
                    method=method,
                    string_constants=string_constants,
                )
                if marker and observed:
                    observed_method, observed_path = observed
                    if observed_method == marker[0] and contract_path_matches(marker[1], observed_path):
                        marker_match_count += 1

            if unified_request_count == 0:
                errors.append(f"测试没有调用统一 HTTP 请求封装: {location} {node.name}")
            elif marker and marker_match_count == 0:
                errors.append(f"没有统一 HTTP 请求可与 api_endpoint 标记核对: {location} {node.name}")

        def visit_statements(statements: list[ast.stmt], class_names: tuple[str, ...]) -> None:
            for child in statements:
                if isinstance(child, ast.ClassDef):
                    visit_statements(child.body, (*class_names, child.name))
                elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and child.name.startswith("test_"):
                    check_test(child, class_names)

        visit_statements(tree.body, ())

    return declarations


def collected_declaration_key(node_id: str) -> str:
    parts = node_id.split("::")
    if len(parts) < 2:
        return node_id
    parts[-1] = parts[-1].split("[", 1)[0]
    return "::".join(parts)


def validate_endpoint_mapping(
    declarations: dict[str, tuple[str, str] | None],
    collected_nodes: list[str],
    endpoints: set[tuple[str, str]],
    endpoint_counts: dict[tuple[str, str], int],
    errors: list[str],
) -> None:
    actual_counts: Counter[tuple[str, str]] = Counter()
    for node_id in collected_nodes:
        key = collected_declaration_key(node_id)
        if key not in declarations:
            errors.append(f"pytest 收集的测试没有可审计声明: {node_id}")
            continue
        endpoint = declarations[key]
        if endpoint is None:
            continue
        if endpoint not in endpoints:
            errors.append(f"测试标记引用接口清单外接口: {node_id} -> {endpoint[0]} {endpoint[1]}")
            continue
        actual_counts[endpoint] += 1

    if endpoints and set(actual_counts) != endpoints:
        missing = sorted(endpoints - set(actual_counts))
        extra = sorted(set(actual_counts) - endpoints)
        if missing:
            errors.append(f"测试没有实际归属到接口: {missing}")
        if extra:
            errors.append(f"测试标记包含接口清单外项目: {extra}")

    for endpoint, documented_count in sorted(endpoint_counts.items()):
        actual_count = actual_counts.get(endpoint, 0)
        if actual_count != documented_count:
            errors.append(
                "MEMORY.md 的接口用例数与 pytest 实际 node 归属不一致: "
                f"{endpoint[0]} {endpoint[1]} = {documented_count}, 实际 {actual_count}"
            )


def document_mentions_endpoint(text: str, endpoint: tuple[str, str]) -> bool:
    method, path = endpoint
    normalized = text.replace("`", "").replace("**", "")
    if re.search(re.escape(f"{method} {path}"), normalized, re.IGNORECASE):
        return True
    return bool(re.search(
        rf"\|\s*{re.escape(method)}\s*\|\s*{re.escape(path)}\s*\|",
        normalized,
        re.IGNORECASE,
    ))


def markdown_case_blocks(text: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    starts: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = re.match(r"^\s*###\s+(.+?)\s*$", line)
        if match:
            starts.append((index, strip_markdown(match.group(1))))
    blocks: list[tuple[str, str]] = []
    for position, (start, title) in enumerate(starts):
        end = starts[position + 1][0] if position + 1 < len(starts) else len(lines)
        body = "\n".join(lines[start + 1:end])
        if re.search(r"(?i)(?:^|\b)TC[-_\s]?[A-Z0-9]", title) or re.search(
            r"(?mi)^\s*(?:\|\s*)?(?:[-*]\s*)?\**用例ID\**\s*[:：|]", body
        ):
            blocks.append((title, body))
    return blocks


def validate_test_document(
    project: Path,
    endpoints: set[tuple[str, str]],
    declaration_count: int,
    errors: list[str],
) -> None:
    path = project / "docs/test_cases.md"
    if not path.is_file() or path.stat().st_size == 0:
        errors.append("完整流程缺少非空的 docs/test_cases.md")
        return
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"docs/test_cases.md 无法按 UTF-8 读取: {exc}")
        return

    scan_text_for_secrets("docs/test_cases.md", text, errors)

    for required in ("系统简介", "核心业务规则"):
        if required not in text:
            errors.append(f"docs/test_cases.md 缺少必要内容: {required}")

    blocks = markdown_case_blocks(text)
    if not blocks:
        errors.append("docs/test_cases.md 没有以 ### 开始的用例块")
    if declaration_count and len(blocks) < declaration_count:
        errors.append(
            "docs/test_cases.md 的用例块少于测试函数声明数: "
            f"{len(blocks)} < {declaration_count}"
        )
    for title, body in blocks:
        label = f"docs/test_cases.md 用例“{title}”"
        for required in ("用例ID", "接口", "接口用途", "前置条件", "测试步骤", "预期结果"):
            if not field_has_content(body, required):
                errors.append(f"{label} 缺少非空字段: {required}")
        if not (field_has_content(body, "请求参数") or field_has_content(body, "请求体")):
            errors.append(f"{label} 缺少非空字段: 请求参数或请求体")
    for endpoint in sorted(endpoints):
        if not any(document_mentions_endpoint(body, endpoint) for _, body in blocks):
            errors.append(f"docs/test_cases.md 未覆盖接口: {endpoint[0]} {endpoint[1]}")


def check_python_syntax(project: Path, paths: list[Path], errors: list[str]) -> None:
    for path in paths:
        try:
            source = path.read_bytes()
            compile(source, str(path), "exec")
        except (OSError, SyntaxError, ValueError) as exc:
            errors.append(f"Python 语法无效: {relative(project, path)} ({exc})")


def validate_core_contract(project: Path, errors: list[str]) -> None:
    def content(relative_path: str) -> str:
        path = project / relative_path
        if not path.is_file():
            return ""
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return ""

    requirements = content("requirements.txt").lower()
    for package in ("pytest", "allure-pytest", "requests", "python-dotenv"):
        if not re.search(rf"(?m)^\s*{re.escape(package)}(?:\s|[<>=!~]|$)", requirements):
            errors.append(f"requirements.txt 缺少核心依赖: {package}")

    pytest_ini = content("pytest.ini")
    for marker in ("need_auth", "smoke", "regression", "api_endpoint"):
        if not re.search(rf"(?mi)^\s*{re.escape(marker)}\s*(?:\(|:)", pytest_ini):
            errors.append(f"pytest.ini 缺少 marker: {marker}")
    for setting in ("testpaths", "python_files", "alluredir"):
        if setting not in pytest_ini:
            errors.append(f"pytest.ini 缺少核心配置: {setting}")

    conftest = content("conftest.py")
    for fragment, label in (
        ("load_dotenv", "加载项目 .env"),
        ("AuthSession", "统一认证会话"),
        ("def auth_session", "auth_session fixture"),
        ("API_AUTH_MODE", "认证模式"),
    ):
        if fragment not in conftest:
            errors.append(f"conftest.py 缺少核心能力: {label}")

    helper_path = project / "utils/request_helper.py"
    helper = content("utils/request_helper.py")
    try:
        helper_tree = ast.parse(helper, filename=str(helper_path)) if helper else None
    except SyntaxError:
        helper_tree = None
    functions = {
        node.name: node for node in ast.walk(helper_tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    } if helper_tree else {}
    classes = {
        node.name: node for node in ast.walk(helper_tree) if isinstance(node, ast.ClassDef)
    } if helper_tree else {}
    allure_function = functions.get("allure_request")
    if allure_function is None:
        errors.append("utils/request_helper.py 缺少 allure_request")
    elif not any(
        isinstance(node, ast.Call) and dotted_name(node.func).lower().endswith(".request")
        for node in ast.walk(allure_function)
    ):
        errors.append("allure_request 没有调用真实 HTTP transport.request")
    auth_class = classes.get("AuthSession")
    auth_methods = {
        node.name for node in auth_class.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    } if auth_class else set()
    for method in sorted(HTTP_VERB_NAMES):
        if method not in auth_methods:
            errors.append(f"AuthSession 缺少方法: {method}")
    for fragment, label in (("_sanitize", "脱敏"), ("allure.attach", "Allure 请求响应附件")):
        if fragment not in helper:
            errors.append(f"utils/request_helper.py 缺少核心能力: {label}")

    probe = content("utils/contract_probe.py")
    for fragment, label in (
        ("load_dotenv", "加载项目 .env"),
        ("AuthSession", "统一请求会话"),
        ("HEAD", "HEAD 探测"),
        ("OPTIONS", "OPTIONS 探测"),
        ("--params-file", "跨平台参数文件"),
        ("--json-body-file", "跨平台请求体文件"),
    ):
        if fragment not in probe:
            errors.append(f"utils/contract_probe.py 缺少核心能力: {label}")


def collected_allure_name(node_id: str) -> str:
    parts = collected_declaration_key(node_id).replace("\\", "/").split("::")
    module = parts[0]
    if module.endswith(".py"):
        module = module[:-3]
    module = module.strip("/").replace("/", ".")
    function = parts[-1]
    owner = ".".join((module, *parts[1:-1]))
    return f"{owner}#{function}"


def iter_allure_nodes(items: object):
    if not isinstance(items, list):
        return
    for item in items:
        if not isinstance(item, dict):
            continue
        yield item
        yield from iter_allure_nodes(item.get("steps"))


def validate_result_evidence(
    project: Path, result_path: Path, payload: dict, errors: list[str]
) -> None:
    nodes = list(iter_allure_nodes(payload.get("steps")))
    step_names = [str(node.get("name", "")) for node in nodes]
    attachment_nodes: list[dict] = []
    for node in nodes:
        attachments = node.get("attachments", [])
        if isinstance(attachments, list):
            attachment_nodes.extend(item for item in attachments if isinstance(item, dict))
    top = payload.get("attachments", [])
    if isinstance(top, list):
        attachment_nodes.extend(item for item in top if isinstance(item, dict))
    attachment_names = [str(item.get("name", "")) for item in attachment_nodes]

    label = relative(project, result_path)
    if not any(name.startswith("请求 #") for name in step_names):
        errors.append(f"Allure 结果缺少统一请求步骤: {label}")
    if not any(name.startswith("响应 #") for name in step_names):
        errors.append(f"Allure 结果缺少统一响应步骤: {label}")
    for required in ("📤 请求", "📋 预期", "📥 响应"):
        if required not in attachment_names:
            errors.append(f"Allure 结果缺少附件“{required}”: {label}")

    results_root = (project / "allure-results").resolve()
    for attachment in attachment_nodes:
        source = str(attachment.get("source", ""))
        if not source:
            errors.append(f"Allure 附件缺少 source: {label}")
            continue
        raw = Path(source)
        candidate = project / "allure-results" / raw
        if raw.is_absolute() or ".." in raw.parts or candidate.is_symlink():
            errors.append(f"Allure 附件路径非法或为符号链接: {label}")
            continue
        resolved = candidate.resolve()
        try:
            resolved.relative_to(results_root)
        except ValueError:
            errors.append(f"Allure 附件路径越界: {label}")
            continue
        if not resolved.is_file():
            errors.append(f"Allure 附件缺失: {label}")
            continue
        mime = str(attachment.get("type", "text/plain")).lower()
        if mime.startswith("text/") or mime in {"application/json", "application/xml"}:
            try:
                if resolved.stat().st_size <= 2_000_000:
                    attachment_text = resolved.read_text(encoding="utf-8", errors="replace")
                    scan_text_for_secrets(f"Allure 文本附件 {relative(project, resolved)}", attachment_text, errors)
            except OSError:
                errors.append(f"Allure 附件无法读取: {relative(project, resolved)}")


def validate_result_identities(
    collected_nodes: list[str], full_names: Counter[str], errors: list[str]
) -> None:
    expected = Counter(collected_allure_name(node) for node in collected_nodes)
    if expected == full_names:
        return
    missing = expected - full_names
    extra = full_names - expected
    if missing:
        errors.append(f"Allure 结果缺少当前 pytest 用例身份: {dict(missing)}")
    if extra:
        errors.append(f"Allure 结果包含旧或无关用例身份: {dict(extra)}")


def validate_report_statistics(
    summary: object,
    status_counts: Counter[str],
    label: str,
    errors: list[str],
) -> None:
    if not isinstance(summary, dict) or not isinstance(summary.get("statistic"), dict):
        errors.append(f"{label}缺少可解析的 statistic")
        return

    statistic = summary["statistic"]
    expected = {
        "total": sum(status_counts.values()),
        "passed": status_counts["passed"],
        "failed": status_counts["failed"],
        "broken": status_counts["broken"],
        "skipped": status_counts["skipped"],
    }
    for key, value in expected.items():
        actual = statistic.get(key)
        if not isinstance(actual, int) or actual != value:
            errors.append(f"{label}统计与 Allure 原始结果不一致: {key}={actual!r}, 应为 {value}")


def validate_official_report(
    report_dir: Path,
    status_counts: Counter[str],
    result_count: int,
    errors: list[str],
) -> None:
    index = report_dir / "index.html"
    try:
        html = index.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"官方 Allure 入口无法按 UTF-8 读取: {exc}")
        return

    lowered = html.lower()
    if "<html" not in lowered or "</html>" not in lowered:
        errors.append("官方 Allure 入口不是完整 HTML")

    local_assets: list[Path] = []
    for raw in re.findall(r"(?:src|href)=[\"']([^\"']+)[\"']", html, re.IGNORECASE):
        asset = raw.split("?", 1)[0].split("#", 1)[0].strip()
        if not asset or asset.startswith(("data:", "http://", "https://", "//", "#")):
            continue
        candidate = (report_dir / asset.lstrip("/")).resolve()
        try:
            candidate.relative_to(report_dir.resolve())
        except ValueError:
            errors.append(f"官方 Allure 入口引用了报告目录外资源: {asset}")
            continue
        local_assets.append(candidate)
        if not candidate.is_file() or candidate.stat().st_size == 0:
            errors.append(f"官方 Allure 资源缺失或为空: {asset}")

    suffixes = {path.suffix.lower() for path in local_assets}
    has_script = ".js" in suffixes or "<script" in lowered
    has_style = ".css" in suffixes or "<style" in lowered
    if not has_script or not has_style:
        errors.append("官方 Allure 入口缺少可执行的 JS/CSS 内容")

    summary_path = report_dir / "widgets/summary.json"
    suites_path = report_dir / "data/suites.json"
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"官方 Allure 的 widgets/summary.json 无法解析: {exc}")
        else:
            validate_report_statistics(summary, status_counts, "官方 Allure 报告", errors)

    if suites_path.exists():
        try:
            suites = json.loads(suites_path.read_text(encoding="utf-8"))
            if not isinstance(suites, dict):
                raise ValueError("根节点不是对象")
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"官方 Allure 的 data/suites.json 无法解析: {exc}")

    test_case_dir = report_dir / "data/test-cases"
    if test_case_dir.exists():
        test_cases = list(test_case_dir.glob("*.json"))
        if len(test_cases) != result_count:
            errors.append(
                "官方 Allure 测试详情数与原始结果不一致: "
                f"{len(test_cases)} != {result_count}"
            )


def validate_fallback_report(
    report: Path,
    status_counts: Counter[str],
    result_count: int,
    errors: list[str],
) -> None:
    try:
        html = report.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"内置报告入口无法按 UTF-8 读取: {exc}")
        return

    lowered = html.lower()
    required_html = ("<html", "</html>", "<style", "<script")
    if any(fragment not in lowered for fragment in required_html):
        errors.append("内置报告不是完整的单页 HTML")

    match = re.search(r'var\s+__B64__\s*=\s*"([A-Za-z0-9+/=]+)"', html)
    if not match:
        errors.append("内置报告缺少可审计的嵌入数据载荷")
        return

    try:
        compressed = base64.b64decode(match.group(1), validate=True)
        payload = json.loads(gzip.decompress(compressed).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("数据载荷根节点不是对象")
    except (binascii.Error, OSError, EOFError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"内置报告的嵌入数据无法解析: {exc}")
        return

    raw_summary = payload.get("widgets/summary.json")
    try:
        summary = json.loads(raw_summary) if isinstance(raw_summary, str) else raw_summary
    except json.JSONDecodeError as exc:
        errors.append(f"内置报告的 summary 无法解析: {exc}")
    else:
        validate_report_statistics(summary, status_counts, "内置报告", errors)

    raw_suites = payload.get("data/suites.json")
    try:
        suites = json.loads(raw_suites) if isinstance(raw_suites, str) else raw_suites
        if not isinstance(suites, dict):
            raise ValueError("根节点不是对象")
    except (json.JSONDecodeError, ValueError) as exc:
        errors.append(f"内置报告缺少可解析的 data/suites.json: {exc}")

    test_case_count = sum(
        1 for key in payload
        if isinstance(key, str) and key.startswith("data/test-cases/") and key.endswith(".json")
    )
    if test_case_count != result_count:
        errors.append(
            "内置报告测试详情数与原始结果不一致: "
            f"{test_case_count} != {result_count}"
        )


def main() -> int:
    args = parse_args()
    project_arg = Path(args.project).expanduser()
    if not project_arg.is_absolute():
        print("FAIL: --project 必须使用绝对路径")
        return 1
    project = project_arg.resolve()
    errors: list[str] = []

    if not project.is_dir():
        print(f"FAIL: 项目目录不存在: {project}")
        return 1

    detected_report = detect_report_mode()
    if args.report != detected_report:
        message = (
            "报告分支与本机实际 Allure 检测不一致："
            f"requested={args.report}, detected={detected_report}"
        )
        if args.report_artifacts_only:
            print("REPORT ARTIFACT AUDIT: BLOCKED")
            print(f"- {message}")
            print("- 请返回 ENV_LOCK 重新锁定；未删除或覆盖任何报告")
            return 2
        errors.append("审计" + message)

    if args.report_artifacts_only:
        return print_report_artifact_audit(project, args.report)

    for item in COMMON_FILES:
        path = project / item
        if not path.is_file():
            errors.append(f"缺少必需文件: {item}")
        elif path.is_symlink():
            errors.append(f"必需文件不能是符号链接: {item}")

    for item in NONEMPTY_FILES:
        path = project / item
        if path.is_file() and path.stat().st_size == 0:
            errors.append(f"必需文件为空: {item}")

    report_generator = project / "utils/report_generator.py"
    if args.report == "fallback":
        if not report_generator.is_file():
            errors.append("fallback 报告分支缺少必需文件: utils/report_generator.py")
        elif report_generator.is_symlink():
            errors.append("fallback 报告生成器不能是符号链接")
        elif report_generator.stat().st_size == 0:
            errors.append("fallback 报告分支的必需文件为空: utils/report_generator.py")
        else:
            template = Path(__file__).resolve().parents[1] / "_templates/report_generator.py"
            try:
                expected_digest = hashlib.sha256(template.read_bytes()).hexdigest()
                actual_digest = hashlib.sha256(report_generator.read_bytes()).hexdigest()
            except OSError as exc:
                errors.append(f"无法验证 fallback 报告模板来源: {exc}")
            else:
                if actual_digest != expected_digest:
                    errors.append(
                        "fallback 报告生成器不是当前 Skill 模板的物化副本；"
                        "已保留原文件，须由用户明确处理"
                    )
    elif args.project_kind == "new" and report_generator.exists():
        errors.append("ALLURE=有的新项目不应复制 utils/report_generator.py")

    memory_text, memory_values, endpoints, endpoint_counts = validate_memory(project, args, errors)

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

    collected = collect_pytest_nodes(project, errors) if test_files else None
    collected_count = collected[0] if collected is not None else None
    collected_nodes = collected[1] if collected is not None else []
    syntax_candidates = [
        project / "conftest.py",
        project / "utils/contract_probe.py",
        project / "utils/request_helper.py",
        *test_files,
    ]
    check_python_syntax(
        project, [path for path in syntax_candidates if path.is_file()], errors
    )
    validate_core_contract(project, errors)
    declarations = check_test_semantics(project, test_files, errors)
    if collected_count is not None and endpoint_counts:
        documented_count = sum(endpoint_counts.values())
        if documented_count != collected_count:
            errors.append(
                "MEMORY.md 用例计数合计与 pytest collect-only 不一致: "
                f"{documented_count} != {collected_count}"
            )

    result_files = sorted((project / "allure-results").glob("*-result.json"))
    status_counts: Counter[str] = Counter()
    result_full_names: Counter[str] = Counter()
    credential_skip_results: list[Path] = []
    if not result_files:
        errors.append("allure-results/ 下没有 *-result.json")
    else:
        for path in result_files:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("根节点不是对象")
                if not payload.get("name"):
                    raise ValueError("缺少测试名称")
                full_name = str(payload.get("fullName", "")).strip()
                if not full_name:
                    raise ValueError("缺少 fullName")
                result_full_names[full_name] += 1
                status = str(payload.get("status", "")).lower()
                if status not in VALID_ALLURE_STATUSES:
                    raise ValueError(f"缺少或不支持的 status: {status or 'EMPTY'}")
                status_counts[status] += 1
                details = payload.get("statusDetails", {})
                message = details.get("message", "") if isinstance(details, dict) else ""
                if (
                    status == "skipped"
                    and memory_values.get("AUTH_MODE", "").lower() != "none"
                    and CREDENTIAL_SKIP.search(str(message))
                ):
                    credential_skip_results.append(path)
                secret_paths = payload_secret_paths(payload)
                if secret_paths:
                    errors.append(
                        f"Allure 结果疑似包含凭据值: {relative(project, path)} "
                        f"({', '.join(secret_paths[:5])})"
                    )
                validate_result_evidence(project, path, payload, errors)
            except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
                errors.append(f"Allure 结果无效: {relative(project, path)} ({exc})")

    if credential_skip_results:
        errors.append(
            "认证测试因本地凭据未配置而跳过，不能完成交付: "
            + ", ".join(relative(project, path) for path in credential_skip_results)
        )

    if collected_count is not None and len(result_files) != collected_count:
        errors.append(
            "Allure 结果数量与 pytest collect-only 不一致: "
            f"{len(result_files)} != {collected_count}"
        )
    if collected_nodes and result_full_names:
        validate_result_identities(collected_nodes, result_full_names, errors)

    if memory_text and status_counts:
        sections = markdown_sections(memory_text)
        result_section = (
            last_section(sections, "最终结果")
            if args.mode == "full" else last_section(sections, "结果统计")
        )
        expected_counts = {
            "通过": status_counts["passed"],
            "失败": status_counts["failed"] + status_counts["broken"],
            "跳过": status_counts["skipped"],
        }
        labels = {
            "通过": ("通过", "passed"),
            "失败": ("失败", "failed"),
            "跳过": ("跳过", "skipped"),
        }
        for label, value in expected_counts.items():
            if not memory_has_result_count(result_section, labels[label], value):
                errors.append(f"MEMORY.md 最终结果未记录正确的{label}数: {value}")

    official = project / "allure-report/index.html"
    fallback = project / "allure-report/report.html"
    selected = official if args.report == "official" else fallback
    if not selected.is_file() or selected.stat().st_size == 0:
        errors.append(f"所选报告缺失或为空: {relative(project, selected)}")
    elif selected.is_symlink() or selected.parent.is_symlink():
        errors.append("所选报告入口或报告目录不能是符号链接")
    for conflict in conflicting_report_entries(project, args.report):
        errors.append(
            f"存在与所选分支冲突的报告入口（已保留）: "
            f"{relative(project, conflict)}"
        )
    if selected.is_file() and result_files:
        latest_result = max(path.stat().st_mtime_ns for path in result_files)
        if selected.stat().st_mtime_ns < latest_result:
            errors.append("所选报告早于 Allure 原始结果，可能是旧报告")
        if args.report == "official":
            validate_official_report(
                selected.parent, status_counts, len(result_files), errors
            )
        else:
            validate_fallback_report(
                selected, status_counts, len(result_files), errors
            )

    expected_runner = "run.bat" if args.os_type == "Windows" else "run.sh"
    other_runner = "run.sh" if expected_runner == "run.bat" else "run.bat"
    runner = project / expected_runner
    if not runner.is_file() or runner.stat().st_size == 0:
        errors.append(f"当前 OS 运行脚本缺失或为空: {expected_runner}")
    elif runner.is_symlink():
        errors.append(f"当前 OS 运行脚本不能是符号链接: {expected_runner}")
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
            required_fragments = [
                "pytest",
                "--alluredir=allure-results",
                "--clean-alluredir",
            ]
            required_fragments.extend(
                ["allure generate", "allure-report/index.html"]
                if args.report == "official"
                else ["report_generator.py", "allure-report/report.html"]
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
            if "__PYTHON_COMMAND__" in runner_text:
                errors.append(f"{expected_runner} 仍含未替换的 Python 占位符")
            if "__REPORT_MODE__" in runner_text:
                errors.append(f"{expected_runner} 仍含未替换的报告模式占位符")
            configured_report_mode = re.search(
                r'(?mi)^\s*(?:set\s+"?)?REPORT_MODE\s*=\s*"?(official|fallback)"?\s*$',
                runner_text,
            )
            if not configured_report_mode:
                errors.append(f"{expected_runner} 未固定 REPORT_MODE")
            elif configured_report_mode.group(1).lower() != args.report:
                errors.append(
                    f"{expected_runner} 的 REPORT_MODE 与审计分支不一致: "
                    f"{configured_report_mode.group(1).lower()} != {args.report}"
                )
            configured_python = memory_values.get("PYTHON", "")
            if configured_python and configured_python not in runner_text:
                errors.append(f"{expected_runner} 未优先使用已确认的 PYTHON={configured_python}")
            if re.search(r"\bpip\s+install\b", lowered):
                errors.append(f"{expected_runner} 不应安装依赖；依赖安装必须在独立流程步骤执行")
            if expected_runner == "run.sh":
                for shell_name in ("bash", "sh"):
                    try:
                        checked = subprocess.run(
                            [shell_name, "-n", str(runner)],
                            capture_output=True,
                            text=True,
                            timeout=15,
                            check=False,
                        )
                    except (OSError, subprocess.TimeoutExpired) as exc:
                        errors.append(f"无法用 {shell_name} 检查 run.sh: {exc}")
                    else:
                        if checked.returncode != 0:
                            errors.append(f"run.sh 未通过 {shell_name} -n 语法检查")

    if args.project_kind == "new" and (project / other_runner).exists():
        errors.append(f"新项目不应同时生成另一平台脚本: {other_runner}")

    if args.mode == "full":
        validate_test_document(project, endpoints, len(declarations), errors)

    if args.report == "fallback":
        check_python_syntax(project, [report_generator] if report_generator.is_file() else [], errors)
    if collected_count is not None:
        validate_endpoint_mapping(
            declarations,
            collected_nodes,
            endpoints,
            endpoint_counts,
            errors,
        )

    if errors:
        print("DELIVERY AUDIT: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("DELIVERY AUDIT: PASS")
    print(f"- mode={args.mode}, os={args.os_type}, report={args.report}")
    print(
        f"- tests={collected_count}, endpoints={len(endpoint_counts)}, "
        f"allure_results={len(result_files)}"
    )
    print(
        f"- passed={status_counts['passed']}, failed={status_counts['failed']}, "
        f"broken={status_counts['broken']}, skipped={status_counts['skipped']}"
    )
    print(f"- runner={expected_runner}, memory=MEMORY.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
