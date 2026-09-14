#!/bin/sh
# 切换到脚本所在目录（项目根目录）
cd "$(dirname "$0")" || exit 1

CONFIGURED_PYTHON="__PYTHON_COMMAND__"
REPORT_MODE="__REPORT_MODE__"
if [ -n "${PYTHON:-}" ]; then
    if ! command -v "$PYTHON" >/dev/null 2>&1 || ! "$PYTHON" --version >/dev/null 2>&1; then
        echo "ERROR: configured PYTHON is not executable: $PYTHON"
        exit 1
    fi
else
    PYTHON=""
    for cmd in "$CONFIGURED_PYTHON" python3 python; do
        if command -v "$cmd" >/dev/null 2>&1 && "$cmd" --version >/dev/null 2>&1; then
            PYTHON="$cmd"
            break
        fi
    done
fi
if [ -z "$PYTHON" ]; then
    echo "ERROR: python not found. Set PYTHON=/path/to/python and retry."
    exit 1
fi
echo "Using: $PYTHON ($("$PYTHON" --version 2>&1))"

if ! "$PYTHON" -m pip install -q -r requirements.txt; then
    echo "ERROR: 依赖安装失败"
    exit 1
fi
"$PYTHON" -m pytest tests/ -v --tb=short --alluredir=allure-results --clean-alluredir "$@"
TEST_EXIT_CODE=$?
if [ $TEST_EXIT_CODE -ne 0 ]; then
    echo "测试有失败，继续生成报告..."
fi

# 检查 allure-results 是否包含测试结果
if ! find allure-results -maxdepth 1 -type f -name '*-result.json' -print -quit 2>/dev/null | grep -q .; then
    echo "ERROR: allure-results 中没有 *-result.json，无法生成报告"
    exit 1
fi

if [ "$REPORT_MODE" = "official" ]; then
    if ! command -v allure >/dev/null 2>&1 || ! allure --version >/dev/null 2>&1; then
        echo "ERROR: report mode is official but allure is unavailable"
        exit 1
    fi
    allure generate allure-results -o allure-report --clean
    REPORT_EXIT_CODE=$?
    REPORT_PATH="allure-report/index.html"
    UNEXPECTED_REPORT="allure-report/report.html"
elif [ "$REPORT_MODE" = "fallback" ]; then
    if [ ! -f "utils/report_generator.py" ]; then
        echo "ERROR: fallback report generator is missing"
        exit 1
    fi
    "$PYTHON" utils/report_generator.py --input allure-results --output allure-report/report.html --clean
    REPORT_EXIT_CODE=$?
    REPORT_PATH="allure-report/report.html"
    UNEXPECTED_REPORT="allure-report/index.html"
else
    echo "ERROR: invalid report mode: $REPORT_MODE"
    exit 1
fi

if [ $REPORT_EXIT_CODE -ne 0 ] || [ ! -s "$REPORT_PATH" ] || [ -e "$UNEXPECTED_REPORT" ]; then
    echo "ERROR: 报告生成失败或报告入口不唯一"
    exit 1
fi
echo "报告已生成: $REPORT_PATH"

exit $TEST_EXIT_CODE
