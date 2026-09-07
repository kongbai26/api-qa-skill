# api-qa-skill 🚀

[English](README.md) | [简体中文](README_zh.md)

> **生产级 API 自动化测试 Agent 技能库**  
> 专为 AI Agent（Antigravity、Claude Code、Cursor、Windsurf 等）打造的端到端接口自动化测试专家级工作流。基于 `pytest` + `Allure`，覆盖真实探活、用例编写、自愈调试到报告交付的全闭环。

---

## 🌟 核心特性与设计哲学

市面上大部分测试 Agent 往往容易陷入“凭空捏造返回”、“断言脆弱假报错”、“自顾自乱跑修改环境”的陷阱。本项目融合了真实测试工程踩坑经验，通过严苛的**红线防御机制**与**分段按需加载**，确保交付可用、稳定、高质量的工程代码。

* 🛡️ **真实探活与防御性断言**：严禁凭空想象返回，强制先调用真实接口探活再写断言；强制采用多状态码容错（如 `in (400, 422)`）与灵活类型校验，避免脆弱断言。
* 🚦 **人在回路（Human-in-the-Loop）质量门禁**：
  * **路由门禁**：根据接口数量（≤5 走快速路径，>5 走完整流程）与复杂度锁定执行路径，全程防降级偷懒。
  * **环境门禁**：前置核验项目目录、Python 解释器与鉴权 Token，防止环境污染与未授权写入。
  * **计划门禁**：对齐预期用例数与测试覆盖范围后方可动笔。
* 📊 **轻量自洽的双轨测试报告体系**：
  * **环境有 Allure**：无缝对接官方 `allure-pytest`，自动化生成静态测试大盘（`index.html`），严禁阻塞式后台服务。
  * **环境无 Allure**：内置纯 Python 原生驱动的 **LiteReport 生成器**（零 Java 依赖、零外部命令），直出独立单文件交互式 HTML 报告（`report.html`）。
* 📐 **9 维度工业级用例覆盖**：涵盖 正向功能、数据完整性、认证鉴权、参数校验、边界值分析、业务逻辑规则、安全性注入防御、CRUD 链式场景、统一错误响应格式。
* 🔄 **闭环自愈调优（最多 5 轮）**：自动分析失败是用例断言偏差还是服务端真实 Bug；自动修正用例代码直至全部通过或精准归档为接口差异缺陷。
* 📦 **开箱即用的一键运行脚本**：自动适配 macOS/Linux (`run.sh`) 与 Windows (`run.bat`)，内置环境检测与权限管理，交付给任何人均可一键复现执行。

---

## 📁 项目目录结构

```text
api-qa-skill/
├── SKILL.md                     # Agent 入口文件（前置路由、红线规约、环境规范）
├── README.md                    # 项目说明文档 (English)
├── README_zh.md                 # 项目说明文档 (简体中文)
├── LICENSE                      # Apache-2.0 开源协议
├── _templates/
│   └── report_generator.py      # LiteReport 独立单文件 HTML 测试报告生成器
└── reference/
    ├── implementation.md        # 核心框架代码模板（conftest.py / request_helper.py 等）
    ├── test-design.md           # 9 维度用例设计规范与防御性断言写法指南
    ├── test-doc.md              # 交付级用例文档规范（docs/test_cases.md）
    ├── run-scripts.md           # 跨平台一键运行脚本模板（run.sh / run.bat）
    └── stages/                  # 分阶段渐进式工作流文件（避免上下文溢出）
        ├── stage-full-setup.md  # 完整流程 阶段一：信息收集与环境确认
        ├── stage-2-setup.md     # 完整流程 阶段二：框架搭建与接口探活
        ├── stage-3-write.md     # 完整流程 阶段三：9 维度用例编写
        ├── stage-full-test.md   # 完整流程 阶段四：测试执行与自愈修复
        ├── stage-5-deliver.md   # 完整流程 阶段五：重跑验收与资产交付
        ├── stage-quick-setup.md # 快速路径 前置：极速环境收集
        └── stage-quick.md       # 快速路径 执行：合并执行搭调写跑
```

---

## 🛠️ 安装与使用方法

### 1. 在 Antigravity (AGY) 中使用
将本项目克隆至 Agent 的 Skills 目录下：
```bash
# 全局生效（推荐）
git clone https://github.com/kongbai26/api-qa-skill.git ~/.gemini/antigravity-cli/skills/api-qa-skill

# 或仅在当前项目生效
git clone https://github.com/kongbai26/api-qa-skill.git .agents/skills/api-qa-skill
```
在对话中提供 API 文档或接口列表，Agent 会自动激活路由。

### 2. 在 Claude Code / Cursor / Windsurf 中使用
* **Claude Code**：在项目根目录的 `CLAUDE.md` 中引用此 Skill，或在对话中提示：
  > “请严格读取并按照 `./api-qa-skill/SKILL.md` 的规范执行 API 自动化测试。”
* **Cursor / Windsurf**：可作为 Rule 引用或将其路径加入提示词上下文。

---

## 🔄 双轨工作流程对比

| 流程对比 | 完整流程 (Full Workflow) | 快速路径 (Quick Path) |
| :--- | :--- | :--- |
| **适用场景** | 接口数 > 5 或 涉及复杂核心业务（支付/权限/工作流） | 接口数 ≤ 5 且无复杂业务逻辑 |
| **执行阶段** | 5 个阶段严密推进，阶段间设置检查门禁 | 2 个阶段合并极速执行 |
| **用例规模** | GET ≥ 8 条，POST ≥ 15 条，每接口平均 15-20 条 | 每接口 3-5 条核心用例，总数 ≥ 接口数 × 3 |
| **覆盖维度** | 9 维度全覆盖（含边界、并发、安全、链式） | 3 维度核心覆盖（正向、鉴权、核心异常） |
| **交付文档** | 测试代码 + 测试报告 + 用例文档 + 差异缺陷记录 | 测试代码 + 测试报告 + 运行脚本 + MEMORY 记录 |

---

## 📑 交付物规范

测试任务执行完毕后，将在目标项目目录下产出结构清晰的测试套件：
```text
<PROJECT_DIR>/
├── tests/
│   └── test_*.py            # 规范编写的 pytest 测试用例
├── utils/
│   ├── request_helper.py    # 封装了 Allure 步骤记录与 Token 自动注入的请求助手
│   └── report_generator.py  # （无 Allure 环境时）轻量单文件报告生成器
├── conftest.py              # 全局 Fixture（base_url, auth_session, 日志钩子等）
├── pytest.ini               # Pytest 与 Allure 标准配置
├── requirements.txt         # 项目所需依赖
├── .env                     # API 基础路径与密钥配置
├── run.sh / run.bat         # 跨平台一键执行测试并产出报告的入口脚本
├── MEMORY.md                # 接口清单、文档与实际差异表、自愈修复记录
├── docs/test_cases.md       # （完整流程产出）标准化用例设计文档
└── allure-report/           # 最终测试报告
    ├── index.html           # （环境有 Allure 时）官方多文件报告入口
    └── report.html          # （环境无 Allure 时）LiteReport 独立单文件报告
```

---

## 📄 开源许可证

本项目基于 [Apache-2.0 License](LICENSE) 开源。欢迎提 Issue 与 Pull Request！
