# 阶段五：交付

> 本阶段只确认前序产物、补齐用例文档和项目记录；不重跑测试、不重新生成报告、不实跑 runner，也不增加独立审计。

## 清单

```text
⬜ 1. 确认测试代码和 Allure 原始结果
⬜ 2. 确认唯一报告入口
⬜ 3. 确认当前 OS runner
⬜ 4. 写 docs/test_cases.md
⬜ 5. 更新 MEMORY.md 并交付
```

按顺序完成并立即打勾。五项全部 `✅` 前不能输出完成结束语。

## ① 测试代码和原始结果

确认存在：

- `tests/` 下至少一个 `test_*.py`
- `allure-results/` 下至少一个 `*-result.json`
- `conftest.py`、`pytest.ini`、`requirements.txt`、`utils/request_helper.py`

缺少测试代码时返回阶段三；缺少原始结果时返回阶段四。不能补写假结果。

## ② 唯一报告入口

按锁定分支确认：

- `ALLURE=有`：`allure-report/index.html` 存在且非空，`report.html` 不存在。
- `ALLURE=无`：`allure-report/report.html` 存在且非空，`index.html` 不存在。

只检查这两个入口，不扫描其他 HTML/Markdown，不解析报告内容。检查失败时返回阶段四按原分支处理。

## ③ 当前 OS runner

- Darwin/Linux：`run.sh` 存在；执行权限缺失时只补 `chmod +x run.sh`。
- Windows：`run.bat` 存在。

脚本存在时不重新物化、不做语法双检、不自动运行。缺失时才按阶段二的 runner 物化步骤补当前 OS 文件。

手动命令：

- Darwin/Linux：`cd "<PROJECT_DIR>" && chmod +x run.sh && ./run.sh`
- Windows：`cd /d "<PROJECT_DIR>" && call run.bat`

## ④ 用例文档

读取 `<SKILL_DIR>/reference/test-doc.md`，生成非空的 `<PROJECT_DIR>/docs/test_cases.md`。内容覆盖接口用途、前置条件、请求步骤和预期结果，不添加只为机器审计服务的占位内容。

## ⑤ 项目记录与交付

在项目 `MEMORY.md` 追加最终统计、交付物绝对路径、已确认缺陷、遗留问题和阶段五日期。确认以下文件实际存在：

- 测试代码：`tests/`
- 原始结果：`allure-results/`
- 唯一报告入口
- 当前 OS runner
- `docs/test_cases.md`
- `MEMORY.md`

全部存在后标记第⑤项，并按以下结构交付：

```text
完整流程交付清单：阶段五 5 项全部 ✅
测试结果：通过 N，失败 N，跳过 N
项目目录：<PROJECT_DIR 绝对路径>
测试代码：<实际文件>
用例文档：<PROJECT_DIR>/docs/test_cases.md
测试报告：<唯一报告入口绝对路径>
原始结果：<PROJECT_DIR>/allure-results/
运行脚本：<当前 OS runner 绝对路径>（供用户复跑）
测试状态：已执行 | 未执行；未执行时请用户运行上述手动命令
项目记录：<PROJECT_DIR>/MEMORY.md
测试完成，报告已生成；交付物已准备完毕。
```

不得列出不存在的路径，也不能把“脚本已交付”写成“脚本已实跑”。输出结束语后停止调用工具。
