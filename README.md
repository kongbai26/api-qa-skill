# api-qa-skill 🚀

[English](README.md) | [简体中文](README_zh.md)

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python: 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Framework: Pytest](https://img.shields.io/badge/framework-pytest-orange.svg)](https://docs.pytest.org/)
[![Reporting: Allure or Built-in HTML](https://img.shields.io/badge/reporting-Allure%20%7C%20Built--in_HTML-yellow.svg)](https://allurereport.org/)
[![Compatible Agents](https://img.shields.io/badge/agents-Universal%20AI%20Agents-purple.svg)](#️-installation--usage)

> **Production-Ready API Automation Testing Skill for AI Agents**  
> An enterprise-grade, end-to-end API automated testing workflow designed for AI Coding Agents (Google Antigravity, Claude Code, Cursor, Windsurf, etc.). Powered by `pytest` + `Allure`, covering live API probing, multi-dimensional test design, self-healing debugging, and turnkey report delivery.

---

## 🌟 Key Highlights & Design Philosophy

Most testing agents fall into common traps: hallucinating API responses, writing brittle assertions that fail on harmless formatting differences, generating blocking background processes, or executing destructive actions without confirmation.

`api-qa-skill` eliminates these pitfalls with strict engineering redlines, human-in-the-loop validation, and modular stage execution:

* 🛡️ **Live Probing & Contract Assertions**: Prohibits guessing server responses. The Agent probes first to identify documentation differences, then writes assertions against the confirmed contract instead of weakening them merely to pass.
* 🚦 **Human-in-the-Loop Quality Gates**:
  * **Routing Gate**: Automatically routes to the Quick Path (≤ 5 simple endpoints) or Full Workflow (> 5 endpoints or complex business logic), preventing silent quality degradation.
  * **Environment Gate**: Verifies `<PROJECT_DIR>`, Python runtime, and authentication credentials upfront.
  * **Planning Gate**: Confirms test scope and expected case counts with the user before writing test code.
* 📊 **Single-Entry Conditional Reporting**:
  * **When Allure works**: Generates only the official static entry `allure-report/index.html`.
  * **When Allure is unavailable**: Uses the built-in Python generator to create only `allure-report/report.html`.
  * The two report entries are mutually exclusive. The runner keeps the report mode verified when the project was generated, and no server or browser is opened automatically.
  * Final delivery only confirms that the locked report entry exists and that the other entry was not generated; report correctness is established in the test/report stage, not re-audited during handoff.
* 📐 **9-Dimension Industrial Test Coverage**: Functional happy paths, data integrity, authentication/authorization, parameter validation, boundary values, business rules, security/injection defense, CRUD chaining, and unified error format.
* 🔄 **Self-Healing Debug Loop (Up to 5 Rounds)**：Automatically runs the test suite, parses tracebacks, fixes test-code issues, and records confirmed API discrepancies without classifying failures by retry count alone.
* ⚡ **Local & Cloud Model Friendly**: Stage instructions are loaded progressively, while deterministic project assets are copied by a helper without injecting their source into the model context. This removes the largest avoidable prompt payload for small local models.
* 📦 **Turnkey Cross-Platform Execution**: Detects the current OS and prepositions one matching runner: `run.sh` on macOS/Linux or `run.bat` on Windows. The runner is pinned to the confirmed report mode. Final delivery checks that the file is present; if commands were not run, the Agent gives the user the exact manual command without claiming execution.

---

## 📁 Repository Structure

```text
api-qa-skill/
├── SKILL.md                     # Agent skill entrypoint (router, redlines, environment rules)
├── README.md                    # English documentation
├── README_zh.md                 # Chinese documentation
├── LICENSE                      # Apache-2.0 License
├── _templates/
│   ├── project/                 # Core pytest project assets copied without prompt injection
│   ├── run.sh                   # macOS/Linux runner asset
│   ├── run.bat                  # Windows runner asset (ASCII)
│   └── report_generator.py      # Built-in standalone HTML fallback generator
├── scripts/
│   ├── configure_project_env.py # Credential-preserving project-local .env merger
│   └── materialize_templates.py # Branch-aware, non-overwriting asset materializer
└── reference/
    ├── implementation.md        # Read only for existing-file conflicts or dynamic auth
    ├── test-design.md           # 9-dimension test design specifications & contract assertion guide
    ├── test-doc.md              # Standardized test case specification format (docs/test_cases.md)
    ├── run-scripts.md           # Read only for runner conflicts or command-blocked prepositioning
    └── stages/                  # Progressive workflow stages (prevents LLM context overflow)
        ├── stage-full-setup.md  # Full Workflow Stage 1: Information Gathering & Environment Audit
        ├── stage-2-setup.md     # Full Workflow Stage 2: Framework Setup & Endpoint Probing
        ├── stage-3-write.md     # Full Workflow Stage 3: 9-Dimension Test Generation
        ├── stage-full-test.md   # Full Workflow Stage 4: Test Execution & Self-Healing Loop
        ├── stage-5-deliver.md   # Full Workflow Stage 5: File Confirmation & Asset Delivery
        ├── stage-quick-setup.md # Quick Path Stage 1: Rapid Environment Setup
        └── stage-quick.md       # Quick Path Stage 2: Combined Probing, Coding & Reporting
```

---

## 🛠️ Installation & Universal Usage

`api-qa-skill` is a **host-neutral, model-agnostic Agent workflow**. It works on any host that can load the complete skill directory and provide equivalent file read/write, recursive file listing, shell/Python execution, and HTTP access. Task tracking is optional because the workflow has a text-checklist fallback. A chat-only host without filesystem or execution access can review the specification, but cannot claim to have generated a runnable project.

### 1. Quick Clone
Clone this repository into your local environment:
```bash
git clone https://github.com/kongbai26/api-qa-skill.git
```

### 2. Universal Prompt Template (Copy & Run)
Paste the following prompt into any AI Agent conversation, replacing the `[...]` placeholders with your actual project details (simply write "None" for any item that does not apply):

```text
Please read and strictly follow the engineering protocol in `./api-qa-skill/SKILL.md` to design and implement a production-ready API automated test suite:

- Target Directory: [Optional; if omitted, the Agent must ask. Reply "default" to use ~/Desktop/<service>-api-qa-skill]
- API Base URL: [Your API Base URL, e.g., https://api.example.com]
- API Specification: [Paste your Swagger JSON / OpenAPI YAML / Markdown / endpoint list]
- Authentication: [Specify the authentication method and secret environment-variable names only; never paste tokens, API keys, passwords, or cookies. Write "None" if unauthenticated]
```

---

### 3. Host Capability Mapping

Do not rewrite the workflow for individual products. Bind the host's native tools to these capabilities once: locate the loaded skill directory, read and write files, enumerate a project recursively, run shell/Python commands, and make real HTTP calls. If task-list tools exist, use them; otherwise maintain the same checklist in the conversation. Keep the **entire directory** available because `SKILL.md` progressively loads stage references and invokes scripts/templates by path; uploading only `SKILL.md` is insufficient for execution.

The workflow preserves the original hard gates: the user must explicitly select the workflow, confirm the project directory, authorize or specify environment detection, and resolve the API base URL/authentication before project work begins. Host workspace metadata, CWD, and tool defaults never count as project-directory confirmation. Full workflow execution also waits for explicit plan approval, and completion remains blocked until every stage item is checked and all required delivery files are present.

---

## 🔄 Dual-Track Workflow Comparison

| Feature | Full Workflow | Quick Path |
| :--- | :--- | :--- |
| **Recommended For** | > 5 endpoints, or core business domains (payment, auth, multi-step workflows) | ≤ 5 endpoints and simple CRUD operations |
| **Stage Progression** | 5 discrete stages separated by strict verification gates | 2 consolidated stages for fast execution |
| **Case Volume** | GET ≥ 8, POST ≥ 15, avg. 15–20 cases per endpoint | 3–5 core cases per endpoint (total ≥ endpoint count × 3) |
| **Coverage Scope** | All 9 industrial dimensions (boundary, concurrency, security, chaining) | 3 core dimensions (happy path, auth, boundary errors) |
| **Deliverables** | Test suite + one HTML report + Test Specs + API Discrepancy Log | Test suite + one HTML report + Runner scripts + MEMORY Log |

---

## 📑 Deliverable Specifications

Upon completion, the Agent outputs a fully standalone, production-ready test repository under `<PROJECT_DIR>`:

```text
<PROJECT_DIR>/
├── tests/
│   └── test_*.py            # Clean, modular pytest test cases with Allure decorators
├── utils/
│   ├── request_helper.py    # Request wrapper with step logging & configurable auth injection
│   └── report_generator.py  # Delivered only when the Allure CLI is unavailable
├── conftest.py              # Global fixtures (base_url, auth_session, cleanup hooks)
├── pytest.ini               # Pytest markers and Allure configurations
├── requirements.txt         # Minimal compatible test dependencies
├── .env                     # API base URL and authentication settings/secrets (git-ignored)
├── run.sh or run.bat        # Exactly one runner matching the detected OS
├── MEMORY.md                # Required user-visible project record; never replaced by agent memory
├── docs/test_cases.md       # (Full Workflow) Comprehensive test design documentation
└── allure-report/           # Exactly one final report entry
    └── index.html           # Allure works; otherwise report.html is generated instead
```

---

## 📄 License

Distributed under the [Apache-2.0 License](LICENSE). Issues and Pull Requests are welcome!
