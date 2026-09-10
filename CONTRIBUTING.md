# Contributing

感谢你改进 `api-qa-skill`。本项目优先接受能提升本地与云端 Agent 一致性、安全性和可复现性的变更。

## 提交问题

请提供以下信息：

- 使用的 Agent/客户端与模型类型（本地或云端）；
- 操作系统、Python 版本、Allure CLI 版本或“未安装”；
- 完整流程或快速路径，以及最小可复现输入；
- 脱敏后的错误输出、退出码和预期行为。

不要提交真实 Token、Cookie、密码、API Key、生产地址中的凭据、客户数据或未脱敏的 Allure 结果。安全问题请按 [SECURITY.md](SECURITY.md) 私下报告。

## 提交变更

1. 保留 `SKILL.md` 的渐进式加载结构，不把所有 reference 内容塞回入口文件。
2. 新增或修改 shell 示例时，同时检查 macOS/Linux 与 Windows 路径、解释器和退出码语义。
3. 报告逻辑必须保持严格二选一：Allure CLI 可运行时只生成官方报告；否则只生成仓库内置的独立 HTML 报告。
4. API 契约失败不得通过放宽断言伪装为通过；未授权的真实写操作不得执行。
5. 对请求助手、结果脱敏或报告生成器的修改，至少覆盖正常、失败、损坏输入和敏感信息四类回归。

提交前至少运行：

```bash
python -m py_compile _templates/report_generator.py
git diff --check
```

同时确认 `SKILL.md` frontmatter 可被目标 Agent 客户端识别，Markdown 链接有效，`run.bat` 保持纯 ASCII，且仓库中没有真实凭据或本机绝对路径。

## Pull Request

PR 描述应说明问题、设计取舍、验证证据以及对本地/云端模型的影响。遵守 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)。
