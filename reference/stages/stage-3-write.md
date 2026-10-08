# 阶段三：写用例

> 进入步骤①时完整读取 `reference/test-design.md`，不要提前读取其他 reference。

## 清单

```text
⬜ 1. 按 9 个维度编写测试用例
⬜ 2. 运行 pytest --collect-only -q
⬜ 3. 核对并补齐每个接口的数量
⬜ 4. 更新 MEMORY.md 覆盖矩阵
```

按顺序处理第一个未完成项，取得证据后立即打勾。四项全部完成后才能进入阶段四。

## ① 编写用例

读取：

```text
<SKILL_DIR>/reference/test-design.md
```

按已确认契约和阶段二的真实响应编写测试：

- 每个 GET 至少 8 个展开后的 node；每个 POST 至少 15 个；总体平均目标 15–20。
- 每个用例通过 `allure_request` 或 `AuthSession` 发真实请求，包含中文 `allure.title`、中文 docstring、中文 `expected` 和有效断言。
- 同一接口、请求步骤和断言结构一致的纯数据变体优先参数化；重复明显时才抽公共助手，具体规则见 `reference/test-design.md`。
- 按模块或测试文件批量编写，减少逐条追加和反复回读；内容较多时按接口或场景分批，已有文件只修改相关部分。全部用例完成后再进入步骤②。
- 无认证 API 不臆造 401/403；用数据完整性或业务规则补足维度。
- 动态认证先运行一个使用项目专用 fixture 的最小真实用例，取得脱敏结果后再扩展。
- 禁止空壳、`assert True`、传输层 mock、与接口无关的凑数用例，以及为通过测试而放宽契约。

## ② 收集计数

```text
<ENTER_PROJECT> <PYTHON_CMD> -m pytest tests/ --collect-only -q
```

命令不可用或被拒绝时不估算、不进入阶段四；保留阶段二的 runner，并给用户手动命令。

## ③ 核对数量

根据 collection 输出建立“方法 | 路径 | 展开后 node 数”表：

1. 参数化实例按实际 node 计数。
2. 各接口 node 数之和等于 pytest collected 总数。
3. 逐接口检查 GET ≥8、POST ≥15，不足就补。
4. 平均数未达到 15 时，只能在契约确实无法产生有效场景的情况下逐接口写明理由。

## ④ 更新项目记录

在 `<PROJECT_DIR>/MEMORY.md` 追加：

- `## 用例计数`：方法、路径、展开后 node 数及总数
- `## 覆盖矩阵`
- `### 阶段三 - YYYY-MM-DD`：实际完成、发现和决定
- 必要时的 `## 用例不足说明`

只写项目 MEMORY，不写 Agent 记忆或数据库。完成后读取 `stage-full-test.md`。
