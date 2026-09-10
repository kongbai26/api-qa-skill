# 快速路径：阶段 3-5 合并

> **⛔ 本阶段需要额外读取：reference/implementation.md + reference/run-scripts.md + _templates/report_generator.py。结束时执行 scripts/validate_delivery.py。**
>
> ⚠️ 仅用于接口数 ≤ 5 的简单任务。复杂逻辑（支付/权限/工作流）必须走完整 5 阶段。
>
> **MEMORY 文件边界**：本阶段所有 `MEMORY.md` 均指 `<PROJECT_DIR>/MEMORY.md`，必须用文件写入工具追加，供用户查看；Agent 工作区记忆、数据库或 `memory_save` 不能替代该文件。

## 目标

合并原阶段 3-5，一口气完成：搭框架 → 调接口 → 写用例 → 跑测试 → 出报告 → 生成脚本 → 更新 MEMORY。

## 步骤清单

```
⬜ 1. 搭框架（conftest.py + request_helper.py + 基础配置）
⬜ 2. 安装依赖
⬜ 3. curl 调每个接口，记录实际返回
⬜ 4. 写测试用例（每接口 3-5 条核心用例，总数 ≥ 接口数 × 3）
⬜ 5. 跑 pytest + 修断言（循环直到通过，最多 3 轮）
⬜ 6. 生成报告
⬜ 7. 生成与 OS_TYPE 对应的一个运行脚本
⬜ 8. 统一更新并验收 `<PROJECT_DIR>/MEMORY.md`
```

**执行规则**：不新增计划确认门控，连续执行；只有认证 API 需要用户在本地填写凭据时，允许在步骤①等待“已配置”。每完成一项立即将 `⬜` 改为 `✅`。

---

## ① 搭框架

用 `save_file` 创建以下文件（**完整代码见 reference/implementation.md**，用 read_file 读取后照抄）：
- `.gitignore`（必须先创建/修复并排除 `.env`）
- `conftest.py`
- `utils/request_helper.py`
- `utils/report_generator.py`（完整复制 `_templates/report_generator.py`，作为无 Allure CLI 时的回退）
- `utils/__init__.py`（空文件）
- `pytest.ini`
- `requirements.txt`

先创建/修复 `.gitignore`，确保包含独立一行 `.env`；再用 `configure_env` 写入已确认的 `API_BASE_URL`、`API_AUTH_MODE`、`API_AUTH_NAME`、`API_AUTH_SCHEME` 等非敏感值和空凭据槽。新项目调用格式与 `reference/implementation.md` 的 `.env` 结构一致，且 `replace_existing=false`。禁止用 `save_file`/`edit_file` 写 `.env`，禁止读取或搜索其内容。需要认证时由用户在本地填写凭据并只回复“已配置”；Agent 等确认后运行测试验证，不回显凭据。追加已有项目只补缺失变量；确需覆盖时单独传非敏感键，绝不读取或覆盖凭据键。

新项目或模板缺失时，`utils/report_generator.py` 必须按以下原流程完整复制；已有文件先验证，验证通过则保留，不能自行缩写：

1. 用 `read_file(path="<skill_dir>/_templates/report_generator.py")` 分页读完；`has_more=true` 时按 `continuation.next_offset` 续读
2. 保存到 `<PROJECT_DIR>/utils/report_generator.py`；已有定制文件只修复与单报告规则冲突的部分，不整文件覆盖
3. 执行 `shell_exec(command="<ENTER_PROJECT> <PYTHON> -m py_compile utils/report_generator.py && <PYTHON> utils/report_generator.py --help")`
4. 缺失或验证失败时重新读取并保存，最多重试 2 次；连续 3 次失败则停止并告知用户，禁止用简化版替代

**pytest.ini 额外注册 marker**（在现有 markers 中追加）：
```ini
markers =
    need_auth: 需要认证的测试
    smoke: 冒烟测试（核心路径）
    regression: 回归测试（全量覆盖）
```

**文件创建失败处理**：最多重试 2 次，连续 3 次失败则停止并告知用户。

---

## ② 安装依赖

```
shell_exec(command="<ENTER_PROJECT> <PYTHON> -m pip install -r requirements.txt")
```

安装失败处理：最多重试 2 次，连续 3 次失败则停止并告知用户。

---

## ③ curl 调每个接口

- **接口无需认证** → 用 `curl` 工具按文档调用接口
- **接口需要认证** → `curl` 对每个接口做一次不带凭据的探测并记录认证失败响应；用户在本地 `.env` 配置后，带认证行为由步骤⑤的 `AuthSession` 测试验证
- **禁止**把 Token、API Key、密码或 Cookie 放进 curl 参数、命令、日志或 MEMORY；禁止猜测登录地址、OAuth 流程或 Bearer 方案

用 `curl` 工具调每个接口，记录实际返回，比对文档差异。

动态登录/OAuth 只按文档或用户确认的契约编写项目专用 fixture，由运行时读取本地凭据；Agent 不调用带真实用户名/密码的登录请求，也不读取 token 响应原文。只记录脱敏后的状态、字段结构和契约差异。

---

## ④ 写测试用例

### 用例数量目标

**每接口必须有 3-5 个 pytest 实际展开后的 node，总数必须等于各接口 node 数之和。**

### 覆盖维度（快速流程只覆盖 3 个维度）

| 维度 | 说明 | 示例 |
|------|------|------|
| **正向功能** | 正常请求，验证核心返回 | GET 返回 200 + data 字段 |
| **认证权限** | 仅认证 API：无 token / 错 token / 过期 token | 按契约精确断言 |
| **核心异常** | 缺必填参数 / 无效参数 | 400/422 返回 |

API 明确无需认证时，不生成虚构的认证测试；把该维度替换为核心数据完整性或业务规则验证。

### 代码 3 要素（必须遵守）

```python
@allure.title("接口功能 - 具体验证点")   # ① 中文标题
def test_xxx(self):
    """描述测什么、为什么。"""             # ② docstring
    resp = allure_request(..., expected="具体预期")  # ③ 预期结果
```

### 断言写法

curl 探测用于发现文档与实际返回的差异；断言以用户确认后的契约为准。只有契约明确允许多个状态码、字段类型或业务码时才能写多值断言，禁止为了通过测试而放宽。

### 用例示例

以下只示范**契约已经明确规定**“无认证返回 401、无效 page 返回 422”的情况。实际项目必须换成确认后的精确状态码；契约未规定多个结果时禁止集合断言。

```python
@pytest.mark.smoke
class TestUsers:
    """用户接口 - 核心用例"""

    @allure.title("获取用户列表 - 正常返回")
    def test_get_users_success(self, auth_session):
        """验证获取用户列表成功，返回 200 且包含 data 字段"""
        resp = auth_session.get("/users", expected="返回200且包含data字段")
        assert resp.status_code == 200
        assert "data" in resp.json()

    @allure.title("获取用户列表 - 无认证拒绝")
    def test_get_users_no_auth(self, base_url):
        """验证未携带 token 时返回 401"""
        resp = allure_request("GET", f"{base_url}/users", expected="返回401")
        assert resp.status_code == 401

    @allure.title("获取用户列表 - 无效参数")
    @pytest.mark.parametrize("page", [-1, 0, "abc"])
    def test_get_users_invalid_param(self, auth_session, page):
        """验证无效分页参数按契约返回 422"""
        resp = auth_session.get("/users", params={"page": page},
                                expected="返回422")
        assert resp.status_code == 422
```

写完执行 `shell_exec(command="<ENTER_PROJECT> <PYTHON> -m pytest tests/ --collect-only -q")`。建立“方法 + 路径 + 展开后 node 数”表；逐接口必须为 3-5，表内合计必须等于 pytest collected 总数。不一致先修正映射或补减用例，不能按函数定义数估算。

---

## ⑤ 跑 pytest + 修断言

```
shell_exec(command="<ENTER_PROJECT> <PYTHON> -m pytest tests/ -v --tb=short --alluredir=allure-results --clean-alluredir")
```

**修复规则**：
- 断言不匹配确认后的契约 → 改断言；不得仅为通过而迎合错误返回
- 实际行为与确认后的契约不一致且有复现证据 → 不改断言，记录到差异列表
- 改完重跑 pytest，直到结果稳定
- **最多 3 轮**，3 轮后仍有失败则按证据分类记录，不能仅凭重试次数判定为 API bug；然后继续下一步

**全部通过** → 直接进入步骤⑥。

---

## ⑥ 生成报告

⚠️ **禁止用 `allure serve` 或 `allure open`。**

**如果有 allure（ALLURE=有）**：
```
shell_exec(command="<ENTER_PROJECT> allure generate allure-results -o allure-report --clean")
```
只保留入口 `allure-report/index.html`。

**如果没有 allure（ALLURE=无）**：
```
shell_exec(command="<ENTER_PROJECT> <PYTHON> utils/report_generator.py --input allure-results --output allure-report/report.html --clean")
```
只保留入口 `allure-report/report.html`。两条分支互斥，禁止同时生成两个入口。

生成后立即检查：ALLURE=有时 `index.html` 必须存在且非空、`report.html` 必须不存在；ALLURE=无时反之。用 `scripts/validate_delivery.py` 的最终审计做完整复核；此处检查失败则按当前分支重新生成并再检查一次，仍失败即停止，禁止声称报告成功。

ALLURE=有：
```text
shell_exec(command="<ENTER_PROJECT> <PYTHON> -c \"from pathlib import Path; import sys; p=Path('allure-report/index.html'); q=Path('allure-report/report.html'); sys.exit(0 if p.is_file() and p.stat().st_size > 0 and not q.exists() else 1)\"")
```

ALLURE=无：
```text
shell_exec(command="<ENTER_PROJECT> <PYTHON> -c \"from pathlib import Path; import sys; p=Path('allure-report/report.html'); q=Path('allure-report/index.html'); sys.exit(0 if p.is_file() and p.stat().st_size > 0 and not q.exists() else 1)\"")
```

---

## ⑦ 生成运行脚本

**只检查当前 OS 对应的脚本是否存在**：

OS_TYPE 是 Darwin 或 Linux：
```
shell_exec(command="<ENTER_PROJECT> test -x run.sh")
```

OS_TYPE 是 Windows：
```
shell_exec(command="<ENTER_PROJECT> if exist run.bat (echo run.bat exists) else (echo MISSING: run.bat & exit /b 1)")
```

- **已存在，且不含自动打开报告或双报告冲突** → 跳过；有冲突时只按模板修正冲突行
- **不存在** → 从 `reference/run-scripts.md` 获取内容，用 `save_file` 保存：
  - OS_TYPE 是 Darwin 或 Linux → 保存为 run.sh，`chmod +x`
  - OS_TYPE 是 Windows → 保存为 run.bat
- **新项目只生成上述对应脚本，禁止同时生成两份**；追加已有项目时不要删除用户原有的另一平台脚本

---

## ⑧ 统一更新 `<PROJECT_DIR>/MEMORY.md`

将以下信息**追加写入** `<PROJECT_DIR>/MEMORY.md`（不要覆盖 stage-quick-setup 已写入的内容）：

1. **差异表**（阶段 ③ curl 调接口发现的文档与实际差异）
2. **用例数**（每个文件的用例数量 + 总数）
3. **结果统计**（通过/失败/跳过数量）
4. **修复记录**（修了什么、API bug 列表）

用例数还必须包含步骤④的“方法 + 路径 + 展开后 node 数”表及 pytest collected 总数。

写入后执行最终交付审计：

```text
shell_exec(command="<ENTER_PROJECT> <PYTHON> \"<skill_dir>/scripts/validate_delivery.py\" --project \"<PROJECT_DIR>\" --mode quick --os <OS_TYPE> --report <official|fallback> --project-kind <PROJECT_KIND>")
```

`ALLURE=有` 时 `--report official`，否则 `--report fallback`。审计脚本只读取交付物和 `.env` 元数据，不读取 `.env` 内容。任一必需文件、测试结果、唯一报告入口、当前 OS 脚本、MEMORY 或 Python 语法校验失败，快速路径不得完成；修复对应项后只重跑一次审计，仍失败则如实告知用户。

---

## 产出

📝 `<PROJECT_DIR>/MEMORY.md`：差异表 + 用例数 + 结果统计 + 修复记录。**必须在步骤⑧统一写入并验收。**

## 双重保存

先写并验收 `<PROJECT_DIR>/MEMORY.md`；数据库可用时再额外写数据库。数据库或 Agent 记忆不可替代项目文件。
