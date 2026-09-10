# api-qa-skill 🚀

[English](README.md) | [简体中文](README_zh.md)

> **生产级 API 自动化测试 Agent 技能库**  
> 专为 AI Agent（Antigravity、Claude Code、Cursor、Windsurf 等）打造的端到端接口自动化测试专家级工作流。基于 `pytest` + `Allure`，覆盖真实探活、用例编写、自愈调试到报告交付的全闭环。

---

## 🌟 核心特性与设计哲学

市面上大部分测试 Agent 往往容易陷入“凭空捏造返回”、“断言脆弱假报错”、“自顾自乱跑修改环境”的陷阱。本项目融合了真实测试工程踩坑经验，通过严苛的**红线防御机制**与**分段按需加载**，确保交付可用、稳定、高质量的工程代码。

* 🛡️ **真实探活与契约断言**：严禁凭空想象返回；先探活识别文档差异，再按用户确认的契约写断言，禁止只为全绿而放宽。
* 🚦 **人在回路（Human-in-the-Loop）质量门禁**：
  * **路由门禁**：根据接口数量（≤5 走快速路径，>5 走完整流程）与复杂度锁定执行路径，全程防降级偷懒。
  * **环境门禁**：前置核验项目目录、Python 解释器与实际鉴权配置，防止环境污染与未授权写入。
  * **计划门禁**：对齐预期用例数与测试覆盖范围后方可动笔。
* 📊 **单入口条件报告体系**：
  * **Allure 可用**：只生成官方静态入口 `allure-report/index.html`。
  * **Allure 不可用**：只由内置 Python 生成器生成 `allure-report/report.html`。
  * 两个报告入口互斥，且不会自动启动服务或浏览器。
* 📐 **9 维度工业级用例覆盖**：涵盖 正向功能、数据完整性、认证鉴权、参数校验、边界值分析、业务逻辑规则、安全性注入防御、CRUD 链式场景、统一错误响应格式。
* 🔄 **闭环自愈调优（最多 5 轮）**：自动分析失败、修正用例代码，并依据契约与复现证据记录接口差异，不以重试次数直接判定服务端 Bug。
* ⚡ **本地与云端模型全适配（Local & Cloud LLMs Friendly）**：得益于模块化按需加载（Progressive Disclosure）与确定性的代码模板，大幅降低了模型的注意力消耗与幻觉率。不仅在顶级商业模型（Claude 3.5/3.7、GPT-4o、Gemini）上表现拔群，在本地开源小模型（如 Qwen 2.5-Coder、DeepSeek-Coder、Llama 3 等通过 Ollama / vLLM 驱动）下同样能稳定输出严谨用例并闭环自愈。
* 📦 **开箱即用的一键运行脚本**：检测当前系统后只交付对应的一份：macOS/Linux 为 `run.sh`，Windows 为 `run.bat`。

---

## 📁 项目目录结构

```text
api-qa-skill/
├── SKILL.md                     # Agent 入口文件（前置路由、红线规约、环境规范）
├── README.md                    # 项目说明文档 (English)
├── README_zh.md                 # 项目说明文档 (简体中文)
├── LICENSE                      # Apache-2.0 开源协议
├── _templates/
│   └── report_generator.py      # 内置独立单文件 HTML 回退生成器
└── reference/
    ├── implementation.md        # 核心框架代码模板（conftest.py / request_helper.py 等）
    ├── test-design.md           # 9 维度用例设计规范与契约断言指南
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

## 🛠️ 安装与通用使用方法

本项目设计为**高度通用、模型无关（Model-Agnostic）的 Agent 规范资产**。无论你使用的是终端命令行 Agent、AI 编程 IDE、自主编程扩展，还是普通网页端大模型，都可以无缝运行。

### 1. 快速获取
将仓库克隆到本地：
```bash
git clone https://github.com/kongbai26/api-qa-skill.git
```

### 2. 通用交互提示词（复制即用）
在任何 AI Agent 或对话框中直接发送以下提示词，将 `[...]` 中的内容替换为你的实际信息（没有的项直接写“无”即可）：

```text
请阅读并严格遵循 `./api-qa-skill/SKILL.md` 的工程规约，为以下接口设计并生成一套生产级自动化测试工程：

- 测试工程保存目录：[可选；不填时默认 ~/Desktop/<service>-api-qa-skill]
- API 基地址：[你的 API 服务基准地址，例如 https://api.example.com]
- 接口定义文档：[粘贴你的 Swagger / OpenAPI / Markdown / 接口清单]
- 认证鉴权信息：[例如 Bearer Token / API Key / 登录账号密码；没有或无需认证直接写“无”]
```

---

### 3. 主流 AI 工具生态集成速查

| 工具类别 | 代表平台 | 推荐集成与使用方式 |
| :--- | :--- | :--- |
| **Agent CLI / 终端助手** | **Claude Code**<br>**Antigravity (AGY)**<br>**Aider / Goose / OpenCode** | 克隆至项目根目录或全局技能目录：<br>• **Antigravity**: `git clone https://github.com/kongbai26/api-qa-skill.git ~/.gemini/antigravity-cli/skills/api-qa-skill`<br>• **Claude Code**: 在 `CLAUDE.md` 中增加 `参考 ./api-qa-skill/SKILL.md 执行接口自动化测试`<br>• **Aider / Goose**: 启动时传入参数 `--message "阅读 ./api-qa-skill/SKILL.md 并执行..."` |
| **AI 原生 IDE / 编辑器** | **Cursor**<br>**Windsurf**<br>**GitHub Copilot (VS Code)** | • **Cursor**: 在 `.cursor/rules/api-qa.mdc` 或 Composer 中通过 `@api-qa-skill/SKILL.md` 引用<br>• **Windsurf**: 在 `.windsurfrules` 中引入规约文件<br>• **Copilot**: 在对话中输入 `@workspace` 并引用 `./api-qa-skill/SKILL.md` |
| **自主编程插件** | **Cline / Roo Code**<br>**Continue.dev** | 放入项目目录。在 Custom Instructions / 规则中配置：<br>`"当需要生成或维护 API 自动化测试时，必须严格阅读并执行 ./api-qa-skill/SKILL.md"` |
| **网页端 / API 大模型** | **ChatGPT / Claude.ai**<br>**DeepSeek / Gemini / Kimi** | 直接将 `SKILL.md` 作为文件附件上传或填入系统提示词。提供接口文档，大模型即可作为高级 QA 架构师输出全套用例设计与测试脚本。 |
| **独立工程脚手架** | **QA 工程师 / CI/CD 流水线** | 无需任何 AI Agent。直接复用 `_templates/report_generator.py` 与 `reference/implementation.md` 作为现代 pytest + Allure 自动化测试项目的标准工程骨架。 |

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
│   ├── request_helper.py    # 封装了 Allure 步骤记录与可配置鉴权注入的请求助手
│   └── report_generator.py  # 始终交付的内置单文件回退生成器
├── conftest.py              # 全局 Fixture（base_url, auth_session, 日志钩子等）
├── pytest.ini               # Pytest 与 Allure 标准配置
├── requirements.txt         # 项目所需依赖
├── .env                     # API 基础路径与密钥配置
├── run.sh 或 run.bat        # 只交付与检测到的 OS 对应的一份
├── MEMORY.md                # 用户可见的强制项目文档，不得以 Agent 记忆替代
├── docs/test_cases.md       # （完整流程产出）标准化用例设计文档
└── allure-report/           # 最终只保留一个报告入口
    └── index.html           # Allure 可用；否则改为生成 report.html
```

---

## 📄 开源许可证

本项目基于 [Apache-2.0 License](LICENSE) 开源。欢迎提 Issue 与 Pull Request！
