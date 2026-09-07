# 阶段一：信息收集

> **⛔ 本阶段无额外 reference 文件需要读取。**

## 目标

读取 API 文档，确认项目位置、运行环境、认证方式，汇报计划等用户确认。

## 步骤清单（执行时必须逐项打勾，跳过禁止）

```
⬜ 1. 获取 API 文档，提取接口清单 + 认证方式
⬜ 2. 确认项目位置（问用户，等回复）
⬜ 3. 确认运行环境（问用户或自动检测，等回复）
⬜ 4. 确认认证方式（已有则跳过，否则问用户）
⬜ 5. 汇报计划，等用户确认
```

**执行规则**：每完成一项立即将 `⬜` 改为 `✅`，全部打勾才能进入阶段二。

---

## ① 确认 API 文档（路由阶段已读取过）

路由阶段已读取文档并提取了接口清单 + 认证方式。

- 路由阶段已提取 → 直接使用，跳过本步骤
- 路由阶段未提取（用户未提供文档）→ 问用户：文档在哪？读完提取接口清单和认证方式

---

## ② 确认项目位置（必须问用户）

向用户输出以下问题，然后**停下来等用户回复**：

> 项目要建在哪个目录？是新建还是追加到已有项目？
> - 新建：我会创建一个项目文件夹（如 `~/Desktop/api-case`）
> - 追加：请提供已有项目的绝对路径
> ⚠️ 请回复后我才继续。

**禁止**：禁止不等用户回复就继续。禁止用"我假设项目位置是 xxx"代替询问。

用户回复后：
- "桌面新建"或类似 → 项目位置 = `~/Desktop/api-case`（或用户指定的名称）
- 用户提供具体路径 → 直接使用
- **确保项目目录已创建**：在进入后续步骤前先执行 `mkdir -p "<PROJECT_DIR>"`（Windows 为 `if not exist "<PROJECT_DIR>" mkdir "<PROJECT_DIR>"`）
- 写入 MEMORY.md（同时将路由阶段提取的认证方式和接口清单一并写入）

---

## ③ 确认运行环境（必须问用户）

向用户输出以下问题，然后**停下来等用户回复**：

> 你的操作系统和 Python 版本是什么？（例如：macOS + python3.11）
> 如果不确定，回复"自动检测"。
> ⚠️ 请回复后我才继续。

**禁止**：禁止不等用户回复就自动检测。禁止用"我检测到你的环境是 xxx"代替询问。

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

写入 MEMORY.md。

---

## ④ 确认认证方式（必须在步骤⑤之前完成）

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

## ⑤ 汇报计划，等用户确认

**步骤①-④全部完成后**，向用户汇报并确认：

> 项目规划如下，请确认：
> - 位置：xxx
> - 环境：OS=xxx, PYTHON=xxx, ALLURE=xxx
> - 认证：xxx
> - 接口数：N 个
> - 预估用例数：xxx
> ⚠️ 请确认后我才继续阶段二。

然后**停下来等用户确认**。

**用户确认后** → 读取 `reference/stages/stage-2-setup.md` 进入阶段二。

**禁止**：
- 禁止步骤①-④未完成时就显示步骤⑤
- 禁止不等用户确认就进入阶段二
- 禁止用"我假设..."代替用户确认

---

## 产出

📝 MEMORY.md：项目位置、PYTHON、OS_TYPE、ALLURE、认证方式、接口清单。保存到 `<PROJECT_DIR>/MEMORY.md`。
