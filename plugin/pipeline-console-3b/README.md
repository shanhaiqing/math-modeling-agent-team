# @local/pipeline-console-3b

Phase 3b Pipeline Console for the DSH Web UI: run view + gate actions + figure feedback.

## What it does

- Sidebar panel icon **Pipeline** → central panel **pipeline**.
- Lists local runs under `<repoRoot>/runs` that contain `run_state.json`.
- Shows status/stage/gate/next action, checks, rework, review/method summary,
  artifact links, figure thumbnails, and the Kernel gate packet.
- **Gate actions**: approve / fix / rollback / return_modeling / return_figures /
  return_writing / proceed / stop / deliver, with a required reason, optional
  `scope` and `root_cause`. Writes go through `tools/pipeline_kernel.py gate`,
  not direct `run_state.json` edits.
- **Figure feedback**: click **Select area** on a figure, drag a rectangle on the
  image, write what should change, and send. The Host appends a record to
  `<run>/decision_logs/figure_feedback.json` for the Figures agent to consume.
  This is not a direct pixel/vector editor; see `system/lessons/figure-editor-design.md`.

## Host API

Same-origin routes:

- `GET /pipeline-console/runs`
- `GET /pipeline-console/detail?run=<id>`
- `GET /pipeline-console/file?run=<id>&path=<relative>`
- `POST /pipeline-console/gate`
- `POST /pipeline-console/figure-feedback`

File reads are confined to the run root; path traversal is rejected. Gate
requests are validated by the Kernel; a missing reason/precondition returns an
error and does not change state.

## Install

```text
plugin_manager action=install_bundle target=C:/Users/35399/Desktop/数模B题专家团/plugin/pipeline-console-3b
```

The old `@local/pipeline-console` was disabled; the new bundle keeps the same
sidebar/main ids (`pipeline`), so there is still one Pipeline icon.

## Verification limits

Host routes, state transitions, slot registration and feedback file writes can be
verified programmatically. Visual rendering still needs a browser check; the
component is not proven by registration alone.
