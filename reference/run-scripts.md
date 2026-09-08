# run.sh / run.bat 代码

必须原样使用，不要自己重写。

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
echo "Using: $PYTHON ($($PYTHON --version 2>&1))"

"$PYTHON" -m pip install -q -r requirements.txt
"$PYTHON" -m pytest tests/ -v --tb=short --alluredir=allure-results "$@"
TEST_EXIT_CODE=$?
if [ $TEST_EXIT_CODE -ne 0 ]; then
    echo "测试有失败，继续生成报告..."
fi

# 检查 allure-results 是否存在
if [ ! -d "allure-results" ] || [ -z "$(ls -A allure-results 2>/dev/null)" ]; then
    echo "ERROR: allure-results 目录不存在或为空，无法生成报告"
    exit 1
fi

if command -v allure &>/dev/null; then
    allure generate allure-results -o allure-report --clean && allure serve allure-results
    echo "报告已生成: allure-report/index.html"
else
    "$PYTHON" utils/report_generator.py
    echo "报告已生成: allure-report/report.html"
fi

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
%PYTHON% --version

%PYTHON% -m pip install -q -r requirements.txt
%PYTHON% -m pytest tests/ -v --tb=short --alluredir=allure-results
set TEST_EXIT_CODE=%ERRORLEVEL%

if %TEST_EXIT_CODE% neq 0 echo Some tests failed, continuing to generate report...

if not exist "allure-results" (
    echo ERROR: allure-results is empty, cannot generate report
    exit /b 1
)

where allure >nul 2>&1
if not errorlevel 1 (
    allure generate allure-results -o allure-report --clean
    echo Report: allure-report\index.html
) else (
    %PYTHON% utils\report_generator.py
    echo Report: allure-report\report.html
)

exit /b %TEST_EXIT_CODE%
```

## 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `PYTHON`（仅 run.sh） | 指定 Python 解释器路径 | `PYTHON=/usr/bin/python3.13 ./run.sh` |

run.sh 和 run.bat 都会自动检测 Python。run.sh 优先 `python3` 其次 `python`；run.bat 优先 `python` 其次 `python3` 其次 `py`（Windows Python Launcher）。找不到则报错退出。
