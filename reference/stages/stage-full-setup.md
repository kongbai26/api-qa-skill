# 阶段一：信息收集

> **⛔ 本阶段无额外 reference 文件需要读取。**
>
> **MEMORY 文件边界**：本阶段所有 `MEMORY.md` 均指 `<PROJECT_DIR>/MEMORY.md`，必须用文件写入工具创建或追加，供用户查看；Agent 工作区记忆、数据库或 `memory_save` 不能替代该文件。

## 目标

读取 API 文档，确认项目位置、运行环境、认证方式，汇报计划等用户确认。

## 步骤清单（执行时必须逐项打勾，跳过禁止）

```
⬜ 1. 获取 API 文档，提取接口清单 + 认证方式
⬜ 2. 确认项目位置（已有则沿用，缺失才问用户）
⬜ 3. 确认运行环境（已有则沿用，缺失才问用户）
⬜ 4. 分别确认 API Base URL 与认证方式（各自已有才跳过）
⬜ 5. 汇报计划，等用户确认
```

**执行规则**：每完成一项立即将 `⬜` 改为 `✅`，全部打勾才能进入阶段二。

---

## ① 确认 API 文档（路由阶段已读取过）

路由阶段已读取文档并提取了接口清单 + 认证方式。

- 路由阶段已提取 → 直接使用，跳过本步骤
- 路由阶段未提取（用户未提供文档）→ 问用户：文档在哪？读完提取接口清单和认证方式

---

## ② 确认项目位置

用户在本轮已经给出绝对路径、桌面默认或追加已有项目时，直接使用，不重复询问。只有尚未提供任何位置时，才输出以下问题并**停下来等用户回复**：

> 项目默认新建在桌面的 `~/Desktop/<service>-api-qa-skill`。如需其他位置或追加已有项目，请提供绝对路径。
> - 新建：默认使用根据 API/服务名生成的 `<service>-api-qa-skill`
> - 追加：请提供已有项目的绝对路径
> ⚠️ 请回复后我才继续。

**禁止**：缺失位置时禁止不等回复就继续；已给出位置时禁止重复询问。禁止把会话工作区当成默认交付目录。

用户回复后：
- 用户未指定路径、回复“默认”或“桌面新建” → 项目位置 = 展开后的 `~/Desktop/<service>-api-qa-skill`（项目名根据 API、服务名或主机名生成）
- 用户提供具体路径 → 直接使用
- 在创建本 Skill 的任何文件前判断：目录不存在或为空 → `PROJECT_KIND=new`；目录已经包含用户文件 → `PROJECT_KIND=existing`
- 写入 `<PROJECT_DIR>/MEMORY.md`（同时将 `PROJECT_KIND`、路由阶段提取的认证方式和接口清单一并写入）

---

## ③ 确认运行环境

用户在本轮已经给出操作系统和 Python 版本时直接沿用；缺失时才输出以下问题并**停下来等用户回复**：

> 你的操作系统和 Python 版本是什么？（例如：macOS + python3.11）
> 如果不确定，回复"自动检测"。
> ⚠️ 请回复后我才继续。

**禁止**：用户未授权自动检测时不得自行检测；已有答案时不得重复询问。

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

写入 `<PROJECT_DIR>/MEMORY.md`。

---

## ④ 分别确认 API Base URL 与认证方式（必须在步骤⑤之前完成）

将这两项作为两个独立门控，禁止因为其中一项存在就跳过另一项。可用 `read_file` 读取 `<PROJECT_DIR>/MEMORY.md` 中的非敏感项目配置；禁止用 shell/grep 读取 `.env`。

### A. API Base URL

按以下优先级取得真实、完整且不含用户名/密码的 HTTP(S) 地址：
1. 用户已经明确提供的地址
2. API 文档的 `servers`/host/base URL
3. `<PROJECT_DIR>/MEMORY.md` 中已有的 `API_BASE_URL`（追加已有项目时必须向用户确认仍有效）
4. 以上均没有 → 询问用户

禁止使用 localhost、示例地址或猜测值作为默认值。

### B. 认证方式

认证方式按文档和用户回复确定为：`none`、`bearer`、`header`、`query`、`cookie`、`basic`，或“动态 OAuth/登录流程”。静态 OAuth access token 按 `bearer` 配置；动态 OAuth/登录刷新只按已确认契约在测试项目中实现专用 fixture，禁止猜测通用登录地址或刷新逻辑。

- 文档明确无需认证 → `AUTH_MODE=none`，不得生成认证失败用例
- 文档明确认证方式 → 记录方式、header/query/cookie 名称和 scheme；不要索要凭据原文
- 文档未说明 → 询问用户是否认证以及认证位置；仍不要让用户在聊天中粘贴凭据

将以下稳定字段写入 `<PROJECT_DIR>/MEMORY.md` 的“项目配置”段；缺失字段明确写“待确认”，不能写成已完成：

```text
PROJECT_KIND: new | existing
API_BASE_URL: 不含凭据的完整地址
AUTH_MODE: none | bearer | header | query | cookie | basic | dynamic
AUTH_NAME: header/query/cookie 名称；不适用则留空
AUTH_SCHEME: 例如 Bearer；不适用则留空
AUTH_SECRET_ENV: API_TOKEN，basic 则为 API_USERNAME + API_PASSWORD；none 留空
```

本阶段不创建或读取 `.env`。阶段二先确保 `.gitignore` 排除 `.env`，再用 `configure_env` 写入 Base URL、认证类型等非敏感值和空凭据槽。非空 Token、API Key、密码或 Cookie 只能由用户在本地填写；需要认证时必须等用户确认“已配置”后再运行带认证测试，但 Agent 不读取、不搜索、不回显该文件。

---

## ⑤ 汇报计划，等用户确认

**步骤①-④全部完成后**，向用户汇报并确认：

> 项目规划如下，请确认：
> - 位置：xxx
> - API Base URL：xxx
> - 环境：OS=xxx, PYTHON=xxx, ALLURE=xxx
> - 认证：xxx（仅方式和变量名，不显示凭据）
> - 接口数：N 个
> - 预估用例数：xxx
> ⚠️ 请确认后我才继续阶段二。

然后**停下来等用户确认**。

**用户确认后** → 读取 `reference/stages/stage-2-setup.md` 进入阶段二。

**禁止**：
- 禁止步骤①-④未完成时就显示步骤⑤
- 禁止不等用户确认就进入阶段二
- 禁止用"我假设..."代替用户确认

---

## 产出

📝 `<PROJECT_DIR>/MEMORY.md`：项目位置、PROJECT_KIND、API Base URL、PYTHON、OS_TYPE、ALLURE、认证方式及凭据变量名、接口清单。**必须写入该项目文件（如果数据库可用，再额外写入数据库），不记录凭据原文。**

## 双重保存

先写 `<PROJECT_DIR>/MEMORY.md`；数据库可用时再额外写数据库。数据库或 Agent 记忆不可替代项目文件。
