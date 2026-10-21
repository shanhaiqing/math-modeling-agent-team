# @local/pipeline-console-3c

Phase 3c Pipeline Console for the DSH Web UI: run view + gate actions + figure feedback + overlay text editor.

## What it does

- Sidebar panel icon **Pipeline** → central panel **pipeline**.
- Lists local runs under `<repoRoot>/runs` that contain `run_state.json`.
- Shows status/stage/gate/next action, checks, rework, review/method summary,
  artifact links, figure thumbnails, and the Kernel gate packet.
- **Gate actions**: approve / fix / rollback / return_modeling / return_figures /
  return_writing / proceed / stop / deliver, with a required reason, optional
  `scope` and `root_cause`. Writes go through `tools/pipeline_kernel.py gate`,
  not direct `run_state.json` edits.
- **Figure feedback**: select a rectangle on a figure, write what should change,
  and send. The Host appends a record to `<run>/decision_logs/figure_feedback.json`
  for the Figures agent to consume.
- **Overlay editor**: add / select / drag / delete text boxes over a figure;
  edit text, font size, color and background; save to
  `<run>/decision_logs/figure_annotations.json`; export
  `*.annotated.png` / `*.annotated.pdf` with `tools/annotate_figure.py`.
  The original figure is never modified; annotation is an explicit overlay layer.

## Host API

Same-origin routes:

- `GET /pipeline-console/runs`
- `GET /pipeline-console/detail?run=<id>`
- `GET /pipeline-console/file?run=<id>&path=<relative>`
- `POST /pipeline-console/gate`
- `POST /pipeline-console/figure-feedback`
- `GET|POST /pipeline-console/annotations`
- `POST /pipeline-console/annotations/export`

File reads are confined to the run root; path traversal is rejected. Gate
requests are validated by the Kernel; a missing reason/precondition returns an
error and does not change state. Annotation elements are normalized to `[0,1]`
and saved as an overlay; export is a separate Python render step.

## Install

```text
plugin_manager action=install_bundle target=C:/Users/35399/Desktop/数模B题专家团/plugin/pipeline-console-3c
```

The old `@local/pipeline-console` and `@local/pipeline-console-3b` were disabled;
the new bundle keeps the same sidebar/main ids (`pipeline`), so there is still one
Pipeline icon.

## Verification limits

Host routes, state transitions, slot registration, annotation persistence and
annotated file generation can be verified programmatically. Visual rendering of
the overlay editor still needs a browser check; registration alone does not prove
the drag experience or pixel alignment.
