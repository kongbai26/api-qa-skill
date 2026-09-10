# run.sh / run.bat 代码

根据 `OS_TYPE` 只复制一个对应代码块：Darwin/Linux 使用 `run.sh`，Windows 使用 `run.bat`。代码必须原样使用，不要自己重写；新项目禁止同时生成两份脚本。

⚠️ **run.bat 编码规则**：bat 文件必须用纯 ASCII 编码，禁止包含任何中文字符。原因：cmd.exe 读 .bat 文件使用系统默认编码（中文 Windows 是 GBK），而 agent 的 `save_file` 工具默认保存为 UTF-8，两者不匹配会导致中文乱码并破坏 bat 语法。`chcp 65001` 只影响控制台输出编码，不影响文件读取编码。纯 ASCII 是唯一可靠的方案。

## run.sh（macOS/Linux）

```bash
#!/bin/bash
# 切换到脚本所在目录（项目根目录）
cd "$(dirname "$0")" || exit 1

PYTHON="${PYTHON:-}"
if [ -z "$PYTHON" ]; then
    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
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

"$PYTHON" -m pip install -q -r requirements.txt
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

if command -v allure &>/dev/null && allure --version >/dev/null 2>&1; then
    allure generate allure-results -o allure-report --clean
    REPORT_EXIT_CODE=$?
    REPORT_PATH="allure-report/index.html"
    UNEXPECTED_REPORT="allure-report/report.html"
else
    "$PYTHON" utils/report_generator.py --input allure-results --output allure-report/report.html --clean
    REPORT_EXIT_CODE=$?
    REPORT_PATH="allure-report/report.html"
    UNEXPECTED_REPORT="allure-report/index.html"
fi

if [ $REPORT_EXIT_CODE -ne 0 ] || [ ! -s "$REPORT_PATH" ] || [ -e "$UNEXPECTED_REPORT" ]; then
    echo "ERROR: 报告生成失败或报告入口不唯一"
    exit 1
fi
echo "报告已生成: $REPORT_PATH"

exit $TEST_EXIT_CODE
```

## run.bat（Windows）

**⚠️ 以下 bat 代码是纯 ASCII（0x00-0x7F），禁止在其中添加任何中文。agent 通过 `save_file` 保存时必须原样输出，不能修改。**

```bat
@echo off
cd /d "%~dp0"

where python  >nul 2>&1 && set "PYTHON=python"
if not defined PYTHON where python3 >nul 2>&1 && set "PYTHON=python3"
if not defined PYTHON where py      >nul 2>&1 && set "PYTHON=py"
if not defined PYTHON (
    echo ERROR: python not found.
    exit /b 1
)

echo Using: %PYTHON%
"%PYTHON%" --version

"%PYTHON%" -m pip install -q -r requirements.txt
"%PYTHON%" -m pytest tests/ -v --tb=short --alluredir=allure-results --clean-alluredir
set TEST_EXIT_CODE=%ERRORLEVEL%

if %TEST_EXIT_CODE% neq 0 echo Some tests failed, continuing to generate report...

if not exist "allure-results\*-result.json" (
    echo ERROR: no *-result.json in allure-results
    exit /b 1
)

where allure >nul 2>&1 && allure --version >nul 2>&1
if not errorlevel 1 (
    allure generate allure-results -o allure-report --clean
    if errorlevel 1 exit /b 1
    if not exist "allure-report\index.html" exit /b 1
    if exist "allure-report\report.html" exit /b 1
    for %%F in ("allure-report\index.html") do if %%~zF LEQ 0 exit /b 1
    echo Report: allure-report\index.html
) else (
    "%PYTHON%" utils\report_generator.py --input allure-results --output allure-report/report.html --clean
    if errorlevel 1 exit /b 1
    if not exist "allure-report\report.html" exit /b 1
    if exist "allure-report\index.html" exit /b 1
    for %%F in ("allure-report\report.html") do if %%~zF LEQ 0 exit /b 1
    echo Report: allure-report\report.html
)

exit /b %TEST_EXIT_CODE%
```

## 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `PYTHON`（仅 run.sh） | 指定 Python 解释器路径 | `PYTHON=/usr/bin/python3.13 ./run.sh` |

run.sh 和 run.bat 都会自动检测 Python。run.sh 优先 `python3` 其次 `python`；run.bat 优先 `python` 其次 `python3` 其次 `py`（Windows Python Launcher）。找不到则报错退出。
