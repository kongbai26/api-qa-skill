# 阶段五：交付

> **⛔ 按需加载：④才读取 `reference/test-doc.md`。本阶段不重跑测试、不重新生成报告，也不重新物化或实跑 runner。**
>
> **MEMORY 文件边界**：本阶段所有 `MEMORY.md` 均指 `<PROJECT_DIR>/MEMORY.md`，必须用文件写入工具追加，供用户查看；不得使用 Agent 工作区记忆、数据库、`memory_save` 或 `memory_recall` 保存或恢复本流程数据。

## 目标

确认前序阶段已经产出的文件齐全，补齐用例文档和项目记录，然后向用户交付。

## 步骤清单（执行时必须逐项打勾）

```text
⬜ 1. 确认测试代码和 Allure 原始结果存在
⬜ 2. 确认锁定分支的唯一报告入口存在
⬜ 3. 确认当前 OS 运行脚本已经交付
⬜ 4. 写 docs/test_cases.md
⬜ 5. 更新 MEMORY.md 并输出交付说明
```

**执行规则**：仅首次进入本阶段时建立上述同一份清单；等待用户或恢复执行后复用原清单，从首个未完成项继续。有任务工具时逐项创建并保存引用，没有时持续更新文本清单。每完成一项立即由 `⬜` 改为 `✅`，五项全部完成后才能输出结束语。最终判断只基于本次测试结果与交付文件是否齐全，不增加语法双检、脚本实跑、报告内容解析或独立审计。

---

## ① 确认测试代码和原始结果

使用文件枚举能力确认：

- `tests/` 下至少有一个 `test_*.py`
- `allure-results/` 下至少有一个 `*-result.json`
- `conftest.py`、`pytest.ini`、`requirements.txt`、`utils/request_helper.py` 均存在

这些文件由前序阶段生成并运行。本步骤只检查存在性，不重复执行 pytest。缺少测试代码时返回阶段三；缺少原始结果时返回阶段四运行测试。不得凭空补写结果文件。

---

## ② 确认唯一报告入口

按 `ENV_LOCK` 已锁定的 `ALLURE` 分支检查一次：

- `ALLURE=有`：`allure-report/index.html` 存在，`allure-report/report.html` 不存在
- `ALLURE=无`：`allure-report/report.html` 存在，`allure-report/index.html` 不存在

检查通过即完成本项，不解析报告内部资源、不扫描项目其他 HTML/Markdown，也不重新生成报告。所选入口缺失或另一入口同时存在时，返回阶段四按锁定分支重新生成一次；仍失败则如实交付当前状态，禁止声称报告已经完成。

---

## ③ 确认当前 OS 运行脚本

脚本应已在阶段二、首次安装依赖或运行测试之前物化：

- Darwin/Linux：`run.sh` 存在；如果执行权限缺失，只补 `chmod +x run.sh`
- Windows：`run.bat` 存在

脚本存在时不重新物化、不做额外语法检查，也不在本阶段自动运行。脚本缺失时才调用一次 `scripts/materialize_templates.py --component runner`，仍只生成当前 OS 对应的一份；已有项目不删除用户原有的另一平台脚本。

若命令能力不可用但脚本文件已经存在，本项仍可按“已交付、未实跑”完成，并在最终回复给出手动命令：

- Darwin/Linux：`cd "<PROJECT_DIR>" && chmod +x run.sh && ./run.sh`
- Windows：`cd /d "<PROJECT_DIR>" && call run.bat`

---

## ④ 写 `docs/test_cases.md`

完整读取：

```text
read_file(path="<SKILL_DIR>/reference/test-doc.md")
```

按格式写入非空的 `<PROJECT_DIR>/docs/test_cases.md`。文档应覆盖接口用途、前置条件、步骤、请求信息和预期结果；不为了适配机器解析器增加固定占位内容。

---

## ⑤ 更新 MEMORY 并交付

以阶段四已经稳定的结果为准，在 `<PROJECT_DIR>/MEMORY.md` 追加：

1. 最终通过、失败、跳过数量
2. 测试代码、原始结果、报告、文档、运行脚本的实际路径
3. 已确认的 API 缺陷或遗留问题；没有则写“无遗留问题”
4. 阶段五完成日期和交付结论

最后确认以下交付物存在：

- 测试代码：`tests/`
- 原始结果：`allure-results/`
- 唯一测试报告：`allure-report/index.html` 或 `allure-report/report.html`
- 当前 OS 运行脚本：`run.sh` 或 `run.bat`
- 用例文档：`docs/test_cases.md`
- 项目记录：`MEMORY.md`

全部存在后把第⑤项标为 `✅`，展示五项全为 `✅` 的清单并按以下结构交付：

```text
完整流程交付清单：阶段五 5 项全部 ✅
测试结果：通过 N，失败 N，跳过 N
项目目录：<PROJECT_DIR 绝对路径>
测试代码：<tests/ 下实际文件>
用例文档：<PROJECT_DIR>/docs/test_cases.md
测试报告：<唯一报告入口绝对路径>
原始结果：<PROJECT_DIR>/allure-results/
运行脚本：<当前 OS 对应脚本绝对路径>（已交付，供用户复跑）
测试状态：已执行 | 未执行；未执行时请用户运行上述手动命令
项目记录：<PROJECT_DIR>/MEMORY.md
测试完成，报告已生成；交付物已准备完毕。
```

不得输出不存在的路径，也不得把“文件已交付”写成“脚本已经实跑”。结束语输出后停止调用工具。
