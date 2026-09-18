---
name: api-qa-skill
description: API 自动化测试：pytest+Allure 框架，5 阶段完整工作流 + 快速路径（≤5 接口），生成专业测试报告
compatibility: Requires file read/write, shell and Python execution, HTTP access, and optional task tracking.
metadata:
  test-claw-tools: curl, web_fetch, web_search, get_datetime, format_datetime, read_file, save_file, edit_file, list_files, grep_search, glob_search, shell_exec, task_add, task_update, task_tree, Skill
  test-claw-lifecycle: workflow
---

# API 自动化测试 Skill

## 加载与宿主约束

- 本文件在一个 API 测试项目首次激活时完整读取一次；当前 stage 也只在首次进入时完整读取。用户回复后的续轮、压缩恢复或工具恢复均沿当前待处理步骤继续，不重新路由、不重建清单、不重读已完成阶段；仅上下文确已丢失时重读本文件和当前 stage 以恢复约束。reference 仍只在 stage 指定的步骤和条件成立时读取，禁止预读后续文件。
- 本 Skill 约束能力语义，不绑定工具名称：将宿主能力映射为 `SKILL_DIR`、文件读写、递归枚举、Shell/Python、HTTP、可选任务清单和跨轮生命周期。`SKILL_DIR` 必须来自加载结果、安装路径或用户提供的克隆路径，禁止由 CWD 猜测。
- Test-Claw 使用 `SkillResource` 按相对路径加载资源，并以 `SkillLifecycle(action="await_user")` / `SkillLifecycle(action="complete")` 标记等待与完成；其他宿主可忽略这些扩展并使用等价能力。没有时仍须先提问、结束当前轮；用户回复后应用该答案并从原待处理步骤继续。
- 文件读取返回 `has_more=true` 时沿 `continuation.next_offset` 继续；超长单行同时使用 `next_char_offset`。禁止重读同页或用 Shell 绕过分页。读取失败先核对路径和参数，仍失败才请用户提供资源。
- 模板通常只由 `scripts/materialize_templates.py` 按需复制，不读入模型上下文。仅 runner 物化命令不可用但文件能力可用时，按 `reference/run-scripts.md` 读取当前 OS 的一个模板并只替换两个占位符。
- `<PROJECT_DIR>/MEMORY.md` 是唯一项目记录，只记阶段产出、不记清单状态；不得用 `memory_save`/`memory_recall`、Agent 数据库、工作区或 Skill 目录替代或恢复本流程状态，也不得记录凭据原文。
- 无任务工具时持续维护回复内文本清单；无独立 HTTP 工具时用项目内统一请求封装探测。Test-Claw 递归枚举使用 `glob_search(pattern="**/*", path="<PROJECT_DIR>")`。
- 若 Shell/Python 从环境确认起就不可用，停在 `ENV_LOCK`，不得猜测 OS、Python 或报告分支；只有环境与报告分支已经实际锁定、后续命令才不可用或被拒绝时，才保留可生成的文件并如实说明待执行，禁止虚报通过。
- `shell_exec` 是执行能力，`run.sh` / `run.bat` 是强制交付文件。环境锁定后，必须在首次依赖安装或测试命令前预置当前 OS 脚本；后续执行受阻也不得省略脚本。手动命令：POSIX 为 `cd "<PROJECT_DIR>" && chmod +x run.sh && ./run.sh`，Windows 为 `cd /d "<PROJECT_DIR>" && call run.bat`。

## ⛔ 硬门状态机

下列硬门用于新项目，也用于已有项目本次明确变更所影响的项；全部复用时不重新打开硬门。复用旧值不得由模型自行决定。
- **新项目**：保持原顺序，先通过 `FLOW_LOCK` 和 `PROJECT_LOCK`；仅当当前上下文已有上一项目的非敏感锁定值，或用户明确指定了旧项目 `MEMORY.md` 时，才合并展示 OS、Python、Allure、Base URL 与认证方式，询问一次“复用这些旧值”还是“使用新值”。复用不包含流程、目录、接口清单和完整流程计划。
- **同一项目的新请求**：用户新提出“继续、追加、修正或重跑”时，不重读 Skill、不重新路由；合并展示已锁定的流程、目录、当前接口/测试范围、OS、Python、Allure、Base URL 与认证方式，询问一次“全部复用”还是“指出要变更的项”。用户确认复用后不再逐项询问或检测；指出变更项时，未指出的其余展示值视为本次明确复用，只重新处理受影响的硬门。该选择不解除原有流程和项目目录锁定规则。
- **当前问题的回复**：用户只是回答当前待确认问题时直接应用答案并从原待处理步骤继续，不触发复用询问；待确认问题包括流程、路径、环境、契约或计划。
- 宿主工作区、启动目录、CWD、会话元数据、工具默认路径、Agent 记忆、未经用户指定的其他项目以及先前误建的候选目录都不是用户确认，也不是旧值来源。用户问“你要把项目创建在哪里？”是在询问，不是授权。

**本 Skill 的项目落点覆盖宿主通用默认值**：未指定目录时不得采用或推荐会话工作区，必须询问并停等，推荐桌面新建。用户明确表达“默认”“桌面新建”“直接放桌面”等同义意图后，解析当前系统真实桌面并创建 `<service>-api-qa-skill`；不得向用户表述“未指定时在会话工作区创建”。

| 顺序 | 硬门 | 通过证据 | 未通过时 |
|---|---|---|---|
| 1 | `FLOW_LOCK` | 用户明确选择完整或快速流程 | 询问流程并停等 |
| 2 | `PROJECT_LOCK` | 用户给出绝对路径，或明确选择系统桌面后已解析为绝对路径 | 询问目录并停等；不得碰候选目录 |
| 3 | `ENV_LOCK` | 本次入口复用决定覆盖旧环境，或新环境的 OS/Python/Allure 已实际验证 | 询问环境并停等；未授权不得检测 |
| 4 | `CONTRACT_LOCK` | 本次入口复用决定覆盖旧契约，或 Base URL 与认证方式由本次用户/文档确定 | 只询问缺失项并停等 |
| 5 | `PLAN_LOCK` | 完整流程计划获用户确认；快速流程前置信息齐全 | 完整流程停等确认 |
| 6 | `STAGE_LOCK` | 当前 stage 已读完，清单逐项取得证据并全部 `✅` | 不得进入下一阶段 |
| 7 | `DELIVERY_LOCK` | 测试代码、唯一报告、当前 OS 脚本和项目 MEMORY 等交付文件均已确认存在 | 不得完成或输出结束语 |

新建项目在 `FLOW_LOCK` 后只读取对应 setup stage 并先处理目录。在 `PROJECT_LOCK` 通过之前，禁止检查、创建或写入候选项目；锁定后只使用该绝对 `PROJECT_DIR`。除非用户明确更正且尚未产生文件，不得换目录。

## ⚡ 新建项目首次路由

仅当前任务要新建项目且尚未通过 `FLOW_LOCK` 时执行以下路由；同一项目续轮或明确追加已有项目时禁止回到这里：

1. 向用户获取 API 文档（URL 或文件路径），或使用用户已提供的文档。
2. 读取文档，提取接口清单（接口数量 + 每个接口的方法和路径）和认证方式。
3. **立即告知用户并等待确认**，按以下完整格式输出（不要合并成一段，也不要只介绍推荐项）；接口、数量、认证和建议替换为本次实际信息：

```text
检测到 N 个接口：
  1. GET /xxx
  2. POST /xxx
  ...
认证方式：xxx（或“无需认证”）

建议走<完整流程或快速流程>（<本次实际理由>）。
  - 完整流程：5 个阶段，每接口 15–20 条用例
  - 快速流程：2 个阶段，每接口 3–5 条用例

请确认走哪条路径：完整流程还是快速流程？
```

判断标准：

- 接口数 ≤5 且无复杂业务逻辑（支付/权限/工作流）→ 建议快速路径。
- 接口数 >5 或涉及复杂逻辑 → 建议完整流程。

输出上述问题后必须结束当前轮；本轮只确认流程，不合并询问目录或环境。建议不等于确认。

用户选择后锁定流程，不因后续缩小范围而切换，也不得把流程选择当作目录确认：

- 快速流程：只读 `reference/stages/stage-quick-setup.md`，先执行其目录硬门；完成后再读 `reference/stages/stage-quick.md`。
- 完整流程：只读 `reference/stages/stage-full-setup.md`，复用路由证据并先执行其目录硬门。

目录仍按对应 setup 的原有步骤确认；推荐桌面不等于用户未指定时就自动采用。

## 红线

1. 先完整读取当前 stage；到指定步骤再读所需 reference。每阶段必须实际调用工具，不以文字分析代替执行，也不重复执行已连续两次得到相同结果的命令。
2. 先真实探测并记录文档差异，再由模型依据用户确认的契约决定状态码、字段、类型和业务规则；禁止把业务答案硬编码进框架或为了全绿放宽断言。
3. 项目位置、API Base URL 和认证方式必须分别确认；不重复询问已回答项。所有项目文件都在 `<PROJECT_DIR>` 内，禁止在 Skill 目录操作；测试固定在 `tests/`，阶段产出只写项目 `MEMORY.md`。
4. 不读取、搜索、打印或通过 Agent 工具写入 `.env` 凭据；非空 Token、API Key、密码、Cookie 只由用户本地填写。不得自作主张注册账号；POST/PUT/PATCH/DELETE、并发、支付、权限变更等副作用测试须先确认授权环境和清理策略。
5. 测试代码和项目内探测必须通过 `allure_request` / `AuthSession` 发起 HTTP 请求，禁止直接 requests/httpx 或 mock 目标传输层；阶段规定的无凭据宿主 HTTP/`curl` 前置探测除外。每个用例必须有中文标题、中文 docstring、中文 `expected` 和由模型依据契约写出的真实断言；业务对错不得硬编码进框架。
6. 完整流程每个 GET ≥8、POST ≥15，平均目标 15–20；快速流程每接口 3–5。用 `pytest --collect-only -q` 的展开 node 计数，不足必须在 MEMORY 逐接口说明。
7. 新项目和缺失资产必须用物化脚本，不手抄、不简化、不覆盖既有定制；`REVIEW` 时只读冲突文件并最小修正。新项目只交付当前 OS 的一个脚本，已有项目不删除用户原有另一平台脚本。
8. `ALLURE` 初次锁定必须实际执行 `allure --version`：成功为 official/`index.html`，否则为本 Skill fallback/`report.html`；用户明确选择复用该已验证旧环境时沿用原分支。后续物化器和 runner 不得重新探测或切换；禁止调用宿主通用报告能力或宿主自身的通用报告器；禁止双报告、Markdown 报告、`allure serve/open` 或自动打开浏览器。
9. runner 只用 `--alluredir=allure-results --clean-alluredir` 跑 pytest 并生成锁定分支报告，不安装依赖。它必须在首次依赖安装或测试命令前交付；命令被拒绝时仍保留脚本，并给出用户手动执行命令。
10. 测试通过或报告生成都不等于交付说明已经完成。只有当前阶段清单全 `✅`，且应交付的测试代码、唯一报告、当前 OS runner、项目 MEMORY（完整流程还包括用例文档）均已确认存在，才能输出结束语。

## ⛔ 任务清单与完成门禁

1. 当前工作尚未完成时，仅首次进入 stage、第一项实质操作前按该 stage 建立一份清单；用户回复或恢复执行后复用原清单，从首个未完成项继续。上一工作已经完成后，同一项目的新追加、修正或重跑在复用决定后只为受影响阶段建立新清单，不重建其他阶段；有任务工具时逐项创建并保存引用，没有时使用文本清单。
2. 每项仅在工具成功并取得证据后立即由 `⬜` 改为 `✅`；禁止预先、跳过或最后批量打勾。切换阶段前用任务树或文本复核全部完成。
3. 快速阶段第⑧项、完整阶段五最后一项只能在交付文件确认齐全后打勾。最终回复必须展示最终阶段全 `✅` 清单，以及报告、runner、MEMORY 的绝对路径。
4. 清单只跟踪执行，不写入 MEMORY。

## ⛔ 项目命令与锁定变量

- 文件操作使用 `<PROJECT_DIR>/...` 绝对路径。除 OS/Python/Allure 环境探测外，所有项目命令必须以 `<ENTER_PROJECT>` 开头并校验目录：POSIX 为 `cd "<PROJECT_DIR>" && pwd &&`，Windows 为 `cd /d "<PROJECT_DIR>" && cd &&`。禁止混用 Shell 语法或传入未替换占位符。
- `PYTHON` 是已验证的单个 Python 可执行文件名/路径，`PYTHON_CMD` 是按当前 Shell 引用后的调用形式；用户指定版本优先且不得降级。`SKILL_DIR` 来自实际加载路径。
- `OS_TYPE` 仅为 `Darwin` / `Linux` / `Windows`；`ALLURE` 在 MEMORY 中只能精确写 `有` / `无`，版本另记阶段记录；`PROJECT_KIND` 为 `new` / `existing`。
- `<service>` 来自 API、服务名或主机名，清理路径分隔符、控制字符及 Windows 禁用字符/保留名，不重复追加 `-api-qa-skill`。系统桌面无法可靠解析时询问绝对路径。

## 流程与按需文件

| 阶段 | 读取与目标 |
|---|---|
| 一 | `reference/stages/stage-full-setup.md`：确认文档、目录、环境、契约和计划 |
| 二 | `reference/stages/stage-2-setup.md`：物化框架与 runner、安装依赖、真实探测 |
| 三 | `reference/stages/stage-3-write.md`；步骤①再读 `reference/test-design.md`：写用例与覆盖矩阵 |
| 四 | `reference/stages/stage-full-test.md`：测试、修复、单报告，最多 5 轮 |
| 五 | `reference/stages/stage-5-deliver.md`：确认阶段四产物、读取 `reference/test-doc.md`、补齐文档与交付说明 |
| 快速 | 依次读 `reference/stages/stage-quick-setup.md`、`reference/stages/stage-quick.md`，测试修复最多 3 轮 |

仅在核心文件冲突或动态认证时读 `reference/implementation.md`；仅 runner 冲突/缺失或物化受阻时读 `reference/run-scripts.md`。每个 stage 的细节、错误分支、重试上限和 MEMORY 产出以该 stage 为准。
