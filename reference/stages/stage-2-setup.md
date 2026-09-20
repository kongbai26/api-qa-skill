# 阶段二：搭框架 + 调接口

> 前置：阶段一清单全部完成，计划已经确认。标准资产使用物化器；只有物化结果为 `REVIEW` 或动态认证时才读 `reference/implementation.md`，只有 runner 冲突或物化命令不可用时才读 `reference/run-scripts.md`。

## 清单

```text
⬜ 1. 创建或确认核心框架
⬜ 2. 按 ALLURE 分支处理报告工具
⬜ 3. 预置当前 OS 的运行脚本
⬜ 4. 安装依赖
⬜ 5. 真实探测接口并记录差异
```

首次进入时展示完整清单；按顺序完成并立即打勾。开始前回读项目 `MEMORY.md`，确认 `PROJECT_DIR`、`PROJECT_KIND`、`PYTHON`、`OS_TYPE`、`ALLURE`、`API_BASE_URL`、`AUTH_MODE` 均为非占位值。缺失时停止本阶段，通过根文件入口纠正该值后再继续当前项。

## ① 核心框架

先枚举项目文件，再执行：

```text
<ENTER_PROJECT> <PYTHON_CMD> "<SKILL_DIR>/scripts/materialize_templates.py" --project "<PROJECT_DIR>" --component core --project-kind <PROJECT_KIND>
```

物化器负责 `.gitignore`、`conftest.py`、`pytest.ini`、`requirements.txt`、`utils/__init__.py`、`utils/request_helper.py` 和 `utils/contract_probe.py`。

- `PASS`：文件已创建或与模板一致，完成本项。
- `REVIEW`：只读取 `PRESERVED` 的非敏感目标和 `reference/implementation.md`；满足契约则保留，有冲突才最小修改。
- `FAIL`：修正路径、权限或参数后最多重试 2 次；仍失败则停止，不能手写简化框架。

然后执行配置脚本：

```text
<ENTER_PROJECT> <PYTHON_CMD> "<SKILL_DIR>/scripts/configure_project_env.py" --project "<PROJECT_DIR>" --base-url "<API_BASE_URL>" --auth-mode <AUTH_MODE> --auth-name "<AUTH_NAME 或空>" --auth-scheme "<AUTH_SCHEME 或空>" [dynamic 时传 --secret-env "<变量名列表>"]
```

配置脚本只输出变量名和处理状态，保留已有凭据。Agent 不读取、搜索或回显 `.env`。需要认证时请用户在本地填写空凭据槽并只回复“已配置”。

## ② 报告工具

只使用阶段一锁定的 `ALLURE`：

- `ALLURE=有`：本项确认使用官方 Allure；不复制、不读取、不验证 `utils/report_generator.py`。
- `ALLURE=无`：执行：

```text
<ENTER_PROJECT> <PYTHON_CMD> "<SKILL_DIR>/scripts/materialize_templates.py" --project "<PROJECT_DIR>" --component report --project-kind <PROJECT_KIND> --report fallback
```

`PASS` 且文件非空即可完成；`REVIEW` 时保留现有文件并请用户决定，不运行或覆盖；`FAIL` 最多重试 2 次。不能用简化生成器或宿主报告工具代替。

## ③ 当前 OS runner

必须在安装依赖和运行测试前执行：

```text
<ENTER_PROJECT> <PYTHON_CMD> "<SKILL_DIR>/scripts/materialize_templates.py" --project "<PROJECT_DIR>" --component runner --project-kind <PROJECT_KIND> --os <OS_TYPE> --python-command "<PYTHON>" --report <official|fallback>
```

- 新项目只生成 Darwin/Linux 的 `run.sh` 或 Windows 的 `run.bat`，不同时生成两份。
- `PASS` 后完成本项；`REVIEW` 时读取 `reference/run-scripts.md` 和当前 OS 的已有脚本，只做必要适配；`FAIL` 最多重试 2 次。
- 物化命令不可用但文件写入可用时，按 `reference/run-scripts.md` 只复制当前 OS 模板并替换两个占位符；Darwin/Linux 可执行命令时补 `chmod +x run.sh`。
- runner 只跑测试并生成报告，不安装依赖。已有项目不删除另一平台的用户文件。

如果步骤①或②的命令权限被拒绝，不能把对应项标为完成；但文件写入仍可用时，先按上一条保留当前 OS runner，再暂停并交给用户手动执行，避免交付目录中连入口脚本都没有。

## ④ 安装依赖

```text
<ENTER_PROJECT> <PYTHON_CMD> -m pip install -r requirements.txt
```

失败时检查 Python、网络和具体依赖，最多重试 2 次；仍失败则停止并如实说明。

## ⑤ 真实探测并记录

- **无需认证**：用宿主 HTTP 能力逐个调用；本地或内网地址无法由宿主访问时，使用项目统一请求封装。
- **静态认证**：先用无凭据 `curl` 记录认证失败响应；用户确认本地凭据已配置后，对每个接口运行：

```text
<ENTER_PROJECT> <PYTHON_CMD> -m utils.contract_probe --method <METHOD> --path "<具体相对路径>" [--params-file "<PROJECT_DIR>/.probe/params.json"] [--json-body-file "<PROJECT_DIR>/.probe/body.json"]
```

参数文件只能含非敏感值，探测后删除。路径参数必须替换为代表值，查询参数不用拼进 `--path`。

- **动态认证**：不猜测登录或刷新接口；阶段三先按已确认契约写一个最小真实认证用例，成功后再扩展。
- 遇到写操作、并发、支付或权限变更，先确认环境授权和清理策略。
- 不把 Token、Cookie、密码或 API Key 放入命令、日志或 MEMORY。

把状态码、脱敏响应摘要和文档差异追加到 `MEMORY.md` 的 `## 差异表`；没有差异也写明。追加 `### 阶段二 - YYYY-MM-DD` 后标记第⑤项。五项全部 `✅` 后读取 `stage-3-write.md`。
