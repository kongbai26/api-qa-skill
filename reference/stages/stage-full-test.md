# 阶段四：运行测试与修复

## 清单

```text
⬜ 1. 运行 pytest
⬜ 2. 生成锁定分支的唯一报告
⬜ 3. 分析失败
⬜ 4. 修复测试或记录 API 差异
⬜ 5. 有修改时重跑测试并更新报告（最多 5 轮）
⬜ 6. 更新 MEMORY.md
```

按顺序完成清单。没有失败或没有修改时，也要记录对应结论后打勾；不能越过该项。六项全部完成后才能进入阶段五。

## ① 运行 pytest

```text
<ENTER_PROJECT> <PYTHON_CMD> -m pytest tests/ -v --tb=short --alluredir=allure-results --clean-alluredir
```

命令不可用或被拒绝时不重试、不伪造结果或报告；保留阶段二 runner，给用户手动命令并停在本项。

依赖或导入错误先做最小修复；环境或认证错误只核对 MEMORY 的非敏感配置，并请用户确认本地凭据，不读取 `.env`。

## ② 生成唯一报告

使用阶段一锁定的分支：

- `ALLURE=有`

```text
<ENTER_PROJECT> allure generate allure-results -o allure-report --clean
```

只认 `allure-report/index.html`。

- `ALLURE=无`

```text
<ENTER_PROJECT> <PYTHON_CMD> utils/report_generator.py --input allure-results --output allure-report/report.html --clean
```

只认 `allure-report/report.html`。

禁止运行 `allure serve/open`、自动打开浏览器、调用宿主通用报告器或生成第二个报告。生成后只检查锁定入口存在且非空、另一入口不存在；不解析报告内容。

## ③ 分析失败

根据 pytest 输出分类：

- 无失败：记录“无失败”。
- 断言与已确认契约不一致：测试断言问题。
- 实际行为与已确认契约不一致且有复现证据：API 差异。
- import、fixture、请求封装等失败：测试代码问题。
- 网络、依赖或凭据不可用：环境问题，不能判为 API 缺陷。

## ④ 修复或记录

- 测试代码或断言有误：按契约最小修改。
- API 差异：保留正确断言，不迎合错误返回，把证据记入差异表。
- 无失败：记录“无需修复”。

优先只修改 `tests/`；只有 fixture、请求封装或 pytest 配置确有错误时才最小修改核心文件。禁止修改报告生成器或放宽契约。

## ⑤ 更新测试与报告

有代码修改时，重新执行步骤①，并立即按步骤②的同一分支重新生成报告；修复后的结果不能配旧报告。最多 5 轮，仍失败时按现有证据分类记录，不能仅凭重试次数判定 API 缺陷。

没有修改时确认步骤②报告对应步骤①的最新结果，记录“当前报告已是最新”。

## ⑥ 更新项目记录

在 `<PROJECT_DIR>/MEMORY.md` 追加：

- `## 结果统计`：通过、失败、跳过
- `## 修复记录`：代码修复、断言修复、API 差异和未决问题
- `### 阶段四 - YYYY-MM-DD`：实际完成、发现和决定

完成后标记第⑥项。六项全部 `✅` 后读取 `stage-5-deliver.md`。
