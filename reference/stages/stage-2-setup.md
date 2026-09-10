# 阶段二：搭框架 + 调接口

> **⛔ 本阶段需要额外读取：reference/implementation.md + reference/run-scripts.md + _templates/report_generator.py**

> **MEMORY 文件边界**：本阶段所有 `MEMORY.md` 均指 `<PROJECT_DIR>/MEMORY.md`，必须用文件写入工具追加，供用户查看；Agent 工作区记忆、数据库或 `memory_save` 不能替代该文件。

## 目标

创建项目结构，验证接口，安装依赖。

## 步骤清单（执行时必须逐项打勾，跳过禁止）

```
⬜ ① 创建框架文件（conftest.py / request_helper.py 等）
⬜ ② 复制报告工具
⬜ ③ 生成与 OS_TYPE 对应的一个运行脚本
⬜ ④ 安装依赖
⬜ ⑤ curl 调每个接口，记录实际返回
```

**执行规则**：每完成一项立即将 `⬜` 改为 `✅`，全部打勾才能进入阶段三。

## ⛔ 开始前：全面检查项目状态

使用 `list_files(path="<PROJECT_DIR>", recursive=true)` 检查文件名，不用 shell 读取项目文件。允许确认 `.env` 文件是否存在，但**禁止**用 `read_file`、grep、Python、shell 或其他工具读取/搜索其内容。API Base URL 是否已确认，以阶段一 `<PROJECT_DIR>/MEMORY.md` 的稳定“项目配置”段为准；`.env` 是否已写入，以本阶段 `configure_env` 的返回结果为准。

**检查结果处理**：
- **所有文件都存在、当前 OS 脚本存在、报告模板已验证，且本次 `configure_env` 已确认非敏感配置** → 直接进入 ⑤ curl 调接口（跳过已满足的 ①-④）
- **核心文件缺失** → 进入 ① 创建核心文件
- **报告工具缺失** → 进入 ② 复制报告工具
- **⛔ 当前 OS 对应的运行脚本缺失** → **必须进入 ③ 生成运行脚本，禁止跳过**
- **`.env` 缺失或本次尚未确认非敏感配置** → 在 ① 中用 `configure_env` 创建/补齐；禁止读取旧值来判断
- **不要重复创建已存在的文件** — 已存在的文件跳过，只创建缺失的

已有 `utils/report_generator.py` 仍须执行步骤②的语法与 `--help` 验证；验证通过可跳过复制，不能仅凭文件存在就跳过验证。

---

## ① 创建框架文件

用 `save_file` 创建以下文件（**完整代码见 reference/implementation.md**，用 read_file 读取后照抄）：
- `.gitignore`（必须先创建/修复并排除 `.env`）
- `conftest.py` — 完整代码在 reference/implementation.md 的 "## conftest.py 完整代码" 章节
- `utils/request_helper.py` — 完整代码在 reference/implementation.md 的 "## request_helper.py 完整代码" 章节
- `utils/__init__.py` — 空文件
- `pytest.ini`
- `requirements.txt`

创建/修复 `.gitignore` 时必须先确保它包含独立一行 `.env`。然后调用 `configure_env` 写入阶段一已经确认的非敏感值。新项目使用：

```text
configure_env(path="<PROJECT_DIR>/.env", variables={"API_BASE_URL":"<已确认地址>","API_AUTH_MODE":"<none|bearer|header|query|cookie|basic|dynamic>","API_AUTH_NAME":"<header/query/cookie 名称或空>","API_AUTH_SCHEME":"<scheme 或空>","API_TOKEN":"","API_USERNAME":"","API_PASSWORD":"","REPORT_TITLE":""}, replace_existing=false)
```

禁止用 `save_file`/`edit_file` 写 `.env`。

- `PROJECT_KIND=new`：创建空凭据槽；需要认证时暂停在本步骤，请用户在本地填写相应变量并只回复“已配置”
- `PROJECT_KIND=existing`：不要读取或覆盖既有凭据。先只用 `replace_existing=false` 补缺失变量；如返回同名冲突，只列出变量名并请用户确认。确需改 Base URL/认证类型时，单独调用 `configure_env(..., replace_existing=true)` 且参数中只包含非敏感键，绝不同时传凭据键
- 用户确认后只通过测试结果验证认证是否可用；禁止读取、搜索、打印或回显 `.env`

**⚠️ 文件创建失败处理**：
- 如果 save_file 失败，**最多重试 2 次**
- 如果连续 3 次都失败，**停止创建**，告知用户："无法创建文件，请检查目录权限或磁盘空间"
- **禁止死循环重试** — 必须有明确的退出条件

---

## ② 复制报告工具

无论 ALLURE=有/无，都交付内置报告生成器，供运行环境没有 Allure CLI 时回退使用。若项目中的文件与模板完全相同可跳过保存；若是用户已有定制文件，只修复与当前单报告规则冲突的部分，禁止整文件覆盖。

**步骤1：获取模板文件（分页读取）**

使用 `read_file`：
```
read_file(path="<skill_dir>/_templates/report_generator.py")
```

如返回 `has_more=true`，按 `continuation.next_offset` 继续读取；只有超长单行时，才同时传回 `continuation.next_char_offset`。不得用 `shell_exec cat` 替代分页。

**⚠️ 如果 read_file 仍失败**：
- 告知用户："无法自动获取报告生成器模板文件"
- 询问："请提供 report_generator.py 的文件路径，或粘贴文件内容"

**步骤2：保存到项目目录**
```
save_file(path="<PROJECT_DIR>/utils/report_generator.py", content="<读取到的内容>")
```

**步骤3：验证文件可用**
```
shell_exec(command="<ENTER_PROJECT> <PYTHON> -m py_compile utils/report_generator.py && <PYTHON> utils/report_generator.py --help")
```

**验证结果处理**：
- **文件存在、语法检查和 `--help` 均通过** → 继续下一步
- **文件不存在或检查失败** → **必须重新执行步骤1-2**，不能跳过，不能自己创建简化版
- **如果连续 3 次都失败** → 告知用户无法复制模板，询问是否手动提供文件内容

**⚠️ 红线**：
1. **禁止自己创建简化版** — 新文件必须完整使用 `_templates/report_generator.py`
2. **禁止用其他文件替代** — 不能用 `simple_report.py` 等替代

**为什么重要**：没有 allure 时，这个文件是生成单页面 HTML 报告的唯一方式。如果用简化版，用户将看不到交互式报告。

---

## ③ 生成运行脚本

**⛔ 本步骤不可跳过。运行脚本是用户一键执行测试+生成报告的唯一入口，缺少脚本等于无法交付。**

**只检查当前 OS 对应的脚本是否存在**：

OS_TYPE 是 Darwin 或 Linux：
```
shell_exec(command="<ENTER_PROJECT> test -x run.sh")
```

OS_TYPE 是 Windows：
```
shell_exec(command="<ENTER_PROJECT> if exist run.bat (echo run.bat exists) else (echo MISSING: run.bat & exit /b 1)")
```

**处理规则**：
- **如果对应脚本已存在，且不含自动打开报告或双报告冲突** → 跳过，不要覆盖；有冲突时只按模板修正冲突行
- **如果对应脚本不存在** → **必须执行下面的步骤1-3，禁止跳过**
- **新项目禁止生成另一操作系统的脚本**；追加已有项目时不要删除用户原有的另一平台脚本

**步骤1：获取脚本内容（分页读取）**

使用 `read_file`：
```
read_file(path="<skill_dir>/reference/run-scripts.md")
```

如返回 `has_more=true`，使用返回的 continuation 读取下一页；不得用 `shell_exec cat` 替代分页。

**⚠️ 如果 read_file 仍失败**：
- 告知用户："无法自动获取运行脚本模板文件"
- 询问："请提供 run.sh 的文件路径，或粘贴文件内容"

**步骤2：保存到项目目录**
- OS_TYPE 是 Darwin 或 Linux → 用 `save_file` 保存为 `<PROJECT_DIR>/run.sh`
- OS_TYPE 是 Windows → 用 `save_file` 保存为 `<PROJECT_DIR>/run.bat`
- **必须原样使用**脚本内容，脚本已内置 Python 自动检测，不需要修改

**步骤3：设置执行权限并验证**

OS_TYPE 是 Darwin 或 Linux：
```
shell_exec(command="<ENTER_PROJECT> chmod +x run.sh && test -x run.sh")
```

OS_TYPE 是 Windows：
```
shell_exec(command="<ENTER_PROJECT> if exist run.bat (echo run.bat exists) else (echo MISSING: run.bat & exit /b 1)")
```

**验证结果处理**：
- **文件存在且有执行权限（Darwin/Linux 有 x 标志）** → 继续下一步
- **文件不存在** → **必须重新执行步骤1-2**，不能跳过
- **连续 3 次都失败** → 告知用户无法生成运行脚本，询问是否手动提供

**⚠️ 红线**：
1. **禁止跳过 ③** — 运行脚本缺失时直接进 ④ 等于交付残缺项目
2. **禁止自己重写脚本** — 必须从 `reference/run-scripts.md` 原样复制，脚本内容已经过验证
3. **禁止忘记 chmod +x** — macOS/Linux 下没有执行权限，用户执行 `./run.sh` 会报 `Permission denied`

**为什么重要**：用户拿到项目后，只需要执行当前系统对应的一个脚本就能自动安装依赖、跑测试、生成报告。缺少对应脚本 = 用户需要手动敲多条命令 = 交付不合格。

---

## ④ 安装依赖

```
shell_exec(command="<ENTER_PROJECT> <PYTHON> -m pip install -r requirements.txt")
```

⚠️ 如果安装失败：
- 检查 PYTHON 是否正确（用 `<PYTHON> --version` 验证）
- 检查网络连接
- 某个包安装失败 → 尝试 `<PYTHON> -m pip install <包名>` 单独安装
- Python 版本不兼容 → 告知用户需要升级

**⚠️ 安装失败处理**：
- 如果 pip install 失败，**最多重试 2 次**
- 如果连续 3 次都失败，**停止安装**，告知用户："依赖安装失败，请检查网络连接或 Python 环境"
- **禁止死循环重试** — 必须有明确的退出条件

---

## ⑤ curl 调每个接口

- **无需认证** → 用 `curl` 工具按文档调用并记录实际返回
- **需要认证** → `curl` 仍对每个接口做一次不带凭据的探测并记录认证失败响应；凭据由用户在本地 `.env` 配置后，带认证行为在阶段三/四通过 `AuthSession` 测试验证
- **禁止**把 Token、API Key、密码或 Cookie 放进 curl 参数、命令、日志或 MEMORY；禁止猜测登录地址或 Bearer 方案

用 `curl` 工具调每个接口，记录实际返回，比对文档差异。

如果 API 使用动态登录/OAuth：仅在文档或用户确认的契约下编写项目专用 fixture，并让运行时从 `.env` 取得本地凭据；Agent 不调用带真实用户名/密码的登录请求，也不读取 token 响应原文。脱敏后的状态、字段结构和契约差异仍需记录。

## 产出

📝 `<PROJECT_DIR>/MEMORY.md`：差异表。**必须更新该项目文件，追加本阶段产出。**

## 双重保存

先写 `<PROJECT_DIR>/MEMORY.md`；数据库可用时再额外写数据库。数据库或 Agent 记忆不可替代项目文件。
