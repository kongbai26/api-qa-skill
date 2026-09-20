# 阶段一：信息收集与计划确认

> 进入本文件前，根文件入口路由已经锁定完整流程、项目绝对路径和本次复用选择。本阶段不创建测试框架、测试代码、报告或 runner。

## 目标

记录 API 范围、项目位置、运行环境和 API 契约，形成测试计划并等待用户确认。

## 清单

```text
⬜ 1. 记录 API 文档与接口清单
⬜ 2. 记录项目位置
⬜ 3. 确认运行环境
⬜ 4. 确认 API Base URL 与认证方式
⬜ 5. 汇报计划并等待用户确认
```

首次进入时展示完整清单；每次只处理第一个未完成项，取得证据后立即标为 `✅`。五项全部完成前不能进入阶段二。

## ① 记录 API 文档与接口清单

使用入口路由已经确认的测试范围，将每个接口按“方法 | 路径”写入 `<PROJECT_DIR>/MEMORY.md` 的 `## 接口清单`。数量必须与路由统计一致，不能把用户指定的单个接口扩成整个资源。

已有项目只在用户本次明确变更范围时更新接口清单，并保留旧的阶段记录。完成后标记第①项。

## ② 记录项目位置

使用用户确认的绝对 `PROJECT_DIR`，不能改用 CWD、会话工作区或 Skill 目录。检查目录状态并确定：

- 目录不存在或为空：`PROJECT_KIND=new`
- 目录已有用户文件：`PROJECT_KIND=existing`

在项目 `MEMORY.md` 的 `## 项目配置` 写入 `PROJECT_DIR` 和 `PROJECT_KIND`。新项目创建记录；已有项目只合并本次明确变更，不能覆盖整份文件。完成后标记第②项。

## ③ 确认运行环境

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
4. `OS_TYPE` 只写 `Darwin`、`Linux` 或 `Windows`；`ALLURE` 只写“有”或“无”。版本信息写入阶段发现。
5. 生成后续使用的 `PYTHON_CMD` 和 `ENTER_PROJECT`，写入项目 MEMORY 后标记第③项。

## ④ 确认 Base URL 与认证方式

分别确定两项；缺哪项只问哪项并等待。来源顺序为：用户本次明确值 → 入口路由已确认的复用值 → API 文档 → 询问用户。

- `API_BASE_URL`：完整 HTTP(S) 地址，不含用户名或密码；不能用猜测地址替代。
- `AUTH_MODE`：`none`、`bearer`、`header`、`query`、`cookie`、`basic` 或 `dynamic`。
- 需要时记录 `AUTH_NAME`、`AUTH_SCHEME`、`AUTH_SECRET_ENV`；只记录变量名，不索取凭据原文。
- 文档明确无需认证时使用 `AUTH_MODE=none`。
- 动态 OAuth/登录只记录已确认契约，不猜测登录或刷新接口。

把完整项目配置写入 `MEMORY.md`。本阶段不创建或读取 `.env`。两项都确定后标记第④项。

## ⑤ 汇报并锁定计划

回读项目 MEMORY，确认项目路径、环境、报告分支、Base URL、认证方式和接口清单都已填写。向用户汇报：

```text
项目规划如下，请确认：
- 位置：<绝对路径>
- API Base URL：<地址>
- 环境：OS=<值>，PYTHON=<值>，ALLURE=<有|无>
- 认证：<方式和变量名，不显示凭据>
- 接口数：N
- 预估用例数：N
请确认后我再进入阶段二。
```

入口路由已经确认沿用同一项目且范围未变时，可用该入口决定完成本项；其他情况必须等待用户明确确认，不能用模型判断、任务清单或含糊回复代替。完成本项后：

1. 在 `## 阶段记录` 追加 `### 阶段一 - YYYY-MM-DD`，记录实际完成、发现和决定。
2. 标记第⑤项为 `✅`。
3. 读取 `<SKILL_DIR>/reference/stages/stage-2-setup.md`。

只写项目内 `MEMORY.md`；不记录凭据原文或清单状态，也不把产出保存到 Agent 数据库、会话工作区或 Skill 目录。
