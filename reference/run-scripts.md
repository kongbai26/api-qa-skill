# 运行脚本冲突修正规范

本文件只在已有 `run.sh` / `run.bat` 被物化脚本标记为 `PRESERVED`，或 runner 缺失、物化命令不可用/被拒绝时读取。正常情况由 `scripts/materialize_templates.py --component runner` 处理，不读取模板正文。

## 命令能力受阻时预置脚本

只有 runner 物化命令不可用或被拒绝、但宿主仍有文件读写能力时，才允许使用本降级路径：

1. 只读取当前 `OS_TYPE` 对应的 `_templates/run.sh` 或 `_templates/run.bat`，不得读取另一平台模板。
2. 只替换 `__PYTHON_COMMAND__` 和 `__REPORT_MODE__`。POSIX 的 Python 值按双引号变量规则转义 `\`、`"`、`$`、反引号；Windows 值必须是 ASCII 且不含 `%`、`&`、`|`、`<`、`>`、`^` 或引号。
3. 同名脚本缺失时用文件写入能力保存并回读，确认两个占位符均已消失且其他内容未改；同名脚本内容不同时保留并进入冲突处理，禁止覆盖。
4. 文件成功写入就保留在项目目录；Darwin/Linux 可执行命令时补 `chmod +x run.sh`。无法运行脚本时只记录“已交付、未实跑”，不能虚报执行结果。

## 共同契约

- 只交付当前 `OS_TYPE` 对应的一份新脚本；已有项目不删除用户原有的另一平台脚本。
- 运行时先进入脚本自身目录，不写生成时的绝对 `PROJECT_DIR`。
- runner 只以 `--alluredir=allure-results --clean-alluredir` 跑 pytest 并生成所选报告；不得安装或更新依赖。依赖安装始终由独立流程步骤完成。
- `REPORT_MODE` 按 `ENV_LOCK` 已确认的 `ALLURE` 固定为 `official` 或 `fallback`；runner 不执行 `allure --version`，不得重新选择或自动切换分支。
- `official` 只生成并检查 `allure-report/index.html`；`fallback` 只生成并检查 `allure-report/report.html`。
- 另一个报告入口存在时必须报错；禁止 `allure serve`、`allure open`、`open`、`xdg-open`、`start`。
- pytest 正常完成（退出码 0）或用例失败（退出码 1）时仍生成报告，脚本最终返回 pytest 的退出码；启动、收集或参数等错误则直接返回原退出码，不拿旧结果重新生成报告。报告无法生成则立即返回失败。

## `run.sh`

- 首行使用 POSIX `sh`，并以 `cd "$(dirname "$0")" || exit 1` 进入项目根目录。
- 外部 `PYTHON` 有效时优先使用；否则先尝试生成项目时已验证的命令，再尝试 `python3`、`python`。
- 使用 `"$PYTHON" -m pytest`，兼容解释器路径中的空格；不得安装依赖。
- 必须具有执行权限。

## `run.bat`

- 文件必须是纯 ASCII；不要加入中文。
- 使用 `cd /d "%~dp0"`，兼容跨盘符路径。
- 外部 `PYTHON` 有效时优先使用；否则先尝试已验证命令，再尝试 `python`、`python3`、`py`。
- 使用 `errorlevel` 检查测试和报告命令。

## 最小修正

读取当前 OS 的既有脚本，只修正违反上述契约的行。不得为了与模板逐字一致而整文件覆盖。修正后重新检查：

- 当前脚本存在且非空；`run.sh` 可执行，`run.bat` 可按 ASCII 解码。
- 不含模板占位符。
- `REPORT_MODE` 与已确认的 `ALLURE` 分支一致。
- 包含 pytest、清理旧结果、对应报告命令和唯一入口检查。
- 交付阶段只确认当前 OS 脚本存在；是否已经执行必须在交付说明中如实标注。
