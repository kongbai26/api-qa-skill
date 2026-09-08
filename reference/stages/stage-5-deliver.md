# 阶段五：交付

> **⛔ 本阶段需要额外读取：reference/test-doc.md。需要阶段一的产出（ALLURE=有/无）。**

## 目标

重新跑测试确保报告最新，整理交付物。

⚠️ **交付前必须重跑一次测试，确保报告是最新的。**

## 步骤清单（执行时必须逐项打勾，跳过禁止）

```
⬜ 1. 重跑 pytest
⬜ 2. 生成报告（allure generate 或 report_generator.py）
⬜ 3. 确认报告文件存在且大小 > 10KB
⬜ 4. 写 docs/test_cases.md
⬜ 5. 确认 run.sh/run.bat 存在
⬜ 6. 更新 MEMORY.md 最终结果
```

**执行规则**：每完成一项立即将 `⬜` 改为 `✅`，全部打勾后输出结束语，任务完成。

## ① 重跑测试

```
shell_exec(command="cd \"<PROJECT_DIR>\" && <PYTHON> -m pytest tests/ -v --tb=short --alluredir=allure-results")
```

⚠️ 如果 pytest 失败（阶段四已修完，阶段五不该再有失败）：
- 检查 `.env` 配置和依赖是否正确
- 修复后重新跑 pytest
- **最多重试 2 轮**，超过则告知用户问题未解决，展示当前结果

---

## ② 生成报告

⚠️ **禁止用 `allure serve` 或 `allure open`，禁止 `open` 任何文件。**
⚠️ **必须生成正式 HTML 测试报告，严禁自制 `TEST_REPORT.md` 等 Markdown 文件代替报告！** 只要未生成标准 HTML 报告，即视为未完成。

pytest 跑完后，先告诉用户测试结果摘要（通过/失败/跳过数量），然后生成报告：

**ALLURE=有**：
1. 执行 Allure 官方生成命令：
```
shell_exec(command="cd \"<PROJECT_DIR>\" && allure generate allure-results -o allure-report --clean")
```
2. 若系统具备 `report_build` 工具，立即调用以同步生成单文件大盘：
```
report_build(allure_results_dir="<PROJECT_DIR>/allure-results", output_path="<PROJECT_DIR>/allure-report/report.html", session_goal="API测试报告")
```

**ALLURE=无**：
若系统具备 `report_build` 工具，优先调用：
```
report_build(allure_results_dir="<PROJECT_DIR>/allure-results", output_path="<PROJECT_DIR>/allure-report/report.html", session_goal="API测试报告")
```
若无该工具，执行 Python 报告生成器（Zb-Report）生成命令：
```
shell_exec(command="cd \"<PROJECT_DIR>\" && <PYTHON> utils/report_generator.py --input allure-results --output allure-report/report.html")
```

⚠️ 如果报告生成失败，不要重试，在③中统一处理。

---

## ③ 确认报告已更新

检查报告文件是否存在且大小正常（> 10KB）：

**如果有 allure（ALLURE=有）**：
```
shell_exec(command="cd \"<PROJECT_DIR>\" && <PYTHON> -c \"import os; sz=os.path.getsize('allure-report/index.html') if os.path.exists('allure-report/index.html') else 0; print('OK' if sz > 10000 else 'FAIL')\"")
```
只检查 `allure-report/index.html` 存在且 > 10KB 即为成功。

**如果没有 allure（ALLURE=无）**：
```
shell_exec(command="cd \"<PROJECT_DIR>\" && <PYTHON> -c \"import os; sz=os.path.getsize('allure-report/report.html') if os.path.exists('allure-report/report.html') else 0; print('OK' if sz > 10000 else 'FAIL')\"")
```
只检查 `allure-report/report.html` 存在且 > 10KB 即为成功。

**⚠️ 关键：检查一次就够了，不要重复检查。**

**判断标准**：
- 检查通过（> 10KB）→ 报告生成成功，继续到④
- 检查失败（≤ 10KB 或不存在）→ 重新执行一次步骤②中的对应生成命令，**最多重试 1 次**，如果仍然失败则告知用户

---

## ④ 写 docs/test_cases.md

用 `save_file` 保存为 `<PROJECT_DIR>/docs/test_cases.md`（格式见 reference/test-doc.md）。

---

## ⑤ 确认所有文件完整

检查以下文件是否存在：
```
shell_exec(command="cd \"<PROJECT_DIR>\" && <PYTHON> -c \"import os; print('FOUND' if os.path.exists('run.sh') or os.path.exists('run.bat') else 'MISSING')\"")
```

如果缺失，直接生成：
```
read_file(path="<skill_dir>/reference/run-scripts.md")
```
然后用 `save_file` 保存到项目目录：
- OS_TYPE 是 Darwin 或 Linux → 保存为 `<PROJECT_DIR>/run.sh`，并执行 `shell_exec(command="chmod +x '<PROJECT_DIR>/run.sh'")`
- OS_TYPE 是 Windows → 保存为 `<PROJECT_DIR>/run.bat`
- ⚠️ 脚本文件必须且只能是 `run.sh` 或 `run.bat`，严禁命名为 `run_tests.sh`！

---

## ⑥ 更新 MEMORY.md 最终结果

将以下信息**追加写入** MEMORY.md：
1. **最终结果**（通过/失败/跳过数量）
2. **交付物清单**（报告路径、文档路径、脚本路径）
3. **遗留问题**（未修复的 API bug 等）

---

## 交付清单

- 测试代码（tests/ 目录）
- 用例文档（docs/test_cases.md）
- 测试报告（ALLURE=有 为 allure-report/index.html；ALLURE=无 为 allure-report/report.html）
- 差异列表（MEMORY.md 中记录）
- 运行说明（run.sh 或 run.bat）

## 产出

📝 MEMORY.md：最终结果、交付物、遗留问题。保存追加到 `<PROJECT_DIR>/MEMORY.md`。

全部完成后，可以输出纯文本总结，不需要再调用工具。

**⛔ 任务完成标志**：当输出以下内容时，表示任务已完全结束，禁止再调用任何工具：
- "测试完成，报告已生成"
- "交付物已准备完毕"
- "所有阶段已完成"

**⚠️ 关键：阶段五的所有步骤完成后，必须输出上述结束语之一，然后停止。不要继续执行任何工具调用。**
