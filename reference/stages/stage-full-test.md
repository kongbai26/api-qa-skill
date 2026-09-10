# 阶段四：跑测试 + 修到通过

> **⛔ 本阶段无额外 reference 文件需要读取。需要阶段一的产出（ALLURE=有/无）。**

> **MEMORY 文件边界**：本阶段所有 `MEMORY.md` 均指 `<PROJECT_DIR>/MEMORY.md`，必须用文件写入工具追加，供用户查看；Agent 工作区记忆、数据库或 `memory_save` 不能替代该文件。

## 目标

执行测试，修复失败用例，生成报告，直到全部通过或确认是 API bug。

## 步骤清单（执行时必须逐项打勾，跳过禁止）

```
⬜ 1. 跑 pytest（传 --alluredir=allure-results）
⬜ 2. 生成单一报告
⬜ 3. 分析失败原因（断言不匹配 vs API bug）
⬜ 4. 修复断言 / 记录 API bug
⬜ 5. 重跑 pytest + 重新生成报告（最多 5 轮）
⬜ 6. 更新 `<PROJECT_DIR>/MEMORY.md` 结果统计 + 修复记录
```

**执行规则**：每完成一项立即将 `⬜` 改为 `✅`。全部通过 → 生成报告后进入步骤⑥；5 轮后仍有失败 → 按证据记录为断言、代码、环境、接口差异或未决问题，进入步骤⑥。

---

## ① 跑 pytest

```
shell_exec(command="<ENTER_PROJECT> <PYTHON> -m pytest tests/ -v --tb=short --alluredir=allure-results --clean-alluredir")
```

⚠️ **关键**：pytest 必须传 `--alluredir=allure-results --clean-alluredir`，否则报告可能缺少结果或混入旧数据！

⚠️ **pytest 报错诊断与修复**：

| 错误信息 | 可能原因 | 自动修复方案 |
|---------|---------|-------------|
| `ModuleNotFoundError: No module named 'xxx'` | 依赖未安装 | 回到阶段二④重新安装依赖 |
| `No module named 'allure'` | allure-pytest 未安装 | `shell_exec(command="<ENTER_PROJECT> <PYTHON> -m pip install allure-pytest")` |
| `No module named 'pytest'` | pytest 未安装 | `shell_exec(command="<ENTER_PROJECT> <PYTHON> -m pip install pytest")` |
| `ImportError: cannot import name 'xxx' from 'utils'` | utils 目录缺少 `__init__.py` | 创建 `utils/__init__.py` 空文件 |
| 测试全部失败 (FAILED) | 环境配置错误或 API 不可用 | 不读取 `.env`；核对 MEMORY 的非敏感配置，请用户确认本地凭据已设置，再结合 curl 无认证探测与测试输出判断 |
| `Permission denied` | 文件权限不足 | Darwin/Linux 执行 `shell_exec(command="<ENTER_PROJECT> chmod +x run.sh")` |
| `pytest: command not found` | pytest 不在 PATH 中 | 使用 `<PYTHON> -m pytest` 而不是直接 `pytest` |

- 全部通过 → 告诉用户"全部通过"，继续步骤②生成报告
- 部分失败 → 告诉用户测试结果摘要（通过/失败/跳过数量 + 失败原因概要），继续步骤②

---

## ② 生成报告

⚠️ **禁止用 `allure serve` 或 `allure open`，禁止 `open` 任何文件。**

**根据阶段一检测的 ALLURE 变量决定报告方式**：

**如果有 allure（ALLURE=有）** → 只生成官方 Allure 报告，入口为 `allure-report/index.html`：
```
shell_exec(command="<ENTER_PROJECT> allure generate allure-results -o allure-report --clean")
```
`--clean` 参数会自动覆盖旧报告，无需手动删除。

**如果没有 allure（ALLURE=无）** → 只用已交付的内置生成器生成单页面报告，入口为 `allure-report/report.html`：
```
shell_exec(command="<ENTER_PROJECT> <PYTHON> utils/report_generator.py --input allure-results --output allure-report/report.html --clean")
```

两条分支互斥，只保留所选入口，禁止同时生成 `index.html` 和 `report.html`。

⚠️ 如果报告生成失败：
- `未找到 allure-results/*-result.json` → 步骤①的 `--alluredir` 参数没传，重新跑步骤①
- 其他错误 → 检查 allure-results 目录是否有内容

---

## ③ 分析失败原因

检查 pytest 输出，区分：
- **断言不匹配** → 断言与用户确认的契约不一致 → 进入步骤④改断言
- **API bug** → 实际行为与用户确认的契约不一致且有复现证据 → 进入步骤④记差异列表
- **代码错误** → import 失败、fixture 缺失等 → 进入步骤④修代码

---

## ④ 修复断言 / 记录 API bug

- 断言不匹配确认后的契约 → **改断言**，不改 API；不得仅为测试通过而迎合错误返回
- API 真有 bug → **不改代码**，记到差异列表
- 改完后进入步骤⑤重跑

⚠️ **阶段四优先只修改 `tests/`。只有 import、fixture 或请求封装本身确有代码错误时，才最小修改 `conftest.py`、`utils/request_helper.py` 或 `pytest.ini`；禁止修改 `utils/report_generator.py`，也禁止借修复之名放宽已确认契约。**

---

## ⑤ 重跑 pytest + 重新生成报告

```
shell_exec(command="<ENTER_PROJECT> <PYTHON> -m pytest tests/ -v --tb=short --alluredir=allure-results --clean-alluredir")
```

每轮 pytest 后立即按步骤②的同一 `ALLURE` 分支重新生成报告：ALLURE=有只运行 `allure generate ... --clean`，ALLURE=无只运行 `report_generator.py ... --clean`。修复后禁止沿用修复前的旧报告，也禁止同时生成两个入口。

每轮重跑后检查结果：
- **全部通过** → 退出循环，进入步骤⑥
- **仍有失败** → 回到步骤③继续分析

**最多 5 轮**，5 轮后仍有失败则按现有证据分类记录；不能仅凭重试次数判定为 API bug。然后进入步骤⑥。

---

## ⑥ 更新 `<PROJECT_DIR>/MEMORY.md`

将以下信息**追加写入** `<PROJECT_DIR>/MEMORY.md`：

1. **结果统计**（通过/失败/跳过数量）
2. **修复记录**（修了什么、API bug 列表）

## 产出

📝 `<PROJECT_DIR>/MEMORY.md`：结果统计、修复记录。**必须写入该项目文件（如果数据库可用，再额外写入数据库）。**

## 双重保存

先写 `<PROJECT_DIR>/MEMORY.md`；数据库可用时再额外写数据库。数据库或 Agent 记忆不可替代项目文件。
