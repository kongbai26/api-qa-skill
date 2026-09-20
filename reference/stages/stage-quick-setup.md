# 快速路径前置：信息与环境

> 仅用于不超过 5 个、且不含支付、权限、工作流等复杂逻辑的接口。进入本文件前，根文件入口路由已经锁定流程、项目绝对路径和本次复用选择。

## 目标

按顺序把接口范围、项目位置、运行环境和 API 契约写入项目内 `MEMORY.md`。本阶段不创建测试框架、测试代码、报告或 runner。

## 清单

```text
⬜ 1. 记录接口范围和项目位置
⬜ 2. 确认运行环境
⬜ 3. 确认 API Base URL 与认证方式
⬜ 4. 核验前置产出并进入快速执行
```

首次进入时展示完整清单；每次只处理第一个未完成项，取得证据后立即标为 `✅`。四项全部完成前不能读取 `stage-quick.md`。

## ① 记录接口范围和项目位置

使用入口路由已经确认的绝对 `PROJECT_DIR`，不能改用 CWD、会话工作区或 Skill 目录。检查目录状态并确定：

- 目录不存在或为空：`PROJECT_KIND=new`
- 目录已有用户文件：`PROJECT_KIND=existing`

在 `<PROJECT_DIR>/MEMORY.md` 建立或更新：

- `## 项目配置`：先写 `PROJECT_DIR`、`PROJECT_KIND`
- `## 接口清单`：按本次已确认范围写“方法 | 路径”，行数与路由统计一致

新项目创建文件；已有项目只合并本次明确变更，保留原有配置和阶段记录。完成后标记第①项。

## ② 确认运行环境

如果入口路由已经记录用户本次确认复用的 `PYTHON`、`OS_TYPE`、`ALLURE`，把这些值写入项目 MEMORY 并完成本项，不重复探测。

否则询问并等待：

```text
你的操作系统和 Python 版本是什么？例如 macOS + python3.11。
不确定可以回复“自动检测”。
```

用户回复后：

1. 用户指定 Python 时验证该命令，不自行降级；回复“自动检测”时，POSIX 依次尝试 `python3`、`python`，Windows 依次尝试 `py`、`python`、`python3`。
2. 用选定的单一 Python 命令实际验证系统和版本：

```text
<PYTHON_CMD> -c "import platform,sys; print('OS:', platform.system()); print('PythonVersion:', sys.version.split()[0])"
```

3. 再实际执行 `allure --version`：成功为 `ALLURE=有`，命令确实不存在或执行失败为 `ALLURE=无`。工具权限被拒绝时停在本项，不能记为“无”。
4. `OS_TYPE` 只写 `Darwin`、`Linux` 或 `Windows`；`ALLURE` 只写“有”或“无”。版本信息写入阶段发现，不附加在字段值后。
5. 生成后续使用的 `PYTHON_CMD` 和 `ENTER_PROJECT`，写入项目 MEMORY 后标记第②项。

## ③ 确认 Base URL 与认证方式

分别确定两项；缺哪项只问哪项并等待。来源顺序为：用户本次明确值 → 入口路由已确认的复用值 → API 文档 → 询问用户。

- `API_BASE_URL`：完整 HTTP(S) 地址，不含用户名或密码；不能用猜测的 localhost、示例域名或其他公网地址代替。
- `AUTH_MODE`：`none`、`bearer`、`header`、`query`、`cookie`、`basic` 或 `dynamic`。
- 需要时记录 `AUTH_NAME`、`AUTH_SCHEME`、`AUTH_SECRET_ENV`；只记录变量名，不索取凭据原文。
- 文档明确无需认证时使用 `AUTH_MODE=none`，后续不生成虚构的认证失败用例。
- 动态 OAuth/登录只记录已确认契约，不猜测登录或刷新接口。

把上述字段以及 `PYTHON`、`OS_TYPE`、`ALLURE` 写入 `## 项目配置`。本阶段不创建或读取 `.env`。两项都确定后标记第③项。

## ④ 核验并转入快速执行

回读 `<PROJECT_DIR>/MEMORY.md`，确认以下内容均为非占位值：

- `PROJECT_DIR`、`PROJECT_KIND`
- `PYTHON`、`OS_TYPE`、`ALLURE`
- `API_BASE_URL`、`AUTH_MODE` 及适用的认证字段
- 与路由数量一致的接口清单

追加 `### 快速阶段一 - YYYY-MM-DD`，记录实际完成、发现和决定；不写清单状态或凭据。核验通过后标记第④项，再读取：

```text
<SKILL_DIR>/reference/stages/stage-quick.md
```

只写项目内 `MEMORY.md`；不把本阶段产出保存到 Agent 数据库、会话工作区或 Skill 目录。
