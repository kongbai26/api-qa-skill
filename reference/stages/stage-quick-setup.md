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

## ① 确认项目位置（必须由用户明确确认，严禁擅自决定）

项目位置涉及文件读写与环境隔离，**严禁 Agent 未经用户确认就擅自创建或默认决定目录**。

向用户输出清晰、专业的选项，并**停下来等待用户明确回复**：

- **情况 A：用户已在提示词中提供了具体路径**（如 `./tests/api-test` 或绝对路径）：
  向用户确认：
  > 检测到你指定的测试工程目录为：`<PATH>`。
  > 请确认是否在此目录创建测试套件？（回复“确认”继续，或提供其他路径）
  > ⚠️ 请回复后我才继续。

- **情况 B：用户未提供路径或写了“无”**：
  提供结构化选项供用户快速选择：
  > 请确认测试工程创建位置（请选择序号或直接提供路径）：
  > 1. 在当前工作区创建独立目录：`./api-test`（推荐）
  > 2. 在桌面新建独立目录：`~/Desktop/api-test`
  > 3. 指定其他已有项目的绝对路径
  > ⚠️ 请回复你的选择或具体路径，确认后我才开始创建。

**规则**：
- **严禁不等用户回复就创建目录或进入下一步**。
- **严禁擅自默认路径**。
- 用户回复后（如回复“1”、“确认”或具体路径）：
  - 确定最终的 `<PROJECT_DIR>` 绝对路径。
  - 执行创建目录：`mkdir -p "<PROJECT_DIR>"`（Windows 为 `if not exist "<PROJECT_DIR>" mkdir "<PROJECT_DIR>"`）。
  - 保存到 MEMORY.md（同时将路由阶段提取的认证方式和接口清单一并写入）。

---

## ② 确认运行环境

按以下规则确定运行环境：

1. **用户已指定 Python 版本**（例如用户说了 `python3.11`）：
   → `PYTHON` 使用用户指定的版本命令，**严禁降级**。
2. **用户未指定或表示自动检测**：
   → **直接静默自动检测，无需中断对话发问！**
   依次探测系统可用的 Python 解释器（python3 / python / py）并获取系统信息：

```
shell_exec(command="<PYTHON> -c \"import platform,shutil,sys; print('OS:',platform.system()); print('PythonVersion:',sys.version.split()[0]); print('Allure:',shutil.which('allure') or 'NOT_FOUND')\"")
```

| 变量 | 规则 |
|------|------|
| `PYTHON` | 用户指定的值 > 自动检测到的可用解释器 |
| `PIP` | 统一用 `PYTHON -m pip` |
| `OS_TYPE` | Darwin=macOS, Linux, Windows |
| `ALLURE` | 有 → allure generate；无 → 用 report_generator.py |

---

## ③ 确认认证方式

按以下优先级处理：
1. **用户已在初始提示词中提供认证信息**（例如提供了 Token / API Key / 登录账号密码 / 或写了“无”）：
   → **直接使用，严禁重复发问！**
2. **路由阶段已提取明确认证方式**：
   → 若需要 Token 但用户尚未提供，向用户索要；若文档说明无需认证，直接记录为“无需认证”。
3. **完全未知且文档未提及**：
   → 向用户询问：该 API 是否需要认证？如需要请提供方式和密钥。
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
