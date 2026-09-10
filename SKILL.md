---
name: api-qa-skill
description: API 自动化测试：pytest+Allure 框架，5 阶段完整工作流 + 快速路径（≤5 接口），生成专业测试报告
tools: curl, web_fetch, web_search, get_datetime, format_datetime, read_file, save_file, edit_file, list_files, grep_search, glob_search, shell_exec, configure_env, memory_recall, memory_save, Skill
---

# API 自动化测试 Skill

> **⛔ 加载规则（只说一次，贯穿全流程）：**
>
> 1. **本文件（SKILL.md）**：每次对话开头读一次，后续阶段不重复读取
> 2. **stage 文件 + reference 文件**：每个阶段只读当前阶段需要的文件（见下方流程表）
> 3. **已完成的阶段**：不重复读取其 stage 文件。agent 自己在上下文中追踪阶段进度
> 4. **MEMORY.md**：固定路径为 `<PROJECT_DIR>/MEMORY.md`，是交付给用户的项目文档。禁止写到会话工作区、Agent 的 project-memory 或 skill 目录；数据库、`memory_save`、Agent 内部记忆只能作为可选副本，不能替代该文件。只记录每阶段产出，不记录阶段进度状态
> 5. **禁止**：一次性读取所有 reference 文件；回头重读已完成阶段的 stage 文件
>
> ⚠️ 所有文件都在本 Skill 目录下。用 `read_file` 读取时，路径是本 Skill 的目录路径 + 上述相对路径。
>
> **文件读取失败处理**：
> - 如果结果 `has_more=true` → 必须使用返回的 `continuation.next_offset`（超长单行同时使用 `next_char_offset`）继续；禁止重读同一页，也禁止用 shell 绕过分页
> - 如果 `read_file` 报错 → 先检查参数必须为 `path`、再用 `list_files` 核对路径；仍失败才告知用户模板文件无法读取，询问是否手动提供

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

建议走完整流程（接口数 > 5）。
  - 完整流程：5 个阶段，每接口 15-20 条用例
  - 快速流程：2 个阶段，每接口 3-5 条用例

请确认走哪条路径。
```

**判断标准**：
- 接口数 ≤ 5 **且** 无复杂业务逻辑（支付/权限/工作流）→ 建议快速路径
- 接口数 > 5 **或** 涉及复杂逻辑 → 建议完整流程

**用户确认后**：
- 快速路径 → 只读取 `reference/stages/stage-quick-setup.md`；该阶段完成后再读取快速执行所需文件，禁止提前或重复读取
- 完整流程 → 读取 `reference/stages/stage-full-setup.md`

**⚠️ 路径锁定**：用户确认后，路径锁定，全程不可更改。即使后续用户说"只测一个接口"、"先测一个试试"等缩减范围的话，也必须按原确认的路径继续执行，不得切换到另一条路径。完整流程就是完整流程，快速路径就是快速路径。

pytest + Allure 框架。**所有测试文件必须位于 `<PROJECT_DIR>/tests/`，所有 HTTP 请求必须通过 `allure_request`/`AuthSession`，正式报告必须是 Allure 或内置生成器产出的 HTML，不能退化为普通 Markdown 报告。完整流程数量目标：每个接口平均 15-20 个用例，20 个接口至少 300 个；同时满足每个 GET ≥8、每个 POST ≥15。快速路径每接口 3-5 条。写完以 `pytest --collect-only -q` 的展开结果计数。**

## 红线

0. **禁止没读完就动手** — 必须读完当前阶段需要的 stage 文件 + reference 文件，才能开始执行
1. 禁止凭空想象 — 先调一遍看实际返回并记录与文档的差异，再依据已确认契约写断言
2. 禁止不确认就动手 — 项目位置、测试范围、认证方式必须明确；用户本轮已经提供的直接沿用，缺失时才询问
3. 禁止重复问 — 同一轮对话内用户已经回答过的，直接用，不再问也不再确认
4. 禁止在 skill 目录下操作
5. 禁止自作主张注册账号 — 先告知用户
6. 禁止跳过阶段 — 完整流程按 5 个阶段顺序执行，快速路径按 2 个阶段顺序执行
7. 禁止写空壳用例 — 必须有 allure.title(中文) + docstring(中文) + expected(中文)，所有用例描述、步骤、预期结果一律用中文。**每次调用 `auth_session.get/post/put/patch/delete` 或 `allure_request` 时必须传 expected 参数**（如 `expected="返回200且包含id字段"），不传 expected = 报告中没有"预期"信息 = 违反本条红线
8. 禁止静默迁就文档或实际返回 — 两者不一致时先记录差异；断言以用户确认的契约为准，禁止仅为全绿而放宽
9. 禁止让用户验证 — 自己跑、自己修、交付跑通的代码
10. 禁止不记录或记错位置 — 每阶段必须用文件写入工具更新 `<PROJECT_DIR>/MEMORY.md`（只记产出，不记进度状态）；任务结束前必须验证该文件存在且非空。Agent 工作区记忆或数据库记录不算完成
11. 禁止偷懒 — 完整流程 GET ≥8 条，POST ≥15 条；快速路径每接口 3-5 条，不足说明理由
12. **禁止只说不做** — 每个阶段必须调用工具执行，不能只输出文本或自我分析来代替实际执行。所有阶段全部完成后才能停止调用工具
13. **禁止循环执行相同命令** — 如果连续 2 次执行相同命令得到相同结果，必须停止并检查是否需要换方法或结束任务
14. **禁止自动打开或降级报告** — 只生成静态 HTML 报告，禁止用 `TEST_REPORT.md` 等 Markdown 代替；禁止执行 `allure serve`、`allure open`、`open allure-report/` 等任何会启动服务或打开浏览器的命令。生成后只检查所选入口，报告由用户手动查看
15. **禁止自动执行运行脚本，也禁止双脚本交付** — agent 应直接执行 pytest 和当前环境对应的报告生成命令；新项目必须按 `OS_TYPE` 二选一：Darwin/Linux 只生成 `run.sh`，Windows 只生成 `run.bat`。追加已有项目时不删除用户原有的另一平台脚本
16. **禁止在项目目录外创建任何文件或文件夹** — 所有产出必须全部创建在 `<PROJECT_DIR>/` 内部，测试文件固定放在 `<PROJECT_DIR>/tests/`。用户未指定目录时默认使用桌面的 `<service>-api-qa-skill`，不是系统提示词里的工作区或 tcli 启动目录
17. **禁止直接调用 requests.get/post/put/patch/delete** — 所有 HTTP 请求必须通过 `allure_request()` 或 `AuthSession` 实例方法（`auth.get()`、`auth.post()` 等）发起
18. **快速路径仅用于简单任务** — 接口数 ≤ 5 且无复杂业务逻辑（支付/权限/工作流）时可用。接口数 > 5 或涉及复杂逻辑时，必须走完整 5 阶段
19. **路径确认后不可更改** — 路由阶段用户确认了完整流程/快速路径后，全程锁定不可切换。不得因用户中途说"只测一个接口"、"先试一个"等缩减范围的话而自动切换路径
20. **禁止生成双报告入口** — `allure --version` 成功时只生成 `allure-report/index.html`；不可用时只生成 `allure-report/report.html`，两种分支互斥
21. **禁止通过 Agent 工具读取或写入凭据** — 不得读取、搜索、打印 `.env` 内容，不得把 Token、API Key、密码或 Cookie 放进工具参数、日志、报告或 `MEMORY.md`。Agent 只可用 `configure_env` 写非敏感配置和空凭据槽；非空凭据由用户在本地填写并确认完成
22. **禁止凭单一字段跳过配置确认** — `API_BASE_URL` 与认证方式必须分别确认；其中任一项缺失，都不能因为另一项已存在而跳过

## ⛔ cd 强制规则（贯穿全流程）

注：项目相关命令如果没有先进入项目目录，可能在桌面或会话工作区产生多余文件。
1. 环境探测命令不读写项目，可以直接执行；其余会读取项目相对路径或产生文件的命令，必须以 `<ENTER_PROJECT>` 开头
2. Darwin/Linux：`<ENTER_PROJECT>` 展开为 `cd "<PROJECT_DIR>" && pwd &&`
3. Windows：`<ENTER_PROJECT>` 展开为 `cd /d "<PROJECT_DIR>" && cd &&`，必须使用 `cd /d` 以支持跨盘符目录
4. `pwd` / `cd` 的输出必须与 `<PROJECT_DIR>` 一致；验证失败立即停止。禁止在同一条命令里混用 POSIX 与 Windows 语法

**正确示例**：
```
shell_exec(command="<ENTER_PROJECT> <PYTHON> -m pytest tests/ -v --tb=short --alluredir=allure-results")
```

## 环境变量（整个流程中使用）

环境检测完成后（完整流程在阶段一，快速路径在 `stage-quick-setup.md` ②），以下变量在整个流程中使用，**每次 shell_exec 调用时必须替换为实际值**：

| 变量 | 含义 | 示例值 |
|------|------|--------|
| `PYTHON` | Python 解释器命令 | `python3` / `python` / `py` |
| `PROJECT_DIR` | 本 Skill 交付的测试项目目录。用户未指定时默认展开为桌面的 `<service>-api-qa-skill`；它不是系统提示词 `<workspace>` 里的用户项目目录或 tcli 启动目录 | `/home/user/Desktop/orders-api-qa-skill` |
| `OS_TYPE` | 操作系统类型 | `Darwin` / `Linux` / `Windows` |
| `ALLURE` | 是否有 allure CLI | `有` / `无` |
| `PROJECT_KIND` | 开始任务前目录是否已有用户文件 | `new` / `existing` |
| `ENTER_PROJECT` | 当前系统对应的进入目录并校验前缀 | POSIX 用 `cd ... && pwd &&`；Windows 用 `cd /d ... && cd &&` |

⚠️ **PYTHON 替换规则**：用户说的版本号 > 检测到的值。pip 统一用 `PYTHON -m pip`。

## 常见问题诊断速查表

| 错误现象 | 可能原因 | 解决方案 |
|---------|---------|---------|
| `read_file` 失败 / 文件不存在 | 参数或路径错误 | 确认使用 `path` 参数，再用 `list_files` 核对；仍失败才询问用户 |
| `save_file` 被拦截 | 重复保存相同内容 | 检查文件是否已存在，改用 `edit_file` |
| 内置报告生成失败 | report_generator.py 未找到 | 检查 `utils/report_generator.py` 是否存在 |
| pytest 找不到模块 | 依赖未安装 | 重新运行 `<PYTHON> -m pip install -r requirements.txt` |
| pytest 全部失败 | 环境配置错误或 API 不可用 | 不读取 `.env`；核对 `MEMORY.md` 中的非敏感配置，必要时请用户确认本地凭据已填写，再用测试结果判断 |
| 部分测试失败 | 断言、实际返回与契约不一致 | 先确认契约；只修错误断言，真实 API 差异写入 `<PROJECT_DIR>/MEMORY.md` |
| `curl` 返回 404 | API 端点不存在 | 检查 URL 路径，或使用 `web_search` / `web_fetch` 获取信息 |
| `curl` 返回 401/403 | 认证失败 | 检查 token 是否过期，或需要重新登录 |
| `shell_exec` 命令未找到 | 命令不存在或路径错误 | 使用 `which <命令>` 检查，或安装对应工具 |

## 流程（5 个阶段 + 快速路径）

> **⛔ 每个阶段执行前必须先读取对应的 stage 文件 + 该阶段需要的 reference 文件。已完成的阶段不重复读取。**

| 阶段 | 目标 | 需要读取的文件 | 前置产出 | 产出 |
|------|------|---------------|---------|------|
| 一、信息收集 | 读文档，确认项目位置、环境、认证，汇报计划 | `reference/stages/stage-full-setup.md` | — | `<PROJECT_DIR>/MEMORY.md`：项目位置、PYTHON、OS_TYPE、ALLURE、认证方式、接口清单 |
| 二、搭框架+调接口 | 创建项目结构，curl 调每个接口记录返回 | `reference/stages/stage-2-setup.md` + `reference/implementation.md` + `reference/run-scripts.md` + `_templates/report_generator.py` | 阶段一产出（PYTHON、OS_TYPE、ALLURE） | `<PROJECT_DIR>/MEMORY.md`：差异表 |
| 三、写用例 | GET ≥8 条，POST ≥15 条，9 维度覆盖 | `reference/stages/stage-3-write.md` + `reference/test-design.md` | 阶段二产出 | `<PROJECT_DIR>/MEMORY.md`：用例数 + 覆盖矩阵 |
| 四、跑测试+修到通过 | pytest + 修断言/API bug + 报告，最多 5 轮 | `reference/stages/stage-full-test.md` | 阶段一产出（ALLURE）、阶段三产出 | `<PROJECT_DIR>/MEMORY.md`：结果统计 + 修复记录 |
| 五、交付 | 重跑测试，写文档，整理交付物 | `reference/stages/stage-5-deliver.md` + `reference/test-doc.md`；执行 `scripts/validate_delivery.py` | 阶段一产出（ALLURE、PROJECT_KIND） | `<PROJECT_DIR>/MEMORY.md`：最终结果 |
| **快速路径** | **阶段 1+2 合并（`stage-quick-setup.md`）+ 阶段 3-5 合并（`stage-quick.md`），接口数 ≤ 5 时可用，共 2 个阶段** | 快速前置：`reference/stages/stage-quick-setup.md`；快速执行：`reference/stages/stage-quick.md` + `reference/implementation.md` + `reference/run-scripts.md` + `_templates/report_generator.py`；执行 `scripts/validate_delivery.py` | — | `<PROJECT_DIR>/MEMORY.md`：差异表+用例数+结果统计+修复记录（一次性） |
