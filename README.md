# api-qa-skill 🚀

[English](README.md) | [简体中文](README_zh.md)

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python: 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Framework: Pytest](https://img.shields.io/badge/framework-pytest-orange.svg)](https://docs.pytest.org/)
[![Reporting: Allure & LiteReport](https://img.shields.io/badge/reporting-Allure%20%7C%20LiteReport-yellow.svg)](https://allurereport.org/)
[![Compatible Agents](https://img.shields.io/badge/agents-Antigravity%20%7C%20Claude%20Code%20%7C%20Cursor%20%7C%20Windsurf-purple.svg)](#️-installation--usage)

> **Production-Ready API Automation Testing Skill for AI Agents**  
> An enterprise-grade, end-to-end API automated testing workflow designed for AI Coding Agents (Google Antigravity, Claude Code, Cursor, Windsurf, etc.). Powered by `pytest` + `Allure`, covering live API probing, multi-dimensional test design, self-healing debugging, and turnkey report delivery.

---

## 🌟 Key Highlights & Design Philosophy

Most testing agents fall into common traps: hallucinating API responses, writing brittle assertions that fail on harmless formatting differences, generating blocking background processes, or executing destructive actions without confirmation.

`api-qa-skill` eliminates these pitfalls with strict engineering redlines, human-in-the-loop validation, and modular stage execution:

* 🛡️ **Live Probing & Defensive Assertions**: Prohibits guessing server responses. The Agent must probe live endpoints first with `request_helper` before writing assertions. Requires fault-tolerant status code checks (e.g. `assert res.status_code in (400, 422)`) and loose type checking.
* 🚦 **Human-in-the-Loop Quality Gates**:
  * **Routing Gate**: Automatically routes to the Quick Path (≤ 5 simple endpoints) or Full Workflow (> 5 endpoints or complex business logic), preventing silent quality degradation.
  * **Environment Gate**: Verifies `<PROJECT_DIR>`, Python runtime, and authentication credentials upfront.
  * **Planning Gate**: Confirms test scope and expected case counts with the user before writing test code.
* 📊 **Zero-Dependency Dual-Track Reporting**:
  * **When Allure is installed**: Generates standard Allure static reports (`index.html`) using clean batch commands—**never** blocking terminal with background server daemons.
  * **When Allure is missing**: Uses the built-in pure Python **LiteReport Generator** to output a beautiful, standalone interactive HTML dashboard (`report.html`) with zero Java / Node.js dependencies.
* 📐 **9-Dimension Industrial Test Coverage**: Functional happy paths, data integrity, authentication/authorization, parameter validation, boundary values, business rules, security/injection defense, CRUD chaining, and unified error format.
* 🔄 **Self-Healing Debug Loop (Up to 5 Rounds)**：Automatically runs the test suite, parses tracebacks, categorizes failures into assertion adjustments vs. actual server defects, and fixes code iteratively until clean pass.
* 📦 **Turnkey Cross-Platform Execution**: Delivers pre-configured `run.sh` (macOS/Linux) and `run.bat` (Windows) scripts with automated environment verification for one-click reproducibility.

---

## 📁 Repository Structure

```text
api-qa-skill/
├── SKILL.md                     # Agent skill entrypoint (router, redlines, environment rules)
├── README.md                    # English documentation
├── README_zh.md                 # Chinese documentation
├── LICENSE                      # MIT License
├── _templates/
│   └── report_generator.py      # Zero-dependency LiteReport standalone HTML generator
└── reference/
    ├── implementation.md        # Core framework code templates (conftest.py, request_helper.py, etc.)
    ├── test-design.md           # 9-dimension test design specifications & assertion guide
    ├── test-doc.md              # Standardized test case specification format (docs/test_cases.md)
    ├── run-scripts.md           # Cross-platform runner script templates (run.sh / run.bat)
    └── stages/                  # Progressive workflow stages (prevents LLM context overflow)
        ├── stage-full-setup.md  # Full Workflow Stage 1: Information Gathering & Environment Audit
        ├── stage-2-setup.md     # Full Workflow Stage 2: Framework Setup & Endpoint Probing
        ├── stage-3-write.md     # Full Workflow Stage 3: 9-Dimension Test Generation
        ├── stage-full-test.md   # Full Workflow Stage 4: Test Execution & Self-Healing Loop
        ├── stage-5-deliver.md   # Full Workflow Stage 5: Verification & Asset Delivery
        ├── stage-quick-setup.md # Quick Path Stage 1: Rapid Environment Setup
        └── stage-quick.md       # Quick Path Stage 2: Combined Probing, Coding & Reporting
```

---

## 🛠️ Installation & Usage

### 1. In Google Antigravity (AGY)
Place the skill directory into your AGY skills path:
```bash
# Global installation (recommended)
cp -r api-qa-skill ~/.gemini/antigravity-cli/skills/

# Or workspace-scoped installation
mkdir -p .agent/skills/
cp -r api-qa-skill .agent/skills/
```
Once installed, simply prompt your Agent with your API documentation or endpoints list. The Agent will automatically activate the skill and prompt the routing decision.

### 2. In Claude Code
Reference this skill in your project's `CLAUDE.md`, or prompt directly:
```text
Please read and strictly follow the testing protocol in ./api-qa-skill/SKILL.md to build the API test suite.
```

### 3. In Cursor / Windsurf
Add `api-qa-skill/SKILL.md` to your workspace Rules or add the skill path into your composer prompt context.

---

## 🔄 Dual-Track Workflow Comparison

| Feature | Full Workflow | Quick Path |
| :--- | :--- | :--- |
| **Recommended For** | > 5 endpoints, or core business domains (payment, auth, multi-step workflows) | ≤ 5 endpoints and simple CRUD operations |
| **Stage Progression** | 5 discrete stages separated by strict verification gates | 2 consolidated stages for fast execution |
| **Case Volume** | GET ≥ 8, POST ≥ 15, avg. 15–20 cases per endpoint | 3–5 core cases per endpoint (total ≥ endpoint count × 3) |
| **Coverage Scope** | All 9 industrial dimensions (boundary, concurrency, security, chaining) | 3 core dimensions (happy path, auth, boundary errors) |
| **Deliverables** | Test suite + Allure/LiteReport + Test Specs + API Discrepancy Log | Test suite + Allure/LiteReport + Runner scripts + MEMORY Log |

---

## 📑 Deliverable Specifications

Upon completion, the Agent outputs a fully standalone, production-ready test repository under `<PROJECT_DIR>`:

```text
<PROJECT_DIR>/
├── tests/
│   └── test_*.py            # Clean, modular pytest test cases with Allure decorators
├── utils/
│   ├── request_helper.py    # Request wrapper with step logging & Bearer token injection
│   └── report_generator.py  # (When Allure is absent) Standalone HTML report generator
├── conftest.py              # Global fixtures (base_url, auth_session, cleanup hooks)
├── pytest.ini               # Pytest markers and Allure configurations
├── requirements.txt         # Minimal, pinned test dependencies
├── .env                     # API base URL and token secrets (git-ignored)
├── run.sh / run.bat         # Cross-platform one-click execution & report generation scripts
├── MEMORY.md                # Endpoint inventory, API spec discrepancies, self-healing log
├── docs/test_cases.md       # (Full Workflow) Comprehensive test design documentation
└── allure-report/           # Final generated report
    ├── index.html           # (When Allure is present) Official Allure static report
    └── report.html          # (When Allure is absent) LiteReport single-file standalone dashboard
```

---

## 🤝 Contributing & Guidelines

Contributions are welcome! If you have suggestions for improving test generation strategies, defensive assertions, or supporting additional agent environments, please open an issue or submit a PR.

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/amazing-feature`)
3. Commit your Changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the Branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the [Apache-2.0 License](LICENSE). Feel free to use, modify, and integrate it into your automated workflows.
