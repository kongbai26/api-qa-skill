# Security Policy

## Supported Version

安全修复以默认分支的最新版本为准。

## Reporting a Vulnerability

请优先使用 GitHub 仓库的 Private vulnerability reporting / Security Advisory 私下报告。若该入口不可用，请通过仓库维护者公开资料中提供的私密联系方式联系；不要在公开 Issue、讨论或 PR 中披露利用细节、真实凭据或客户数据。

报告中请包含：受影响文件与版本、最小复现步骤、可能影响，以及已经脱敏的日志。以下问题属于重点范围：

- 凭据进入终端、Allure 结果、HTML 报告、测试标题或 `MEMORY.md`；
- 项目路径或用户输入造成命令注入、路径越界或误删；
- 未经授权执行真实写操作、并发、支付或权限测试；
- 报告生成器读取 `allure-results` 目录之外的附件；
- 失败退出码被吞掉，或错误分支生成了看似成功的报告。

维护者确认问题前，请勿公开 PoC。修复发布后再协调披露时间。
