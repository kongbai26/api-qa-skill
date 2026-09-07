# 快速路径前置：信息收集 + 环境确认（阶段 1+2 合并）

> **⛔ 本阶段无额外 reference 文件需要读取。**
>
> ⚠️ 仅用于接口数 ≤ 5 的简单任务。复杂逻辑（支付/权限/工作流）必须走完整 5 阶段。

## 前置条件

本阶段在用户确认走快速路径后开始。此时 API 文档已读取，接口清单已提取，路由已确认。

## 目标

一次性收集剩余必要信息：项目位置、运行环境、认证方式。收集完毕后直接进入快速路径执行阶段。

## 步骤清单（执行时必须逐项打勾，跳过禁止）

```
⬜ 1. 确认项目位置（问用户）
⬜ 2. 确认运行环境（问用户或自动检测）
⬜ 3. 确认认证方式（已有则跳过，否则问用户）
⬜ 4. 直接进入快速路径（不等确认）
```

**执行规则**：每完成一项立即将 `⬜` 改为 `✅`，全部打勾后读取 `reference/stages/stage-quick.md` + `reference/implementation.md` 进入快速路径。

---

## ① 确认项目位置

向用户输出以下问题，然后**停下来等用户回复**：

> 项目要建在哪个目录？是新建还是追加到已有项目？
> - 新建：我会创建一个项目文件夹（如 `~/Desktop/api-case`）
> - 追加：请提供已有项目的绝对路径
> ⚠️ 请回复后我才继续。

用户回复后：
- "桌面新建"或类似 → 项目位置 = `~/Desktop/api-case`（或用户指定的名称）
- 用户提供具体路径 → 直接使用
- **确保项目目录已创建**：在进入后续步骤前先执行 `mkdir -p "<PROJECT_DIR>"`（Windows 为 `if not exist "<PROJECT_DIR>" mkdir "<PROJECT_DIR>"`）
- 保存到 MEMORY.md（同时将路由阶段提取的认证方式和接口清单一并写入）

---

## ② 确认运行环境

向用户输出以下问题，然后**停下来等用户回复**：

> 你的操作系统和 Python 版本是什么？（例如：macOS + python3.11）
> 如果不确定，回复"自动检测"。
> ⚠️ 请回复后我才继续。

根据用户回复确定 PYTHON：
- 用户说了版本号 → PYTHON=该版本（**不要降级**）
- 用户说"自动检测" → 依次检测 python3 / python / py，全部失败则告知用户安装

然后检测系统信息：
```
shell_exec(command="<PYTHON> -c \"import platform,shutil,sys; print('OS:',platform.system()); print('PythonVersion:',sys.version.split()[0]); print('Allure:',shutil.which('allure') or 'NOT_FOUND')\"")
```

| 变量 | 规则 |
|------|------|
| PYTHON | 用户说的值 > 检测到的值 |
| PIP | 统一用 `PYTHON -m pip` |
| OS_TYPE | Darwin=macOS, Linux, Windows |
| ALLURE | 有 → allure generate；无 → 用 report_generator.py |

---

## ③ 确认认证方式

**先检查 MEMORY.md 中是否已有认证方式**：
```
shell_exec(command="<PYTHON> -c \"import os; print('FOUND' if os.path.exists('<PROJECT_DIR>/MEMORY.md') and 'auth_info' in open('<PROJECT_DIR>/MEMORY.md', encoding='utf-8', errors='ignore').read() else 'NOT_FOUND')\"")
```
- **FOUND** → 直接使用，跳过本步骤
- **NOT_FOUND** → 按以下优先级处理：
  1. **路由阶段已提取认证方式**（文档明确提到 Token / API Key / OAuth）→ 直接使用，向用户索要密钥/Token
  2. **路由阶段未提取**（文档未提及认证）→ 问用户：该 API 是否需要认证？如需要请提供方式和密钥
  - 等回复后写入 MEMORY.md

---

## ④ 进入快速路径

信息收集完毕，**不等用户确认计划**，直接读取以下文件并执行：

```
read_file(file_path="<skill_dir>/reference/stages/stage-quick.md")
read_file(file_path="<skill_dir>/reference/implementation.md")
```

## 产出

📝 MEMORY.md：N 个接口，项目位置，PYTHON，OS_TYPE，ALLURE，认证方式。保存到 `<PROJECT_DIR>/MEMORY.md`。
