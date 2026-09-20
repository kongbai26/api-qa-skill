# 快速路径：搭建、测试与交付

> 仅用于不超过 5 个简单接口。前置阶段四项必须全部完成，项目 `MEMORY.md` 已包含非占位的目录、环境、报告分支、Base URL、认证方式和接口清单。

## 清单

```text
⬜ 1. 搭建框架并预置当前 OS runner
⬜ 2. 安装依赖
⬜ 3. 真实探测每个接口并记录差异
⬜ 4. 编写并收集测试用例（每接口 3–5 条）
⬜ 5. 运行测试并修复（最多 3 轮）
⬜ 6. 生成锁定分支的唯一报告
⬜ 7. 确认交付文件
⬜ 8. 更新 MEMORY.md 并交付
```

首次进入时展示完整清单；始终处理第一个未完成项，取得证据后立即打勾。八项全部 `✅` 前不能输出完成结束语。发现前置字段缺失时停止本阶段，通过根文件入口纠正该值后再继续当前项。

## ① 框架、报告工具与 runner

先枚举项目文件，再运行核心物化：

```text
<ENTER_PROJECT> <PYTHON_CMD> "<SKILL_DIR>/scripts/materialize_templates.py" --project "<PROJECT_DIR>" --component core --project-kind <PROJECT_KIND>
```

物化器创建或核对 `.gitignore`、`conftest.py`、`pytest.ini`、`requirements.txt`、`utils/__init__.py`、`utils/request_helper.py` 和 `utils/contract_probe.py`。

- `PASS`：继续。
- `REVIEW`：只读取 `PRESERVED` 的非敏感文件和 `reference/implementation.md`；满足契约就保留，有冲突才最小修改。
- `FAIL`：修正路径、权限或参数后最多重试 2 次；仍失败则停止，不能手写简化框架。

运行配置脚本：

```text
<ENTER_PROJECT> <PYTHON_CMD> "<SKILL_DIR>/scripts/configure_project_env.py" --project "<PROJECT_DIR>" --base-url "<API_BASE_URL>" --auth-mode <AUTH_MODE> --auth-name "<AUTH_NAME 或空>" --auth-scheme "<AUTH_SCHEME 或空>" [dynamic 时传 --secret-env "<变量名列表>"]
```

Agent 不读取、搜索或回显 `.env`。需要认证时，请用户在本地填好空凭据槽并只回复“已配置”。

按锁定报告分支处理：

- `ALLURE=有`：不复制、不读取、不验证 `utils/report_generator.py`。
- `ALLURE=无`：

```text
<ENTER_PROJECT> <PYTHON_CMD> "<SKILL_DIR>/scripts/materialize_templates.py" --project "<PROJECT_DIR>" --component report --project-kind <PROJECT_KIND> --report fallback
```

报告物化结果为 `REVIEW` 时保留现有文件并请用户决定，不能运行或覆盖；不能用简化生成器或宿主报告工具代替。

最后、在安装依赖或测试前物化 runner：

```text
<ENTER_PROJECT> <PYTHON_CMD> "<SKILL_DIR>/scripts/materialize_templates.py" --project "<PROJECT_DIR>" --component runner --project-kind <PROJECT_KIND> --os <OS_TYPE> --python-command "<PYTHON>" --report <official|fallback>
```

新项目只生成当前 OS 的一份 runner。`REVIEW` 时读取 `reference/run-scripts.md` 和已有脚本做最小适配；物化命令不可用但文件写入可用时，按该 reference 只复制当前 OS 模板并替换占位符。Darwin/Linux 可执行命令时补 `chmod +x run.sh`。runner 不安装依赖。

如果核心或报告物化命令被拒绝，不能把步骤①标为完成；但文件写入仍可用时，先按上一条保留当前 OS runner，再暂停并给出手动命令。

## ② 安装依赖

```text
<ENTER_PROJECT> <PYTHON_CMD> -m pip install -r requirements.txt
```

失败时检查 Python、网络和具体依赖，最多重试 2 次；仍失败则停止并如实说明。

## ③ 真实探测接口

- 无需认证：用宿主 HTTP 能力逐个调用；本地或内网地址无法由宿主访问时使用项目统一请求封装。
- 静态认证：先用无凭据 `curl` 记录认证失败响应；用户确认本地凭据已配置后，对每个接口运行：

```text
<ENTER_PROJECT> <PYTHON_CMD> -m utils.contract_probe --method <METHOD> --path "<具体相对路径>" [--params-file "<PROJECT_DIR>/.probe/params.json"] [--json-body-file "<PROJECT_DIR>/.probe/body.json"]
```

参数文件只能含非敏感值，探测后删除；路径参数必须替换为代表值。

- 动态认证：按已确认契约实现项目专用 fixture；步骤④先运行一个最小真实认证用例。
- 写操作、并发、支付或权限变更先确认环境授权和清理策略。
- Token、Cookie、密码和 API Key 不进入命令、日志或 MEMORY。

记录每个接口的状态码、脱敏响应摘要以及文档差异。

## ④ 编写并收集用例

每个接口编写 3–5 个实际展开的 pytest node，覆盖：

- 正向功能
- 核心数据或业务规则
- 契约明确的认证/权限或核心异常

无需认证的 API 不生成虚构的认证失败用例。每个用例必须：

- 使用 `allure_request` 或 `AuthSession` 发真实请求
- 有中文 `allure.title`、中文 docstring、中文 `expected`
- 由模型依据已确认契约写真实断言
- 不使用 `assert True`、传输层 mock、空壳或为全绿而放宽的断言

写完运行：

```text
<ENTER_PROJECT> <PYTHON_CMD> -m pytest tests/ --collect-only -q
```

建立“方法 | 路径 | 展开后 node 数”表。逐接口必须为 3–5，合计必须等于 collected 总数。命令不可用或被拒绝时不估算，保留 runner 并请用户手动执行。

## ⑤ 运行与修复

```text
<ENTER_PROJECT> <PYTHON_CMD> -m pytest tests/ -v --tb=short --alluredir=allure-results --clean-alluredir
```

- 测试代码或断言与已确认契约不一致：最小修复。
- 实际行为与契约不一致且有复现证据：保留正确断言，记录 API 差异。
- 环境、网络或凭据问题：如实记录，不能判为 API 缺陷。
- 修改后重跑，最多 3 轮；仍失败时按现有证据分类。

命令不可用或被拒绝时不重试、不伪造结果；给出步骤①已交付 runner 的手动命令并停在本项。

## ⑥ 唯一报告

使用锁定分支：

- `ALLURE=有`

```text
<ENTER_PROJECT> allure generate allure-results -o allure-report --clean
```

只认 `allure-report/index.html`。

- `ALLURE=无`

```text
<ENTER_PROJECT> <PYTHON_CMD> utils/report_generator.py --input allure-results --output allure-report/report.html --clean
```

只认 `allure-report/report.html`。

禁止生成第二个报告、调用宿主报告器、运行 `allure serve/open` 或自动打开浏览器。生成后只检查锁定入口存在且非空、另一入口不存在；不解析报告内容。命令不可用时不伪造报告，保留 runner 并请用户手动执行。

## ⑦ 确认交付文件

只检查存在性，不重跑测试、不重新生成报告、不做 runner 语法双检或实跑：

- `tests/` 下至少一个 `test_*.py`
- `allure-results/` 下至少一个 `*-result.json`
- 锁定报告入口存在，另一入口不存在
- Darwin/Linux 的 `run.sh` 存在且可执行，或 Windows 的 `run.bat` 存在
- `MEMORY.md` 存在

runner 缺失时才按步骤①补当前 OS 文件。手动命令：

- Darwin/Linux：`cd "<PROJECT_DIR>" && chmod +x run.sh && ./run.sh`
- Windows：`cd /d "<PROJECT_DIR>" && call run.bat`

## ⑧ 更新 MEMORY 并交付

在项目 `MEMORY.md` 追加：

- `## 差异表`
- `## 用例计数`
- `## 结果统计`：通过、失败、跳过
- `## 修复记录`
- `### 快速阶段二 - YYYY-MM-DD`：实际完成、发现和交付结论

回读确认文件非空，标记第⑧项。八项全部 `✅` 后按以下结构交付：

```text
快速流程步骤清单：8 项全部 ✅
测试结果：通过 N，失败 N，跳过 N
项目目录：<PROJECT_DIR 绝对路径>
测试代码：<实际文件>
测试报告：<唯一报告入口绝对路径>
原始结果：<PROJECT_DIR>/allure-results/
运行脚本：<当前 OS runner 绝对路径>（供用户复跑）
测试状态：已执行 | 未执行；未执行时请用户运行上述手动命令
项目记录：<PROJECT_DIR>/MEMORY.md
测试完成，报告已生成；交付物已准备完毕。
```

不得列出不存在的路径，也不能把“runner 已交付”写成“runner 已实跑”。只写项目 MEMORY，不写 Agent 记忆或数据库。
