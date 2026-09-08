# 阶段四：跑测试 + 修到通过

> **⛔ 本阶段无额外 reference 文件需要读取。需要阶段一的产出（ALLURE=有/无）。**

## 目标

执行测试，修复失败用例，生成报告，直到全部通过或确认是 API bug。

## 步骤清单（执行时必须逐项打勾，跳过禁止）

```
⬜ 1. 跑 pytest（传 --alluredir=allure-results）
⬜ 2. 生成 Allure 报告
⬜ 3. 分析失败原因（断言不匹配 vs API bug）
⬜ 4. 修复断言 / 记录 API bug
⬜ 5. 重跑 pytest + 重新生成报告（最多 5 轮）
⬜ 6. 更新 MEMORY.md 结果统计 + 修复记录
```

**执行规则**：每完成一项立即将 `⬜` 改为 `✅`。全部通过 → 生成报告后进入步骤⑥；5 轮后仍有失败 → 记录为 API bug，进入步骤⑥。

---

## ① 跑 pytest

```
shell_exec(command="cd \"<PROJECT_DIR>\" && <PYTHON> -m pytest tests/ -v --tb=short --alluredir=allure-results")
```

⚠️ **关键**：pytest 必须传 `--alluredir=allure-results`，否则不会生成 Allure JSON 结果文件，后续生成报告就读不到数据！

⚠️ **pytest 报错诊断与修复**：

| 错误信息 | 可能原因 | 自动修复方案 |
|---------|---------|-------------|
| `ModuleNotFoundError: No module named 'xxx'` | 依赖未安装 | 回到阶段二④重新安装依赖 |
| `No module named 'allure'` | allure-pytest 未安装 | `shell_exec(command="<PYTHON> -m pip install allure-pytest")` |
| `No module named 'pytest'` | pytest 未安装 | `shell_exec(command="<PYTHON> -m pip install pytest")` |
| `ImportError: cannot import name 'xxx' from 'utils'` | utils 目录缺少 `__init__.py` | 创建 `utils/__init__.py` 空文件 |
| 测试全部失败 (FAILED) | .env 配置错误或 API 不可用 | 检查 `.env` 中的 `API_BASE_URL` 和 `API_TOKEN`，用 curl 测试接口 |
| `Permission denied` | 文件权限不足 | `shell_exec(command="chmod +x '<PROJECT_DIR>/run.sh'")` |
| `pytest: command not found` | pytest 不在 PATH 中 | 使用 `<PYTHON> -m pytest` 而不是直接 `pytest` |

- 全部通过 → 告诉用户"全部通过"，继续步骤②生成报告
- 部分失败 → 告诉用户测试结果摘要（通过/失败/跳过数量 + 失败原因概要），继续步骤②

---

## ② 生成报告

⚠️ **禁止用 `allure serve` 或 `allure open`，禁止 `open` 任何文件。**
⚠️ **必须生成正式 HTML 测试报告，严禁自制 `TEST_REPORT.md` 等 Markdown 文件代替报告！** 只要未生成标准 HTML 报告，即视为未完成。

**根据环境与工具链生成报告**：

**如果有 allure（ALLURE=有）**：
1. 生成官方多文件静态报告：
```
shell_exec(command="cd \"<PROJECT_DIR>\" && allure generate allure-results -o allure-report --clean")
```
2. 若系统具备 `report_build` 工具，立即调用以同步生成单文件大盘：
```
report_build(allure_results_dir="<PROJECT_DIR>/allure-results", output_path="<PROJECT_DIR>/allure-report/report.html", session_goal="API测试报告")
```

**如果没有 allure（ALLURE=无）**：
若系统具备 `report_build` 工具，优先调用：
```
report_build(allure_results_dir="<PROJECT_DIR>/allure-results", output_path="<PROJECT_DIR>/allure-report/report.html", session_goal="API测试报告")
```
若无该工具，执行 Python 报告生成器脚本：
```
shell_exec(command="cd \"<PROJECT_DIR>\" && <PYTHON> utils/report_generator.py --input allure-results --output allure-report/report.html")
```

⚠️ 如果报告生成失败：
- `未找到 allure-results/*-result.json` → 步骤①的 `--alluredir` 参数没传，重新跑步骤①
- 其他错误 → 检查 allure-results 目录是否有内容

---

## ③ 分析失败原因

检查 pytest 输出，区分：
- **断言不匹配** → 断言写的和真实返回不一致 → 进入步骤④改断言
- **API bug** → 接口行为和文档描述不一致 → 进入步骤④记差异列表
- **代码错误** → import 失败、fixture 缺失等 → 进入步骤④修代码

---

## ④ 修复断言 / 记录 API bug

- 断言不匹配真实返回 → **改断言**，不改 API
- API 真有 bug → **不改代码**，记到差异列表
- 改完后进入步骤⑤重跑

⚠️ **阶段四只修改 tests/ 目录下的测试文件，禁止修改 utils/report_generator.py。**

---

## ⑤ 重跑 pytest + 重新生成报告

```
shell_exec(command="cd \"<PROJECT_DIR>\" && <PYTHON> -m pytest tests/ -v --tb=short --alluredir=allure-results")
```

每轮重跑后检查结果：
- **全部通过** → 退出循环，进入步骤⑥
- **仍有失败** → 回到步骤③继续分析

**最多 5 轮**，5 轮后仍有失败则记录为 API bug，进入步骤⑥。

---

## ⑥ 更新 MEMORY.md

将以下信息**追加写入** MEMORY.md：

1. **结果统计**（通过/失败/跳过数量）
2. **修复记录**（修了什么、API bug 列表）

## 产出

📝 MEMORY.md：结果统计、修复记录。保存追加到 `<PROJECT_DIR>/MEMORY.md`。
