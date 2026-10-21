# @local/modeling-pipeline

> **Status: ACTIVE (2026-10-19).**
> The bundle is enabled in the live `desktop` profile (`fiberPhase: active`) and its
> six tools are visible in `Tool.listTools`. Two bugs were fixed on the way:
>
> 1. `ctx.effect(() => ctx.tools.register(tool))` was wrong: `ctx.effect` expects
>    a generator-style disposer contract. Tools are now registered directly.
> 2. The six `parameters` blocks used the short DSL, which is only valid through
>    `defineTool`. Direct registration requires standard JSON Schema:
>    `{ type: 'object', properties, required }`. This is the fixed shape.
>
> Full incident notes and the verification checklist are in
> [`system/lessons/dsh-plugin-lessons.md`](../../system/lessons/dsh-plugin-lessons.md).
> Live `pipeline_status` has returned `run_id=plugin-test-run`, `stage=INTAKE`,
> `gate=G0`; the plugin -> Python kernel path is closed. Coordination rule: only one
> AI edits `index.js` at a time. The Python CLI remains the fallback interface.

Host-only DSH bundle for the math-modeling pipeline kernel (Phase 1).

## What it does

Registers six tools that call `tools/pipeline_kernel.py`:

| Tool | Side effect |
|---|---|
| `pipeline_status` | read-only; `view=full/brief/gate/budget/artifacts` |
| `pipeline_start` | creates `run_state.json`; one per run |
| `pipeline_submit` | runs the stage checks and may advance; never exposes the test-only `--no-checks` |
| `pipeline_gate` | records a human decision; call only after the human answers |
| `pipeline_freshness` | records `resume` / `fresh` / `fresh_dossier` / `fresh_independent` |
| `pipeline_rework` | `validate-plan` / `run-regressions` / `route` |

## Install

> Do not install this in the live profile yet. Use an isolated profile or a copy
> of the desktop profile for activation testing.

```powershell
# from the repo root, via DSH plugin_manager
# action: install_bundle, target: <this directory>
```

The bundle config in `cordis.patch.yml` must point `repoRoot` at the checkout that owns
`system/framework.json` and `tools/pipeline_kernel.py`. The kernel is deterministic and
uses the repository's `.venv` Python by default.

## Offline test

```powershell
node plugin/modeling-pipeline/test-apply.mjs
```

It imports only `index.js` and a mock `ctx`; it does not load DSH.

## Safe activation protocol (for the future)

1. Copy the `desktop` profile to a scratch profile or use a separate `--profile`.
2. Install a no-op bundle with one trivial tool first; verify the harness boots.
3. Add the six tools incrementally: `pipeline_status` first, then `start`, `submit`,
   `gate`, `freshness`, `rework`.
4. Only after the scratch profile boots and the tools are visible, consider the live
   profile. Keep a backup of `package.json` and `cordis.patch.yml`.
5. If activation fails, disable/remove the bundle before restarting the harness.

## Scope

This is the Phase 1 Kernel MVP. It wraps the existing Python checkers and writes
`run_state.json` / `pipeline_state.json`; it does not change the live Trae pipeline and
does not install anything automatically. `pipeline_submit` never passes `--no-checks`;
that flag exists only for the kernel's own test suite.
