#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_machine_checks.py — 机查执行证据链对账（编排器阶段转换后置）

[契约] rules/orchestrator.md §3（machine_checks 字段）+ §4（阶段转换机查表）
       papers/产物注册表.md（生产者="编排器（机查）"的行 = 应产出报告集）
[背景] 双模型评审共识 C7 / 场景 F：machine_checks 由编排器自己填写，
       "登记了"与"执行了"之间无第三方验证；漏跑或虚报 PASS 均可过关。
       本脚本用报告文件的客观状态反查登记，把自证改为他证。
[分工] check_pipeline_manifest.py 只查"报告文件在不在"；本脚本查
       "登记与执行是否一致"——虚报 PASS、漏登记、陈旧报告三类，为增量价值。

检查项：
  1. 虚报通过：machine_checks 登记 result=pass/PASS，但报告文件内 error_count>0 → ERROR
  2. 报告缺失：登记的 report_path 文件不存在 → ERROR
  3. 漏登记：注册表要求本机查报告存在于该阶段，但 machine_checks 未登记 → ERROR
  4. 陈旧报告：报告 mtime 早于本阶段 stage_timestamps.start → ERROR（疑为上轮遗留）
  5. 登记结构：machine_checks 条目缺 time/result/report_path 任一 → WARN

用法：
  python check_machine_checks.py <项目根> --stage <modeling|writing|review|
             calibration|retro|approval|compliance> [--mode competition|training]
             [--report 路径]
  **默认仅终端输出，不落盘**——本报告不注册入产物注册表，避免与 manifest 形成
  循环依赖（manifest 校验注册表内报告，本脚本校验 manifest 的登记）。
  仅在需要留证时用 --report 显式写入，建议路径 machine_checks_audit_report.json。

退出码: 0 = 无 ERROR；1 = 存在 ERROR；2 = 用法错误
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# 与 check_pipeline_manifest.py 同源，修订须同步（含 compliance，2026-09 批次1 追加）
STAGE_ORDER = ["modeling", "writing", "review", "calibration", "retro", "approval", "compliance"]

# manifest 自身报告不参与本脚本对账：本脚本在其之后执行，且它已由 manifest 自查
SELF_EXEMPT = {"manifest_check_report.json", "machine_checks_audit_report.json"}

errors, warns = [], []


def err(item, msg):
    errors.append({"item": item, "msg": msg})


def warn(item, msg):
    warns.append({"item": item, "msg": msg})


def parse_registry_reports(registry_path: Path):
    """从注册表解析生产者含"机查"的行 → [{name, path, stage, required}]"""
    rows = []
    if not registry_path.is_file():
        return rows
    for line in registry_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 6 or cells[0] == "名称" or set(cells[0]) <= set("-: "):
            continue
        producer = cells[2]
        if "机查" not in producer:
            continue
        rows.append({"name": cells[0],
                     "path": cells[1].split("（")[0].strip().strip("`"),
                     "stage": cells[4], "required": cells[5]})
    return rows


def parse_time(val):
    """尽力解析时间字符串为 datetime；失败返回 None。"""
    if not val:
        return None
    if isinstance(val, (int, float)):
        try:
            return datetime.fromtimestamp(val)
        except Exception:
            return None
    s = str(val).strip().replace("Z", "+00:00")
    for fmt in (None, "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.fromisoformat(s) if fmt is None else datetime.strptime(s, fmt)
        except Exception:
            continue
    return None


def read_json(path: Path):
    """读取 JSON，容忍 UTF-8 BOM（Windows PowerShell 5.1 写文件默认带 BOM）。"""
    return json.loads(path.read_text(encoding="utf-8-sig"))


def report_error_count(path: Path):
    """读取报告文件内的 ERROR 计数；无法识别时返回 None。

    B/C 两系统的机查报告存在两种字段约定，必须都支持，否则虚报通过检测失效：
      约定一（扁平）：顶层 error_count / error / errors / err
        —— manifest_check_report、code_hygiene_report、workspace_hygiene_report
      约定二（嵌套）：summary.ERROR（值为整数）
        —— contract_check_report、modeling_artifacts_report
    2026-09-10 修复：原实现只认约定一，导致契约报告与建模产物报告的内部
    ERROR 无法被读取，"登记 pass 但报告内有 ERROR"这一虚报情形检测不到。
    """
    try:
        data = read_json(path)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None

    # 约定二优先判定：嵌套 summary.ERROR / summary.error
    summary = data.get("summary")
    if isinstance(summary, dict):
        for key in ("ERROR", "error", "error_count", "err"):
            if key in summary:
                v = summary[key]
                if isinstance(v, bool):
                    continue
                if isinstance(v, (int, float)):
                    return int(v)
                if isinstance(v, list):
                    return len(v)

    # 约定一：扁平字段
    for key in ("error_count", "error", "errors", "err"):
        if key in data:
            v = data[key]
            if isinstance(v, bool):
                continue
            if isinstance(v, (int, float)):
                return int(v)
            if isinstance(v, list):
                return len(v)
    return None


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("project_root")
    ap.add_argument("--stage", required=True, choices=STAGE_ORDER)
    ap.add_argument("--mode", default="competition", choices=["competition", "training"])
    ap.add_argument("--registry", default=None)
    ap.add_argument("--report", default=None)
    args = ap.parse_args()

    root = Path(args.project_root)
    if not root.is_dir():
        print(f"FATAL: 项目根不存在 {root}")
        sys.exit(2)

    registry = Path(args.registry) if args.registry else (
        Path(__file__).resolve().parent.parent / "papers" / "产物注册表.md")

    state_path = root / "pipeline_state.json"
    if not state_path.is_file():
        err("pipeline_state.json", "状态文件不存在，无法对账 machine_checks（HG0 应已创建）")
        print(json.dumps({"error_count": len(errors), "errors": errors}, ensure_ascii=False))
        sys.exit(1)
    try:
        state = read_json(state_path)
    except Exception as e:
        err("pipeline_state.json", f"解析失败：{e}")
        print(json.dumps({"error_count": len(errors), "errors": errors}, ensure_ascii=False))
        sys.exit(1)

    mc = state.get("machine_checks") or {}
    if not isinstance(mc, dict):
        err("machine_checks", f"字段类型应为对象，实际 {type(mc).__name__}")
        mc = {}

    stage_idx = STAGE_ORDER.index(args.stage)
    stage_start = None
    ts = (state.get("stage_timestamps") or {}).get(args.stage)
    if isinstance(ts, dict):
        stage_start = parse_time(ts.get("start"))

    # ---- 检查 5：登记结构完整性 ----
    for name, entry in mc.items():
        if not isinstance(entry, dict):
            warn(name, f"machine_checks 条目应为对象，实际 {type(entry).__name__}")
            continue
        missing = [k for k in ("time", "result", "report_path") if k not in entry]
        if missing:
            warn(name, f"登记缺字段：{', '.join(missing)}（orchestrator §3 要求三项齐全）")

    # ---- 检查 1/2：登记项 → 反查报告文件 ----
    for name, entry in mc.items():
        if not isinstance(entry, dict):
            continue
        rp = entry.get("report_path")
        result = str(entry.get("result", "")).strip().lower()
        if not rp:
            continue
        p = Path(rp) if Path(rp).is_absolute() else root / rp
        if not p.is_file():
            err(name, f"登记了报告但文件不存在：{rp}——虚报执行（orchestrator §3 自登记不可自证）")
            continue
        actual = report_error_count(p)
        if actual is None:
            warn(name, f"报告 {p.name} 无 error_count 类字段，无法核验登记的 result={result}")
        elif actual > 0 and result in ("pass", "passed", "ok", "0", "success"):
            err(name, f"虚报通过：登记 result={result}，但 {p.name} 内 error_count={actual}")

    # ---- 检查 3/4：注册表应产出报告 → 反查登记与新鲜度 ----
    for r in parse_registry_reports(registry):
        fname = Path(r["path"]).name
        if fname in SELF_EXEMPT:
            continue
        if STAGE_ORDER.index(r["stage"]) > stage_idx:
            continue
        if "可选" in r["required"]:
            continue
        if "训练" in r["required"] and args.mode == "competition":
            continue

        p = root / r["path"]
        registered = None
        for name, entry in mc.items():
            if not isinstance(entry, dict):
                continue
            rp = entry.get("report_path")
            if rp and Path(rp).name == fname:
                registered = (name, entry)
                break
        if registered is None:
            if p.is_file():
                err(r["name"], f"报告 {r['path']} 已存在但 machine_checks 未登记（漏登记）")
            else:
                err(r["name"], f"应产出的机查报告缺失且未登记：{r['path']}"
                               f"（{r['stage']} 阶段{r['required']}）")
            continue

        # 检查 4：陈旧报告
        if p.is_file() and stage_start is not None:
            mtime = datetime.fromtimestamp(p.stat().st_mtime)
            if mtime < stage_start:
                err(r["name"], f"报告 {r['path']} mtime {mtime:%Y-%m-%d %H:%M:%S} 早于"
                               f"本阶段 start {stage_start:%Y-%m-%d %H:%M:%S}——疑为上轮遗留未重跑")
    if stage_start is None:
        warn("stage_timestamps", f"未记录 {args.stage} 阶段 start 时间，陈旧报告检查（第 4 项）已跳过")

    result = {"stage": args.stage, "mode": args.mode,
              "registered_checks": len(mc),
              "error_count": len(errors), "warn_count": len(warns),
              "errors": errors, "warns": warns}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.report:
        Path(args.report).write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
        print(f"报告已写入: {args.report}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
