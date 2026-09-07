---
name: api-qa-skill
description: API 自动化测试：pytest+Allure 框架，5 阶段完整工作流 + 快速路径（≤5 接口），生成专业测试报告
tools: curl, web_fetch, web_search, read_file, save_file, edit_file, list_files, shell_exec
---

# API 自动化测试 Skill

> **⛔ 加载规则（只说一次，贯穿全流程）：**
>
> 1. **本文件（SKILL.md）**：每次对话开头读一次，后续阶段不重复读取
> 2. **stage 文件 + reference 文件**：每个阶段只读当前阶段需要的文件（见下方流程表）
> 3. **已完成的阶段**：不重复读取其 stage 文件。agent 自己在上下文中追踪阶段进度
> 4. **MEMORY.md**：路径为 `<PROJECT_DIR>/MEMORY.md`（项目目录下，不是 skill 目录下）。只用于记录每阶段的产出（接口清单、差异表等），不用于记录阶段进度状态
> 5. **禁止**：一次性读取所有 reference 文件；回头重读已完成阶段的 stage 文件
>
> ⚠️ 所有文件都在本 Skill 目录下。用 `read_file` 读取时，路径是本 Skill 的目录路径 + 上述相对路径。
>
> **文件读取失败处理**：
> - 如果 `read_file` 失败 → 立即用 `shell_exec(command="cat '<skill_dir>/文件路径'")` 重试
> - 如果两种方法都失败 → 告知用户模板文件无法读取，询问是否手动提供

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
- 快速路径 → 读取 `reference/stages/stage-quick-setup.md` + `reference/implementation.md`
- 完整流程 → 读取 `reference/stages/stage-full-setup.md`

**⚠️ 路径锁定**：用户确认后，路径锁定，全程不可更改。即使后续用户说"只测一个接口"、"先测一个试试"等缩减范围的话，也必须按原确认的路径继续执行，不得切换到另一条路径。完整流程就是完整流程，快速路径就是快速路径。

pytest + Allure 框架。**完整流程数量目标：每个接口平均 15-20 个用例，20 个接口至少 300 个。快速路径每接口 3-5 条。写完 `pytest --co -q` 数一下，不够就补。**

## 红线

0. **禁止没读完就动手** — 必须读完当前阶段需要的 stage 文件 + reference 文件，才能开始执行
1. 禁止凭空想象 — 先调一遍看实际返回再写断言
2. 禁止不问就动手 — 项目位置、测试范围、认证方式没确认不写代码
3. 禁止重复问 — 同一轮对话内用户已经回答过的，直接用，不再问也不再确认
4. 禁止在 skill 目录下操作
5. 禁止自作主张注册账号 — 先告知用户
6. 禁止跳过阶段 — 完整流程按 5 个阶段顺序执行，快速路径按 2 个阶段顺序执行
7. 禁止写空壳用例 — 必须有 allure.title(中文) + docstring(中文) + expected(中文)，所有用例描述、步骤、预期结果一律用中文。**每次调用 auth_session.get/post/put/patch/delete 或 allure_request 时必须传 expected 参数**（如 `expected="返回200且包含id字段"`），不传 expected = 报告中没有"预期"信息 = 违反本条红线
8. 禁止照抄文档写断言 — 以真实返回为准
9. 禁止让用户验证 — 自己跑、自己修、交付跑通的代码
10. 禁止不记录 — 每阶段将产出写入 MEMORY.md（只记产出，不记进度状态）
11. 禁止偷懒 — 完整流程 GET ≥8 条，POST ≥15 条；快速路径每接口 3-5 条，不足说明理由
12. **禁止只说不做** — 每个阶段必须调用工具执行，不能只输出文本或自我分析来代替实际执行。所有阶段全部完成后才能停止调用工具
13. **禁止循环执行相同命令** — 如果连续 2 次执行相同命令得到相同结果，必须停止并检查是否需要换方法或结束任务
14. **禁止自动打开报告** — 生成报告时只生成静态文件（`allure generate` 或 `report_generator.py`），禁止执行 `allure serve`、`allure open`、`open allure-report/` 等任何会启动服务或打开浏览器的命令。生成后只需检查文件大小确认成功，报告由用户通过 `./run.sh` 手动查看
15. **禁止自动执行 run.sh/run.bat** — 不要执行 `./run.sh` 或 `./run.bat` 脚本，该脚本由用户手动执行。agent 应直接执行 pytest 以及对应的报告生成命令（`allure generate` 或 `python utils/report_generator.py`）
16. **禁止在项目目录外创建任何文件或文件夹** — 所有产出必须全部创建在 `<PROJECT_DIR>/` 内部
17. **禁止直接调用 requests.get/post/put/patch/delete** — 所有 HTTP 请求必须通过 `allure_request()` 或 `AuthSession` 实例方法（`auth_session.get()`、`auth_session.post()` 等）发起
18. **快速路径仅用于简单任务** — 接口数 ≤ 5 且无复杂业务逻辑（支付/权限/工作流）时可用。接口数 > 5 或涉及复杂逻辑时，必须走完整 5 阶段
19. **路径确认后不可更改** — 路由阶段用户确认了完整流程/快速路径后，全程锁定不可切换。不得因用户中途说"只测一个接口"、"先试一个"等缩减范围的话而自动切换路径

## ⛔ cd 强制规则（贯穿全流程）

注：如果不 先cd 会产生多余的文件在桌面，后果很严重 ！！！
1. **在项目目录下操作时，命令必须以 `cd "<PROJECT_DIR>" &&` 开头**，禁止直接执行不带 cd 的项目内命令（前置环境探测与目录初始化除外）
2. **执行完 cd 后，必须验证当前目录**（`pwd` / `echo %CD%`），确认输出路径与 `<PROJECT_DIR>` 一致
3. **如果验证失败，立即停止执行**

**正确示例**：
```
shell_exec(command="cd \"<PROJECT_DIR>\" && python -m pytest tests/ -v --tb=short --alluredir=allure-results")
```

## 环境变量（整个流程中使用）

环境检测完成后（完整流程在阶段一，快速路径在 `stage-quick-setup.md` ②），以下变量在整个流程中使用，**每次 shell_exec 调用时必须替换为实际值**：

| 变量 | 含义 | 示例值 |
|------|------|--------|
| `PYTHON` | Python 解释器命令 | `python3` / `python` / `py` |
| `PROJECT_DIR` | 项目目录绝对路径 | `/path/to/my-api-project` |
| `OS_TYPE` | 操作系统类型 | `Darwin` / `Linux` / `Windows` |
| `ALLURE` | 是否有 allure CLI | `有` / `无` |

⚠️ **PYTHON 替换规则**：用户说的版本号 > 检测到的值。pip 统一用 `PYTHON -m pip`。

## 常见问题诊断速查表

| 错误现象 | 可能原因 | 解决方案 |
|---------|---------|---------|
| `read_file` 失败 / 文件不存在 | 路径错误或文件缺失 | 用 `shell_exec cat` 备用读取，或询问用户 |
| `save_file` 被拦截 | 重复保存相同内容 | 检查文件是否已存在，改用 `edit_file` |
| 报告生成失败 | report_generator.py 未找到（仅ALLURE=无时） | 检查 `utils/report_generator.py` 是否已从模板复制 |
| pytest 找不到模块 | 依赖未安装 | 重新运行 `<PYTHON> -m pip install -r requirements.txt` |
| pytest 全部失败 | .env 配置错误 | 检查 `API_BASE_URL` 和 `API_TOKEN` |
| 部分测试失败 | 断言不匹配 | 修复断言，先调接口看真实返回 |
| `curl` 返回 404 | API 端点不存在 | 检查 URL 路径，或使用 `web_search` / `web_fetch` 获取信息 |
| `curl` 返回 401/403 | 认证失败 | 检查 token 是否过期，或需要重新登录 |
| `shell_exec` 命令未找到 | 命令不存在或路径错误 | 使用 `which <命令>` 检查，或安装对应工具 |

## 流程（5 个阶段 + 快速路径）

> **⛔ 每个阶段执行前必须先读取对应的 stage 文件 + 该阶段需要的 reference 文件。已完成的阶段不重复读取。**

| 阶段 | 目标 | 需要读取的文件 | 前置产出 | 产出 |
|------|------|---------------|---------|------|
| 一、信息收集 | 读文档，确认项目位置、环境、认证，汇报计划 | `reference/stages/stage-full-setup.md` | — | MEMORY.md：项目位置、PYTHON、OS_TYPE、ALLURE、认证方式、接口清单 |
| 二、搭框架+调接口 | 创建项目结构，curl 调每个接口记录返回 | `reference/stages/stage-2-setup.md` + `reference/implementation.md` + `reference/run-scripts.md` +（`_templates/report_generator.py` 仅ALLURE=无） | 阶段一产出（PYTHON、OS_TYPE、ALLURE） | MEMORY.md：差异表 |
| 三、写用例 | GET ≥8 条，POST ≥15 条，9 维度覆盖 | `reference/stages/stage-3-write.md` + `reference/test-design.md` | 阶段二产出 | MEMORY.md：用例数 + 覆盖矩阵 |
| 四、跑测试+修到通过 | pytest + 修断言/API bug + 报告，最多 5 轮 | `reference/stages/stage-full-test.md` | 阶段一产出（ALLURE）、阶段三产出 | MEMORY.md：结果统计 + 修复记录 |
| 五、交付 | 重跑测试，写文档，整理交付物 | `reference/stages/stage-5-deliver.md` + `reference/test-doc.md` | 阶段一产出（ALLURE） | MEMORY.md：最终结果 |
| **快速路径** | **阶段 1+2 合并（`stage-quick-setup.md`）+ 阶段 3-5 合并（`stage-quick.md`），接口数 ≤ 5 时可用，共 2 个阶段** | 快速前置：`reference/stages/stage-quick-setup.md`；快速执行：`reference/stages/stage-quick.md` + `reference/implementation.md` + `reference/run-scripts.md` | — | MEMORY.md：差异表+用例数+结果统计+修复记录（一次性） |
