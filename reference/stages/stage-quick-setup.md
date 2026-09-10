# 快速路径前置：信息收集 + 环境确认（阶段 1+2 合并）

> **⛔ 本阶段无额外 reference 文件需要读取。**
>
> ⚠️ 仅用于接口数 ≤ 5 的简单任务。复杂逻辑（支付/权限/工作流）必须走完整 5 阶段。
>
> **MEMORY 文件边界**：本阶段所有 `MEMORY.md` 均指 `<PROJECT_DIR>/MEMORY.md`，必须用文件写入工具创建或追加，供用户查看；Agent 工作区记忆、数据库或 `memory_save` 不能替代该文件。

## 前置条件

本阶段在用户确认走快速路径后开始。此时 API 文档已读取，接口清单已提取，路由已确认。

## 目标

一次性收集剩余必要信息：项目位置、运行环境、认证方式。收集完毕后直接进入快速路径执行阶段。

## 步骤清单（执行时必须逐项打勾，跳过禁止）

```
⬜ 1. 确认项目位置（已有则沿用，缺失才问用户）
⬜ 2. 确认运行环境（已有则沿用，缺失才问用户）
⬜ 3. 分别确认 API Base URL 与认证方式（各自已有才跳过）
⬜ 4. 直接进入快速路径（不等确认）
```

**执行规则**：每完成一项立即将 `⬜` 改为 `✅`，全部打勾后读取 `reference/stages/stage-quick.md` + `reference/implementation.md` 进入快速路径。

---

## ① 确认项目位置

用户在本轮已经给出绝对路径、桌面默认或追加已有项目时，直接使用，不重复询问。只有尚未提供位置时，才输出以下问题并**停下来等用户回复**：

> 项目默认新建在桌面的 `~/Desktop/<service>-api-qa-skill`。如需其他位置或追加已有项目，请提供绝对路径。
> - 新建：默认使用根据 API/服务名生成的 `<service>-api-qa-skill`
> - 追加：请提供已有项目的绝对路径
> ⚠️ 请回复后我才继续。

用户回复后：
- 用户未指定路径、回复“默认”或“桌面新建” → 项目位置 = 展开后的 `~/Desktop/<service>-api-qa-skill`（项目名根据 API、服务名或主机名生成）
- 用户提供具体路径 → 直接使用
- 在创建本 Skill 的任何文件前判断：目录不存在或为空 → `PROJECT_KIND=new`；目录已经包含用户文件 → `PROJECT_KIND=existing`
- 保存到 `<PROJECT_DIR>/MEMORY.md`（同时将 `PROJECT_KIND`、路由阶段提取的认证方式和接口清单一并写入）

---

## ② 确认运行环境

用户在本轮已经给出操作系统和 Python 版本时直接沿用；缺失时才输出以下问题并**停下来等用户回复**：

> 你的操作系统和 Python 版本是什么？（例如：macOS + python3.11）
> 如果不确定，回复"自动检测"。
> ⚠️ 请回复后我才继续。

根据用户回复确定 PYTHON：
- 用户说了版本号 → PYTHON=该版本（**不要降级**）
- 用户说"自动检测" → 依次检测 python3 / python / py，全部失败则告知用户安装

然后检测系统信息：
```
shell_exec(command="<PYTHON> -c \"import platform,shutil,sys; print('OS:',platform.system()); print('PythonVersion:',sys.version.split()[0]); print('Allure:',shutil.which('allure') or 'NOT_FOUND')\"")
```

`shutil.which` 只用于定位；随后必须实际执行 `allure --version`，只有返回成功才记录 `ALLURE=有`，否则记录 `ALLURE=无`。

| 变量 | 规则 |
|------|------|
| PYTHON | 用户说的值 > 检测到的值 |
| PIP | 统一用 `PYTHON -m pip` |
| OS_TYPE | Darwin=macOS, Linux, Windows |
| ALLURE | `allure --version` 成功 → allure generate；否则 → 用 report_generator.py |

---

## ③ 分别确认 API Base URL 与认证方式

将这两项作为两个独立门控。可用 `read_file` 读取 `<PROJECT_DIR>/MEMORY.md` 中的非敏感项目配置；禁止用 shell/grep 读取 `.env`。

### A. API Base URL

按“用户已提供 → 文档 servers/host → MEMORY 既有值（需用户确认）→ 询问用户”的顺序取得完整、不含用户名/密码的 HTTP(S) 地址。禁止使用 localhost、示例地址或猜测值。

### B. 认证方式

按文档和用户回复确定 `none`、`bearer`、`header`、`query`、`cookie`、`basic` 或“动态 OAuth/登录流程”。静态 OAuth access token 按 `bearer`；动态流程只按已确认契约实现专用 fixture，不猜测通用登录/刷新逻辑。

- 无认证 → `AUTH_MODE=none`，快速用例的“认证权限”维度改为核心数据或业务校验
- 文档明确认证 → 记录方式、位置、名称和 scheme，不索要凭据原文
- 文档未说明 → 询问用户认证方式，仍不要让用户在聊天中粘贴凭据

将以下稳定字段写入 `<PROJECT_DIR>/MEMORY.md`：“PROJECT_KIND、API_BASE_URL、AUTH_MODE、AUTH_NAME、AUTH_SCHEME、AUTH_SECRET_ENV”。其中只记录配置和环境变量名，不记录凭据。

本阶段不创建或读取 `.env`。快速执行阶段的步骤①先确保 `.gitignore` 排除 `.env`，再用 `configure_env` 写非敏感值和空凭据槽。非空凭据由用户在本地填写；需要认证时等用户确认“已配置”后再运行带认证测试，但 Agent 不读取、搜索或回显 `.env`。

---

## ④ 进入快速路径

信息收集完毕，**不等用户确认计划**，直接读取以下文件并执行：

```
read_file(path="<skill_dir>/reference/stages/stage-quick.md")
read_file(path="<skill_dir>/reference/implementation.md")
read_file(path="<skill_dir>/reference/run-scripts.md")
read_file(path="<skill_dir>/_templates/report_generator.py")
```

## 产出

📝 `<PROJECT_DIR>/MEMORY.md`：N 个接口、项目位置、PROJECT_KIND、API Base URL、PYTHON、OS_TYPE、ALLURE、认证方式和凭据变量名。**必须写入该项目文件，不记录凭据原文。**

## 双重保存

先写 `<PROJECT_DIR>/MEMORY.md`；数据库可用时再额外写数据库。数据库或 Agent 记忆不可替代项目文件。
