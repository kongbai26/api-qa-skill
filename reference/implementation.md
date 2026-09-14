# 框架实现契约

本文件只在以下情况读取：

- `scripts/materialize_templates.py` 返回 `TEMPLATE MATERIALIZATION: REVIEW`
- 已有项目的核心文件需要最小修正
- 认证方式为 `dynamic`，需要按已确认契约定制 fixture

新项目的标准框架由脚本从 `_templates/project/` 按字节复制，禁止先读取模板正文再手抄。

## 标准框架边界

核心文件为：

- `.gitignore`
- `conftest.py`
- `utils/contract_probe.py`
- `utils/request_helper.py`
- `utils/__init__.py`
- `pytest.ini`
- `requirements.txt`

通用请求必须经过 `allure_request()` 或 `AuthSession`；不得在测试中直接调用 `requests`/`httpx` 或 mock 传输层。GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS 均由 `AuthSession` 提供。每次 HTTP 调用都传入中文 `expected`。请求 URL、headers、params、body、响应和日志必须经过统一脱敏逻辑，真实凭据只允许在运行时由 `.env` 注入。

## 已有项目的处理

物化脚本不会覆盖内容不同的已有文件，而是输出 `PRESERVED <相对路径>` 和哈希，并以 `TEMPLATE MATERIALIZATION: REVIEW` 结束。此时：

1. 只读取 `PRESERVED` 列出的非敏感文件；永远不读取或搜索 `.env`。
2. 文件已经满足本节契约时保留原样，不为统一格式而重写。
3. 只有语法错误，或与已确认的 Base URL、认证、统一请求封装、脱敏、报告单分支直接冲突时，才最小修改相关行。
4. 不得用模板整文件覆盖用户定制；修正后运行语法检查和相关测试。

`.gitignore` 至少包含独立一行 `.env`。`pytest.ini` 至少配置 `tests/`、`test_*.py`、Allure 结果目录及实际使用的 markers。`need_auth`、`smoke`、`regression` 和 `api_endpoint(method, path)` 必须注册；不删除已有配置。

`utils/contract_probe.py` 只用于写用例前的真实接口探测：它在项目进程内读取 `.env`，通过 `AuthSession` 发请求，并只输出状态码、Content-Type 和脱敏后的字段结构。查询参数和 JSON body 可从项目内 `.probe/*.json` 读取，以避开不同 Shell 的引号差异；文件必须位于项目内且不能是符号链接。Agent 不得读取 `.env`，也不得把凭据放进参数。静态认证未配置时返回 `PROBE: BLOCKED`；动态认证必须先按已确认契约实现 fixture。

## 认证契约

支持以下 `API_AUTH_MODE`：

| 模式 | 非敏感配置 | 本地凭据槽 |
| --- | --- | --- |
| `none` | 无 | 无 |
| `bearer` | `API_AUTH_SCHEME=Bearer` | `API_TOKEN` |
| `header` | `API_AUTH_NAME`、可选 `API_AUTH_SCHEME` | `API_TOKEN` |
| `query` | `API_AUTH_NAME`、可选 `API_AUTH_SCHEME` | `API_TOKEN` |
| `cookie` | `API_AUTH_NAME` | `API_TOKEN` |
| `basic` | 无 | `API_USERNAME`、`API_PASSWORD` |
| `dynamic` | 按已确认契约 | 按已确认契约 |

旧项目的 `API_AUTH_HEADER`、`API_AUTH_QUERY_PARAM`、`API_AUTH_COOKIE` 和 `API_AUTH_LOCATION` 继续兼容。新项目统一优先使用 `API_AUTH_MODE` + `API_AUTH_NAME`。

`dynamic` 不猜测登录地址、OAuth 流程或 token 字段。仅按文档或用户确认的契约定制项目级 fixture：运行时读取本地凭据，建立已配置的 `requests.Session`，再传给 `AuthSession(..., auth_mode="dynamic", session=session)`。不得通过 Agent 工具提交真实用户名/密码或读取 token 响应原文。

## `.env` 写入规则

先确保 `.gitignore` 已排除 `.env`，然后通过 `scripts/configure_project_env.py` 写入已确认的非敏感项，并只补当前认证模式需要的凭据槽。下面是字段集合说明，不是要求把所有凭据槽同时写入：

```text
API_BASE_URL=
API_AUTH_MODE=none
API_AUTH_NAME=
API_AUTH_SCHEME=

bearer/header/query/cookie: API_TOKEN=
basic: API_USERNAME= 与 API_PASSWORD=
dynamic: 仅已确认的凭据环境变量名
none: 不创建凭据槽
```

- 配置脚本在进程内读取并原样保留已有凭据，只输出变量名和处理状态；Agent 不用文件工具读写 `.env`。
- `PROJECT_KIND=new`：认证需要凭据时，等待用户在本地填写并回复“已配置”。
- `PROJECT_KIND=existing`：更新用户已经确认的非敏感项，补当前模式需要的槽；已有凭据值只标记 `PRESERVED`，重复键或异常结构必须先处理，绝不回显值。
- 用户确认后只通过测试行为验证认证，不回显凭据。

## `MEMORY.md` 稳定格式

`MEMORY.md` 固定保存在 `<PROJECT_DIR>/MEMORY.md`，是用户可见交付物。只记录凭据变量名，不记录值；不得使用 Agent 数据库、project-memory、`memory_save` 或 `memory_recall` 保存或恢复本流程数据。

以下章节名和核心表格列保持稳定，实际文件不得保留尖括号占位符：

```text
## 项目配置
PROJECT_DIR: <已确认的绝对路径>
PROJECT_KIND: new | existing
API_BASE_URL: <已确认的完整 HTTP(S) 地址>
AUTH_MODE: none | bearer | header | query | cookie | basic | dynamic
AUTH_NAME: <不适用时留空>
AUTH_SCHEME: <不适用时留空>
AUTH_SECRET_ENV: <只写变量名；none 时留空>
PYTHON: <已验证命令>
OS_TYPE: Darwin | Linux | Windows
ALLURE: 有 | 无

## 接口清单
| 方法 | 路径 | 说明 |
| --- | --- | --- |
| <METHOD> | <CONTRACT_PATH> | <接口说明> |

## 差异表
<没有则写“无差异”>

## 用例计数
| 方法 | 路径 | 展开后 node 数 |
| --- | --- | ---: |
| <METHOD> | <与接口清单一致的 CONTRACT_PATH> | <整数> |

## 结果统计（快速流程）或 ## 最终结果（完整流程）
| 通过 | <Allure passed 数> |
| 失败 | <Allure failed + broken 数> |
| 跳过 | <Allure skipped 数> |

## 修复记录
<没有则写“无修复”>
```

完整流程还保留 `## 覆盖矩阵`、`## 交付物清单`、`## 遗留问题`。平均用例数因契约范围无法达到 15 时，增加 `## 用例不足说明` 并逐接口写明原因。

`## 阶段记录` 只记录阶段产出，不记录任务清单状态。完整流程必须有阶段一至阶段五，快速流程必须有快速阶段一和快速阶段二；每条标题带 `YYYY-MM-DD`，正文包含非空的“完成、发现、决策”。

## 频率限制

遇到 429 时按契约与 `Retry-After` 做最小必要等待和重试，不能把成功与限流一概都判为正确。大量 401 先停止请求并请用户检查本地凭据或风控状态，禁止读取 `.env` 排查。
