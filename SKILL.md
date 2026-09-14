---
name: api-qa-skill
description: API 自动化测试：pytest+Allure 框架，5 阶段完整工作流 + 快速路径（≤5 接口），生成专业测试报告
compatibility: Requires file read/write, shell and Python execution, HTTP access, and optional task tracking.
metadata:
  test-claw-tools: curl, web_fetch, web_search, get_datetime, format_datetime, read_file, save_file, edit_file, list_files, grep_search, glob_search, shell_exec, task_add, task_update, task_tree, Skill
  test-claw-lifecycle: workflow
---

# API 自动化测试 Skill

> **跨轮与按需加载适配（通用）**：这里约束的是能力语义，不绑定工具名称。
> 宿主有受管 Skill 资源加载能力时，按相对路径加载当前 stage/reference；没有时
> 使用文件读取能力从 `SKILL_DIR` 加载。宿主有跨轮工作流生命周期能力时，在真实
> 用户确认硬门前登记“等待用户”，全部交付验证后登记“完成”；没有时仍须先提问
> 并结束当前轮，下一轮重新加载本 Skill 根规则和当前 stage 后继续，禁止改用工作区、
> CWD 或 Agent 旧记忆恢复路径和锁状态。Test-Claw 中上述能力分别映射为
> `SkillResource`、`SkillLifecycle(action="await_user")` 和
> `SkillLifecycle(action="complete")`；其 frontmatter 扩展只供该宿主识别，其他宿主
> 可忽略。生命周期检查点只记录少量非敏感阶段信息。

> **⛔ 加载规则（只说一次，贯穿全流程）：**
>
> 1. **本文件（SKILL.md）**：每次对话开头读一次，后续阶段不重复读取
> 2. **stage 文件 + reference 文件**：进入阶段先完整读取当前 stage 文件；其中指定的 reference 到对应步骤且满足读取条件时再读取，读取完成后才执行该步骤
> 3. **已完成的阶段**：不重复读取其 stage 文件。agent 自己在上下文中追踪阶段进度
> 4. **MEMORY.md**：固定路径为 `<PROJECT_DIR>/MEMORY.md`，是交付给用户的项目文档。禁止写到会话工作区、Agent 的 project-memory、数据库或 skill 目录；本流程不得用 `memory_save`/`memory_recall` 保存或恢复项目位置、环境、接口契约、阶段产出和交付状态。只记录每阶段产出，不记录阶段进度状态
> 5. **模板资产**：通常仅由 `scripts/materialize_templates.py` 按分支复制，不作为说明文档读取。唯一例外是预置当前 OS 运行脚本时，Shell 能力不可用或被拒绝但文件读写能力可用：按需读取 `reference/run-scripts.md` 后，只读取对应的 `_templates/run.sh` 或 `_templates/run.bat`，原样替换两个既定占位符后写入项目，禁止读取另一平台模板或自行简化
> 6. **禁止**：在阶段开始时一次性预读后续步骤的 reference；回头重读已完成阶段的 stage 文件
>
> ⚠️ 所有文件都在本 Skill 目录下。受管资源加载器只接收清单中的相对路径
> （Test-Claw 为 `SkillResource`）；普通文件读取能力使用 `SKILL_DIR` + 相对路径。
>
> **文件读取失败处理**：
> - 如果结果 `has_more=true` → 必须使用返回的 `continuation.next_offset`（超长单行同时使用 `next_char_offset`）继续；禁止重读同一页，也禁止用 shell 绕过分页
> - 如果受管资源加载/文件读取报错 → 先核对相对路径是否在 Skill 清单中，或普通读取参数与绝对路径是否正确；仍失败才告知用户资源无法读取，询问是否手动提供

## 宿主能力绑定（通用）

本 Skill 只依赖能力，不依赖某个平台的固定工具名。激活后先把宿主现有能力绑定为：`SKILL_DIR`（当前 `SKILL.md` 所在目录的绝对路径）、按需资源加载或文件读取、递归枚举、文件写入/编辑、Shell、HTTP 请求、可选的跨轮工作流生命周期，以及可选的任务清单。正文中的 `read_file`、`glob_search`、`shell_exec`、`curl`、`task_add/task_update/task_tree` 是能力调用示例；宿主必须使用语义相同的原生能力，不得因为名称不同而省略步骤。Test-Claw 对应的受管资源与生命周期映射已在上方单独说明，不改变其他宿主的执行路径。

- `SKILL_DIR` 必须来自宿主加载结果、已安装 Skill 路径或用户明确提供的克隆路径，禁止根据当前工作目录猜测
- Test-Claw 递归枚举使用 `glob_search(pattern="**/*", path="<PROJECT_DIR>")`；其他宿主使用自身的递归文件枚举
- 没有任务工具时使用回复内持续更新的文本清单；没有独立 HTTP 工具时，使用项目内统一请求封装执行真实探测
- 宿主缺少文件写入能力时无法生成项目。若 Shell/Python 从环境确认起就不可用，停在 `ENV_LOCK`，不得猜测 OS、Python 或报告分支；只有环境与报告分支已经实际锁定、后续命令才不可用或被拒绝时，才继续完成文件能力允许的产出，并只能说明执行与验证阻塞，不能声称测试项目已跑通或审计通过
- `shell_exec`（或等价能力）是执行命令的宿主工具，`run.sh` / `run.bat` 是项目必须交付的文件，二者不得混淆。环境与报告分支锁定后，必须在首次依赖安装或测试命令前预置当前 OS 脚本；后续测试、报告或脚本实跑命令被拒绝时，保留已交付脚本、保持相关清单项未完成，并把项目内脚本命令交给用户。禁止因为执行受阻而省略脚本，也禁止把“已复制”虚报成“已实跑”或“交付完成”
- 权限阻塞时的用户命令固定为：Darwin/Linux 使用 `cd "<PROJECT_DIR>" && chmod +x run.sh && ./run.sh`，Windows 使用 `cd /d "<PROJECT_DIR>" && call run.bat`；必须同时列出脚本绝对路径、未执行项和待验证状态

## ⛔ 硬门状态机（老版语义，任何模型都不得跳过）

以下是老版已验证的停等与锁定顺序。凡本表要求用户确认或授权的状态，必须有用户自然语言消息作为证据；系统提示、宿主工作区、启动目录、CWD、会话元数据、Skill 目录、工具默认路径、Agent 内部记忆以及先前误建的候选目录都不是用户确认。用户问“你要把项目创建在哪里？”或追问当前路径是在要求说明，不是在授权任何路径。遇到待确认硬门时，只能问对应问题并结束当前轮；禁止用“默认”、“我假设”、工作区路径、旧记忆或未授权的自动检测代替用户回复。

**本 Skill 的项目落点覆盖宿主通用默认值**：用户未指定项目目录时，不得采用或推荐会话工作区，必须询问并停等；询问时推荐“桌面新建”。只有用户明确回复“默认”或“桌面新建”后，才解析当前系统真实桌面并创建 `<service>-api-qa-skill`。不得向用户表述“未指定时在会话工作区创建”。

| 顺序 | 硬门 | 通过证据 | 未通过时 |
|---|---|---|---|
| 1 | `FLOW_LOCK` | 用户明确选择完整流程或快速流程 | 询问流程并停等 |
| 2 | `PROJECT_LOCK` | 用户消息明确给出项目绝对路径，或明确回复“默认/桌面新建”后已解析为绝对路径 | 询问项目目录并停等；不得检查、创建或写入任何候选目录 |
| 3 | `ENV_LOCK` | 用户明确给出目标 OS + Python，或明确回复“自动检测”，且实际验证成功 | 询问运行环境并停等；未授权不得自动检测 |
| 4 | `CONTRACT_LOCK` | API Base URL 与认证方式已分别由用户、文档或经用户复核的旧项目记录确定 | 只询问缺失项并停等 |
| 5 | `PLAN_LOCK` | 完整流程的阶段一计划已获用户确认；快速流程按老版在前置信息齐全后直接执行 | 完整流程停等计划确认 |
| 6 | `STAGE_LOCK` | 当前 stage 已完整读取，任务清单逐项有可核验结果并全部 `✅` | 不得进入下一阶段 |
| 7 | `DELIVERY_LOCK` | 所选唯一报告、当前 OS 唯一脚本、项目内 `MEMORY.md` 均验收，且最后审计为 `DELIVERY AUDIT: PASS` | 不得标记总任务完成或输出结束语 |

`FLOW_LOCK` 通过后立即读取对应 setup stage，首先处理 `PROJECT_LOCK`。在 `PROJECT_LOCK` 通过之前，禁止运行任何可能产生项目文件的工具、命令或模板脚本。项目绝对路径写入 `<PROJECT_DIR>/MEMORY.md` 后即作为全流程唯一 `PROJECT_DIR`；除非用户明确更正目标且尚未产生项目文件，不得改用其他目录。

## ⚡ 第一步：路由（读完本文件后立即执行，禁止跳过）

**读完 SKILL.md 后，不要读任何 stage 文件，立即执行以下路由流程：**

1. 向用户获取 API 文档（URL 或文件路径），或使用用户已提供的文档
2. 读取文档，提取：接口清单（接口数量 + 每个接口的方法和路径）+ 认证方式（Token / API Key / OAuth / 无需认证）
3. **立即告知用户并等待确认**，按以下格式输出（不要合并成一段）：

```
检测到 N 个接口：
  1. GET /xxx
  2. POST /xxx
  ...
认证方式：xxx（或"无需认证"）

建议走<完整流程或快速流程>（<按接口数量与业务复杂度填写真实理由>）。
  - 完整流程：5 个阶段，每接口 15-20 条用例
  - 快速流程：2 个阶段，每接口 3-5 条用例

请确认走哪条路径。
```

输出上述问题后必须结束当前轮，不得把“建议快速/完整流程”当成用户已确认。用户回复明确分支后才能通过 `FLOW_LOCK`。

**判断标准**：
- 接口数 ≤ 5 **且** 无复杂业务逻辑（支付/权限/工作流）→ 建议快速路径
- 接口数 > 5 **或** 涉及复杂逻辑 → 建议完整流程

**用户确认后**：
- 快速路径 → 只读取 `reference/stages/stage-quick-setup.md`，立即执行其第①项目录硬门；该阶段完成后再读取快速执行所需文件，禁止提前或重复读取
- 完整流程 → 读取 `reference/stages/stage-full-setup.md`，复用已完成的文档证据后立即执行其第②项目录硬门

**⚠️ 流程分支锁定（不是项目目录）**：用户确认完整流程或快速路径后，流程分支锁定，全程不可更改。即使后续用户说"只测一个接口"、"先测一个试试"等缩减范围的话，也必须按原确认的流程继续执行，不得切换分支。选择流程分支不代表已经确认 `PROJECT_DIR`；项目目录仍须在对应 setup 阶段单独确认。

pytest + Allure 框架。**所有测试文件必须位于 `<PROJECT_DIR>/tests/`，所有 HTTP 请求必须通过 `allure_request`/`AuthSession`，正式报告必须是 Allure 或内置生成器产出的 HTML，不能退化为普通 Markdown 报告。完整流程数量目标：每个接口平均 15-20 个用例，20 个接口至少 300 个；同时满足每个 GET ≥8、每个 POST ≥15。快速路径每接口 3-5 条。写完以 `pytest --collect-only -q` 的展开结果计数。**

## 红线

0. **禁止没读完就动手** — 必须先读完当前 stage 文件；到需要 reference 的步骤时，先读完该步骤明确指定的 reference，再执行该步骤
1. 禁止凭空想象 — 先调一遍看实际返回并记录与文档的差异，再依据已确认契约写断言
2. 禁止不确认就动手 — 项目位置、测试范围、认证方式必须明确；只有用户自然语言消息在当前 API 测试任务中明确提供项目绝对路径，或明确回复“默认/桌面新建”，才能直接沿用；否则必须询问项目位置并停下来等待回复。仅选择“快速路径”、提供 API 文档路径、宿主暴露工作区/CWD，或说明存在默认目录，都不等于用户确认项目位置
3. 禁止重复问 — 同一轮对话内用户已经回答过的，直接用，不再问也不再确认
4. 禁止在 skill 目录下操作
5. 禁止自作主张注册账号 — 先告知用户
6. 禁止跳过阶段 — 完整流程按 5 个阶段顺序执行，快速路径按 2 个阶段顺序执行
7. 禁止写空壳用例 — 必须有 allure.title(中文) + docstring(中文) + expected(中文) + 至少一个真实断言，所有用例描述、步骤、预期结果一律用中文。**每次调用 `auth_session.get/post/put/patch/delete/head/options` 或 `allure_request` 时必须传 expected 参数**（如 `expected="返回200且包含id字段"），不传 expected = 报告中没有“预期”信息 = 违反本条红线；断言内容由模型依据已确认契约决定
8. 禁止静默迁就文档或实际返回 — 两者不一致时先记录差异；断言以用户确认的契约为准，禁止仅为全绿而放宽
9. 禁止无故让用户验证 — 执行能力可用时必须自己跑、自己修；只有命令能力不可用或被拒绝时，才在已经预置当前 OS 脚本后请用户执行，并明确任务仍待测试、报告和审计验证
10. 禁止不记录或记错位置 — 每阶段必须用文件写入工具更新 `<PROJECT_DIR>/MEMORY.md`（只记产出，不记进度状态）；任务结束前必须验证该文件存在且非空。禁止把本流程的项目路径、环境、接口契约、阶段产出或交付状态写入或读取 Agent 的 project-memory、数据库、`memory_save`/`memory_recall`；这些内部记忆既不能代替项目文件，也不能作为本次硬门通过证据
11. 禁止偷懒 — 完整流程 GET ≥8 条，POST ≥15 条；快速路径每接口 3-5 条，不足说明理由
12. **禁止只说不做** — 每个阶段必须调用工具执行，不能只输出文本或自我分析来代替实际执行。所有阶段全部完成后才能停止调用工具
13. **禁止循环执行相同命令** — 如果连续 2 次执行相同命令得到相同结果，必须停止并检查是否需要换方法或结束任务
14. **禁止自动打开或降级报告** — 只生成静态 HTML 报告，禁止用 `TEST_REPORT.md` 等 Markdown 代替；禁止执行 `allure serve`、`allure open`、`open allure-report/` 等任何会启动服务或打开浏览器的命令。生成后只检查所选入口，报告由用户手动查看
15. **禁止未实跑却声称完成或双脚本交付** — `OS_TYPE`、`PYTHON` 和 `ALLURE` 锁定后，先预置当前脚本：Darwin/Linux 为 `run.sh`，Windows 为 `run.bat`；再由 agent 直接执行 pytest 和当前报告命令。测试与报告稳定后，在交付阶段复核、验收并实际执行该脚本一次，脚本产生的最新测试结果和唯一报告再通过最终审计。命令能力受阻时保留已预置脚本并交给用户执行，但只能说明待验证。脚本的报告模式必须与已确认的 `ALLURE` 一致，禁止运行时切换分支。新项目只生成当前 OS 的一份脚本；追加已有项目不删除用户原有的另一平台脚本
16. **禁止在项目目录外创建任何文件或文件夹** — 所有产出必须全部创建在 `<PROJECT_DIR>/` 内部，测试文件固定放在 `<PROJECT_DIR>/tests/`。用户确认“默认”或“桌面新建”后使用系统真实桌面目录下的 `<service>-api-qa-skill`；用户尚未确认项目位置时禁止自动采用该目录。它不是系统提示词里的工作区或启动目录
17. **禁止直接调用 requests/httpx 或 mock 传输层** — 所有 HTTP 请求必须通过 `allure_request()` 或 `AuthSession` 实例方法发起，并在 Allure 原始结果中留下请求、预期、响应证据；禁止用 monkeypatch、mock、responses、requests-mock、respx、VCR 等替代目标 API 的真实调用
18. **快速路径仅用于简单任务** — 接口数 ≤ 5 且无复杂业务逻辑（支付/权限/工作流）时可用。接口数 > 5 或涉及复杂逻辑时，必须走完整 5 阶段
19. **流程分支确认后不可更改** — 路由阶段用户确认了完整流程/快速路径后，全程锁定不可切换。这里锁定的是流程分支，不是项目目录；不得把“选择快速路径”当成 `PROJECT_DIR` 已确认
20. **禁止生成双报告入口或调用宿主通用报告器代替模板** — `allure --version` 成功时只生成 `allure-report/index.html`；不可用时只允许由本 Skill 的 `_templates/report_generator.py` 经 `scripts/materialize_templates.py` 物化后生成 `allure-report/report.html`。两种分支互斥；无论哪一分支都禁止调用宿主自身的通用报告构建能力另建 HTML
21. **禁止通过 Agent 工具读取或写入凭据** — 不得读取、搜索、打印 `.env` 内容，不得把 Token、API Key、密码或 Cookie 放进工具参数、日志、报告或 `MEMORY.md`。只允许项目配置脚本在进程内保留既有凭据并写非敏感配置或空凭据槽；非空凭据由用户在本地填写并确认完成
22. **禁止凭单一字段跳过配置确认** — `API_BASE_URL` 与认证方式必须分别确认；其中任一项缺失，都不能因为另一项已存在而跳过
23. **禁止提前结束或提前标记任务完成** — “测试通过”或“报告已生成”都不等于交付完成。当前 OS 脚本必须已物化、通过权限/语法检查并实际执行一次；随后当前流程的步骤清单必须全部变为 `✅`，且最后一次 `scripts/validate_delivery.py` 必须实际返回 `DELIVERY AUDIT: PASS`，才允许把整个任务标记为完成或输出结束语。缺少脚本实跑结果、项目内 `MEMORY.md`、所选报告或审计通过证据时只能继续处理或如实报告阻塞
24. **禁止手抄标准模板** — 新项目和缺失文件优先调用 `scripts/materialize_templates.py` 按字节落盘。物化结果为 `REVIEW` 时只读取它列出的既有冲突文件并最小修改；不得用简化版替代。仅当预置当前 OS 运行脚本且 Shell 能力不可用或被拒绝时，允许按 `reference/run-scripts.md` 的降级规则通过文件能力读取对应的一个 runner 模板，只替换 `__PYTHON_COMMAND__` 与 `__REPORT_MODE__` 后写入项目并回读核对；这不是重写模板，也不得读取或生成另一平台脚本
25. **禁止虚报接口覆盖** — 每个测试必须标明它实际归属的 `METHOD + 路径`，并至少调用一次统一 HTTP 请求封装；最终审计按 pytest 实际展开的 node 反算接口计数，空壳用例或虚报接口数量不得交付
26. **禁止把业务答案硬编码进框架** — 每个用例必须有中文标题、中文 docstring、中文 expected 和至少一个真实判断；状态码、字段、类型和业务规则由模型依据用户确认的契约决定，校验器只验证判断和证据是否存在
27. **禁止未经确认执行有副作用的测试** — 对真实环境发起 POST/PUT/PATCH/DELETE、并发、支付、权限变更或其他可能改变数据的场景前，必须确认目标是获准测试的环境并明确清理策略；未获确认时停在对应步骤。GET/HEAD/OPTIONS 仍按契约执行。确认结果只记录非敏感结论到项目 `MEMORY.md`

## ⛔ 统一任务清单与完成门禁

1. 进入任一 stage 后、执行该阶段第一项实质操作前，按该 stage 的“步骤清单”建立并持续更新同一份任务清单。“建立”不是在思考或计划文字中复述：`task_add` 可用时，必须为每个清单项分别调用一次 `task_add` 并保存返回的 `task_ref`；存在稳定的当前流程任务引用时作为共同父任务，否则省略父任务。相同标题的未完成项只沿用，不重复创建
2. 没有等价任务能力时，使用当前回复中的文本清单持续跟进；不得因为宿主已经自动创建了一个总任务，就省略 stage 的逐项清单
3. 每一步只有在相应工具调用成功并取得可核验结果后，才能通过 `task_update` 或文本清单将该项从 `⬜` 改为 `✅`；完成一项立即更新一项，禁止攒到最后批量完成，也不得一次性预先打勾或用“已生成报告”代替后续脚本、MEMORY 和审计步骤
4. 阶段切换前必须调用 `task_tree`（不可用时复核文本清单）确认当前阶段全部为 `✅`。快速路径的第⑧步和完整流程阶段五的第⑥步，只有最终审计返回 `DELIVERY AUDIT: PASS` 后才能标为 `✅`
5. 在最终回复前再次调用 `task_tree`（不可用时复核文本清单），展示最终阶段的全 `✅` 清单，并给出所选报告、当前 OS 运行脚本、项目内 `MEMORY.md` 的路径及 `DELIVERY AUDIT: PASS`。在此之前禁止通过任何任务管理能力把当前流程总任务标记为完成
6. 任务清单只用于执行跟踪，不写入 `<PROJECT_DIR>/MEMORY.md`；MEMORY 仍只记录各阶段产出

## ⛔ cd 强制规则（贯穿全流程）

注：项目相关命令如果没有先进入项目目录，可能在桌面或会话工作区产生多余文件。
1. `PROJECT_DIR` 必须先由用户确认并转换为绝对路径；仅选择完整/快速流程、系统工作区路径或默认目录说明都不能代替确认
2. 文件能力涉及项目文件时必须使用已确认的 `<PROJECT_DIR>/...` 绝对路径，禁止依赖当前工作目录
3. 系统/Python/Allure 探测命令不读写项目，是唯一不加 `<ENTER_PROJECT>` 的 `shell_exec`；其余会读取项目相对路径或产生文件的命令，必须以 `<ENTER_PROJECT>` 开头
4. Darwin/Linux：`<ENTER_PROJECT>` 展开为 `cd "<PROJECT_DIR>" && pwd &&`
5. Windows：`<ENTER_PROJECT>` 展开为 `cd /d "<PROJECT_DIR>" && cd &&`，必须使用 `cd /d` 以支持跨盘符目录
6. 执行前必须把 `<PROJECT_DIR>`、`<PYTHON_CMD>`、`<SKILL_DIR>` 等占位符替换为实际值；禁止把字面占位符传给工具
7. `pwd` / `cd` 的输出必须与已确认的 `PROJECT_DIR` 指向同一目录；验证失败立即停止，不得在其他目录重试项目命令。禁止在同一条命令里混用 POSIX 与 Windows 语法

**正确示例**：
```
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> -m pytest tests/ -v --tb=short --alluredir=allure-results")
```

## 环境变量（整个流程中使用）

环境检测完成后（完整流程在阶段一，快速路径在 `stage-quick-setup.md` ②），以下变量在整个流程中使用，**每次 shell_exec 调用时必须替换为实际值**：

| 变量 | 含义 | 示例值 |
|------|------|--------|
| `PYTHON` | 已验证的单个 Python 可执行文件名或绝对路径，不包含命令参数 | `python3` / `python` / `py` / `/opt/python/bin/python3` |
| `PYTHON_CMD` | 按当前 Shell 正确引用 `PYTHON` 后的调用形式，供命令示例替换；路径含空格时必须整体引用 | `python3` / `"/opt/My Python/python3"` |
| `SKILL_DIR` | 宿主实际加载的本 Skill 根目录绝对路径 | `/opt/skills/api-qa-skill` |
| `PROJECT_DIR` | 本 Skill 交付的测试项目目录。用户明确回复“默认”或“桌面新建”后，解析当前系统真实桌面目录并追加 `<service>-api-qa-skill`；无法可靠解析时必须询问绝对路径。它不是系统提示词 `<workspace>` 或启动目录 | `/home/user/Desktop/orders-api-qa-skill` |
| `OS_TYPE` | 操作系统类型 | `Darwin` / `Linux` / `Windows` |
| `ALLURE` | 是否有 allure CLI | `有` / `无` |
| `PROJECT_KIND` | 开始任务前目录是否已有用户文件 | `new` / `existing` |
| `ENTER_PROJECT` | 当前系统对应的进入目录并校验前缀 | POSIX 用 `cd ... && pwd &&`；Windows 用 `cd /d ... && cd &&` |

⚠️ **PYTHON 替换规则**：用户说的版本号 > 检测到的值。`PYTHON` 必须是单个可执行文件，不把 `-3.11` 等参数混入路径；命令中统一使用 `PYTHON_CMD -m ...`，传给模板脚本的 `--python-command` 使用未加 Shell 引号的原始 `PYTHON`。

## 常见问题诊断速查表

| 错误现象 | 可能原因 | 解决方案 |
|---------|---------|---------|
| `read_file` 失败 / 文件不存在 | 参数或路径错误 | 确认使用 `path` 参数，再用 `list_files` 核对；仍失败才询问用户 |
| `save_file` 被拦截 | 重复保存相同内容 | 检查文件是否已存在，改用 `edit_file` |
| 模板物化失败 | 路径、权限、参数或模板缺失 | 按脚本错误修复后最多重试 2 次；禁止手写替代模板 |
| `ALLURE=无` 时模板报告生成失败 | report_generator.py 未找到或与模板不一致 | 用 `materialize_templates.py --component report --report fallback` 校验；缺失则补齐，冲突则保留并询问用户；`ALLURE=有` 时禁止复制 |
| pytest 找不到模块 | 依赖未安装 | 重新运行 `<PYTHON_CMD> -m pip install -r requirements.txt` |
| pytest 全部失败 | 环境配置错误或 API 不可用 | 不读取 `.env`；核对 `MEMORY.md` 中的非敏感配置，必要时请用户确认本地凭据已填写，再用测试结果判断 |
| 部分测试失败 | 断言、实际返回与契约不一致 | 先确认契约；只修错误断言，真实 API 差异写入 `<PROJECT_DIR>/MEMORY.md` |
| `curl` 返回 404 | API 端点不存在 | 检查 URL 路径，或使用 `web_search` / `web_fetch` 获取信息 |
| `curl` 返回 401/403 | 认证失败 | 检查 token 是否过期，或需要重新登录 |
| Shell 命令未找到 | 命令不存在或路径错误 | POSIX 用 `command -v <命令>`，Windows 用 `where <命令>` 检查，或安装对应工具 |

## 流程（5 个阶段 + 快速路径）

> **⛔ 每个阶段先读取对应的 stage 文件；reference 按 stage 标明的步骤即时读取，不提前批量加载。已完成的阶段不重复读取。**

| 阶段 | 目标 | 需要读取的文件 | 前置产出 | 产出 |
|------|------|---------------|---------|------|
| 一、信息收集 | 读文档，确认项目位置、环境、认证，汇报计划 | `reference/stages/stage-full-setup.md` | — | `<PROJECT_DIR>/MEMORY.md`：项目位置、PYTHON、OS_TYPE、ALLURE、认证方式、接口清单 |
| 二、搭框架+调接口 | 创建项目结构，预置当前 OS 脚本，按认证分支真实探测每个接口并记录返回 | 先读 `reference/stages/stage-2-setup.md`；模板由物化脚本按需复制；仅已有核心文件冲突/动态认证时读 `reference/implementation.md`，仅 runner 冲突或物化命令受阻时读 `reference/run-scripts.md` | 阶段一产出（PYTHON、OS_TYPE、ALLURE） | `<PROJECT_DIR>/MEMORY.md`：差异表 |
| 三、写用例 | GET ≥8 条，POST ≥15 条，9 维度覆盖 | 先读 `reference/stages/stage-3-write.md`；①读 `reference/test-design.md` | 阶段二产出 | `<PROJECT_DIR>/MEMORY.md`：用例数 + 覆盖矩阵 |
| 四、跑测试+修到通过 | pytest + 修断言/API bug + 报告，最多 5 轮 | `reference/stages/stage-full-test.md` | 阶段一产出（ALLURE）、阶段三产出 | `<PROJECT_DIR>/MEMORY.md`：结果统计 + 修复记录 |
| 五、交付 | 重跑测试，交付前实跑脚本，写文档并整理交付物 | 先读 `reference/stages/stage-5-deliver.md`；④复核并实跑已预置脚本，runner 冲突/缺失/命令受阻时读 `reference/run-scripts.md`；⑤读 `reference/test-doc.md`；最后执行 `scripts/validate_delivery.py` | 阶段一产出（ALLURE、PROJECT_KIND） | `<PROJECT_DIR>/MEMORY.md`：最终结果 |
| **快速路径** | **阶段 1+2 合并（`stage-quick-setup.md`）+ 阶段 3-5 合并（`stage-quick.md`），接口数 ≤ 5 时可用，共 2 个阶段** | 先读 `reference/stages/stage-quick-setup.md`，完成后只读 `reference/stages/stage-quick.md`；步骤①预置当前 OS 脚本；仅已有核心文件冲突/动态认证时读 `reference/implementation.md`，runner 冲突或物化命令受阻时读 `reference/run-scripts.md`；最后执行 `scripts/validate_delivery.py` | — | `<PROJECT_DIR>/MEMORY.md`：差异表+用例数+结果统计+修复记录（一次性） |
