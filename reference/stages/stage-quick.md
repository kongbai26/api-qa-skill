# 快速路径：阶段 3-5 合并

> **⛔ 本阶段需要额外读取：reference/implementation.md + reference/run-scripts.md +（_templates/report_generator.py 仅 ALLURE=无 时）**
>
> ⚠️ 仅用于接口数 ≤ 5 的简单任务。复杂逻辑（支付/权限/工作流）必须走完整 5 阶段。

## 目标

合并原阶段 3-5，一口气完成：搭框架 → 调接口 → 写用例 → 跑测试 → 出报告 → 生成脚本 → 更新 MEMORY。

## 步骤清单

```
⬜ 1. 搭框架（conftest.py + request_helper.py + 基础配置 + tests/ 目录）
⬜ 2. 安装依赖
⬜ 3. curl 调每个接口，记录实际返回
⬜ 4. 写测试用例（保存至 tests/ 目录，每接口 3-5 条核心用例，总数 ≥ 接口数 × 3）
⬜ 5. 跑 pytest + 修断言（循环直到通过，最多 3 轮）
⬜ 6. 生成报告（静态 Allure / HTML 报告，严禁 Markdown 代替）
⬜ 7. 生成运行脚本（run.sh / run.bat）
⬜ 8. 统一更新 MEMORY.md
```

**执行规则**：无门控，连续执行。每完成一项立即将 `⬜` 改为 `✅`。

---

## ① 搭框架

在 `<PROJECT_DIR>` 目录下用 `save_file` 创建以下文件（完整代码见 `reference/implementation.md`，用 `read_file` 读取后照抄）：
- `<PROJECT_DIR>/conftest.py` — 核心 fixture 与 Allure 挂钩（完整代码见 reference/implementation.md）
- `<PROJECT_DIR>/utils/request_helper.py` — allure_request 与 AuthSession 实现（完整代码见 reference/implementation.md）
- `<PROJECT_DIR>/utils/__init__.py`（空文件）
- `<PROJECT_DIR>/tests/__init__.py`（空文件，用于初始化 `tests/` 用例目录，测试用例必须放入 `tests/`）
- `<PROJECT_DIR>/pytest.ini` — 必须包含 `addopts = -v --tb=short --alluredir=allure-results`
- `<PROJECT_DIR>/requirements.txt` — 必须包含 pytest、allure-pytest、requests、python-dotenv
- `<PROJECT_DIR>/.env`（填入 API 基地址和 token）
- `<PROJECT_DIR>/.gitignore`

**⚠️ 严禁直接使用 requests 裸写测试**：必须遵循 pytest + Allure 架构规范，所有网络调用封装在 `allure_request` / `AuthSession` 中。

**复制报告生成工具（仅当 ALLURE=无 时）**：
- 如果 `ALLURE=无`：用 `read_file` 读取 `<skill_dir>/_templates/report_generator.py`，保存为 `<PROJECT_DIR>/utils/report_generator.py`
- 如果 `ALLURE=有`：跳过

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
shell_exec(command="cd \"<PROJECT_DIR>\" && <PYTHON> -m pip install -r requirements.txt")
```

安装失败处理：最多重试 2 次，连续 3 次失败则停止并告知用户。

---

## ③ curl 调每个接口

- **如果 API_TOKEN 已配置** → 直接调用接口
- **如果 API_TOKEN 未配置** → 需要调用登录接口获取 token

用 `curl` 命令调每个接口，记录实际返回，比对文档差异。

如果 API 需要登录获取 token：
```
shell_exec(command="curl -s -X POST '<登录接口URL>' -H 'Content-Type: application/json' -d '{\"username\":\"xxx\",\"password\":\"xxx\"}'")
```
从返回中提取 token，写入 .env 文件。

---

## ④ 写测试用例

### 文件命名与存放路径（强制红线）

- **保存路径**：用 `save_file` 保存为 `<PROJECT_DIR>/tests/test_<模块名>.py`（例如：`<PROJECT_DIR>/tests/test_posts.py`）
- **⚠️ 严禁直接保存在根目录（如 `<PROJECT_DIR>/test_posts.py`）**，所有测试用例必须位于 `<PROJECT_DIR>/tests/` 目录！
- **⚠️ 严禁使用原生 requests 裸调接口**，所有请求必须通过 `auth_session` 或 `allure_request` 发起！
- **⚠️ 每条用例必须包含 `@allure.title("...")`** 与 `expected="..."` 参数！

### 用例数量目标

**每接口 3-5 条核心用例，总数 ≥ 接口数 × 3。**

### 覆盖维度（快速流程只覆盖 3 个维度）

| 维度 | 说明 | 示例 |
|------|------|------|
| **正向功能** | 正常请求，验证核心返回 | GET 返回 200 + data 字段 |
| **认证权限** | 无 token / 错 token / 过期 token | 401 返回 |
| **核心异常** | 缺必填参数 / 无效参数 | 400/422 返回 |

### 代码 3 要素（必须遵守）

```python
@allure.title("接口功能 - 具体验证点")   # ① 中文标题
def test_xxx(self):
    """描述测什么、为什么。"""             # ② docstring
    resp = allure_request(..., expected="具体预期")  # ③ 预期结果
```

### 断言防御写法

| 场景 | 错误写法 | 正确写法 |
|------|---------|---------|
| 校验错误码 | `== 422` | `in (400, 422)` |
| 字段类型 | `isinstance(x, str)` | `isinstance(x, (str, int, float))` |
| 业务错误码 | `== "XXX"` | `in {"XXX", "YYY"}` |

### 用例示例

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
        assert resp.status_code in (401, 403)

    @allure.title("获取用户列表 - 无效参数")
    @pytest.mark.parametrize("page", [-1, 0, "abc"])
    def test_get_users_invalid_param(self, auth_session, page):
        """验证无效分页参数返回 400 或 422"""
        resp = auth_session.get("/users", params={"page": page},
                                expected="返回400或422")
        assert resp.status_code in (400, 422)
```

---

## ⑤ 跑 pytest + 修断言

```
shell_exec(command="cd \"<PROJECT_DIR>\" && <PYTHON> -m pytest tests/ -v --tb=short --alluredir=allure-results")
```

⚠️ 必须针对 `tests/` 目录执行，且必须附带 `--alluredir=allure-results` 参数以生成 Allure 结果数据！

**修复规则**：
- 断言不匹配真实返回 → 改断言
- API 真有 bug → 不改代码，记录到差异列表
- 改完重跑 pytest，直到结果稳定
- **最多 3 轮**，3 轮后仍有失败则记录为 API bug，继续下一步

**全部通过** → 直接进入步骤⑥。

---

## ⑥ 生成报告

⚠️ **红线警示**：
1. **禁止用 `allure serve` 或 `allure open`。**
2. **必须生成正式 HTML 测试报告，严禁自制 `TEST_REPORT.md` 等 Markdown 文件代替报告！** 只要未生成标准 HTML 报告，即视为任务未完成。

**报告生成方式**：

**如果有 allure（ALLURE=有）**：
1. 生成官方多文件静态报告：
```
shell_exec(command="cd \"<PROJECT_DIR>\" && allure generate allure-results -o allure-report --clean")
```
2. 若系统具备 `report_build` 工具，立即调用以同步生成单文件交互大盘：
```
report_build(allure_results_dir="<PROJECT_DIR>/allure-results", output_path="<PROJECT_DIR>/allure-report/report.html", session_goal="API测试报告")
```

**如果没有 allure（ALLURE=无）**：
若系统具备 `report_build` 工具，优先调用：
```
report_build(allure_results_dir="<PROJECT_DIR>/allure-results", output_path="<PROJECT_DIR>/allure-report/report.html", session_goal="API测试报告")
```
若无该工具，执行 Python 报告生成器脚本：
```
shell_exec(command="cd \"<PROJECT_DIR>\" && <PYTHON> utils/report_generator.py --input allure-results --output allure-report/report.html")
```

**验证报告文件已生成**：
```
shell_exec(command="cd \"<PROJECT_DIR>\" && <PYTHON> -c \"import os; ok=os.path.exists('allure-report/index.html') or os.path.exists('allure-report/report.html'); print('REPORT_OK' if ok else 'REPORT_FAIL')\"")
```

---

## ⑦ 生成运行脚本

**先检查脚本是否存在**：
```
shell_exec(command="cd \"<PROJECT_DIR>\" && <PYTHON> -c \"import os; print('FOUND' if os.path.exists('run.sh') or os.path.exists('run.bat') else 'MISSING')\"")
```

- **已存在** → 跳过
- **不存在** → 用 `read_file` 读取 `<skill_dir>/reference/run-scripts.md` 获取脚本模板，用 `save_file` 保存：
  - OS_TYPE 是 Darwin 或 Linux → 保存为 `<PROJECT_DIR>/run.sh`，并执行 `chmod +x "<PROJECT_DIR>/run.sh"`
  - OS_TYPE 是 Windows → 保存为 `<PROJECT_DIR>/run.bat`
  - ⚠️ 脚本文件名必须且只能是 `run.sh` 或 `run.bat`，严禁命名为 `run_tests.sh`！

---

## ⑧ 统一更新 MEMORY.md

将以下信息**追加写入** MEMORY.md（不要覆盖 stage-quick-setup 已写入的内容）：

1. **差异表**（阶段 ③ curl 调接口发现的文档与实际差异）
2. **用例数**（每个文件的用例数量 + 总数）
3. **结果统计**（通过/失败/跳过数量）
4. **修复记录**（修了什么、API bug 列表）

---

## 产出

📝 MEMORY.md：差异表 + 用例数 + 结果统计 + 修复记录。保存追加到 `<PROJECT_DIR>/MEMORY.md`。

