#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_pipeline_manifest.py — 产物齐备性机查（编排器阶段转换前置）

把"产物契约"从散文执行转为确定性机器检查：
  [契约] papers/产物注册表.md（唯一注册源，本脚本解析其表格，表结构不得改动）
  [执行] rules/orchestrator.md 第 4 节（阶段转换协议：ERROR 未清零不得推进）
  [对账] 注册表"历史漂移对账"节（契约外编号/双份/误命名 检测规则来源）
  [防跳过] method_card_matching.md 卡片编号全覆盖校验（卡片集动态取自 papers/优化方法卡片/）

用法：
  python check_pipeline_manifest.py --project-root <项目根> --stage <modeling|writing|review|calibration|retro|approval> [--mode competition|training] [--report]
  --report 时把结果写入 <项目根>/manifest_check_report.json
"""
import argparse, json, re, sys
from pathlib import Path

STAGE_ORDER = ["modeling", "writing", "review", "calibration", "retro", "approval", "compliance"]

# 契约外产物检测（历史漂移对账节，一处定义）
FORBIDDEN_PATTERNS = [
    (r"^handoff_notes_([5-9]|\d{2,})\.md$", "契约外 handoff_notes 编号（注册表仅 1-4 号）"),
    (r"^fix_round([4-9]|\d{2,})\.md$", "契约外 fix_round 编号（仅 R1-R3；用户裁决清理应命名 user_cleanup.md）"),
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

def check_method_card_coverage(root: Path, card_dir: Path):
    """method_card_matching.md 卡片编号全覆盖校验（防早停/跳卡）。

    卡片集动态取自卡片目录（NN_名称.md），日志中每张卡片须被逐一点名：
    新格式匹配矩阵表格行（| 01 | …）或旧格式"卡片 01"表述均可。
    """
    log = root / "decision_logs" / "method_card_matching.md"
    if not log.is_file():
        return  # 文件缺失已由注册表齐备性检查报告，此处不重复
    if not card_dir.is_dir():
        warn("method_card_matching", f"卡片目录不存在，无法校验全覆盖：{card_dir}")
        return
    card_ids = []
    for f in sorted(card_dir.glob("*.md")):
        m = re.match(r"^(\d{2})_", f.name)
        if m:
            card_ids.append(m.group(1))
    if not card_ids:
        warn("method_card_matching", "卡片目录未找到编号卡片，无法校验全覆盖")
        return
    text = log.read_text(encoding="utf-8", errors="replace")
    missing = []
    for cid in card_ids:
        hit_table = re.search(rf"^\|\s*{cid}(?![0-9])", text, re.M)      # 新格式：矩阵表格行
        hit_legacy = re.search(rf"卡片\s*{cid}(?![0-9])", text)           # 旧格式：卡片 NN 表述
        if not (hit_table or hit_legacy):
            missing.append(cid)
    if missing:
        err("method_card_matching",
            f"卡片编号未逐一点名（疑似跳卡/早停）：{', '.join(missing)}——匹配矩阵须每张卡片一行")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--stage", required=True, choices=STAGE_ORDER)
    ap.add_argument("--mode", default="training", choices=["competition", "training"])
    ap.add_argument("--registry", default=str(Path(__file__).resolve().parent.parent / "papers" / "产物注册表.md"))
    ap.add_argument("--card-dir", default=str(Path(__file__).resolve().parent.parent / "papers" / "优化方法卡片"))
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
    compile_mode = None
    ps = root / "pipeline_state.json"
    if ps.is_file():
        try:
            compile_mode = json.loads(ps.read_text(encoding="utf-8-sig")).get("compile_mode")
        except Exception:
            pass

    checked = 0
    for r in rows:
        if STAGE_ORDER.index(r["stage"]) > stage_idx:
            continue  # 未到该产物的产出阶段
        req = r["required"]
        if "可选" in req:
            continue  # 可选产物（WARN 级辅助）不参与齐备性拦截
        if "训练" in req and args.mode == "competition":
            continue  # 比赛模式跳过训练模式必填项
        checked += 1
        p = root / r["path"].rstrip("/")
        exists = p.exists()
        if r["name"] == "figures 目录":
            # 图表目录：存在且 PDF ≥6
            pdf_count = len(list(p.glob("*.pdf"))) if p.is_dir() else 0
            if not p.is_dir() or pdf_count < 6:
                err(r["name"], f"figures 目录缺失或 PDF 数量不足（{pdf_count}/6）")
            continue
        if not exists:
            if r["name"] == "paper.pdf" and compile_mode == "external":
                if stage_idx >= STAGE_ORDER.index("compliance"):
                    err(r["name"], "编译降级模式（compile_mode=external）下交付前 paper.pdf 仍缺失——用户外部编译回传件不齐（orchestrator §4 编译降级专项条款）")
                else:
                    warn(r["name"], "编译降级模式（compile_mode=external）：paper.pdf 缓由用户外部编译回传（.aux/.log/.pdf 三件齐备）")
            elif "必填" in req or "训练" in req:
                err(r["name"], f"缺失必填产物：{r['path']}")
            else:
                warn(r["name"], f"条件产物缺失（请人工确认条件是否触发）：{r['path']}")

    # 卡片编号全覆盖校验（防早停/跳卡）：modeling 及之后阶段执行
    if stage_idx >= STAGE_ORDER.index("modeling"):
        check_method_card_coverage(root, Path(args.card_dir))

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
