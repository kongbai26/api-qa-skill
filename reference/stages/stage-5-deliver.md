# 阶段五：交付

> **⛔ 按需加载：④复核阶段二已预置的当前 OS 脚本，仅在 runner 冲突、缺失或物化命令受阻时读取 `reference/run-scripts.md`；⑤读取 `reference/test-doc.md`。禁止提前批量读取。需要阶段一的产出（ALLURE、PROJECT_KIND），结束时执行 `scripts/validate_delivery.py`。**

> **MEMORY 文件边界**：本阶段所有 `MEMORY.md` 均指 `<PROJECT_DIR>/MEMORY.md`，必须用文件写入工具追加，供用户查看；不得使用 Agent 工作区记忆、数据库、`memory_save` 或 `memory_recall` 保存或恢复本流程数据。

## 目标

重新跑测试确保报告最新，在最终文档与审计前实跑已预置脚本，再整理交付物。

⚠️ **交付前必须重跑一次测试，确保报告是最新的。**

## 步骤清单（执行时必须逐项打勾，跳过禁止）

```
⬜ 1. 重跑 pytest
⬜ 2. 生成单一报告
⬜ 3. 确认所选报告入口存在且非空
⬜ 4. 交付前复核、验收并实际执行已预置的运行脚本
⬜ 5. 写 docs/test_cases.md
⬜ 6. 更新并验收 `<PROJECT_DIR>/MEMORY.md` 最终结果
```

**执行规则**：进入本阶段时按上述 6 项建立同一份任务清单；`task_add` 可用时必须在步骤①前逐项调用并保存 `task_ref`，不能只在计划中复述。每完成一项并取得可核验结果后，立即通过 `task_update`（不可用时更新文本清单）将对应 `⬜` 改为 `✅`，结束前用 `task_tree` 复核；6 项不可拆散或提前结束，报告生成或入口检查成功都不代表交付完成。只有步骤⑥的最终审计返回 `DELIVERY AUDIT: PASS` 后，才能把第⑥项和整个任务标为完成并输出结束语。

## ① 重跑测试

```
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> -m pytest tests/ -v --tb=short --alluredir=allure-results --clean-alluredir")
```

如果测试命令能力不可用或被拒绝，不重试、不把它当成测试失败。保留阶段二已预置的脚本，保持①-⑥为 `⬜`，直接按④的权限阻塞格式把脚本交给用户执行；不得生成虚假报告或输出完成结束语。

⚠️ 如果 pytest 出现阶段四没有记录过的新失败，说明交付状态不稳定，必须重新分类处理。阶段四已用证据确认并记录的 API 契约缺陷可以继续存在，但必须与 MEMORY 的遗留问题一致，不能伪装为通过：
- 不读取 `.env`；核对 MEMORY 的非敏感配置、请用户确认本地凭据已填写，并检查依赖与 API 可用性
- 修复后重新跑 pytest
- **最多重试 2 轮**，超过则告知用户问题未解决，展示当前结果

---

## ② 生成报告

⚠️ **禁止用 `allure serve` 或 `allure open`，禁止 `open` 任何文件。**

pytest 跑完后，先告诉用户测试结果摘要（通过/失败/跳过数量），然后生成报告：

先执行路径无关的报告产物扫描；`<REPORT_MODE>` 按已锁定的 `ALLURE` 替换为 `official` 或 `fallback`：

```text
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> \"<SKILL_DIR>/scripts/validate_delivery.py\" --project \"<PROJECT_DIR>\" --report <REPORT_MODE> --report-artifacts-only")
```

扫描为 `PASS` 才能继续；扫描为 `BLOCKED` 时保持列出的既有报告不动，登记“等待用户”并询问如何处理，用户明确处理前禁止重建报告或完成交付。

**ALLURE=有** → 只生成官方 Allure 报告：
```
shell_exec(command="<ENTER_PROJECT> allure generate allure-results -o allure-report --clean")
```

**ALLURE=无** → 只用阶段二从本 Skill 模板物化并验收过的 `utils/report_generator.py` 生成单文件报告：
```
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> utils/report_generator.py --input allure-results --output allure-report/report.html --clean")
```

两条分支互斥；ALLURE=有只保留 `index.html`，ALLURE=无只保留 `report.html`。无论哪一分支都禁止调用宿主通用报告器代替模板或另建报告。

报告扫描或生成命令能力不可用/被拒绝时，不重试、不伪造报告；保留阶段二已预置脚本，保持②-⑥为 `⬜`，按④的权限阻塞格式交给用户执行。

⚠️ 如果报告生成失败，不要重试，在③中统一处理。

---

## ③ 确认报告已更新

检查所选报告入口存在、非空，且另一个入口不存在：

**如果有 allure（ALLURE=有）**：
```
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> -c \"from pathlib import Path; import sys; p=Path('allure-report/index.html'); q=Path('allure-report/report.html'); sys.exit(0 if p.is_file() and p.stat().st_size > 0 and not q.exists() else 1)\"")
```

**如果没有 allure（ALLURE=无）**：
```
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> -c \"from pathlib import Path; import sys; p=Path('allure-report/report.html'); q=Path('allure-report/index.html'); sys.exit(0 if p.is_file() and p.stat().st_size > 0 and not q.exists() else 1)\"")
```

**⚠️ 关键：检查一次就够了，不要重复检查。**

**判断标准**：
- 所选入口存在且非空、另一入口不存在 → 报告生成成功，继续到④
- 否则 → 按当前 ALLURE 分支重新生成并再次检查，**最多重试1次**；仍失败则告知用户，禁止输出报告生成成功

报告入口检查通过后，只能把任务清单第③项标为 `✅`，随后继续④；此处禁止把整个任务标记为完成或输出结束语。

---

## ④ 交付前复核、验收并实跑当前 OS 运行脚本

脚本已在阶段二预置。交付前再次调用物化脚本做确定性比对；它不会覆盖内容不同的已有脚本。`<REPORT_MODE>` 在 `ALLURE=有` 时替换为 `official`，否则替换为 `fallback`：
```
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> \"<SKILL_DIR>/scripts/materialize_templates.py\" --project \"<PROJECT_DIR>\" --component runner --project-kind <PROJECT_KIND> --os <OS_TYPE> --python-command \"<PYTHON>\" --report <REPORT_MODE>")
```

- 物化结果为 `PASS`：继续验证当前脚本；`run.sh` 已自动设置执行权限
- 物化结果为 `REVIEW`，或既有脚本存在自动打开报告、双报告冲突、报告模式与 `ALLURE` 不一致、Python 解释器不一致、pip 失败后继续执行等冲突：此时才读取 `reference/run-scripts.md` 和当前 OS 的既有脚本，按短契约最小修正，禁止整文件覆盖
- 物化结果为 `FAIL`：按错误修复后最多重试 2 次；连续 3 次失败停止并如实报告
- 物化命令不可用或被拒绝：保留阶段二已预置的脚本，按需读取 `reference/run-scripts.md` 后用文件能力回读核对；脚本意外缺失时立即按其中的降级路径补回
- 新项目禁止同时生成两份；追加已有项目时不删除用户原有的另一平台脚本

物化后必须验证：Darwin/Linux 的 `run.sh` 存在、可执行，且 `bash -n run.sh` 与 `sh -n run.sh` 都通过；Windows 的 `run.bat` 存在、非空并可按 ASCII 解码。不能只凭文件名存在完成本步骤。

权限与语法检查通过后，必须实际执行当前 OS 脚本一次，不向用户转交此步：

- Darwin/Linux：`shell_exec(command="<ENTER_PROJECT> ./run.sh")`
- Windows：`shell_exec(command="<ENTER_PROJECT> call run.bat")`

脚本会重新运行依赖检查、pytest 和已锁定的唯一报告分支；其产出的 `allure-results` 和报告才是最终审计输入。之前全部通过时，脚本必须返回 0；已记录的 API 契约缺陷导致 pytest 非 0 时，脚本仍必须完成报告生成，且最终结果必须与 MEMORY 一致。其他脚本错误最小修复后最多重试 2 次。

如执行测试或脚本的命令能力不可用或被拒绝，必须保留已经预置的脚本，保持尚未执行及其后清单项为 `⬜`，登记“等待用户”，并给出项目内手动命令：Darwin/Linux 为 `cd "<PROJECT_DIR>" && chmod +x run.sh && ./run.sh`，Windows 为 `cd /d "<PROJECT_DIR>" && call run.bat`。这表示脚本已交付但测试、报告、实跑与最终审计中的未执行部分仍待完成；禁止说“用户没有要求脚本”，也禁止输出完成结束语。

权限阻塞时的回复必须同时列出“运行脚本：<绝对路径>（已交付）”“执行状态：待用户执行”，并请用户执行后回复结果；不得写“运行脚本实跑：PASS”或“交付审计：DELIVERY AUDIT: PASS”。

只有脚本检查和实际执行均完成后，才能把任务清单第④项标为 `✅`，随后继续⑤；此处仍禁止把整个任务标记为完成或输出结束语。

---

## ⑤ 写 docs/test_cases.md

先完整读取文档格式；如有分页，必须读到 `has_more=false`：

```text
read_file(path="<SKILL_DIR>/reference/test-doc.md")
```

然后按该格式写入 `docs/test_cases.md`。

---

## ⑥ 更新 `<PROJECT_DIR>/MEMORY.md` 最终结果

以步骤④脚本实跑后最新的 `allure-results` 为准，将以下信息**追加写入** `<PROJECT_DIR>/MEMORY.md`：
1. `## 最终结果`（用 `| 通过 | N |`、`| 失败 | N |`、`| 跳过 | N |` 三行记录；失败数包含 Allure 的 failed + broken）
2. `## 交付物清单`（报告路径、文档路径、脚本路径）
3. `## 遗留问题`（未修复的 API bug 等；没有则写“无遗留问题”）
4. 在 `## 阶段记录` 追加 `### 阶段五 - YYYY-MM-DD`，非空记录“完成、发现、决策”

写入后执行最终交付审计：

```text
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> \"<SKILL_DIR>/scripts/validate_delivery.py\" --project \"<PROJECT_DIR>\" --mode full --os <OS_TYPE> --report <official|fallback> --project-kind <PROJECT_KIND>")
```

`ALLURE=有` 时 `--report official`，否则 `--report fallback`。审计脚本不读取 `.env`；它必须交叉验证用例归属、断言与真实请求证据、Allure 结果身份、MEMORY、报告唯一性、核心框架、逐用例文档和当前 OS 脚本。业务对错仍由模型按契约判断。只有最后一次审计实际输出 `DELIVERY AUDIT: PASS`，才能把第⑥项和整个任务标为完成；失败后按不同错误逐项修复并重跑，最多 3 轮，连续相同错误不得重复同一操作，仍失败则如实报告阻塞。

---

## 交付清单

- 测试代码（tests/ 目录）
- 用例文档（docs/test_cases.md）
- 测试报告（allure-report/index.html 或 allure-report/report.html）
- 差异列表（`<PROJECT_DIR>/MEMORY.md` 中记录）
- 当前 OS 对应的运行脚本（Darwin/Linux 为 run.sh，Windows 为 run.bat）

## 产出

📝 `<PROJECT_DIR>/MEMORY.md`：最终结果、交付物、遗留问题。**必须更新并验收该项目文件。**

## 保存边界

只写并验收 `<PROJECT_DIR>/MEMORY.md`。不得把本流程的项目配置、阶段产出或交付状态额外写入 Agent 数据库、project-memory 或会话工作区。

全部完成后，必须先展示 6 项全为 `✅` 的任务清单，并列出所选报告入口、当前 OS 运行脚本、`<PROJECT_DIR>/MEMORY.md` 的绝对路径和 `DELIVERY AUDIT: PASS`，然后可以输出纯文本总结，不需要再调用工具。

最终回复必须使用下面的交付结构，不得只说“测试通过”或只列测试代码和报告：

```text
完整流程交付清单：阶段五 6 项全部 ✅
测试结果：通过 N，失败 N，跳过 N
项目目录：<PROJECT_DIR 绝对路径>
测试代码：<tests/ 下实际文件>
用例文档：<PROJECT_DIR>/docs/test_cases.md
测试报告：<唯一报告入口绝对路径>
原始结果：<PROJECT_DIR>/allure-results/
运行脚本：<当前 OS 对应脚本绝对路径>
运行脚本实跑：PASS（已重新生成最新测试结果和唯一报告）
项目记录：<PROJECT_DIR>/MEMORY.md
交付审计：DELIVERY AUDIT: PASS
测试完成，报告已生成；交付物已准备完毕。
```

**⛔ 任务完成标志**：当输出以下内容时，表示任务已完全结束，禁止再调用任何工具：
- "测试完成，报告已生成"
- "交付物已准备完毕"
- "所有阶段已完成"

**⚠️ 关键：阶段五的所有步骤全为 `✅` 且最终审计返回 `DELIVERY AUDIT: PASS` 后，才允许通过任务管理能力把整个任务标记为完成，并必须输出上述结束语之一，然后停止。不要继续执行任何工具调用。**
