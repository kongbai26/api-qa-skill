# 阶段五：交付

> **⛔ 本阶段需要额外读取：reference/test-doc.md。需要阶段一的产出（ALLURE、PROJECT_KIND），结束时执行 scripts/validate_delivery.py。**

> **MEMORY 文件边界**：本阶段所有 `MEMORY.md` 均指 `<PROJECT_DIR>/MEMORY.md`，必须用文件写入工具追加，供用户查看；Agent 工作区记忆、数据库或 `memory_save` 不能替代该文件。

## 目标

重新跑测试确保报告最新，整理交付物。

⚠️ **交付前必须重跑一次测试，确保报告是最新的。**

## 步骤清单（执行时必须逐项打勾，跳过禁止）

```
⬜ 1. 重跑 pytest
⬜ 2. 生成单一报告
⬜ 3. 确认所选报告入口存在且非空
⬜ 4. 写 docs/test_cases.md
⬜ 5. 确认 OS_TYPE 对应的一个运行脚本存在
⬜ 6. 更新并验收 `<PROJECT_DIR>/MEMORY.md` 最终结果
```

**执行规则**：每完成一项立即将 `⬜` 改为 `✅`，全部打勾后输出结束语，任务完成。

## ① 重跑测试

```
shell_exec(command="<ENTER_PROJECT> <PYTHON> -m pytest tests/ -v --tb=short --alluredir=allure-results --clean-alluredir")
```

⚠️ 如果 pytest 失败（阶段四已修完，阶段五不该再有失败）：
- 不读取 `.env`；核对 MEMORY 的非敏感配置、请用户确认本地凭据已填写，并检查依赖与 API 可用性
- 修复后重新跑 pytest
- **最多重试 2 轮**，超过则告知用户问题未解决，展示当前结果

---

## ② 生成报告

⚠️ **禁止用 `allure serve` 或 `allure open`，禁止 `open` 任何文件。**

pytest 跑完后，先告诉用户测试结果摘要（通过/失败/跳过数量），然后生成报告：

**ALLURE=有** → 只生成官方 Allure 报告：
```
shell_exec(command="<ENTER_PROJECT> allure generate allure-results -o allure-report --clean")
```

**ALLURE=无** → 只用内置生成器生成单文件报告：
```
shell_exec(command="<ENTER_PROJECT> <PYTHON> utils/report_generator.py --input allure-results --output allure-report/report.html --clean")
```

两条分支互斥；ALLURE=有只保留 `index.html`，ALLURE=无只保留 `report.html`。

⚠️ 如果报告生成失败，不要重试，在③中统一处理。

---

## ③ 确认报告已更新

检查所选报告入口存在、非空，且另一个入口不存在：

**如果有 allure（ALLURE=有）**：
```
shell_exec(command="<ENTER_PROJECT> <PYTHON> -c \"from pathlib import Path; import sys; p=Path('allure-report/index.html'); q=Path('allure-report/report.html'); sys.exit(0 if p.is_file() and p.stat().st_size > 0 and not q.exists() else 1)\"")
```

**如果没有 allure（ALLURE=无）**：
```
shell_exec(command="<ENTER_PROJECT> <PYTHON> -c \"from pathlib import Path; import sys; p=Path('allure-report/report.html'); q=Path('allure-report/index.html'); sys.exit(0 if p.is_file() and p.stat().st_size > 0 and not q.exists() else 1)\"")
```

**⚠️ 关键：检查一次就够了，不要重复检查。**

**判断标准**：
- 所选入口存在且非空、另一入口不存在 → 报告生成成功，继续到④
- 否则 → 按当前 ALLURE 分支重新生成并再次检查，**最多重试1次**；仍失败则告知用户，禁止输出报告生成成功

---

## ④ 写 docs/test_cases.md

格式见 reference/test-doc.md。

---

## ⑤ 确认当前 OS 运行脚本

只检查当前 OS 对应的脚本是否存在：

OS_TYPE 是 Darwin 或 Linux：
```
shell_exec(command="<ENTER_PROJECT> test -x run.sh")
```

OS_TYPE 是 Windows：
```
shell_exec(command="<ENTER_PROJECT> if exist run.bat (echo run.bat exists) else (echo MISSING: run.bat & exit /b 1)")
```

如果缺失，直接生成：
```
read_file(path="<skill_dir>/reference/run-scripts.md")
```
然后用 `save_file` 保存到项目目录：
- OS_TYPE 是 Darwin 或 Linux → 保存为 run.sh
- OS_TYPE 是 Windows → 保存为 run.bat
- 新项目禁止同时生成两份；追加已有项目时不删除用户原有的另一平台脚本

---

## ⑥ 更新 `<PROJECT_DIR>/MEMORY.md` 最终结果

将以下信息**追加写入** `<PROJECT_DIR>/MEMORY.md`：
1. **最终结果**（通过/失败/跳过数量）
2. **交付物清单**（报告路径、文档路径、脚本路径）
3. **遗留问题**（未修复的 API bug 等）

写入后执行最终交付审计：

```text
shell_exec(command="<ENTER_PROJECT> <PYTHON> \"<skill_dir>/scripts/validate_delivery.py\" --project \"<PROJECT_DIR>\" --mode full --os <OS_TYPE> --report <official|fallback> --project-kind <PROJECT_KIND>")
```

`ALLURE=有` 时 `--report official`，否则 `--report fallback`。审计脚本只检查 `.env` 是否存在/非空，不读取内容。它必须同时验证测试代码、核心框架、Allure 原始结果、唯一报告入口、`docs/test_cases.md`、当前 OS 脚本和 MEMORY。任一项失败，本阶段不得完成；修复对应项后只重跑一次审计，仍失败则如实告知用户，禁止输出完成标志。

---

## 交付清单

- 测试代码（tests/ 目录）
- 用例文档（docs/test_cases.md）
- 测试报告（allure-report/index.html 或 allure-report/report.html）
- 差异列表（`<PROJECT_DIR>/MEMORY.md` 中记录）
- 当前 OS 对应的运行说明（Darwin/Linux 为 run.sh，Windows 为 run.bat）

## 产出

📝 `<PROJECT_DIR>/MEMORY.md`：最终结果、交付物、遗留问题。**必须更新并验收该项目文件。**

## 双重保存

先写并验收 `<PROJECT_DIR>/MEMORY.md`；数据库可用时再额外写数据库。数据库或 Agent 记忆不可替代项目文件。

全部完成后，可以输出纯文本总结，不需要再调用工具。

**⛔ 任务完成标志**：当输出以下内容时，表示任务已完全结束，禁止再调用任何工具：
- "测试完成，报告已生成"
- "交付物已准备完毕"
- "所有阶段已完成"

**⚠️ 关键：阶段五的所有步骤完成后，必须输出上述结束语之一，然后停止。不要继续执行任何工具调用。**
