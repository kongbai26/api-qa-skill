---
name: api-qa-skill
description: API 自动化测试：pytest+Allure 框架，5 阶段完整工作流 + 快速路径（≤5 个简单接口），生成专业测试报告
metadata:
  test-claw-tools: curl, web_fetch, web_search, get_datetime, format_datetime, read_file, save_file, edit_file, list_files, grep_search, glob_search, shell_exec, task_add, task_update, task_tree, Skill
  test-claw-lifecycle: workflow
---

# API 自动化测试 Skill

## 使用边界

- 完整流程按 5 个阶段执行；快速流程按 2 个阶段执行。接口数大于 5，或涉及支付、权限、工作流等复杂逻辑时，只能走完整流程。
- 本文件在一个项目首次激活时完整读取一次；之后只读取当前 stage 指定的文件。用户回复、工具恢复或上下文压缩后继续当前步骤，不重新开始。上下文确已丢失时才重读本文件和当前 stage。
- `SKILL_DIR` 必须来自 Skill 加载结果、安装路径或用户提供的克隆路径，不能由 CWD 猜测。Test-Claw 用 `SkillResource` 加载相对资源；需要结构化断点时可调用 `SkillLifecycle(action="await_user")`，交付门禁通过后调用 `SkillLifecycle(action="complete")`。其他宿主使用等价能力即可。
- 文件读取分页时必须继续到 EOF。标准资产由 `scripts/materialize_templates.py` 复制，不把模板正文读进模型上下文；只有 stage 明确要求时才读短 reference。
- 项目记录固定为 `<PROJECT_DIR>/MEMORY.md`，只记录配置和阶段产出，不记录凭据原文或清单状态，也不用 Agent 记忆、数据库或会话工作区替代。

## 入口路由

**续做、复用、纠正和是否重读只在这里判断。进入 stage 后不再重新路由。**

先判断本次输入属于哪一种：

1. **正在回答当前问题**：把答案用于当前待办项，继续该项；不重新询问复用，不重建清单。
2. **同一项目的新请求**：展示已锁定的流程、目录、接口范围、OS、Python、Allure、Base URL 和认证方式，只问一次“全部复用”还是“指出变更项”。未指出的值视为用户本次确认复用；完整流程的范围未变时，“全部复用”也沿用已确认计划。选择后从用户请求影响的第一个 stage 开始，不重做无关阶段。
3. **新项目或用户指定另一个项目**：执行下面的新项目路由；旧项目值只有在当前上下文明确存在，或用户指定旧项目 `MEMORY.md` 时才可供选择，不能由模型自动套用。

已经完成的阶段不重做。若工具证据证明某个已锁定值失效，只重新确认该值，然后回到原清单项；不能借此切换目录、流程或报告分支。

### 新项目路由

1. 获取用户要求的 API 文档或接口信息；只按用户本次指定的测试范围列出 `METHOD + path`，不能把单个接口自动扩成整个资源。接口数量必须与列出的行数一致。
2. 告知接口清单、认证方式和流程建议：
   - `≤5` 个简单接口：说明完整流程和快速流程，让用户选择。
   - `>5` 个接口或复杂业务：说明规则要求完整流程，请用户确认完整流程；不能接受快速流程。
3. 用户确认流程后，单独确认项目目录并等待回复。未指定时推荐系统桌面新建 `<service>-api-qa-skill`，但不能自动使用桌面或会话工作区。
4. 用户回复“默认”“桌面新建”“直接放桌面”等同义表达后，解析当前系统真实桌面并得到绝对路径；用户给相对路径时先请其确认展开后的绝对路径。目录确认前不检查、创建或写入候选项目。
5. 路径锁定后判断 `PROJECT_KIND`：目录不存在或为空为 `new`，已有用户文件为 `existing`。新项目若有合法旧值来源，展示旧环境与契约并询问“复用这些旧值 / 使用新值”；指定已有项目时读取其非敏感 `MEMORY.md`，询问“全部复用 / 指出变更项”。新项目的流程、目录、接口清单和完整流程计划始终重新确认。
6. 入口选择完成后读取对应 setup stage；后续 stage 只消费本次已确认的值。

符合快速条件时，流程确认必须同时说明两条路径：

```text
检测到 N 个接口：
1. METHOD /path
...
认证方式：<实际方式>

建议走<快速流程或完整流程>（<实际理由>）。
- 完整流程：5 个阶段，每接口约 15–20 条用例
- 快速流程：2 个阶段，每接口 3–5 条用例

请确认走完整流程还是快速流程？
```

不符合快速条件时，把建议改为“按规则必须走完整流程”，只请求用户确认完整流程。

项目目录问题使用以下格式：

```text
测试项目目录放在哪里？请选择新建还是追加到已有项目。
- 新建（推荐）：回复“默认”或“桌面新建”，使用当前系统真实桌面下的 <service>-api-qa-skill
- 追加：请提供已有项目的绝对路径
- 不会默认使用会话工作区；收到你的选择后再创建或更新项目
```

## 顺序门禁

| 顺序 | 必须取得的证据 |
|---|---|
| `FLOW_LOCK` | 用户确认流程；不符合快速条件时只能确认完整流程 |
| `PROJECT_LOCK` | 用户确认的绝对目录，或明确选择桌面后解析出的绝对目录 |
| `ENV_LOCK` | 用户确认复用，或已实际验证 OS、Python 和 `allure --version` |
| `CONTRACT_LOCK` | Base URL 与认证方式由用户、文档或本次复用决定确定 |
| `PLAN_LOCK` | 完整流程计划得到用户确认；快速流程不增加计划确认 |
| `STAGE_LOCK` | 当前 stage 清单按顺序全部 `✅` |
| `DELIVERY_LOCK` | 当前流程要求的交付文件均确认存在 |

每个 stage 首次进入时展示该 stage 的完整清单；始终处理第一个未完成项，取得工具或用户证据后立即打勾。宿主有任务能力时可用一个阶段任务承载同一清单，没有时在回复中维护文本清单；不能让任务工具的具体形态改变执行顺序。所有步骤打勾后才能进入下一阶段或输出结束语。

## 全流程不变量

1. 项目文件只写入 `<PROJECT_DIR>`。除环境探测外，项目命令先进入并核对该目录：POSIX 用 `cd "<PROJECT_DIR>" && pwd &&`，Windows 用 `cd /d "<PROJECT_DIR>" && cd &&`。
2. 环境首次确认必须验证 Python、OS，并实际执行 `allure --version`：成功记录 `ALLURE=有`，否则记录 `ALLURE=无`。命令能力被拒绝不能当作“无 Allure”，应停在环境确认。
3. `ALLURE=有` 只生成 `allure-report/index.html`；`ALLURE=无` 只使用本 Skill 模板生成 `allure-report/report.html`。禁止双报告、Markdown 报告、宿主通用报告器、`allure serve/open` 和自动打开浏览器。
4. 新项目或缺失资产使用物化器；已有定制文件由物化器返回 `PRESERVED/REVIEW` 后才读取并做最小适配。禁止手抄简化模板。
5. 当前 OS runner 必须在首次安装依赖或运行测试前交付：Darwin/Linux 为 `run.sh`，Windows 为 `run.bat`。runner 只跑测试并生成已锁定分支报告，不安装依赖；新项目只生成当前 OS 的一份。
6. `.env` 只由配置脚本在项目进程内合并。Agent 不读取、搜索或回显凭据；MEMORY 只记录凭据变量名。
7. 先真实探测并记录文档差异，再由模型依据用户确认的契约编写断言。禁止硬编码业务答案、`assert True`、传输层 mock 或为全绿放宽断言。
8. 所有测试请求使用项目统一封装 `allure_request` / `AuthSession`；每个用例包含中文标题、中文 docstring、中文 `expected` 和真实断言。
9. 完整流程每个 GET 至少 8 条、POST 至少 15 条，平均目标 15–20；快速流程每接口 3–5 条。数量以 `pytest --collect-only -q` 展开的 node 为准。
10. POST/PUT/PATCH/DELETE、并发、支付或权限变更测试必须先确认目标环境允许并确定清理策略。
11. 后续命令被拒绝时保留已经生成的文件，如实标注“未执行”，并给出 runner 手动命令；不能虚报测试或报告完成。
12. 交付阶段只确认要求的文件存在，不增加脚本语法双检、runner 实跑、报告内容解析或额外审计程序。

## 按需阶段

| 流程 | 读取顺序 |
|---|---|
| 快速 | `reference/stages/stage-quick-setup.md` → `reference/stages/stage-quick.md` |
| 完整一 | `reference/stages/stage-full-setup.md` |
| 完整二 | `reference/stages/stage-2-setup.md` |
| 完整三 | `reference/stages/stage-3-write.md`，步骤①再读 `reference/test-design.md` |
| 完整四 | `reference/stages/stage-full-test.md` |
| 完整五 | `reference/stages/stage-5-deliver.md`，写文档时再读 `reference/test-doc.md` |

只有核心文件冲突或动态认证时读 `reference/implementation.md`；只有 runner 冲突或物化命令不可用时读 `reference/run-scripts.md`。阶段细节、重试上限和 MEMORY 产出以当前 stage 为准。
