# @local/pipeline-console

> **Superseded by `@local/pipeline-console-3b`.** This read-only bundle is disabled;
> the active console is `plugin/pipeline-console-3b/` (gate actions + figure feedback).

Phase 3 read-only Pipeline Console for the DSH Web UI.

## What it does

- Sidebar panel icon **Pipeline** → central panel **pipeline**.
- Lists local runs under `<repoRoot>/runs` that contain `run_state.json`.
- Shows status/stage/gate/next action, checks, rework, review/method summary,
  artifact links, figure thumbnails, and the Kernel gate packet.
- Read-only MVP: no approve/return buttons; gate decisions still use
  `ask_user_question` + `pipeline_gate` in chat.

## Host API

The Host half registers same-origin JSON/file routes:

- `GET /pipeline-console/runs`
- `GET /pipeline-console/detail?run=<id>`
- `GET /pipeline-console/file?run=<id>&path=<relative>`

All file reads are confined to the run root; path traversal is rejected.

## Install

Install the bundle in the current DSH profile:

```text
plugin_manager action=install_bundle target=C:/Users/35399/Desktop/数模B题专家团/plugin/pipeline-console
```

Then open the Web UI sidebar and click **Pipeline** (or **流水线**).

## Verification limits

Registration and Host routes can be inspected programmatically. Visual
appearance remains a browser/UI check; installation or slot registration alone
does not prove the rendered panel looks correct.
