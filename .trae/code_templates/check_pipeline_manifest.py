#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_pipeline_manifest.py — 产物齐备性机查（编排器阶段转换前置）

把"产物契约"从散文执行转为确定性机器检查：
  [契约] papers/产物注册表.md（唯一注册源，本脚本解析其表格，表结构不得改动）
  [执行] rules/orchestrator.md 第 4 节（阶段转换协议：ERROR 未清零不得推进）
  [对账] 注册表"历史漂移对账"节（契约外编号/双份/误命名 检测规则来源）

用法：
  python check_pipeline_manifest.py --project-root <项目根> --stage <intake|modeling|method|figures|writing|review|compliance> [--report]
  --report 时把结果写入 <项目根>/manifest_check_report.json
"""
import argparse, json, re, sys
from pathlib import Path

STAGE_ORDER = ["intake", "modeling", "method", "figures", "writing", "review", "compliance"]
MIN_STATEMENT_CHARS = 200  # 须与 convert_problem.MIN_STATEMENT_CHARS 一致

# 契约外产物检测（历史漂移对账节，一处定义）
FORBIDDEN_PATTERNS = [
    (r"^handoff_notes_([4-9]|\d{2,})\.md$", "契约外 handoff_notes 编号（注册表仅 1-3 号）"),
    (r"^fix_round([3-9]|\d{2,})\.md$", "契约外 fix_round 编号（仅 R1-R2；用户裁决清理应命名 user_cleanup.md）"),
    (r"^rework_brief_\d+\.(md|json)$", "契约外 rework_brief 编号（仅 decision_logs/rework_brief.md|.json；再次回退覆盖）"),
    (r"^retrospective_(modeling|writing|review|calibration|modeling_solver|paper_writer|independent_reviewer|calibration_analyzer).*\.md$", "复盘文件误命名（应为 retro_*.md）"),
    (r"^(审批清单|final_approval_checklist)\.md$", "审批清单别名（唯一文件名：总审批清单.md）"),
    (r"^S[1-4]_reflection\.md$", "反思日志文件名大小写错误（应为 s*_reflection.md 小写）"),
]

errors, warns = [], []

def err(item, msg): errors.append({"item": item, "msg": msg})
def warn(item, msg): warns.append({"item": item, "msg": msg})

def parse_registry(registry_path: Path):
    """解析注册表第一个 markdown 表格 → [{name, path, stage, required}]"""
    rows = []
    for line in registry_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 6 or cells[0] in ("名称",) or set(cells[0]) <= set("-: "):
            continue
        name, raw_path, _prod, _cons, stage, required = cells[0], cells[1], cells[2], cells[3], cells[4], cells[5]
        # 提取纯路径（按全角括号截断中文说明）
        path = re.split(r"（", raw_path)[0].strip().strip("`")
        rows.append({"name": name, "path": path, "stage": stage, "required": required})
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--stage", required=True, choices=STAGE_ORDER)
    ap.add_argument("--mode", default="competition", choices=["competition"])
    ap.add_argument("--registry", default=str(Path(__file__).resolve().parent.parent / "papers" / "产物注册表.md"))
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    root = Path(args.project_root)
    if not root.is_dir():
        print(f"FATAL: 项目根不存在 {root}"); sys.exit(2)
    registry_path = Path(args.registry)
    if not registry_path.is_file():
        print(f"FATAL: 注册表不存在 {registry_path}"); sys.exit(2)

    stage_idx = STAGE_ORDER.index(args.stage)
    rows = parse_registry(registry_path)
    if not rows:
        print("FATAL: 注册表解析为空，检查表结构"); sys.exit(2)

    # 编译降级模式感知（2026-09 批次 4 第 24 项；prompt 条款：orchestrator §3 compile_mode 字段、§4 编译降级专项条款）
    # 建模返工：rework_brief_active（orchestrator §7）
    compile_mode = None
    rework_brief_active = False
    problem_track = None
    ps = root / "pipeline_state.json"
    if ps.is_file():
        try:
            ps_data = json.loads(ps.read_text(encoding="utf-8-sig"))
            if isinstance(ps_data, dict):
                compile_mode = ps_data.get("compile_mode")
                rework_brief_active = bool(ps_data.get("rework_brief_active"))
                problem_track = ps_data.get("problem_track")
        except Exception:
            pass

    checked = 0
    for r in rows:
        if r["stage"] not in STAGE_ORDER:
            err(r["name"], f"注册表产出阶段未知：{r['stage']}（合法：{', '.join(STAGE_ORDER)}）")
            continue
        if STAGE_ORDER.index(r["stage"]) > stage_idx:
            continue  # 未到该产物的产出阶段
        req = r["required"]
        if "可选" in req:
            continue  # 可选产物（WARN 级辅助）不参与齐备性拦截
        checked += 1
        p = root / r["path"].rstrip("/")
        exists = p.exists()
        if r["name"] == "figures 目录":
            # 图表目录：存在且 PDF ≥6
            pdf_count = len(list(p.glob("*.pdf"))) if p.is_dir() else 0
            if not p.is_dir() or pdf_count < 6:
                err(r["name"], f"figures 目录缺失或 PDF 数量不足（{pdf_count}/6）")
            continue
        if r["name"] in ("rework_brief.md", "rework_brief.json"):
            if rework_brief_active:
                if not exists:
                    err(r["name"], f"rework_brief_active 时缺失返工单：{r['path']}")
                elif r["name"] == "rework_brief.json":
                    try:
                        data = json.loads(p.read_text(encoding="utf-8-sig"))
                    except Exception as e:
                        err(r["name"], f"无法解析：{e}")
                        continue
                    if not isinstance(data, dict):
                        err(r["name"], f"根类型应为对象，实际 {type(data).__name__}")
                    else:
                        for key in ("trigger", "keep", "change", "forbidden", "must_read"):
                            if key not in data:
                                err(r["name"], f"缺 {key} 字段")
            elif not exists:
                warn(r["name"], f"条件产物缺失（请人工确认条件是否触发）：{r['path']}")
            continue
        if r["name"] == "题面.md":
            if not exists:
                err(r["name"], f"缺失必填产物：{r['path']}")
            else:
                n = len(re.sub(r"\s+", "", p.read_text(encoding="utf-8", errors="replace")))
                if n < MIN_STATEMENT_CHARS:
                    err(r["name"], f"题面转写过短（{n} 字 < {MIN_STATEMENT_CHARS}）——须原文转写而非占位")
            continue
        if "problem_track=stats" in req:
            if problem_track == "stats" and not exists:
                err(r["name"], f"stats 轨缺失泄漏机查报告：{r['path']}")
            continue
        if not exists:
            if r["name"] == "paper.pdf" and compile_mode == "external":
                if stage_idx >= STAGE_ORDER.index("compliance"):
                    err(r["name"], "编译降级模式（compile_mode=external）下交付前 paper.pdf 仍缺失——用户外部编译回传件不齐（orchestrator §4 编译降级专项条款）")
                else:
                    warn(r["name"], "编译降级模式（compile_mode=external）：paper.pdf 缓由用户外部编译回传（.aux/.log/.pdf 三件齐备）")
            elif "必填" in req:
                err(r["name"], f"缺失必填产物：{r['path']}")
            else:
                warn(r["name"], f"条件产物缺失（请人工确认条件是否触发）：{r['path']}")
            continue
        if r["name"] == "method_critique.json":
            try:
                data = json.loads(p.read_text(encoding="utf-8-sig"))
            except Exception as e:
                err(r["name"], f"无法解析：{e}")
                continue
            if not isinstance(data, dict):
                err(r["name"], f"根类型应为对象，实际 {type(data).__name__}")
                continue
            v = data.get("verdict")
            if v not in ("PASS", "PASS_WITH_NOTES", "BLOCKED"):
                err(r["name"], f"verdict 非法：{v!r}（须为 PASS / PASS_WITH_NOTES / BLOCKED）")
            tickets = data.get("tickets")
            if tickets is None:
                err(r["name"], "缺 tickets 字段（无票须为 []）")
            elif not isinstance(tickets, list):
                err(r["name"], f"tickets 应为列表，实际 {type(tickets).__name__}")
            elif len(tickets) > 2:
                err(r["name"], f"升级票 {len(tickets)} 张 > 2")
            rec = data.get("recommend")
            if not isinstance(rec, dict):
                err(r["name"], "缺 recommend 对象（须含 choice / ticket_index / reason）")
            else:
                ch = rec.get("choice")
                if ch not in ("proceed", "rollback"):
                    err(r["name"], f"recommend.choice 非法：{ch!r}（须为 proceed / rollback）")
                elif v == "BLOCKED" and ch != "rollback":
                    err(r["name"], "verdict=BLOCKED 时 recommend.choice 须为 rollback")
                elif v == "PASS" and ch != "proceed":
                    err(r["name"], "verdict=PASS 时 recommend.choice 须为 proceed")
                if not str(rec.get("reason") or "").strip():
                    err(r["name"], "recommend.reason 为空")
                if ch == "rollback" and v == "PASS_WITH_NOTES":
                    ti = rec.get("ticket_index")
                    n = len(tickets) if isinstance(tickets, list) else 0
                    if ti not in (0, 1) or (isinstance(tickets, list) and ti >= n):
                        err(r["name"], "choice=rollback 时 ticket_index 须为 0 或 1 且指向已有票")
            continue

    handoff = root / "handoff_notes_1.md"
    if problem_track in ("opt", "stats") and handoff.is_file():
        text = handoff.read_text(encoding="utf-8", errors="replace")
        if problem_track == "opt" and re.search(r"数据方法卡片(?!/\d{2}_)", text):
            err("handoff_notes_1", "opt 轨交接把数据方法卡片整夹列入必读；只允许点名 数据方法卡片/NN_文件")
        if problem_track == "stats" and re.search(r"优化方法卡片(?!/\d{2}_)", text):
            err("handoff_notes_1", "stats 轨交接把优化方法卡片整夹列入必读；只允许点名具体文件")

    # 契约外产物检测（decision_logs/ 与项目根）
    for scan_dir in [root, root / "decision_logs"]:
        if not scan_dir.is_dir():
            continue
        for f in scan_dir.iterdir():
            if not f.is_file():
                continue
            for pat, msg in FORBIDDEN_PATTERNS:
                if re.match(pat, f.name):
                    err(f.name, f"契约外/漂移产物（{scan_dir.name}）：{msg}")

    # 双份检查：术语表.json 禁止项目根与 result_bundle 双份并存
    if (root / "术语表.json").exists() and (root / "result_bundle" / "术语表.json").exists():
        err("术语表.json", "双份并存（唯一路径：result_bundle/术语表.json）")

    result = {
        "stage": args.stage, "mode": args.mode,
        "registry": str(registry_path), "checked": checked,
        "error_count": len(errors), "warn_count": len(warns),
        "errors": errors, "warns": warns,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.report:
        (root / "manifest_check_report.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.exit(1 if errors else 0)

if __name__ == "__main__":
    main()
