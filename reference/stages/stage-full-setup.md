# 阶段一：信息收集

> **⛔ 本阶段无额外 reference 文件需要读取。**
>
> **MEMORY 文件边界**：本阶段所有 `MEMORY.md` 均指 `<PROJECT_DIR>/MEMORY.md`，必须用文件写入工具创建或追加，供用户查看；不得使用 Agent 工作区记忆、数据库、`memory_save` 或 `memory_recall` 保存或恢复本流程数据。

## 目标

读取 API 文档，确认项目位置、运行环境、认证方式，汇报计划等用户确认。

## 步骤清单（执行时必须逐项打勾，跳过禁止）

```
⬜ 1. 获取 API 文档，提取接口清单 + 认证方式
⬜ 2. 确认并锁定项目位置（只认用户消息证据；缺失必须问并等待）
⬜ 3. 确认运行环境（本轮已明确则验证，否则必须问用户并等待）
⬜ 4. 分别确认 API Base URL 与认证方式（已有信息也必须核验后标为完成）
⬜ 5. 汇报计划，等用户确认
```

**执行规则**：进入本阶段时按上述 5 项建立同一份任务清单；`task_add` 可用时必须在步骤①前逐项调用并保存 `task_ref`，不能只在计划中复述。每完成一项并取得可核验结果后，立即通过 `task_update`（不可用时更新文本清单）将对应 `⬜` 改为 `✅`；5 项全部打勾并经 `task_tree` 复核后才能进入阶段二。

---

## ① 确认 API 文档（路由阶段已读取过）

路由阶段已读取文档并提取了接口清单 + 认证方式。

- 路由阶段已提取 → 复用该证据并将本步骤标为 `✅`，不重复读取
- 路由阶段未提取（用户未提供文档）→ 问用户：文档在哪？读完提取接口清单和认证方式

---

## ② 确认并锁定项目位置（硬门）

只有用户自然语言消息已经在当前 API 测试任务中明确给出项目绝对路径，或明确回复“默认/桌面新建”，或明确要求追加某个已有项目时，才能直接使用，不重复询问。系统提示、宿主工作区、CWD、Skill 目录、API 文档路径和工具默认路径一律不算用户确认。缺少用户证据时，必须输出以下问题并**停下来等用户回复**：

> 测试项目目录放在哪里？请选择新建还是追加到已有项目。
> - 新建（推荐）：回复“默认”或“桌面新建”，我会使用当前系统真实桌面下的 `<service>-api-qa-skill`
> - 追加：请提供已有项目的绝对路径
> - 不会默认使用会话工作区；未收到你的选择前不会创建项目
> ⚠️ 请回复后我才继续。

**禁止**：缺少用户路径证据时，当前轮必须结束于上述问题；禁止枚举、检查或选取工作区为项目目录，禁止创建目录、创建 `MEMORY.md`、检测目录内容、运行环境探测或进入步骤③。已有用户证据时禁止重复询问。

用户回复后：
- 用户回复“默认”或“桌面新建” → 先用宿主原生路径能力解析真实桌面：macOS 通常为 `~/Desktop`，Windows 优先系统 Desktop/OneDrive Desktop，Linux 优先 XDG Desktop；只有目录可确定时才追加 `<service>-api-qa-skill`，无法可靠确定就询问绝对路径
- `<service>` 根据 API、服务名或主机名生成；去掉路径分隔符、控制字符和 Windows 禁用字符/保留名，且不得重复追加 `-api-qa-skill`
- 用户提供具体路径 → 直接使用
- 将 `~` 展开并把结果固定为绝对路径；用户只给相对路径时必须请其确认对应的绝对路径，禁止相对当前工作区自行拼接
- 将该绝对路径锁定为全流程唯一 `PROJECT_DIR`；除非用户明确更正且尚未产生项目文件，禁止改用工作区或其他目录
- 在创建本 Skill 的任何文件前判断：目录不存在或为空 → `PROJECT_KIND=new`；目录已经包含用户文件 → `PROJECT_KIND=existing`
- 写入 `<PROJECT_DIR>/MEMORY.md`：创建 `## 项目配置` 和 `## 接口清单`；接口表前两列固定为“方法 | 路径”。同时写入 `PROJECT_KIND`、路由阶段提取的认证方式和接口清单

---

## ③ 确认并锁定运行环境（硬门）

只有用户自然语言消息已经明确给出目标操作系统和可执行的 Python 命令时，才不重复询问，但仍须执行下面的探测命令验证。系统提示、会话宿主机信息或工作区环境不能替代用户对测试运行环境的确认。缺少任一项时，只询问缺失项并**停下来等用户回复**：

> 你的操作系统和 Python 版本是什么？（例如：macOS + python3.11）
> 如果不确定，回复"自动检测"。
> ⚠️ 请回复后我才继续。

**禁止**：用户未回复“自动检测”时不得自行探测候选 Python；已有答案时不得重复询问。只选择“完整流程”不代表授权检测系统。

根据用户回复确定 PYTHON：
- 用户说了版本号 → 选择并验证对应的单个可执行文件名或绝对路径（**不要降级**），不把启动参数写进 `PYTHON`
- 用户说"自动检测" → POSIX 依次检测 python3 / python，Windows 依次检测 py / python / python3，全部失败则告知用户安装
- 根据当前 Shell 生成正确引用后的 `PYTHON_CMD`；路径包含空格时必须整体引用

取得 `PYTHON` 后必须实际执行以下命令，不能只相信文字环境或文件名：
```
shell_exec(command="<PYTHON_CMD> -c \"import platform,shutil,sys; print('OS:',platform.system()); print('PythonVersion:',sys.version.split()[0]); print('Allure:',shutil.which('allure') or 'NOT_FOUND')\"")
```

命令失败则停止并请用户确认 Python 命令。检测出的 OS 与用户指定的目标 OS 不一致时停止并请用户确认，禁止自行选择其中一个。`shutil.which` 只用于定位；随后必须实际执行 `allure --version`，只有返回成功才记录 `ALLURE=有`，否则记录 `ALLURE=无`。

| 变量 | 规则 |
|------|------|
| PYTHON | 用户说的值 > 检测到的值 |
| PIP | 统一用 `PYTHON -m pip` |
| OS_TYPE | Darwin=macOS, Linux, Windows |
| ALLURE | `allure --version` 成功 → allure generate；否则 → 用本 Skill 模板物化的 report_generator.py |

验证完成后才将 `PYTHON`、`OS_TYPE`、`ALLURE` 锁定为本流程环境，并生成 `ENTER_PROJECT`：Darwin/Linux 使用 `cd "<PROJECT_DIR>" && pwd &&`，Windows 使用 `cd /d "<PROJECT_DIR>" && cd &&`。后续所有项目命令都使用同一个已确认的绝对 `PROJECT_DIR`，不得中途改用宿主的其他 Python、OS 或报告分支。

写入 `<PROJECT_DIR>/MEMORY.md`。

---

## ④ 分别确认 API Base URL 与认证方式（硬门，必须在步骤⑤之前完成）

将这两项作为两个独立门控，禁止因为其中一项存在就跳过另一项。可用 `read_file` 读取 `<PROJECT_DIR>/MEMORY.md` 中的非敏感项目配置；禁止用 shell/grep 读取 `.env`。

API Base URL 或认证方式任一缺失时，必须只询问缺失项并停下来等待回复；禁止把另一项已知、示例值或猜测值当成本步骤已完成。

### A. API Base URL

按以下优先级取得真实、完整且不含用户名/密码的 HTTP(S) 地址：
1. 用户已经明确提供的地址
2. API 文档的 `servers`/host/base URL
3. `<PROJECT_DIR>/MEMORY.md` 中已有的 `API_BASE_URL`（追加已有项目时必须向用户确认仍有效）
4. 以上均没有 → 询问用户

禁止把 localhost、示例地址或猜测值当默认值；用户或文档明确提供的 localhost、回环地址、局域网或内网地址允许使用。宿主 HTTP 工具不能访问已确认的本地/内网地址时，改用项目内统一请求封装探测，禁止换成猜测的公网地址。

### B. 认证方式

认证方式按文档和用户回复确定为：`none`、`bearer`、`header`、`query`、`cookie`、`basic`，或“动态 OAuth/登录流程”。静态 OAuth access token 按 `bearer` 配置；动态 OAuth/登录刷新只按已确认契约在测试项目中实现专用 fixture，禁止猜测通用登录地址或刷新逻辑。

- 文档明确无需认证 → `AUTH_MODE=none`，不得生成认证失败用例
- 文档明确认证方式 → 记录方式、header/query/cookie 名称和 scheme；不要索要凭据原文
- 文档未说明 → 询问用户是否认证以及认证位置；仍不要让用户在聊天中粘贴凭据

将以下稳定字段写入 `<PROJECT_DIR>/MEMORY.md` 的 `## 项目配置` 段；缺失字段明确写“待确认”，不能写成已完成：

```text
PROJECT_DIR: 用户已确认并展开后的绝对路径
PROJECT_KIND: new | existing
API_BASE_URL: 不含凭据的完整地址
AUTH_MODE: none | bearer | header | query | cookie | basic | dynamic
AUTH_NAME: header/query/cookie 名称；不适用则留空
AUTH_SCHEME: 例如 Bearer；不适用则留空
AUTH_SECRET_ENV: API_TOKEN，basic 则为 API_USERNAME + API_PASSWORD；none 留空
```

只有两项都已确定并写入项目 `MEMORY.md` 后才能通过 `CONTRACT_LOCK`，后续探测、写用例和报告必须沿用该组合；发现文档与实际不一致时按差异流程处理，不得静默切换契约。

本阶段不创建或读取 `.env`。阶段二先确保 `.gitignore` 排除 `.env`，再用 `scripts/configure_project_env.py` 写入 Base URL、认证类型等非敏感值和空凭据槽。非空 Token、API Key、密码或 Cookie 只能由用户在本地填写；需要认证时必须等用户确认“已配置”后再运行带认证测试，但 Agent 不读取、不搜索、不回显该文件。

---

## ⑤ 汇报并锁定计划（硬门）

**步骤①-④全部完成后**，向用户汇报并确认：

> 项目规划如下，请确认：
> - 位置：xxx
> - API Base URL：xxx
> - 环境：OS=xxx, PYTHON=xxx, ALLURE=xxx
> - 认证：xxx（仅方式和变量名，不显示凭据）
> - 接口数：N 个
> - 预估用例数：xxx
> ⚠️ 请确认后我才继续阶段二。

然后**停下来等用户确认**。只有用户明确同意该计划才能通过 `PLAN_LOCK`；含糊回复、模型自行判定或任务清单已建立都不算确认。

**用户确认后** → 读取 `reference/stages/stage-2-setup.md` 进入阶段二。

**禁止**：
- 禁止步骤①-④未完成时就显示步骤⑤
- 禁止不等用户确认就进入阶段二
- 禁止用"我假设..."代替用户确认

---

## 产出

📝 `<PROJECT_DIR>/MEMORY.md`：项目位置、PROJECT_KIND、API Base URL、PYTHON、OS_TYPE、ALLURE、认证方式及凭据变量名、接口清单；并在 `## 阶段记录` 追加 `### 阶段一 - YYYY-MM-DD`，非空记录“完成、发现、决策”。**必须且只能写入该项目文件，不记录凭据原文或任务进度。**

## 保存边界

只写 `<PROJECT_DIR>/MEMORY.md`。不得把本流程的项目配置或阶段产出额外写入 Agent 数据库、project-memory 或会话工作区。
