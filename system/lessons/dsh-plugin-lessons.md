# DSH Host 插件两次翻车记录（2026-10-19）

> 用途：把“插件怎么写、怎么验证、怎么装”的经验沉淀下来，避免下一次重蹈覆辙。
> 这不是活流水线规则；现行 `AGENTS.md` 未因此修改。

## 一句话结论

**插件能启动 ≠ 工具能被模型调用。** 两次问题分别发生在“启动注册”和“API 工具 schema”两个不同层面；必须两层都验证。

## 第一次：`ctx.effect` 用法错误

- 写法：`ctx.effect(() => ctx.tools.register(tool))`。
- 问题：`ctx.effect` 是 generator-style 的收尾契约（shipped 插件写 `ctx.effect(function* () { yield ... }, "description")`），不是“普通函数返回 disposer”。激活时抛错，harness 起不来。
- 修正：工具直接 `ctx.tools.register(tool)`，与 `dsh-tool-schedule` 等 shipped 插件一致；不要用 `ctx.effect` 注册工具。
- 教训：**先看 shipped 插件怎么写，再写自己的。**

## 第二次：`parameters` 的 schema 形状错误

- 写法：`parameters: { project_root: { type: 'string', required: true }, ... }`（简写 DSL）。
- 问题：这种简写只有经过 `defineTool()` 转换才能注册。我们是**直接** `ctx.tools.register(rawTool)`，DSH 在把工具 schema 发给模型 API 时要求标准 JSON Schema：
  ```js
  parameters: {
    type: 'object',
    properties: { project_root: { type: 'string', description: '...' } },
    required: ['project_root'],
  }
  ```
  简写直接注册会在 API 端触发 `INVALID_REQUEST` / `type: null` 一类错误。
- 修正：Trae 把 `index.js` 里 6 个工具的 `parameters` 全部改成标准 JSON Schema；描述、执行逻辑、Python 内核调用未动。
- 教训：**要么用 `defineTool` + 简写；要么直接 `register` + 标准 JSON Schema。不要混。**

## 正确的最小写法

```js
export const inject = ['tools']

export const name = 'my-plugin'

export function apply(ctx, config = {}) {
  ctx.tools.register({
    name: 'pipeline_status',
    description: 'Read the pipeline run state.',
    parameters: {
      type: 'object',
      properties: {
        project_root: { type: 'string', description: 'Absolute run root.' },
        view: { type: 'string', enum: ['full', 'brief', 'gate'], description: 'Projection.' },
      },
      required: ['project_root'],
    },
    output: {
      schema: { type: 'object' },
      render: (_args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }],
    },
    async execute(args) {
      // call the Python kernel / any service
    },
  })
}
```

## 验证清单（以后按顺序做）

1. `node --check index.js` —— 语法。
2. `node plugin/modeling-pipeline/test-apply.mjs` —— 离线注册 + 一次真实工具执行（mock ctx，不加载 DSH）。
3. 在**隔离 profile** 里启动一次（例如 `plugin-test`），确认没有插件激活告警；headless 可能因账号/API key 停在别处，但不应出现插件激活失败。
4. `plugin_manager list_plugins` —— 目标行 `fiberPhase: active`，不是 `failed/pending`。
5. `cordis_inspect_query Tool.listTools` —— 6 个工具都在，且每个 `parameters` 是 `{type:'object', properties, required}`。
6. 用一次**只读**工具（`pipeline_status`）对测试 run 做端到端调用。
7. 以上都过，才算“装上并能用”。

## 协作纪律

- **同一时间只让一个 AI 改 `index.js`**；另一个 AI 要改，先交接。
- 改插件前备份 profile 的 `package.json` / `cordis.patch.yml`；本次备份在 `C:\Users\35399\.dsh\backups\desktop-plugin-install-20261019-143434`。
- 先在隔离 profile 装，再考虑 live profile；隔离 profile 是 `C:\Users\35399\.dsh\profiles\plugin-test`。
- `submit --no-checks` 只用于测试，**永远不要**在真实运行里用。
- 插件只是“方向盘按钮”；Python CLI 是保底接口，插件坏了不影响干活。

## 当前状态（2026-10-19 15:10 左右）

- `@local/modeling-pipeline`：`enabled: true`，`fiberPhase: active`。
- `Tool.listTools` 可见 6 个工具：`pipeline_status`、`pipeline_start`、`pipeline_submit`、`pipeline_gate`、`pipeline_freshness`、`pipeline_rework`。
- 工具 schema 已是标准 JSON Schema。
- **Phase 1.5 已完成**：live `pipeline_status` 对 `runs/plugin-test-run` 返回 `run_id=plugin-test-run`、`stage=INTAKE`、`gate=G0`；插件→Python Kernel 闭环。
- 下一步：Phase 2 真实往年题链路 + 角色技能/Team。
