# 阶段二：搭框架 + 调接口

> **⛔ 按需加载：标准模板一律优先通过 `scripts/materialize_templates.py` 落盘，不读取模板正文。只有物化结果为 `REVIEW`、已有核心文件需要适配或认证为 `dynamic` 时才读 `reference/implementation.md`；③仅在 runner 冲突或物化命令不可用/被拒绝时读 `reference/run-scripts.md`。运行脚本在本阶段预置，交付前才验收和实跑。**

> **MEMORY 文件边界**：本阶段所有 `MEMORY.md` 均指 `<PROJECT_DIR>/MEMORY.md`，必须用文件写入工具追加，供用户查看；不得使用 Agent 工作区记忆、数据库、`memory_save` 或 `memory_recall` 保存或恢复本流程数据。

## 目标

创建项目结构，预置当前 OS 运行脚本，验证接口，安装依赖。

## 步骤清单（执行时必须逐项打勾，跳过禁止）

```
⬜ ① 创建或确认框架文件（conftest.py / request_helper.py 等）
⬜ ② 按 ALLURE 分支处理报告工具（有则确认无需复制，无则复制并验证）
⬜ ③ 预置 OS_TYPE 对应的一个运行脚本
⬜ ④ 安装依赖
⬜ ⑤ 按认证分支真实探测每个接口，记录实际返回
```

**执行规则**：进入本阶段时按上述 5 项建立同一份任务清单；`task_add` 可用时必须在步骤①前逐项调用并保存 `task_ref`，不能只在计划中复述。每项实际执行成功，或经工具核验已满足且无需重复写入后，立即通过 `task_update`（不可用时更新文本清单）将对应 `⬜` 改为 `✅`；不得标记为 `skipped`。5 项全部打勾并经 `task_tree` 复核后才能进入阶段三。若①或②的命令能力已被拒绝，不把它标为完成，但仍必须执行③的文件能力降级路径，先把当前 OS 脚本留在项目中，再结束本轮并交给用户执行。

## ⛔ 开始前：全面检查项目状态

先读取并核对 `<PROJECT_DIR>/MEMORY.md` 中已确认的绝对 `PROJECT_DIR`、`PROJECT_KIND`、`PYTHON`、`OS_TYPE`、`ALLURE`、`API_BASE_URL`、`AUTH_MODE`，以及当前认证方式所需的名称、scheme 和凭据环境变量名。任一应有项缺失或仍为占位符时，返回阶段一的对应硬门补齐，禁止猜测后继续。根据已锁定的 `OS_TYPE` 生成一次 `ENTER_PROJECT`，后续不得切换目录、Python、OS、认证或报告分支。

使用宿主的递归文件枚举能力检查文件名；Test-Claw 调用 `glob_search(pattern="**/*", path="<PROJECT_DIR>")`，不要向 `list_files` 传不存在的 `recursive` 参数，也不用 shell 读取项目文件。允许确认 `.env` 是否存在，但**禁止**用文件、grep、Python、shell 或其他 Agent 工具读取/搜索其内容。API Base URL 以阶段一 `<PROJECT_DIR>/MEMORY.md` 为准；`.env` 是否写入，以本阶段配置脚本的结果为准。

**检查结果处理**：
- **核心文件、当前 OS 脚本均存在，`ALLURE=有` 或报告模板已验证，且本次配置脚本已确认非敏感配置** → 仍按步骤①-④逐项核验并标为 `✅`，再进入⑤；无需重复写入，但不得标为 `skipped`
- **核心文件缺失** → 进入 ① 创建核心文件
- **报告工具缺失且 `ALLURE=无`** → 进入 ② 复制报告工具；`ALLURE=有` 时不读取、不复制也不验证报告工具
- **当前 OS 脚本缺失** → 必须进入③预置；不能等到测试或交付结束才补
- **`.env` 缺失或本次尚未确认非敏感配置** → 在①中用配置脚本创建/合并；禁止读取旧值来判断
- **不要重复创建已存在的文件** — 已存在的文件经核验后视为该项完成，只创建缺失的

仅 `ALLURE=无` 时，已有 `utils/report_generator.py` 必须先由物化脚本做字节一致性校验；只有与当前 Skill 模板一致时才执行步骤②的语法与 `--help` 验证并标 `✅`。内容不一致时保留并询问用户，不能仅凭文件存在或可执行就继续。`ALLURE=有` 的已有项目如原本存在该文件，保留不动，不读取、不覆盖也不删除。

---

## ① 创建框架文件

直接执行物化脚本，按字节复制缺失模板；不得先读取 `_templates/project/` 或手抄模板：

```text
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> \"<SKILL_DIR>/scripts/materialize_templates.py\" --project \"<PROJECT_DIR>\" --component core --project-kind <PROJECT_KIND>")
```

脚本处理 `.gitignore`、`conftest.py`、`utils/contract_probe.py`、`utils/request_helper.py`、`utils/__init__.py`、`pytest.ini`、`requirements.txt`，并逐项输出 `CREATED` / `UNCHANGED` / `PRESERVED` 和哈希：

- `TEMPLATE MATERIALIZATION: PASS`：模板已创建或逐字一致，不读实现规范
- `TEMPLATE MATERIALIZATION: REVIEW`：仅此时完整读取 `reference/implementation.md`，再只读取 `PRESERVED` 列出的非敏感目标文件；满足契约则保留，有直接冲突才最小修改
- `TEMPLATE MATERIALIZATION: FAIL`：先根据错误修复路径、权限或参数后重试，最多 2 次；连续 3 次失败即停止并告知用户，禁止手写简化模板

认证为 `dynamic` 时，即使物化通过，也只在需要定制 fixture 时读取 `reference/implementation.md` 的认证契约；其他认证不读取。

确认 `.gitignore` 包含独立一行 `.env` 后，调用项目配置脚本。它会在进程内合并 `.env`，只输出变量名和 CREATED/UPDATED/UNCHANGED/PRESERVED，不输出任何值；已有凭据始终保留：

```text
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> \"<SKILL_DIR>/scripts/configure_project_env.py\" --project \"<PROJECT_DIR>\" --base-url \"<已确认地址>\" --auth-mode <AUTH_MODE> --auth-name \"<名称或空>\" --auth-scheme \"<scheme 或空>\" [dynamic 时传 --secret-env \"<已确认的变量名列表>\"]")
```

禁止用 Agent 文件工具写或读取 `.env`。

- `PROJECT_KIND=new`：创建空凭据槽；需要认证时暂停在本步骤，请用户在本地填写相应变量并只回复“已配置”
- `PROJECT_KIND=existing`：配置脚本只把用户已确认的 Base URL、认证类型、名称和 scheme 更新为当前值，补齐当前认证模式需要的凭据槽；已有凭据值只标记 `PRESERVED`，绝不覆盖或回显
- 用户确认后只通过测试结果验证认证是否可用；禁止读取、搜索、打印或回显 `.env`

**⚠️ 文件创建失败处理**：
- 如果模板物化或必要的最小修改失败，**最多重试 2 次**
- 如果连续 3 次都失败，**停止创建**，告知用户："无法创建文件，请检查目录权限或磁盘空间"
- **禁止死循环重试** — 必须有明确的退出条件

---

## ② 复制报告工具（根据 ALLURE 决定）

先使用阶段一已经实际验证并写入 `<PROJECT_DIR>/MEMORY.md` 的 `ALLURE` 值，禁止在本步骤重新猜测。物化 `report` 或 `runner` 时，物化脚本还会独立执行 `allure --version`；若输出“报告模式与本机实际 Allure 检测不一致”，不得把它当作普通重试，必须返回 `ENV_LOCK` 重新锁定，不能复制 fallback 或继续生成报告。

**ALLURE=有**：禁止读取或复制 `_templates/report_generator.py`；确认当前报告分支使用官方 Allure 后，将步骤②标记为 `✅` 并进入③。追加已有项目时如原本存在 `utils/report_generator.py`，保留不动，不验证、不覆盖也不删除。

**ALLURE=无**：不读取报告模板，直接按字节复制：

```text
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> \"<SKILL_DIR>/scripts/materialize_templates.py\" --project \"<PROJECT_DIR>\" --component report --project-kind <PROJECT_KIND> --report fallback")
```

- `PASS`：文件已创建或与模板一致
- `REVIEW`：说明已有生成器并非当前 Skill 模板；保留原文件，不读取、不运行、不修改，登记“等待用户”并询问如何处理。用户明确移走、删除或允许替换前不得继续 fallback 分支
- `FAIL`：按错误修复后最多重试 2 次；连续 3 次失败停止并如实报告

随后验证文件可用：
```
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> -m py_compile utils/report_generator.py && <PYTHON_CMD> utils/report_generator.py --help")
```

只有物化结果为 `PASS` 时才执行下面的验证；`REVIEW` 不得执行现有生成器。

**验证结果处理**：
- **文件存在、语法检查和 `--help` 均通过** → 继续下一步
- **文件不存在或检查失败** → 返回物化/冲突修正步骤，不能跳过，不能自己创建简化版
- **如果连续 3 次都失败** → 告知用户无法交付回退报告生成器并停止

**⚠️ 红线**：
1. **禁止自己创建简化版** — 新文件必须完整使用 `_templates/report_generator.py`
2. **禁止用其他文件替代** — 不能用 `simple_report.py` 等替代

**为什么重要**：没有 allure 时，这个文件是生成单页面 HTML 报告的唯一方式。如果用简化版，用户将看不到交互式报告。

---

## ③ 预置当前 OS 运行脚本

在任何依赖安装或测试命令之前，按已锁定的 `OS_TYPE`、`PYTHON` 和 `ALLURE` 预置唯一脚本；`<REPORT_MODE>` 为 `official` 或 `fallback`：

```text
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> \"<SKILL_DIR>/scripts/materialize_templates.py\" --project \"<PROJECT_DIR>\" --component runner --project-kind <PROJECT_KIND> --os <OS_TYPE> --python-command \"<PYTHON>\" --report <REPORT_MODE>")
```

- `PASS`：脚本已创建或与当前模板一致；新项目只允许当前 OS 的一份脚本
- `REVIEW`：读取 `reference/run-scripts.md` 和当前 OS 的既有脚本，只做必要的冲突判断或最小修正，禁止覆盖定制内容
- `FAIL`：按错误修复后最多重试 2 次；连续 3 次失败停止
- runner 物化命令不可用或被拒绝：读取 `reference/run-scripts.md`，按其中“命令能力受阻时预置脚本”只用文件能力落盘；脚本存在并回读核对后可将③标为 `✅`，权限、语法和实跑留到交付前

无论前面①或②是否因命令权限而阻塞，只要文件读写能力仍可用，都必须先完成本步骤再向用户交接。新项目不得生成另一平台脚本；已有项目不删除用户原有脚本。

---

## ④ 安装依赖

```
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> -m pip install -r requirements.txt")
```

⚠️ 如果安装失败：
- 检查 PYTHON 是否正确（用 `<PYTHON_CMD> --version` 验证）
- 检查网络连接
- 某个包安装失败 → 尝试 `<PYTHON_CMD> -m pip install <包名>` 单独安装
- Python 版本不兼容 → 告知用户需要升级

**⚠️ 安装失败处理**：
- 如果 pip install 失败，**最多重试 2 次**
- 如果连续 3 次都失败，**停止安装**，告知用户："依赖安装失败，请检查网络连接或 Python 环境"
- **禁止死循环重试** — 必须有明确的退出条件

---

## ⑤ 调每个接口并记录真实返回

- **无需认证** → 用宿主 HTTP 能力按文档调用并记录实际返回；宿主不能访问已确认的本地/内网地址时改用项目内统一请求封装
- **静态认证**（`bearer` / `header` / `query` / `cookie` / `basic`）→ 先做一次无凭据 `curl` 探测并记录认证失败响应；用户确认已在本地填好 `.env` 后，**在写用例前**对每个接口用项目内安全探测器取得成功或业务错误响应的状态码和脱敏字段结构：

```text
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> -m utils.contract_probe --method <METHOD> --path \"<已把路径参数替换为非敏感代表值的具体路径>\" [--params-file \"<PROJECT_DIR>/.probe/<非敏感参数文件>.json\"] [--json-body-file \"<PROJECT_DIR>/.probe/<非敏感请求体文件>.json\"]")
```

查询参数或 JSON 请求体存在时，用文件能力写入项目内临时 `.probe/*.json`，通过文件参数传递并在探测完成后删除 `.probe` 临时文件；这样不依赖 POSIX/Windows Shell 的 JSON 引号规则。命令参数和临时文件不得包含 Token、Cookie、密码或 API Key。若契约要求 form、multipart 或额外非敏感 header，先写一个最小项目内测试通过统一请求封装真实探测，不扩展探测器猜测协议。将 `PROBE: PASS` 的状态码和结构追加到差异表；`PROBE: BLOCKED` 时停止并请用户完成本地配置，`PROBE: FAIL` 时先排查 Base URL、契约或网络。
- **动态 OAuth/登录** → 不猜测登录地址或刷新逻辑。先按文档或用户确认的契约实现项目专用 fixture；阶段三先写并运行一个最小真实认证用例取得状态码和脱敏结构，确认后才扩展其余用例
- **禁止**把 Token、API Key、密码或 Cookie 放进 curl 参数、命令、日志或 MEMORY；禁止猜测登录地址或 Bearer 方案

按上述认证分支逐个取得真实响应，记录状态码、脱敏字段结构并比对文档差异；不得用无凭据探测的 401/403 代替认证后的接口结果。HEAD/OPTIONS 与其他方法一样按契约探测。

遇到 POST/PUT/PATCH/DELETE 或并发、支付、权限变更场景时，先确认目标环境允许测试并在 MEMORY 记录非敏感的授权结论与清理策略；未确认就停下，不发送有副作用的请求。准备数据和清理请求可以与主验证接口不同，后续用例只把 `api_endpoint` 标在主验证接口上。

`--path` 只写 `/` 开头的具体相对路径，必须先把 `{id}` 等路径参数替换成非敏感代表值，不能包含查询串；查询参数统一使用 `--params-file`。`utils/contract_probe.py` 在项目进程内读取 `.env`，但 stdout 只输出状态、Content-Type 和脱敏字段结构；脚本会拒绝越界文件、凭据字段、已配置凭据值和未替换路径占位符，Agent 不读取 token 响应原文。

## 产出

📝 `<PROJECT_DIR>/MEMORY.md`：将文档与实际返回差异追加到 `## 差异表`；没有差异也明确写“无差异”。并在 `## 阶段记录` 追加 `### 阶段二 - YYYY-MM-DD`，非空记录“完成、发现、决策”。**必须更新该项目文件，追加本阶段产出。**

## 保存边界

只写 `<PROJECT_DIR>/MEMORY.md`。不得把本流程的项目配置或阶段产出额外写入 Agent 数据库、project-memory 或会话工作区。
