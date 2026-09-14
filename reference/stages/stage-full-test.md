# 阶段四：跑测试 + 修到通过

> **⛔ 本阶段无额外 reference 文件需要读取。需要阶段一的产出（ALLURE=有/无）。**

> **MEMORY 文件边界**：本阶段所有 `MEMORY.md` 均指 `<PROJECT_DIR>/MEMORY.md`，必须用文件写入工具追加，供用户查看；不得使用 Agent 工作区记忆、数据库、`memory_save` 或 `memory_recall` 保存或恢复本流程数据。

## 目标

执行测试，修复失败用例，生成报告，直到全部通过或确认是 API bug。

## 步骤清单（执行时必须逐项打勾，跳过禁止）

```
⬜ 1. 跑 pytest（传 --alluredir=allure-results）
⬜ 2. 生成单一报告
⬜ 3. 分析测试结果（有失败则分类，无失败则确认）
⬜ 4. 按分析结果修复或记录（无失败则确认无需修复）
⬜ 5. 有修改则重跑 pytest + 重新生成报告（最多 5 轮）；无修改则确认当前报告已是最新
⬜ 6. 更新 `<PROJECT_DIR>/MEMORY.md` 结果统计 + 修复记录
```

**执行规则**：进入本阶段时按上述 6 项建立同一份任务清单；`task_add` 可用时必须在步骤①前逐项调用并保存 `task_ref`，不能只在计划中复述。每完成一项并取得可核验结果后，立即通过 `task_update`（不可用时更新文本清单）将对应 `⬜` 改为 `✅`，条件项经结果证明无需动作时也必须记录该结论并标为 `✅`，不得标记为 `skipped`。6 项全部打勾并经 `task_tree` 复核后才能进入阶段五。首次全部通过 → 步骤②后依次确认③无失败、④无需修复、⑤当前报告已是最新，再进入⑥；5 轮后仍有失败 → 按证据完成③-⑤并记录为断言、代码、环境、接口差异或未决问题，再进入⑥。

---

## ① 跑 pytest

```
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> -m pytest tests/ -v --tb=short --alluredir=allure-results --clean-alluredir")
```

⚠️ **关键**：pytest 必须传 `--alluredir=allure-results --clean-alluredir`，否则报告可能缺少结果或混入旧数据！

如果测试命令能力不可用或被拒绝，不重试、不把它当成测试失败，也不进入阶段五。保留阶段二已预置的当前 OS 脚本，保持本阶段未执行项为 `⬜`，给出项目内脚本绝对路径和手动命令，请用户自行执行；不得声称报告或交付审计已通过。

⚠️ **pytest 报错诊断与修复**：

| 错误信息 | 可能原因 | 自动修复方案 |
|---------|---------|-------------|
| `ModuleNotFoundError: No module named 'xxx'` | 依赖未安装 | 回到阶段二④重新安装依赖 |
| `No module named 'allure'` | allure-pytest 未安装 | `shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> -m pip install allure-pytest")` |
| `No module named 'pytest'` | pytest 未安装 | `shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> -m pip install pytest")` |
| `ImportError: cannot import name 'xxx' from 'utils'` | utils 目录缺少 `__init__.py` | 创建 `utils/__init__.py` 空文件 |
| 测试全部失败 (FAILED) | 环境配置错误或 API 不可用 | 不读取 `.env`；核对 MEMORY 的非敏感配置，请用户确认本地凭据已设置，再结合 curl 无认证探测与测试输出判断 |
| `Permission denied` | 报错目标的文件或目录权限不足 | 核对报错所指目标并做最小权限修正 |
| `pytest: command not found` | pytest 不在 PATH 中 | 使用 `<PYTHON_CMD> -m pytest` 而不是直接 `pytest` |

- 全部通过 → 告诉用户"全部通过"，继续步骤②生成报告
- 部分失败 → 告诉用户测试结果摘要（通过/失败/跳过数量 + 失败原因概要），继续步骤②

---

## ② 生成报告

⚠️ **禁止用 `allure serve` 或 `allure open`，禁止 `open` 任何文件。**

**根据阶段一检测的 ALLURE 变量决定报告方式**：

生成前先执行路径无关的报告产物扫描；`<REPORT_MODE>` 按已锁定的 `ALLURE` 替换为 `official` 或 `fallback`：

```text
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> \"<SKILL_DIR>/scripts/validate_delivery.py\" --project \"<PROJECT_DIR>\" --report <REPORT_MODE> --report-artifacts-only")
```

扫描为 `PASS` 才能继续；扫描为 `BLOCKED` 时保持列出的既有报告不动，登记“等待用户”并询问如何处理，用户明确处理前禁止生成新报告或进入后续步骤。

**如果有 allure（ALLURE=有）** → 只生成官方 Allure 报告，入口为 `allure-report/index.html`：
```
shell_exec(command="<ENTER_PROJECT> allure generate allure-results -o allure-report --clean")
```
`--clean` 参数会自动覆盖旧报告，无需手动删除。

**如果没有 allure（ALLURE=无）** → 只用阶段二从本 Skill 模板物化并验收过的 `utils/report_generator.py` 生成单页面报告，入口为 `allure-report/report.html`：
```
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> utils/report_generator.py --input allure-results --output allure-report/report.html --clean")
```

两条分支互斥，只保留所选入口，禁止同时生成 `index.html` 和 `report.html`；无论哪一分支都禁止调用宿主通用报告器代替模板或另建报告。

报告扫描或生成命令能力不可用/被拒绝时，不重试、不伪造报告，也不进入阶段五。保留阶段二已预置脚本，给出脚本绝对路径和手动命令，请用户自行执行；本阶段尚未执行及其后清单项保持 `⬜`。

⚠️ 如果报告生成失败：
- `未找到 allure-results/*-result.json` → 步骤①的 `--alluredir` 参数没传，重新跑步骤①
- 其他错误 → 检查 allure-results 目录是否有内容

---

## ③ 分析测试结果

检查 pytest 输出，区分：
- **没有失败** → 记录“无失败”，将步骤③标为 `✅`，进入步骤④确认无需修复
- **断言不匹配** → 断言与用户确认的契约不一致 → 进入步骤④改断言
- **API bug** → 实际行为与用户确认的契约不一致且有复现证据 → 进入步骤④记差异列表
- **代码错误** → import 失败、fixture 缺失等 → 进入步骤④修代码

---

## ④ 按分析结果修复或记录

- 步骤③确认没有失败 → 记录“无需修复”，将步骤④标为 `✅`，进入步骤⑤确认当前报告已是最新
- 断言不匹配确认后的契约 → **改断言**，不改 API；不得仅为测试通过而迎合错误返回
- API 真有 bug → **不改代码**，记到差异列表
- 改完后进入步骤⑤重跑

⚠️ **阶段四优先只修改 `tests/`。只有 import、fixture 或请求封装本身确有代码错误时，才最小修改 `conftest.py`、`utils/request_helper.py` 或 `pytest.ini`；禁止修改 `utils/report_generator.py`，也禁止借修复之名放宽已确认契约。**

---

## ⑤ 确保测试结果与报告为修改后的最新版本

```
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> -m pytest tests/ -v --tb=short --alluredir=allure-results --clean-alluredir")
```

每轮 pytest 后立即按步骤②的同一 `ALLURE` 分支重新生成报告：ALLURE=有只运行 `allure generate ... --clean`，ALLURE=无只运行 `report_generator.py ... --clean`。修复后禁止沿用修复前的旧报告，也禁止同时生成两个入口。

每轮重跑后检查结果：
- **全部通过** → 退出循环，进入步骤⑥
- **仍有失败** → 回到步骤③继续分析

如果步骤④确认无需修改，不重复执行 pytest 或报告命令；核对步骤②的报告确由本阶段步骤①的最新 `allure-results` 生成后，将步骤⑤标为 `✅`，再进入步骤⑥。

**最多 5 轮**，5 轮后仍有失败则按现有证据分类记录；不能仅凭重试次数判定为 API bug。然后进入步骤⑥。

---

## ⑥ 更新 `<PROJECT_DIR>/MEMORY.md`

将以下信息**追加写入** `<PROJECT_DIR>/MEMORY.md`：

1. `## 结果统计`（通过/失败/跳过数量）
2. `## 修复记录`（修了什么、API bug 列表；没有则写“无修复”）
3. 在 `## 阶段记录` 追加 `### 阶段四 - YYYY-MM-DD`，非空记录“完成、发现、决策”

## 产出

📝 `<PROJECT_DIR>/MEMORY.md`：结果统计、修复记录。**必须且只能写入该项目文件。**

## 保存边界

只写 `<PROJECT_DIR>/MEMORY.md`。不得把本流程的项目配置或阶段产出额外写入 Agent 数据库、project-memory 或会话工作区。
