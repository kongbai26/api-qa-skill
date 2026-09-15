# 快速路径：阶段 3-5 合并

> **⛔ 按需加载：标准模板一律优先通过 `scripts/materialize_templates.py` 落盘，不读取模板正文。只有物化结果为 `REVIEW`、已有核心文件需要适配或认证为 `dynamic` 时才读 `reference/implementation.md`；只有 runner 冲突或物化命令不可用/被拒绝时才读 `reference/run-scripts.md`。禁止提前批量读取。结束时执行 `scripts/validate_delivery.py`。**
>
> ⚠️ 仅用于接口数 ≤ 5 的简单任务。复杂逻辑（支付/权限/工作流）必须走完整 5 阶段。
>
> **MEMORY 文件边界**：本阶段所有 `MEMORY.md` 均指 `<PROJECT_DIR>/MEMORY.md`，必须用文件写入工具追加，供用户查看；不得使用 Agent 工作区记忆、数据库、`memory_save` 或 `memory_recall` 保存或恢复本流程数据。

## 目标

合并原阶段 3-5，一口气完成：搭框架并预置脚本 → 调接口 → 写用例 → 跑测试 → 出报告 → 交付前实跑脚本 → 更新 MEMORY。

## 步骤清单

```
⬜ 1. 搭框架并预置 OS_TYPE 对应的一个运行脚本
⬜ 2. 安装依赖
⬜ 3. 按认证分支真实探测每个接口，记录实际返回
⬜ 4. 写测试用例（每接口 3-5 条核心用例，总数 ≥ 接口数 × 3）
⬜ 5. 跑 pytest + 修断言（循环直到通过，最多 3 轮）
⬜ 6. 生成报告
⬜ 7. 交付前复核、验收并实际执行已预置的运行脚本
⬜ 8. 统一更新并验收 `<PROJECT_DIR>/MEMORY.md`
```

**执行规则**：不新增计划确认门控，连续执行；只有认证 API 需要用户在本地填写凭据时，允许在步骤①等待“已配置”。进入本阶段后、步骤①实质操作前，`task_add` 可用时必须为上述 8 项逐项调用并保存 `task_ref`，不能只在思考或计划中列出 8 项；完成一项立即用 `task_update` 更新一项，并在结束前用 `task_tree` 复核。任务工具不可用时才使用持续更新的文本清单。8 项不可拆散或提前结束：步骤⑥完成后下一步必须是⑦，步骤⑦完成后下一步必须是⑧；报告生成成功不代表交付完成。

**执行前置校验**：先读取并核对 `<PROJECT_DIR>/MEMORY.md` 中已确认的绝对 `PROJECT_DIR`、`PROJECT_KIND`、`PYTHON`、`OS_TYPE`、`ALLURE`、`API_BASE_URL`、`AUTH_MODE`，以及当前认证方式所需的名称、scheme 和凭据环境变量名。任一应有项缺失、仍为占位符，或项目目录尚未得到用户确认时，返回 `stage-quick-setup.md` 的对应硬门补齐，禁止猜测后继续。根据已锁定的 `OS_TYPE` 生成一次 `ENTER_PROJECT`，后续不得切换目录、Python、OS、认证或报告分支。

---

## ① 搭框架

先用宿主递归文件枚举能力盘点已有文件；Test-Claw 调用 `glob_search(pattern="**/*", path="<PROJECT_DIR>")`，不要向 `list_files` 传不存在的 `recursive` 参数。再直接物化缺失的标准框架，不得先读取模板正文或手抄模板：

```text
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> \"<SKILL_DIR>/scripts/materialize_templates.py\" --project \"<PROJECT_DIR>\" --component core --project-kind <PROJECT_KIND>")
```

脚本逐项输出 `CREATED` / `UNCHANGED` / `PRESERVED` 和哈希；标准核心文件包含 `utils/contract_probe.py`，供静态认证接口在写用例前安全探测真实响应：

- `TEMPLATE MATERIALIZATION: PASS`：模板已创建或逐字一致，不读实现规范
- `TEMPLATE MATERIALIZATION: REVIEW`：仅此时完整读取 `reference/implementation.md`，再只读取 `PRESERVED` 列出的非敏感目标文件；满足契约则保留，有直接冲突才最小修改
- `TEMPLATE MATERIALIZATION: FAIL`：按错误修复后最多重试 2 次；连续 3 次失败即停止并告知用户，禁止手写简化模板

认证为 `dynamic` 时，即使物化通过，也只在需要定制 fixture 时读取 `reference/implementation.md` 的认证契约。

先确认 `.gitignore` 包含独立一行 `.env`；再调用项目配置脚本。它只输出变量名和处理状态，保留已有凭据值，不向模型暴露 `.env` 内容：

```text
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> \"<SKILL_DIR>/scripts/configure_project_env.py\" --project \"<PROJECT_DIR>\" --base-url \"<已确认地址>\" --auth-mode <AUTH_MODE> --auth-name \"<名称或空>\" --auth-scheme \"<scheme 或空>\" [dynamic 时传 --secret-env \"<已确认的变量名列表>\"]")
```

禁止用 Agent 文件工具写、读或搜索 `.env`。需要认证时由用户在本地填写凭据并只回复“已配置”；Agent 等确认后运行测试验证，不回显凭据。追加已有项目会更新用户已确认的非敏感配置并补当前模式需要的凭据槽，已有凭据只会标记 `PRESERVED`。

先按前置阶段已实际验证的 `ALLURE` 分支处理。物化器会独立实际复核 `allure --version`；若报告分支不一致，必须返回 `ENV_LOCK` 重新锁定，不能把它当作普通重试或静默切换：

- `ALLURE=有`：不执行报告模板物化，不读取、不复制、不验证 `utils/report_generator.py`；已有项目如原本存在该文件则保留不动
- `ALLURE=无`：不读取模板正文，执行：

```text
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> \"<SKILL_DIR>/scripts/materialize_templates.py\" --project \"<PROJECT_DIR>\" --component report --project-kind <PROJECT_KIND> --report fallback")
```

物化结果为 `PASS` 时再执行 `<PYTHON_CMD> -m py_compile utils/report_generator.py && <PYTHON_CMD> utils/report_generator.py --help`。结果为 `REVIEW` 时说明现有生成器并非当前 Skill 模板：保留原文件，不运行、不修改，登记“等待用户”并询问用户如何处理；用户明确移走、删除或允许替换前不得继续 fallback 分支。结果为 `FAIL` 或验证失败时最多重试 2 次；连续 3 次失败停止并如实报告，禁止用简化版或宿主通用报告器替代。

随后、在任何依赖安装或测试命令之前，按已锁定的 `OS_TYPE`、`PYTHON` 和 `ALLURE` 预置当前 OS 唯一脚本；`<REPORT_MODE>` 为 `official` 或 `fallback`：

```text
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> \"<SKILL_DIR>/scripts/materialize_templates.py\" --project \"<PROJECT_DIR>\" --component runner --project-kind <PROJECT_KIND> --os <OS_TYPE> --python-command \"<PYTHON>\" --report <REPORT_MODE>")
```

- `PASS`：脚本已创建或与当前模板一致
- `REVIEW`：读取 `reference/run-scripts.md` 和当前 OS 的既有脚本，只做必要冲突判断或最小修正，禁止覆盖定制内容
- `FAIL`：按错误修复后最多重试 2 次；连续 3 次失败停止
- runner 物化命令不可用或被拒绝：读取 `reference/run-scripts.md`，按其中“命令能力受阻时预置脚本”只用文件能力落盘；脚本存在并回读核对后，权限、语法和实跑留到步骤⑦

即使本步骤前面的核心或报告工具命令因权限阻塞，只要文件读写能力仍可用，也必须先预置当前 OS 脚本再向用户交接。新项目禁止同时生成两份脚本；追加已有项目不删除用户原有的另一平台脚本。

**pytest.ini 额外注册 marker**（在现有 markers 中追加）：
```ini
markers =
    need_auth: 需要认证的测试
    smoke: 冒烟测试（核心路径）
    regression: 回归测试（全量覆盖）
    api_endpoint(method, path): 标记测试实际归属的接口方法和路径
```

**文件创建失败处理**：最多重试 2 次，连续 3 次失败则停止并告知用户。

---

## ② 安装依赖

```
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> -m pip install -r requirements.txt")
```

安装失败处理：最多重试 2 次，连续 3 次失败则停止并告知用户。

---

## ③ 调每个接口并记录真实返回

- **接口无需认证** → 用宿主 HTTP 能力按文档调用接口；宿主不能访问已确认的本地/内网地址时改用项目内统一请求封装
- **静态认证**（`bearer` / `header` / `query` / `cookie` / `basic`）→ 先用 `curl` 对每个接口做一次无凭据探测并记录认证失败响应；用户确认本地 `.env` 已配置后，**在步骤④写用例前**对每个接口运行：

```text
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> -m utils.contract_probe --method <METHOD> --path \"<已把路径参数替换为非敏感代表值的具体路径>\" [--params-file \"<PROJECT_DIR>/.probe/<非敏感参数文件>.json\"] [--json-body-file \"<PROJECT_DIR>/.probe/<非敏感请求体文件>.json\"]")
```

查询参数或 JSON 请求体存在时，用文件能力写入项目内临时 `.probe/*.json`，通过文件参数传递并在探测完成后删除临时文件；不依赖 POSIX/Windows 的 JSON 引号规则。参数和文件不得含 Token、Cookie、密码或 API Key。契约要求 form、multipart 或额外非敏感 header 时，改写一个最小项目内用例通过统一请求封装探测，不扩展探测器猜测协议。只将 `PROBE: PASS` 的状态码和脱敏字段结构写入 MEMORY。
- **动态 OAuth/登录** → 不猜测登录/刷新接口。先按已确认契约实现项目专用 fixture；步骤④先写并运行一个最小真实认证用例，记录状态码和脱敏结构后才扩展其他用例
- **禁止**把 Token、API Key、密码或 Cookie 放进 curl 参数、命令、日志或 MEMORY；禁止猜测登录地址、OAuth 流程或 Bearer 方案

按上述认证分支逐个取得真实响应，记录状态码、脱敏字段结构并比对文档差异；不得用无凭据探测的 401/403 代替认证后的接口结果。HEAD/OPTIONS 与其他方法一样按契约探测。

遇到 POST/PUT/PATCH/DELETE 或并发、支付、权限变更场景时，先确认目标环境允许测试并在 MEMORY 记录非敏感的授权结论与清理策略；未确认就停下，不发送有副作用的请求。准备数据和清理请求可与主验证接口不同，`api_endpoint` 只标主验证接口。

`--path` 只写 `/` 开头的具体相对路径，必须先把 `{id}` 等路径参数替换成非敏感代表值，不能包含查询串；查询参数统一使用 `--params-file`。动态登录/OAuth 只按确认契约编写项目专用 fixture。探测器会拒绝越界文件、凭据字段、已配置凭据值和未替换路径占位符，stdout 只给出脱敏状态和结构。

---

## ④ 写测试用例

### 用例数量目标

**每接口必须有 3-5 个 pytest 实际展开后的 node，总数必须等于各接口 node 数之和。**

### 覆盖维度（快速流程只覆盖 3 个维度）

| 维度 | 说明 | 示例 |
|------|------|------|
| **正向功能** | 正常请求，验证核心返回 | 按契约精确校验状态与核心字段 |
| **认证权限** | 仅认证 API：无 token / 错 token / 过期 token | 按契约精确断言 |
| **核心异常** | 缺必填参数 / 无效参数 | 按契约精确校验异常响应 |

API 明确无需认证时，不生成虚构的认证测试；把该维度替换为核心数据完整性或业务规则验证。

### 代码 3 要素（必须遵守）

```python
@pytest.mark.api_endpoint(method="<METHOD>", path="<CONTRACT_PATH>")
@allure.title("接口功能 - 具体验证点")   # ① 中文标题
def test_xxx(self):
    """描述测什么、为什么。"""             # ② docstring
    resp = allure_request(..., expected="具体预期")  # ③ 预期结果
```

每个 `test_` 函数必须有一个 `@pytest.mark.api_endpoint(method="<METHOD>", path="<CONTRACT_PATH>")` 标记，并至少调用一次 `auth_session` 或 `allure_request`。参数化实例按该标记归属的接口计数；最终审计会反算 node 数，空壳测试和把同一接口虚报给其他接口都会失败。

保留老版已验证的三种结构模式，但所有业务值都必须由模型按契约填写：认证成功使用 `auth_session`；未认证拒绝使用 `allure_request` + `base_url`，不得借用带凭据 session；非法输入使用 `pytest.mark.parametrize`，每组数据都写清契约依据。接口无需认证时不生成未认证拒绝模式。

### 断言写法

真实探测（无认证接口用 `curl`，静态认证接口用项目内安全探测器）用于发现文档与实际返回的差异；断言以用户确认后的契约为准。只有契约明确允许多个状态码、字段类型或业务码时才能写多值断言，禁止为了通过测试而放宽。

### 用例骨架（占位符不得原样交付）

下面只约束代码结构，不提供任何可照抄的接口路径、字段名、参数名或状态码。生成测试时必须逐项替换为已确认契约中的真实值；任何占位符仍留在测试代码中都视为未完成。

```text
@pytest.mark.smoke
class TestContractEndpoint:
    """<按实际业务命名>"""

    @pytest.mark.api_endpoint(method="<METHOD>", path="<CONTRACT_PATH>")
    @allure.title("<按契约填写中文标题>")
    def test_success(self, auth_session):
        """<说明按契约验证的正向行为及原因。>"""
        resp = auth_session.<method>(
            "<contract_path>",
            expected="<按契约填写中文预期>",
        )
        assert resp.status_code == <contract_status>
        assert <contract_response_assertion>

    @pytest.mark.api_endpoint(method="<METHOD>", path="<CONTRACT_PATH>")
    @allure.title("<按契约填写中文异常场景标题>")
    def test_contract_error(self, auth_session):
        """<说明契约明确规定的异常行为及原因。>"""
        resp = auth_session.<method>(
            "<contract_path>",
            <contract_invalid_input>,
            expected="<按契约填写中文异常预期>",
        )
        assert resp.status_code == <contract_error_status>
```

写完执行 `shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> -m pytest tests/ --collect-only -q")`。建立“方法 + 路径 + 展开后 node 数”表；逐接口必须为 3-5，表内合计必须等于 pytest collected 总数。不一致先修正映射或补减用例，不能按函数定义数估算。命令能力不可用或被拒绝时不重试、不估算；保留步骤①预置脚本，保持④-⑧未完成，按步骤⑦的权限阻塞格式交给用户执行。

---

## ⑤ 跑 pytest + 修断言

```
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> -m pytest tests/ -v --tb=short --alluredir=allure-results --clean-alluredir")
```

命令能力不可用或被拒绝时，不重试、不把它当成测试失败，也不生成虚假报告；保留步骤①已预置的脚本，保持⑤-⑧为 `⬜`，按步骤⑦的权限阻塞格式把脚本交给用户执行。

**修复规则**：
- 断言不匹配确认后的契约 → 改断言；不得仅为通过而迎合错误返回
- 实际行为与确认后的契约不一致且有复现证据 → 不改断言，记录到差异列表
- 改完重跑 pytest，直到结果稳定
- **最多 3 轮**，3 轮后仍有失败则按证据分类记录，不能仅凭重试次数判定为 API bug；然后继续下一步

**全部通过** → 直接进入步骤⑥。

---

## ⑥ 生成报告

⚠️ **禁止用 `allure serve` 或 `allure open`。**

生成前先执行路径无关的报告产物扫描；`<REPORT_MODE>` 按已锁定的 `ALLURE` 替换为 `official` 或 `fallback`：

```text
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> \"<SKILL_DIR>/scripts/validate_delivery.py\" --project \"<PROJECT_DIR>\" --report <REPORT_MODE> --report-artifacts-only")
```

- `REPORT ARTIFACT AUDIT: PASS`：继续当前分支
- `REPORT ARTIFACT AUDIT: BLOCKED`：保持列出的既有报告不动；若原因是报告分支与实际 Allure 检测不一致，返回 `ENV_LOCK` 重新锁定。其他冲突登记“等待用户”并询问如何处理；用户明确处理前禁止生成新报告、禁止结束交付

**如果有 allure（ALLURE=有）**：
```
shell_exec(command="<ENTER_PROJECT> allure generate allure-results -o allure-report --clean")
```
只保留入口 `allure-report/index.html`。

**如果没有 allure（ALLURE=无）**：只运行步骤①由本 Skill 模板物化并验收过的 `utils/report_generator.py`，禁止用宿主通用报告构建能力代替：
```
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> utils/report_generator.py --input allure-results --output allure-report/report.html --clean")
```
只保留入口 `allure-report/report.html`。两条分支互斥，禁止同时生成两个入口；无论哪一分支都禁止调用宿主通用报告器另建单文件报告。

报告扫描或生成命令能力不可用/被拒绝时，不伪造报告；保留已预置脚本，保持⑥-⑧为 `⬜`，按步骤⑦的权限阻塞格式交给用户执行。

生成后立即检查：ALLURE=有时 `index.html` 必须存在且非空、`report.html` 必须不存在；ALLURE=无时反之。用 `scripts/validate_delivery.py` 的最终审计做完整复核；此处检查失败则按当前分支重新生成并再检查一次，仍失败即停止，禁止声称报告成功。

ALLURE=有：
```text
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> -c \"from pathlib import Path; import sys; p=Path('allure-report/index.html'); q=Path('allure-report/report.html'); sys.exit(0 if p.is_file() and p.stat().st_size > 0 and not q.exists() else 1)\"")
```

ALLURE=无：
```text
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> -c \"from pathlib import Path; import sys; p=Path('allure-report/report.html'); q=Path('allure-report/index.html'); sys.exit(0 if p.is_file() and p.stat().st_size > 0 and not q.exists() else 1)\"")
```

所选报告入口检查通过后，只能把任务清单第⑥项标为 `✅`，随后立即进入⑦；此处禁止把整个任务标记为完成或输出结束语。

---

## ⑦ 交付前复核并实跑运行脚本

脚本已在步骤①预置。交付前再次调用物化脚本做确定性比对；它不会覆盖内容不同的已有脚本，并会独立实际复核 `allure --version`。若报告分支不一致，返回 `ENV_LOCK` 重新锁定，禁止把失败当作普通重试。`<REPORT_MODE>` 在 `ALLURE=有` 时替换为 `official`，否则替换为 `fallback`：

```text
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> \"<SKILL_DIR>/scripts/materialize_templates.py\" --project \"<PROJECT_DIR>\" --component runner --project-kind <PROJECT_KIND> --os <OS_TYPE> --python-command \"<PYTHON>\" --report <REPORT_MODE>")
```

- `PASS` → 脚本已创建或与当前模板一致
- `REVIEW` → 仅已有项目允许；此时才读取 `reference/run-scripts.md` 和当前 OS 的既有脚本，确认满足契约或最小修正冲突行
- `FAIL` → 按错误修复后最多重试 2 次，连续 3 次失败停止
- 物化命令不可用或被拒绝 → 保留步骤①已预置的脚本，按需读取 `reference/run-scripts.md` 后用文件能力回读核对；脚本意外缺失时立即按其中的降级路径补回
- 物化脚本只选择当前 OS 资产，并自动为 `run.sh` 设置执行权限；Windows 模板与替换值均强制为 ASCII
- **新项目只生成上述对应脚本，禁止同时生成两份**；追加已有项目时不要删除用户原有的另一平台脚本

物化后必须检查当前脚本：Darwin/Linux 要求存在、可执行，且 `bash -n run.sh` 与 `sh -n run.sh` 都通过；Windows 要求 `run.bat` 存在、非空并可按 ASCII 解码。失败时返回物化或最小修正步骤，不能只凭文件存在标记完成。

权限与语法检查通过后，必须实际执行当前 OS 脚本一次，不向用户转交此步：

- Darwin/Linux：`shell_exec(command="<ENTER_PROJECT> ./run.sh")`
- Windows：`shell_exec(command="<ENTER_PROJECT> call run.bat")`

脚本只重新执行 pytest 和已锁定报告分支；依赖安装仍由步骤②的独立流程负责。它必须产出最新的 `allure-results` 与唯一报告入口。之前全部通过时，此次脚本也必须返回 0；如有已确认并记录的 API 契约缺陷，允许 pytest 返回非 0，但脚本必须完成报告生成，且结果须与 MEMORY 记录一致。其他脚本错误按原因最小修复后最多重试 2 次。

如执行测试或脚本的命令能力不可用或被拒绝，必须保留已经预置的脚本，保持尚未执行及其后清单项为 `⬜`，登记“等待用户”，并给出项目内手动命令：Darwin/Linux 为 `cd "<PROJECT_DIR>" && chmod +x run.sh && ./run.sh`，Windows 为 `cd /d "<PROJECT_DIR>" && call run.bat`。这表示脚本已交付但测试、报告、实跑与最终审计中的未执行部分仍待完成；禁止说“用户没有要求脚本”，也禁止输出完成结束语。

权限阻塞时的回复必须同时列出“运行脚本：<绝对路径>（已交付）”“执行状态：待用户执行”，并请用户执行后回复结果；不得写“运行脚本实跑：PASS”或“交付审计：DELIVERY AUDIT: PASS”。

只有脚本检查和实际执行均完成后，才能把任务清单第⑦项标为 `✅`，随后立即进入⑧；此处仍禁止把整个任务标记为完成或输出结束语。

---

## ⑧ 统一更新 `<PROJECT_DIR>/MEMORY.md`

以步骤⑦脚本实跑后最新的 `allure-results` 为准，将以下信息**追加写入** `<PROJECT_DIR>/MEMORY.md`（不要覆盖 stage-quick-setup 已写入的内容）：

1. `## 差异表`（阶段 ③ 真实探测接口发现的文档与实际差异；没有则写“无差异”）
2. `## 用例计数`（每个文件的用例数量 + 总数；接口表固定前三列为“方法 | 路径 | 展开后 node 数”）
3. `## 结果统计`（用 `| 通过 | N |`、`| 失败 | N |`、`| 跳过 | N |` 三行记录；失败数包含 Allure 的 failed + broken）
4. `## 修复记录`（修了什么、API bug 列表；没有则写“无修复”）
5. 在 `## 阶段记录` 追加 `### 快速阶段二 - YYYY-MM-DD`，非空记录“完成、发现、决策”

用例数还必须包含步骤④的“方法 + 路径 + 展开后 node 数”表及 pytest collected 总数。

写入后执行最终交付审计：

```text
shell_exec(command="<ENTER_PROJECT> <PYTHON_CMD> \"<SKILL_DIR>/scripts/validate_delivery.py\" --project \"<PROJECT_DIR>\" --mode quick --os <OS_TYPE> --report <official|fallback> --project-kind <PROJECT_KIND>")
```

`ALLURE=有` 时 `--report official`，否则 `--report fallback`。审计脚本不读取 `.env`；它交叉验证用例归属、断言与真实请求证据、Allure 结果身份、MEMORY、报告唯一性、核心框架及当前 OS 脚本。业务对错仍由模型按契约判断。只有最后一次审计实际输出 `DELIVERY AUDIT: PASS`，才能把第⑧项和整个任务标为完成；失败后按不同错误逐项修复并重跑，最多 3 轮，连续相同错误不得重复同一操作，仍失败则如实报告阻塞。

最终回复前必须展示 8 项全为 `✅` 的任务清单，并列出所选报告入口、当前 OS 运行脚本、`<PROJECT_DIR>/MEMORY.md` 的绝对路径和 `DELIVERY AUDIT: PASS`。在这些证据齐全前，禁止通过任何任务管理能力把整个任务标记为完成，禁止输出结束语。

最终回复必须使用下面的交付结构，不得只说“测试通过”或只列测试代码和报告：

```text
快速流程步骤清单：8 项全部 ✅
测试结果：通过 N，失败 N，跳过 N
项目目录：<PROJECT_DIR 绝对路径>
测试代码：<tests/ 下实际文件>
测试报告：<唯一报告入口绝对路径>
原始结果：<PROJECT_DIR>/allure-results/
运行脚本：<当前 OS 对应脚本绝对路径>
运行脚本实跑：PASS（已重新生成最新测试结果和唯一报告）
项目记录：<PROJECT_DIR>/MEMORY.md
交付审计：DELIVERY AUDIT: PASS
测试完成，报告已生成；交付物已准备完毕。
```

---

## 产出

📝 `<PROJECT_DIR>/MEMORY.md`：差异表 + 用例数 + 结果统计 + 修复记录。**必须在步骤⑧统一写入并验收。**

## 保存边界

只写并验收 `<PROJECT_DIR>/MEMORY.md`。不得把本流程的项目配置、阶段产出或交付状态额外写入 Agent 数据库、project-memory 或会话工作区。
