# 阶段二：搭框架 + 调接口

> **⛔ 本阶段需要额外读取：reference/implementation.md + reference/run-scripts.md + _templates/report_generator.py**

## 目标

创建项目结构，验证接口，安装依赖。

## 步骤清单（执行时必须逐项打勾，跳过禁止）

```
⬜ ① 创建框架文件（conftest.py / request_helper.py 等）
⬜ ② 复制报告工具（ALLURE=有则跳过）
⬜ ③ 生成运行脚本（run.sh / run.bat）
⬜ ④ 安装依赖
⬜ ⑤ curl 调每个接口，记录实际返回
```

**执行规则**：每完成一项立即将 `⬜` 改为 `✅`，全部打勾才能进入阶段三。

## ⛔ 开始前：确保目录存在并检查项目状态

首先确保项目目录已创建：
```
shell_exec(command="<PYTHON> -c \"import os; os.makedirs(r'<PROJECT_DIR>', exist_ok=True)\"")
```

然后执行项目状态检查：
```
shell_exec(command="cd \"<PROJECT_DIR>\" && <PYTHON> -c \"import os; files=['conftest.py', 'utils/request_helper.py', 'utils/__init__.py', 'pytest.ini', 'requirements.txt', '.env', '.gitignore', 'MEMORY.md']; print('=== 项目状态检查 ==='); [print(f'✅ {f}' if os.path.exists(f) else f'❌ {f} 缺失') for f in files]; script_ok = os.path.exists('run.sh') or os.path.exists('run.bat'); print('✅ 运行脚本存在' if script_ok else '❌ 运行脚本缺失'); rep_ok = os.path.exists('utils/report_generator.py'); print('✅ utils/report_generator.py 存在' if rep_ok else ('⚪ utils/report_generator.py 未复制（ALLURE=有，无需复制）' if '<ALLURE>'=='有' else '❌ utils/report_generator.py 缺失'))\"")
```

**检查结果处理**：
- **所有核心文件都存在、运行脚本存在、且 .env 中 API 配置完整** → 直接进入 ⑤ curl 调接口（跳过 ①-④）
- **核心文件缺失** → 进入 ① 创建核心文件
- **报告工具缺失（仅当 ALLURE=无 时）** → 进入 ② 复制报告工具；若 ALLURE=有 则直接跳过
- **⛔ 运行脚本缺失（run.sh 或 run.bat 不存在）** → **必须进入 ③ 生成运行脚本，禁止跳过**
- **不要重复创建已存在的文件** — 已存在的文件跳过，只创建缺失的

---

## ① 创建框架文件

用 `save_file` 创建以下文件（**完整代码见 reference/implementation.md**，用 read_file 读取后照抄）：
- `conftest.py` — 完整代码在 reference/implementation.md 的 "## conftest.py 完整代码" 章节
- `utils/request_helper.py` — 完整代码在 reference/implementation.md 的 "## request_helper.py 完整代码" 章节
- `utils/__init__.py` — 空文件
- `pytest.ini`
- `requirements.txt`
- `.env`（填入 API 基地址和 token）
- `.gitignore`

**⚠️ 文件创建失败处理**：
- 如果 save_file 失败，**最多重试 2 次**
- 如果连续 3 次都失败，**停止创建**，告知用户："无法创建文件，请检查目录权限或磁盘空间"
- **禁止死循环重试** — 必须有明确的退出条件

---

## ② 复制报告工具（根据环境决定）

**先检查阶段一检测的 ALLURE 变量**：

**如果有 allure（ALLURE=有）**：
- ✅ **跳过复制** `_templates/report_generator.py` — 全程使用 Allure 官方工具链，无需此文件
- ✅ 阶段四和阶段五统一使用 `allure generate`，只验收 `allure-report/index.html`
- **直接跳到 ③**，不要执行下面的步骤1-3

**如果没有 allure（ALLURE=无）**：
- 必须复制 LiteReport 生成器（完整版）

**步骤1：获取模板文件（双保险策略）**

方法A - 使用 `read_file`（优先）：
```
read_file(file_path="<skill_dir>/_templates/report_generator.py")
```

方法B - 如果方法A失败，使用 `shell_exec cat`：
```
shell_exec(command="cat '<skill_dir>/_templates/report_generator.py'")
```

**⚠️ 如果两种方法都失败**：
- 告知用户："无法自动获取报告生成器模板文件"
- 询问："请提供 report_generator.py 的文件路径，或粘贴文件内容"

**步骤2：保存到项目目录**
```
save_file(file_path="<PROJECT_DIR>/utils/report_generator.py", content="<读取到的内容>")
```

**步骤3：验证文件存在**
```
shell_exec(command="cd \"<PROJECT_DIR>\" && <PYTHON> -c \"import os; sz=os.path.getsize('utils/report_generator.py') if os.path.exists('utils/report_generator.py') else 0; print('OK' if sz > 45000 else 'FAIL')\"")
```

**验证结果处理**：
- **如果文件存在且大小正常** → 继续下一步
- **如果文件不存在或异常** → **必须重新执行步骤1-2**，不能跳过，不能自己创建简化版
- **如果连续 3 次都失败** → 告知用户无法复制模板，询问是否手动提供文件内容

**⚠️ 红线**：
1. **禁止自己创建简化版** — 必须使用 `_templates/report_generator.py` 完整版
2. **禁止用其他文件替代** — 不能用 `simple_report.py` 等替代

**为什么重要**：没有 allure 时，这个文件是生成单页面 HTML 报告的唯一方式。如果用简化版，用户将看不到交互式报告。

---

## ③ 生成运行脚本

**⛔ 本步骤不可跳过。运行脚本是用户一键执行测试+生成报告的唯一入口，缺少脚本等于无法交付。**

**先检查脚本是否存在**：
```
shell_exec(command="ls -la '<PROJECT_DIR>/run.sh' 2>/dev/null && echo 'run.sh 存在' || echo '❌ run.sh 缺失'")
shell_exec(command="ls -la '<PROJECT_DIR>/run.bat' 2>/dev/null && echo 'run.bat 存在' || echo '❌ run.bat 缺失'")
```

**处理规则**：
- **如果对应脚本已存在** → 跳过，不要覆盖
- **如果对应脚本不存在** → **必须执行下面的步骤1-3，禁止跳过**

**步骤1：获取脚本内容（双保险策略）**

方法A - 使用 `read_file`（优先）：
```
read_file(file_path="<skill_dir>/reference/run-scripts.md")
```

方法B - 如果方法A失败，使用 `shell_exec cat`：
```
shell_exec(command="cat '<skill_dir>/reference/run-scripts.md'")
```

**⚠️ 如果两种方法都失败**：
- 告知用户："无法自动获取运行脚本模板文件"
- 询问："请提供 run.sh 的文件路径，或粘贴文件内容"

**步骤2：保存到项目目录**
- OS_TYPE 是 Darwin 或 Linux → 用 `save_file` 保存为 `<PROJECT_DIR>/run.sh`
- OS_TYPE 是 Windows → 用 `save_file` 保存为 `<PROJECT_DIR>/run.bat`
- **必须原样使用**脚本内容，脚本已内置 Python 自动检测，不需要修改

**步骤3：设置执行权限并验证**

OS_TYPE 是 Darwin 或 Linux：
```
shell_exec(command="chmod +x '<PROJECT_DIR>/run.sh' && ls -la '<PROJECT_DIR>/run.sh'")
```

OS_TYPE 是 Windows：
```
shell_exec(command="ls -la '<PROJECT_DIR>/run.bat'")
```

**验证结果处理**：
- **文件存在且有执行权限（Darwin/Linux 有 x 标志）** → 继续下一步
- **文件不存在** → **必须重新执行步骤1-2**，不能跳过
- **连续 3 次都失败** → 告知用户无法生成运行脚本，询问是否手动提供

**⚠️ 红线**：
1. **禁止跳过 ③** — 运行脚本缺失时直接进 ④ 等于交付残缺项目
2. **禁止自己重写脚本** — 必须从 `reference/run-scripts.md` 原样复制，脚本内容已经过验证
3. **禁止忘记 chmod +x** — macOS/Linux 下没有执行权限，用户执行 `./run.sh` 会报 `Permission denied`

**为什么重要**：用户拿到项目后，只需要执行一个 `./run.sh` 就能自动安装依赖、跑测试、生成报告。缺少脚本 = 用户需要手动敲多条命令 = 交付不合格。

---

## ④ 安装依赖

```
shell_exec(command="cd \"<PROJECT_DIR>\" && <PYTHON> -m pip install -r requirements.txt")
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

- **如果 API_TOKEN 已配置** → 直接调用接口
- **如果 API_TOKEN 未配置** → 需要调用登录接口获取 token

用 `curl` 工具调每个接口，记录实际返回，比对文档差异。

如果 API 需要登录获取 token：
```
curl(url="<登录接口URL>", method="POST", body='{"username":"xxx","password":"xxx"}', headers='{"Content-Type": "application/json"}')
```
从返回中提取 token，写入 .env 文件。

## 产出

📝 MEMORY.md：差异表。保存追加到 `<PROJECT_DIR>/MEMORY.md`。
