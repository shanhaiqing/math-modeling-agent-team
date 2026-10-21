#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline_kernel.py — Phase 1 Kernel MVP（确定性状态机 + 契约 + 机查 + 预算 + 门 + 返工策略）

设计目标：
  - 唯一状态写者：run_state.json（兼容生成 pipeline_state.json）
  - 包装现有 Python 机查，不重写判据
  - 门决策绑定 artifact hash；退工写 brief / failure dossier
  - freshness: resume / fresh / fresh_dossier / fresh_independent
  - fresh_dossier: failure_dossier + rework_plan 计划门 + regression checks
  - T55: 返工完成回到最早 stale 的下游，而不是一律回 METHOD

用法（CLI）：
  python tools/pipeline_kernel.py start --project-root <root> --track opt --profile balanced --contest-profile cumcm
  python tools/pipeline_kernel.py status --project-root <root> [--view full|brief|gate|budget|artifacts]
  python tools/pipeline_kernel.py submit --project-root <root> --stage INTAKE --role lead --produced-by lead
  python tools/pipeline_kernel.py gate --project-root <root> --gate G0 --decision approve --reason "..."
  python tools/pipeline_kernel.py freshness --project-root <root> --role solver --trigger local_fix --scope local
  python tools/pipeline_kernel.py validate-rework-plan --project-root <root>
  python tools/pipeline_kernel.py run-regressions --project-root <root>
  python tools/pipeline_kernel.py route --project-root <root>
  python tools/pipeline_kernel.py check --project-root <root> --stage MODELING

测试专用：submit --no-checks（只推进状态，不跑机查；禁止用于真实运行）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SYSTEM = REPO_ROOT / "system"
FRAMEWORK_PATH = SYSTEM / "framework.json"
CHECKS_PATH = SYSTEM / "checks.json"

STAGE_ORDER = [
    "INIT", "INTAKE", "MODELING", "METHOD", "METHOD_GATE", "FIGURES", "MODEL_REVIEW",
    "WRITING", "DRAFT_REVIEW", "REVIEW", "FIX_R1", "RE_REVIEW_R1", "FIX_R2",
    "RE_REVIEW_R2", "ADJUDICATION", "COMPLIANCE", "DELIVER", "DELIVERED", "BLOCKED", "STOPPED",
]
GATE_STAGES = {"INTAKE": "G0", "METHOD_GATE": "G1", "MODEL_REVIEW": "G2", "DRAFT_REVIEW": "G3", "ADJUDICATION": "G4", "DELIVER": "G5"}
PURE_GATE_STAGES = {"METHOD_GATE", "MODEL_REVIEW", "DRAFT_REVIEW", "ADJUDICATION", "DELIVER"}
TERMINAL = {"DELIVERED", "STOPPED"}
REPAIR_SCOPE_COMPLIANCE = "compliance"


class KernelError(RuntimeError):
    pass


# ---------- generic helpers ----------

def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # noqa: BLE001
        raise KernelError(f"无法解析 JSON {path}: {exc}") from exc


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json(path: Path, data) -> None:
    atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def append_jsonl(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(data, ensure_ascii=False) + "\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_hash(path: Path) -> tuple[str | None, int | None]:
    if not path.exists():
        return None, None
    if path.is_file():
        return sha256_file(path), path.stat().st_size
    digest = hashlib.sha256()
    total = 0
    for child in sorted(path.rglob("*")):
        if child.is_file():
            rel = child.relative_to(path).as_posix()
            digest.update(rel.encode("utf-8"))
            digest.update(sha256_file(child).encode("ascii"))
            total += child.stat().st_size
    return digest.hexdigest(), total


def load_framework() -> dict:
    data = read_json(FRAMEWORK_PATH)
    if not isinstance(data, dict):
        raise KernelError("system/framework.json 缺失或非法")
    return data


def load_checks() -> dict:
    data = read_json(CHECKS_PATH)
    if not isinstance(data, dict):
        raise KernelError("system/checks.json 缺失或非法")
    return data


def stage_def(fw: dict, stage: str) -> dict:
    for item in fw.get("stages", []):
        if item.get("id") == stage:
            return item
    raise KernelError(f"未知阶段：{stage}")


def role_def(fw: dict, role: str) -> dict:
    for item in fw.get("roles", []):
        if item.get("id") == role:
            return item
    raise KernelError(f"未知角色：{role}")


def check_def(ck: dict, check_id: str) -> dict:
    for item in ck.get("checks", []):
        if item.get("id") == check_id:
            return item
    raise KernelError(f"未知检查：{check_id}")


# ---------- state ----------

def state_path(root: Path) -> Path:
    return root / "run_state.json"


def events_path(root: Path) -> Path:
    return root / "events.jsonl"


def decisions_path(root: Path) -> Path:
    return root / "gate_decisions.jsonl"


def load_state(root: Path, required=True) -> dict:
    data = read_json(state_path(root))
    if not isinstance(data, dict):
        if required:
            raise KernelError(f"run_state.json 不存在：{root}")
        return {}
    return data


def save_state(root: Path, state: dict, event: str | None = None, data: dict | None = None) -> None:
    state["updated_at"] = now_iso()
    state["events_count"] = int(state.get("events_count", 0)) + (1 if event else 0)
    write_json(state_path(root), state)
    write_compat(root, state)
    if event:
        append_jsonl(events_path(root), {"ts": now_iso(), "event": event, "stage": state.get("stage"), "data": data or {}})


def write_compat(root: Path, state: dict) -> None:
    compat = {
        "system": "B",
        "mode": "competition",
        "contest_profile": state.get("contest_profile", "cumcm"),
        "problem_track": state.get("problem_track"),
        "compile_mode": state.get("compile_mode"),
        "project_root": str(root),
        "current_stage": state.get("stage"),
        "passed_gates": state.get("passed_gates", []),
        "fix_rounds_used": state.get("fix_rounds_used", {"R1": False, "R2": False}),
        "stage_timestamps": state.get("stage_timestamps", {}),
        "machine_checks": state.get("machine_checks", {}),
        "blocked_history": state.get("blocked_history", []),
        "redline_results": state.get("redline_results", {}),
        "subagent_ids": state.get("subagent_ids", {}),
        "rework_brief_active": bool(state.get("rework", {}).get("active")),
        "stale_stages": state.get("stale_stages", []),
    }
    write_json(root / "pipeline_state.json", compat)


def close_stage(state: dict, stage: str | None = None) -> None:
    stage = stage or state.get("stage")
    ts = state.setdefault("stage_timestamps", {}).setdefault(stage, {"start": None, "end": None})
    ts["end"] = now_iso()


def open_stage(state: dict, stage: str) -> None:
    state["stage"] = stage
    state["stage_timestamps"].setdefault(stage, {"start": None, "end": None})
    state["stage_timestamps"][stage]["start"] = now_iso()
    if stage == "INTAKE":
        state["status"] = "RUNNING"
    elif stage in GATE_STAGES:
        state["status"] = "WAITING_HUMAN"
    elif stage in TERMINAL:
        state["status"] = "DELIVERED" if stage == "DELIVERED" else "STOPPED"
    else:
        state["status"] = "RUNNING"
    state["budget"]["stage_started_at"] = state["stage_timestamps"][stage]["start"]
    state["budget"]["stage_elapsed_minutes"] = 0


def transition(root: Path, state: dict, target: str, event: str, data: dict | None = None) -> dict:
    old = state.get("stage")
    close_stage(state, old)
    open_stage(state, target)
    save_state(root, state, event, {"from": old, "to": target, **(data or {})})
    return state


def refresh_artifacts(root: Path, state: dict, fw: dict) -> dict:
    artifacts = state.setdefault("artifacts", {})
    for item in fw.get("artifacts", []):
        aid = item.get("id")
        rel = item.get("path", "")
        path = root / rel.rstrip("/")
        digest, size = artifact_hash(path)
        artifacts[aid] = {
            "id": aid,
            "path": rel,
            "sha256": digest,
            "size": size,
            "stage": item.get("stage"),
            "status": "present" if digest else "missing",
            "validated_at": now_iso() if digest else None,
        }
    return artifacts


def artifact_hashes(state: dict) -> dict:
    return {aid: item.get("sha256") for aid, item in state.get("artifacts", {}).items() if item.get("sha256")}


# ---------- checks ----------

def check_when(check: dict, state: dict) -> bool:
    when = check.get("when")
    if not when:
        return True
    if not isinstance(when, dict):
        return True
    for key, value in when.items():
        if key == "track" and state.get("problem_track") != value:
            return False
        if key == "profile" and state.get("contest_profile") != value:
            return False
        if key == "mode" and value == "fallback":
            return False  # kernel mode always
        if key == "artifact":
            if not state.get("artifacts", {}).get(value, {}).get("sha256"):
                return False
        if key == "freshness" and state.get("rework", {}).get("mode") != value:
            return False
        if key == "rework":
            if value in ("true", "fresh", "local"):
                if not state.get("rework", {}).get("active"):
                    return False
            if value == "false" and state.get("rework", {}).get("active"):
                return False
    return True


def resolve_command(command: list, state: dict, root: Path) -> list:
    repo = str(REPO_ROOT)
    python = state.get("python") or str(REPO_ROOT / ".venv" / "Scripts" / "python.exe")
    if not Path(python).exists():
        python = "python"
    values = {
        "python": python,
        "repo": repo,
        "root": str(root),
        "profile": state.get("contest_profile", "cumcm"),
        "track": state.get("problem_track", "opt"),
        "year": str(state.get("contest_year", datetime.now().year)),
        "round": str(state.get("fix_round", 1)),
    }
    out = []
    for token in command:
        text = str(token)
        for key, value in values.items():
            text = text.replace("{" + key + "}", value)
        out.append(text)
    return out


def normalize_report(check: dict, root: Path, exit_code: int, stdout: str, stderr: str, duration_ms: int) -> dict:
    reports = check.get("reports") or []
    explicit_error = 0
    explicit_warn = 0
    has_explicit = False
    finding_error = 0
    finding_warn = 0
    array_error = 0
    array_warn = 0
    findings = []
    report_path = None
    report_hash = None
    for rel in reports:
        path = root / rel
        if not path.exists():
            continue
        report_path = str(path)
        report_hash = sha256_file(path)
        data = read_json(path, {})
        if not isinstance(data, dict):
            continue
        if isinstance(data.get("error_count"), int):
            explicit_error += data["error_count"]
            has_explicit = True
        if isinstance(data.get("warn_count"), int):
            explicit_warn += data["warn_count"]
            has_explicit = True
        summary = data.get("summary")
        if isinstance(summary, dict):
            for key, target in (("ERROR", "error"), ("WARN", "warn")):
                if isinstance(summary.get(key), int):
                    if target == "error":
                        explicit_error += summary[key]
                    else:
                        explicit_warn += summary[key]
                    has_explicit = True
        for finding in data.get("findings", []) if isinstance(data.get("findings"), list) else []:
            if not isinstance(finding, dict):
                continue
            level = str(finding.get("level", "")).upper()
            if level == "ERROR":
                finding_error += 1
            elif level == "WARN":
                finding_warn += 1
            findings.append(finding)
        for key in ("errors", "warns"):
            items = data.get(key)
            if isinstance(items, list):
                if key == "errors":
                    array_error += len(items)
                else:
                    array_warn += len(items)
    # Reports such as check_pipeline_manifest carry both explicit counts and
    # detail arrays. Trust the explicit counts and count the details only once.
    error_count = explicit_error if has_explicit else (finding_error + array_error)
    warn_count = explicit_warn if has_explicit else (finding_warn + array_warn)
    blocking = check.get("blocking", "ERROR")
    if exit_code != 0 and blocking == "ERROR" and error_count == 0:
        error_count = 1
    if exit_code != 0 and blocking == "WARN" and warn_count == 0:
        warn_count = 1
    status = "fail" if error_count else ("warn" if warn_count else "pass")
    if check.get("on_error") == "external_compile" and error_count:
        status = "mode_switch"
    return {
        "checker": check.get("id"),
        "stage": check.get("stage"),
        "status": status,
        "error_count": error_count,
        "warn_count": warn_count,
        "findings": findings,
        "report_path": report_path,
        "hash": report_hash,
        "duration_ms": duration_ms,
        "started_at": now_iso(),
        "finished_at": now_iso(),
        "exit_code": exit_code,
        "stdout_tail": stdout[-4000:],
        "stderr_tail": stderr[-4000:],
    }


def run_check(root: Path, state: dict, check: dict, ck: dict) -> dict:
    check_id = check.get("id")
    started = time.time()
    if check_id == "modeling_rework_plan":
        result = validate_rework_plan_internal(root)
        duration = int((time.time() - started) * 1000)
        result.update({"checker": check_id, "stage": check.get("stage"), "duration_ms": duration})
        result.setdefault("findings", [])
        return result
    command = check.get("command") or []
    if command and command[0] == "kernel":
        # Unknown internal kernel check: fail loud.
        return {
            "checker": check_id, "stage": check.get("stage"), "status": "fail", "error_count": 1,
            "warn_count": 0, "findings": [{"level": "ERROR", "rule": "kernel", "location": check_id,
                                            "message": f"未实现的 kernel check：{command}"}],
            "report_path": None, "hash": None, "duration_ms": 0, "started_at": now_iso(),
            "finished_at": now_iso(), "exit_code": 2, "stdout_tail": "", "stderr_tail": "",
        }
    cmd = resolve_command(command, state, root)
    timeout = int(check.get("timeout_seconds", 120))
    try:
        proc = subprocess.run(
            cmd, cwd=str(root), capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, shell=False,
        )
        exit_code = proc.returncode
        stdout, stderr = proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = f"TIMEOUT after {timeout}s"
    duration = int((time.time() - started) * 1000)
    log_dir = root / "logs" / "checks"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / f"{check_id}.log").write_text(
        f"COMMAND: {cmd}\nEXIT: {exit_code}\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}\n",
        encoding="utf-8",
    )
    return normalize_report(check, root, exit_code, stdout, stderr, duration)


def run_stage_checks(root: Path, state: dict, stage: str, ck: dict, fw: dict, no_checks: bool = False) -> dict:
    if no_checks:
        summary = {"stage": stage, "ok": True, "deferred": False, "error_count": 0, "warn_count": 0,
                   "results": [], "test_only": True}
        state["last_check_summary"] = {"stage": stage, "ok": True, "deferred": False,
                                       "error_count": 0, "warn_count": 0}
        write_json(root / "checks_summary.json", summary)
        return summary
    sdef = stage_def(fw, stage)
    check_ids = sdef.get("checks") or []
    checks = [check_def(ck, cid) for cid in check_ids]
    checks.sort(key=lambda c: int(c.get("order", 0)))
    results = []
    deferred = False
    for check in checks:
        if not check_when(check, state):
            continue
        if check.get("defer_on") == "external_compile" and state.get("compile_mode") == "external":
            paper_pdf = root / "paper.pdf"
            if not paper_pdf.exists():
                results.append({
                    "checker": check.get("id"), "stage": stage, "status": "deferred",
                    "error_count": 0, "warn_count": 0, "findings": [],
                    "report_path": None, "hash": None, "duration_ms": 0,
                    "started_at": now_iso(), "finished_at": now_iso(), "exit_code": None,
                    "stdout_tail": "", "stderr_tail": "",
                })
                deferred = True
                continue
        result = run_check(root, state, check, ck)
        if result.get("status") == "mode_switch":
            state["compile_mode"] = "external"
            result["status"] = "warn"
        results.append(result)
        state.setdefault("checks", {})[check.get("id")] = {
            "id": check.get("id"), "stage": stage, "status": result.get("status"),
            "error_count": result.get("error_count", 0), "warn_count": result.get("warn_count", 0),
            "report_path": result.get("report_path"), "duration_ms": result.get("duration_ms", 0),
            "started_at": result.get("started_at"), "finished_at": result.get("finished_at"),
        }
        state.setdefault("machine_checks", {})[check.get("id")] = {
            "time": now_iso(),
            "result": "pass" if result.get("status") in ("pass", "warn") else "fail",
            "report_path": result.get("report_path"),
        }
    errors = [r for r in results if r.get("status") == "fail"]
    summary = {
        "stage": stage,
        "ok": not errors and not deferred,
        "deferred": deferred,
        "error_count": sum(int(r.get("error_count", 0)) for r in results),
        "warn_count": sum(int(r.get("warn_count", 0)) for r in results),
        "results": results,
    }
    write_json(root / "checks_summary.json", summary)
    state["last_check_summary"] = {k: summary[k] for k in ("stage", "ok", "deferred", "error_count", "warn_count")}
    save_state(root, state, "checks.run", {"stage": stage, "ok": summary["ok"], "deferred": deferred})
    return summary


# ---------- review parsing ----------

def review_high_count(root: Path) -> int:
    path = root / "decision_logs" / "review_report.json"
    data = read_json(path, {})
    if not isinstance(data, dict):
        return 1
    count = data.get("high_severity_count")
    if isinstance(count, int):
        return max(count, 0)
    for key in ("high_severity", "high_severity_issues", "issues"):
        items = data.get(key)
        if isinstance(items, list):
            return len([x for x in items if isinstance(x, dict) and str(x.get("severity", "high")).lower() == "high"])
    findings = data.get("findings")
    if isinstance(findings, list):
        n = 0
        for item in findings:
            if isinstance(item, dict) and str(item.get("severity", "")).lower() == "high":
                n += 1
        if n:
            return n
    verdict = str(data.get("verdict", "")).upper()
    if verdict in ("REJECT", "BLOCKED", "FAIL"):
        return 1
    return 0


# ---------- artifact / dossier helpers ----------

def modeling_summary(root: Path) -> dict:
    fingerprint = read_json(root / "result_bundle" / "feature_fingerprint.json", {}) or {}
    plan = read_json(root / "result_bundle" / "modeling_plan.json", {}) or {}
    solution = read_json(root / "result_bundle" / "solution.json", {}) or {}
    sub_count = 0
    if isinstance(solution, dict):
        sub_count = len([k for k, v in solution.items() if isinstance(v, dict)])
    return {
        "problem_type": str(fingerprint.get("problem_type", "unknown")),
        "algorithm": str(plan.get("main_algorithm") or plan.get("algorithm") or "unknown"),
        "model_structure": str(plan.get("model_structure") or plan.get("main_model") or "unknown"),
        "data_split": str(plan.get("data_split") or plan.get("split") or "unknown"),
        "objective": str(plan.get("objective") or "unknown"),
        "subproblem_count": sub_count or 1,
        "summary": str(plan.get("summary") or "rejected approach"),
    }


def make_failure_dossier(root: Path, state: dict, gate_id: str, reason: str, root_cause: str = "unknown") -> dict:
    summary = modeling_summary(root)
    dossier = {
        "dossier_id": f"F-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}",
        "run_id": state.get("run_id"),
        "created_at": now_iso(),
        "created_by": "kernel",
        "source": f"{gate_id} return: {reason}",
        "root_cause": root_cause if root_cause in (
            "method_mismatch", "model_structure", "data_or_leakage", "numeric_or_code",
            "missing_verification", "assumption", "writing_or_compliance", "unknown",
        ) else "unknown",
        "failed_approach": {
            "summary": summary["summary"],
            "method": summary["algorithm"],
            "algorithm": summary["algorithm"],
            "assumptions": [],
        },
        "rejected_signature": {
            "problem_type": summary["problem_type"],
            "algorithm": summary["algorithm"],
            "model_structure": summary["model_structure"],
            "data_split": summary["data_split"],
            "objective": summary["objective"],
            "subproblem_count": summary["subproblem_count"],
        },
        "failure_modes": [{
            "id": "F1",
            "description": reason,
            "evidence": f"{gate_id} decision",
            "severity": "high",
            "affected_subproblems": [],
            "affected_sections": [],
        }],
        "must_not_repeat": [reason],
        "acceptance_tests": [{
            "id": "R1",
            "description": "reproduce the returned defect; replace with a real regression test",
            "command": "python -c \"import sys; sys.exit(1)\"",
            "expected": "exit 0 after the fix",
            "failure_mode_id": "F1",
        }],
        "attic_paths": ["result_bundle/solution.json"] if (root / "result_bundle" / "solution.json").exists() else ["project/"],
    }
    write_json(root / "decision_logs" / "failure_dossier.json", dossier)
    return dossier


def write_rework_brief(root: Path, state: dict, gate_id: str, reason: str, mode: str, return_to: str,
                       scope: str, ticket_index=None) -> dict:
    brief = {
        "active": True,
        "trigger": f"{gate_id}_RETURN",
        "source_gate": gate_id,
        "ticket_index": ticket_index,
        "mode": mode,
        "return_to": return_to,
        "return_scope": scope,
        "reason": reason,
        "keep": [],
        "change": [],
        "forbidden": ["do not change the method unless the brief says so", "do not write outside the declared write scope"],
        "must_read": ["赛题/题面.md", "decision_logs/rework_brief.md"],
        "created_at": now_iso(),
        "created_by": "kernel",
    }
    # For a local return, carry the METHOD critic's optional tickets into the brief
    # so the solver fixes exactly what was flagged instead of guessing.
    critique = read_json(root / "decision_logs" / "method_critique.json", {})
    tickets = critique.get("tickets") if isinstance(critique, dict) else None
    if mode == "resume" and isinstance(tickets, list) and tickets:
        brief["tickets"] = tickets
        brief["change"] = [
            t.get("alternative", "") for t in tickets
            if isinstance(t, dict) and t.get("action") == "optional"
        ]
        brief["keep"] = ["主解与结论不变；只修 tickets 点名的表/字段/验证"]
        brief["must_read"].append("decision_logs/method_critique.json")
    if mode == "fresh_dossier":
        brief["must_read"] += ["decision_logs/failure_dossier.json", "decision_logs/rework_plan.json"]
    write_json(root / "decision_logs" / "rework_brief.json", brief)
    lines = [
        "# 返工单",
        "",
        f"- 触发：{gate_id}",
        f"- 模式：`{mode}`",
        f"- 返回目标：`{return_to}`",
        f"- 范围：`{scope}`",
        f"- 原因：{reason}",
        "",
        "## 必读",
        "",
    ]
    lines += [f"- `{item}`" for item in brief["must_read"]]
    lines += [
        "",
        "## 规则",
        "",
        "- 只改 `change` 范围；`keep` 不得当新题重开。",
        "- `fresh_dossier`：先写 `rework_plan.json`，计划门通过后才能写代码。",
        "- 回归测试必须复现旧失败并证明已修。",
    ]
    atomic_write(root / "decision_logs" / "rework_brief.md", "\n".join(lines) + "\n")
    return brief


def compute_return_target(root: Path, state: dict, target_hint: str | None, gate_id: str, decision: str) -> str:
    if target_hint:
        return target_hint
    if decision == "return_figures":
        return "FIGURES"
    if decision == "return_writing":
        return "WRITING"
    if decision == "rollback":
        return "METHOD"
    # return_modeling: earliest stale downstream based on existing artifacts
    if (root / "result_bundle" / "figures").exists() and any((root / "result_bundle" / "figures").glob("*.pdf")):
        return "FIGURES"
    if (root / "paper.tex").exists():
        return "WRITING"
    if (root / "decision_logs" / "method_critique.json").exists():
        return "MODEL_REVIEW"
    return "METHOD"


def stale_for_target(target: str) -> list:
    if target in ("METHOD", "MODELING"):
        return ["METHOD", "FIGURES", "WRITING", "REVIEW"]
    if target == "FIGURES":
        return ["FIGURES", "WRITING", "REVIEW"]
    if target == "WRITING":
        return ["WRITING", "REVIEW"]
    if target in ("MODEL_REVIEW", "DRAFT_REVIEW", "ADJUDICATION"):
        return ["REVIEW"]
    return []


def clear_gates_after(state: dict, target: str) -> None:
    order = ["G0", "G1", "G2", "G3", "G4", "G5"]
    idx = {"MODELING": 0, "METHOD": 0, "FIGURES": 1, "MODEL_REVIEW": 1, "WRITING": 2,
           "DRAFT_REVIEW": 2, "REVIEW": 3, "COMPLIANCE": 3, "DELIVER": 4}.get(target, -1)
    if idx < 0:
        return
    keep = set(order[: idx + 1])
    state["passed_gates"] = [g for g in state.get("passed_gates", []) if g in keep]


# ---------- review / plan gate ----------

def validate_rework_plan_internal(root: Path) -> dict:
    started = time.time()
    findings = []
    dossier = read_json(root / "decision_logs" / "failure_dossier.json", {})
    plan = read_json(root / "decision_logs" / "rework_plan.json", {})
    if not isinstance(dossier, dict) or not dossier:
        findings.append({"level": "ERROR", "rule": "plan-gate", "location": "failure_dossier.json",
                         "message": "缺少 failure_dossier.json"})
    if not isinstance(plan, dict) or not plan:
        findings.append({"level": "ERROR", "rule": "plan-gate", "location": "rework_plan.json",
                         "message": "缺少 rework_plan.json"})
    required_plan = ["run_id", "dossier_ids", "approach", "changes", "unchanged_parts",
                     "similarity_to_rejected", "regression_checks", "risks", "budget"]
    for key in required_plan:
        if key not in plan:
            findings.append({"level": "ERROR", "rule": "plan-gate", "location": f"rework_plan.{key}",
                             "message": f"缺字段 {key}"})
    failure_modes = dossier.get("failure_modes", []) if isinstance(dossier, dict) else []
    mode_ids = {m.get("id") for m in failure_modes if isinstance(m, dict) and m.get("id")}
    changes = plan.get("changes", []) if isinstance(plan, dict) else []
    regressions = plan.get("regression_checks", []) if isinstance(plan, dict) else []
    change_ids = {c.get("failure_mode_id") for c in changes if isinstance(c, dict)}
    regression_ids = {r.get("failure_mode_id") for r in regressions if isinstance(r, dict)}
    for mid in sorted(mode_ids - change_ids):
        findings.append({"level": "ERROR", "rule": "plan-gate", "location": "changes",
                         "message": f"failure_mode {mid} 没有 countermeasure"})
    for mid in sorted(mode_ids - regression_ids):
        findings.append({"level": "ERROR", "rule": "plan-gate", "location": "regression_checks",
                         "message": f"failure_mode {mid} 没有 regression check"})
    for idx, change in enumerate(changes):
        if not isinstance(change, dict):
            continue
        for key in ("failure_mode_id", "countermeasure", "verification", "residual_risk"):
            if not str(change.get(key, "")).strip():
                findings.append({"level": "ERROR", "rule": "plan-gate", "location": f"changes[{idx}].{key}",
                                 "message": "为空"})
    for idx, reg in enumerate(regressions):
        if not isinstance(reg, dict):
            continue
        if not str(reg.get("command", "")).strip():
            findings.append({"level": "ERROR", "rule": "plan-gate", "location": f"regression_checks[{idx}].command",
                             "message": "回归命令为空"})
    similarity = plan.get("similarity_to_rejected") if isinstance(plan, dict) else {}
    if isinstance(similarity, dict):
        if similarity.get("materially_same") and not str(similarity.get("new_evidence", "")).strip():
            findings.append({"level": "ERROR", "rule": "plan-gate", "location": "similarity_to_rejected",
                             "message": "与旧方案实质相同但没有新证据"})
    budget = plan.get("budget") if isinstance(plan, dict) else {}
    if not isinstance(budget, dict) or not isinstance(budget.get("wall_minutes"), (int, float)) or budget.get("wall_minutes", 0) <= 0:
        findings.append({"level": "ERROR", "rule": "plan-gate", "location": "budget.wall_minutes",
                         "message": "预算非法"})
    errors = [f for f in findings if f["level"] == "ERROR"]
    report = {
        "checker": "modeling_rework_plan",
        "stage": "MODELING",
        "status": "fail" if errors else "pass",
        "error_count": len(errors),
        "warn_count": 0,
        "findings": findings,
        "report_path": str(root / "decision_logs" / "plan_gate_report.json"),
        "hash": None,
        "duration_ms": int((time.time() - started) * 1000),
        "started_at": now_iso(),
        "finished_at": now_iso(),
        "exit_code": 1 if errors else 0,
    }
    write_json(root / "decision_logs" / "plan_gate_report.json", report)
    return report


def run_regressions_internal(root: Path) -> dict:
    plan = read_json(root / "decision_logs" / "rework_plan.json", {})
    checks = plan.get("regression_checks", []) if isinstance(plan, dict) else []
    results = []
    errors = 0
    started = time.time()
    for item in checks:
        if not isinstance(item, dict):
            continue
        command = str(item.get("command", "")).strip()
        if not command:
            errors += 1
            results.append({"failure_mode_id": item.get("failure_mode_id"), "command": command,
                            "pass": False, "exit_code": None, "stdout": "", "stderr": "empty command"})
            continue
        try:
            proc = subprocess.run(command, cwd=str(root), capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=180, shell=True)
            ok = proc.returncode == 0
            results.append({"failure_mode_id": item.get("failure_mode_id"), "command": command,
                            "pass": ok, "exit_code": proc.returncode,
                            "stdout": (proc.stdout or "")[-2000:], "stderr": (proc.stderr or "")[-2000:]})
            if not ok:
                errors += 1
        except Exception as exc:  # noqa: BLE001
            errors += 1
            results.append({"failure_mode_id": item.get("failure_mode_id"), "command": command,
                            "pass": False, "exit_code": None, "stdout": "", "stderr": str(exc)})
    report = {
        "checker": "regression_checks",
        "stage": "MODELING",
        "status": "fail" if errors else "pass",
        "error_count": errors,
        "warn_count": 0,
        "findings": [{"level": "ERROR", "rule": "regression", "location": r.get("failure_mode_id", ""),
                      "message": f"regression failed: {r.get('command')}"} for r in results if not r.get("pass")],
        "report_path": str(root / "decision_logs" / "regression_check_report.json"),
        "hash": None,
        "duration_ms": int((time.time() - started) * 1000),
        "started_at": now_iso(),
        "finished_at": now_iso(),
        "exit_code": 1 if errors else 0,
        "results": results,
    }
    write_json(root / "decision_logs" / "regression_check_report.json", report)
    return report


# ---------- core commands ----------

def start(root: Path, track: str, profile: str, contest_profile: str, run_id: str | None = None,
          contest_year: int | None = None, force: bool = False) -> dict:
    fw = load_framework()
    root = root.resolve()
    if state_path(root).exists() and not force:
        raise KernelError(f"run_state.json 已存在：{root}（用 --force 覆盖）")
    root.mkdir(parents=True, exist_ok=True)
    for sub in ("赛题", "result_bundle", "project", "decision_logs", "logs/checks"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    run_id = run_id or f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    python = str(REPO_ROOT / ".venv" / "Scripts" / "python.exe")
    if not Path(python).exists():
        python = "python"
    state = {
        "schema_version": fw.get("schema_version", "2026-10-19"),
        "framework_version": fw.get("framework_version", "3.0.0"),
        "run_id": run_id,
        "status": "RUNNING",
        "stage": "INIT",
        "project_root": str(root),
        "contest_profile": contest_profile,
        "problem_track": track,
        "profile": profile,
        "route_version": fw.get("model_routing", {}).get("route_version", "unknown"),
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "gates": {},
        "artifacts": {},
        "checks": {},
        "budget": {
            "wall_minutes": fw.get("budgets", {}).get("run", {}).get("wall_minutes", 4320),
            "human_minutes": fw.get("budgets", {}).get("run", {}).get("human_minutes", 120),
            "token_baseline": None,
            "soft_multiplier": fw.get("budgets", {}).get("run", {}).get("soft_multiplier", 1.2),
            "hard_multiplier": fw.get("budgets", {}).get("run", {}).get("hard_multiplier", 1.5),
            "stage_started_at": now_iso(),
            "stage_elapsed_minutes": 0,
        },
        "stale_stages": [],
        "rework": {"active": False, "mode": None, "return_to": None, "brief_path": None, "counts": {}},
        "human": {"available_windows": [], "decisions": 0, "last_decision_at": None},
        "fix_rounds_used": {"R1": False, "R2": False},
        "passed_gates": [],
        "stage_timestamps": {},
        "machine_checks": {},
        "subagent_ids": {},
        "freshness_decisions": [],
        "blocked_history": [],
        "compile_mode": None,
        "contest_year": contest_year or datetime.now().year,
        "python": python,
        "events_count": 0,
        "last_check_summary": None,
    }
    open_stage(state, "INIT")
    close_stage(state, "INIT")
    open_stage(state, "INTAKE")
    state["stage_timestamps"]["INIT"] = {"start": state["stage_timestamps"]["INTAKE"]["start"], "end": now_iso()}
    refresh_artifacts(root, state, fw)
    save_state(root, state, "run.created", {"run_id": run_id, "track": track, "profile": profile})
    return state


def status(root: Path, view: str = "brief") -> dict:
    fw = load_framework()
    state = load_state(root)
    refresh_artifacts(root, state, fw)
    if view == "full":
        return state
    if view == "artifacts":
        return {"run_id": state.get("run_id"), "artifacts": state.get("artifacts")}
    if view == "budget":
        return {"run_id": state.get("run_id"), "budget": state.get("budget"),
                "stage_timestamps": state.get("stage_timestamps")}
    if view == "gate":
        gate_id = GATE_STAGES.get(state.get("stage"))
        if not gate_id:
            return {"run_id": state.get("run_id"), "stage": state.get("stage"), "gate": None,
                    "message": "当前阶段不是人工门"}
        gate = next((g for g in fw.get("gates", []) if g.get("id") == gate_id), {})
        summary = state.get("last_check_summary") or {}
        return {
            "run_id": state.get("run_id"), "stage": state.get("stage"), "gate": gate_id,
            "mode": gate.get("mode"), "timebox_minutes": gate.get("timebox_minutes"),
            "packet_sections": gate.get("packet_sections", []),
            "recommendation": "review the packet; approve only if the redlines and top risks are acceptable",
            "options": gate.get("options", []),
            "artifact_hashes": artifact_hashes(state),
            "checks": summary,
            "rework": state.get("rework", {}),
        }
    # brief
    gate_id = GATE_STAGES.get(state.get("stage"))
    summary = state.get("last_check_summary") or {}
    next_action = f"gate:{gate_id}" if gate_id else f"submit:{state.get('stage')}"
    return {
        "run_id": state.get("run_id"), "status": state.get("status"), "stage": state.get("stage"),
        "contest_profile": state.get("contest_profile"), "problem_track": state.get("problem_track"),
        "profile": state.get("profile"), "compile_mode": state.get("compile_mode"),
        "gate": gate_id, "next_action": next_action, "checks": summary,
        "rework": state.get("rework", {}), "stale_stages": state.get("stale_stages", []),
        "freshness_last": (state.get("freshness_decisions") or [None])[-1],
        "budget": state.get("budget", {}),
    }


def submit(root: Path, stage: str, role: str, produced_by: str, ck: dict, fw: dict,
           no_checks: bool = False, summary: str = "") -> dict:
    state = load_state(root)
    if state.get("stage") != stage:
        raise KernelError(f"当前阶段 {state.get('stage')} 与提交阶段 {stage} 不一致")
    sdef = stage_def(fw, stage)
    if stage in PURE_GATE_STAGES:
        raise KernelError(f"{stage} 是人工门阶段，用 gate 命令")
    if role != sdef.get("owner") and role not in sdef.get("support_roles", []):
        raise KernelError(f"角色 {role} 不是 {stage} 的 owner（{sdef.get('owner')}）")
    # fresh_dossier preconditions
    if stage == "MODELING" and state.get("rework", {}).get("active"):
        if state["rework"].get("mode") == "fresh_dossier":
            plan_gate = validate_rework_plan_internal(root)
            state.setdefault("checks", {})["modeling_rework_plan"] = {
                "id": "modeling_rework_plan", "stage": "MODELING", "status": plan_gate["status"],
                "error_count": plan_gate["error_count"], "warn_count": 0,
                "report_path": plan_gate["report_path"], "duration_ms": plan_gate["duration_ms"],
                "started_at": plan_gate["started_at"], "finished_at": plan_gate["finished_at"],
            }
            if plan_gate["status"] != "pass":
                save_state(root, state, "rework.plan_gate.fail", {"error_count": plan_gate["error_count"]})
                return {"ok": False, "stage": stage, "phase": "plan_gate", "report": plan_gate}
            reg = run_regressions_internal(root)
            if reg["status"] != "pass":
                save_state(root, state, "rework.regression.fail", {"error_count": reg["error_count"]})
                return {"ok": False, "stage": stage, "phase": "regression", "report": reg}
    check_summary = run_stage_checks(root, state, stage, ck, fw, no_checks=no_checks)
    if check_summary.get("deferred"):
        save_state(root, state, "submit.deferred", {"stage": stage})
        return {"ok": False, "deferred": True, "stage": stage, "checks": check_summary,
                "message": "外部编译未回传；保持当前阶段，不推进"}
    if not check_summary.get("ok"):
        save_state(root, state, "submit.fail", {"stage": stage, "error_count": check_summary.get("error_count")})
        return {"ok": False, "stage": stage, "checks": check_summary}
    # advance
    if stage == "INIT":
        transition(root, state, "INTAKE", "stage.advance", {"stage": stage})
    elif stage == "INTAKE":
        state["status"] = "WAITING_HUMAN"
        save_state(root, state, "submit.pass", {"stage": stage, "next": "G0"})
    elif stage == "MODELING":
        if state.get("rework", {}).get("active"):
            target = state["rework"].get("return_to") or compute_return_target(root, state, None, "G2", "return_modeling")
            state["rework"]["active"] = False
            state["rework"]["brief_path"] = None
            transition(root, state, target, "modeling.rework_done", {"return_to": target})
        else:
            transition(root, state, "METHOD", "stage.advance", {"stage": stage})
    elif stage == "METHOD":
        transition(root, state, "METHOD_GATE", "stage.advance", {"stage": stage})
    elif stage == "FIGURES":
        transition(root, state, "MODEL_REVIEW", "stage.advance", {"stage": stage})
    elif stage == "WRITING":
        if state.get("repair_scope") == REPAIR_SCOPE_COMPLIANCE:
            state.pop("repair_scope", None)
            transition(root, state, "COMPLIANCE", "compliance.repair_done", {})
        else:
            transition(root, state, "DRAFT_REVIEW", "stage.advance", {"stage": stage})
    elif stage == "REVIEW":
        high = review_high_count(root)
        if high:
            state["fix_rounds_used"]["R1"] = False
            transition(root, state, "FIX_R1", "review.high_severity", {"high": high})
        else:
            transition(root, state, "COMPLIANCE", "review.clean", {"high": 0})
    elif stage == "FIX_R1":
        state["fix_rounds_used"]["R1"] = True
        transition(root, state, "RE_REVIEW_R1", "fix.submitted", {"round": 1})
    elif stage == "RE_REVIEW_R1":
        high = review_high_count(root)
        if high and not state["fix_rounds_used"].get("R2"):
            transition(root, state, "FIX_R2", "review.high_severity", {"high": high, "round": 1})
        elif high:
            transition(root, state, "ADJUDICATION", "review.residual_high", {"high": high, "round": 1})
        else:
            transition(root, state, "COMPLIANCE", "review.clean", {"high": 0, "round": 1})
    elif stage == "FIX_R2":
        state["fix_rounds_used"]["R2"] = True
        transition(root, state, "RE_REVIEW_R2", "fix.submitted", {"round": 2})
    elif stage == "RE_REVIEW_R2":
        high = review_high_count(root)
        if high:
            transition(root, state, "ADJUDICATION", "review.residual_high", {"high": high, "round": 2})
        else:
            transition(root, state, "COMPLIANCE", "review.clean", {"high": 0, "round": 2})
    elif stage == "COMPLIANCE":
        transition(root, state, "DELIVER", "stage.advance", {"stage": stage})
    else:
        raise KernelError(f"{stage} 没有自动推进规则")
    save_state(root, state, "submit.pass", {"stage": stage, "next": state.get("stage")})
    return {"ok": True, "stage": stage, "next": state.get("stage"), "status": state.get("status"),
            "checks": state.get("last_check_summary"), "rework": state.get("rework", {})}


def gate(root: Path, gate_id: str, decision: str, reason: str, ck: dict, fw: dict,
         return_target: str | None = None, scope: str = "root", root_cause: str = "unknown") -> dict:
    state = load_state(root)
    expected_gate = GATE_STAGES.get(state.get("stage"))
    if expected_gate != gate_id:
        raise KernelError(f"当前阶段 {state.get('stage')} 对应门 {expected_gate}，不是 {gate_id}")
    gate_def = next((g for g in fw.get("gates", []) if g.get("id") == gate_id), None)
    if not gate_def:
        raise KernelError(f"未知门：{gate_id}")
    options = {o.get("id"): o.get("to") for o in gate_def.get("options", []) if isinstance(o, dict)}
    if decision not in options:
        raise KernelError(f"{gate_id} 不支持决策 {decision}；可选：{list(options)}")
    required_stage = {"G0": "INTAKE", "G1": "METHOD", "G2": "FIGURES", "G3": "WRITING", "G5": "COMPLIANCE"}.get(gate_id)
    if required_stage:
        last = state.get("last_check_summary") or {}
        if last.get("stage") != required_stage or not last.get("ok"):
            raise KernelError(f"先完成 {required_stage} 的 submit 并通过机查，才能进入 {gate_id}")
    if gate_id == "G4" and state.get("stage") != "ADJUDICATION":
        raise KernelError("G4 只能在 ADJUDICATION 阶段执行")
    refresh_artifacts(root, state, fw)
    record = {
        "gate_id": gate_id, "run_id": state.get("run_id"), "stage": state.get("stage"),
        "decision": decision, "reason": reason, "return_target": None, "return_scope": None,
        "artifact_hashes": artifact_hashes(state), "decided_by": "human", "decided_at": now_iso(),
        "timebox_met": True, "recommendation": "human decision via gate tool", "waiver_risk": None,
    }
    append_jsonl(decisions_path(root), record)
    state["human"]["decisions"] = int(state["human"].get("decisions", 0)) + 1
    state["human"]["last_decision_at"] = now_iso()
    # return decisions
    if decision in ("fix", "rollback", "return_modeling", "return_figures", "return_writing"):
        work_stage = "MODELING" if decision in ("rollback", "return_modeling") else (
            "FIGURES" if decision == "return_figures" else "WRITING"
        )
        if work_stage == "MODELING":
            downstream = compute_return_target(root, state, return_target, gate_id, decision)
        else:
            downstream = work_stage
        record["return_target"] = work_stage
        record["return_scope"] = scope
        mode = "fresh_dossier" if scope == "root" else "resume"
        write_rework_brief(root, state, gate_id, reason, mode, downstream, scope)
        if mode == "fresh_dossier":
            make_failure_dossier(root, state, gate_id, reason, root_cause)
        state["rework"] = {
            "active": True, "mode": mode, "return_to": downstream, "work_stage": work_stage,
            "brief_path": "decision_logs/rework_brief.json", "counts": state.get("rework", {}).get("counts", {}),
        }
        stale = set(stale_for_target(work_stage))
        if mode == "resume" and work_stage == "MODELING":
            stale.discard("METHOD")  # local resume does not invalidate an unchanged method
        state["stale_stages"] = sorted(set(state.get("stale_stages", [])) | stale)
        clear_gates_after(state, work_stage)
        close_stage(state, state.get("stage"))
        open_stage(state, work_stage)
        state["status"] = "RUNNING"
        save_state(root, state, "gate.return", {"gate": gate_id, "to": work_stage, "mode": mode})
        return {"ok": True, "gate": gate_id, "decision": decision, "to": work_stage, "mode": mode,
                "return_to": downstream, "rework": state["rework"], "stale_stages": state["stale_stages"]}
    if decision == "stop":
        close_stage(state, state.get("stage"))
        open_stage(state, "STOPPED")
        save_state(root, state, "gate.stop", {"gate": gate_id, "reason": reason})
        return {"ok": True, "gate": gate_id, "decision": decision, "to": "STOPPED"}
    # approval
    target = options[decision]
    state["passed_gates"] = sorted(set(state.get("passed_gates", [])) | {gate_id})
    if gate_id != "G5":
        state["rework"]["active"] = False
        state["rework"]["brief_path"] = None
    close_stage(state, state.get("stage"))
    open_stage(state, target)
    save_state(root, state, "gate.approve", {"gate": gate_id, "to": target, "decision": decision})
    return {"ok": True, "gate": gate_id, "decision": decision, "to": target, "status": state.get("status")}


def freshness(root: Path, role: str, trigger: str, scope: str, affected: int = 0,
              context_lost: bool = False, human_request: bool = False,
              child_id: str | None = None, round_no: int = 1) -> dict:
    state = load_state(root)
    if role == "solver":
        if trigger in ("initial", "initial_modeling"):
            mode, why = "fresh", "initial modeling"
        elif context_lost or human_request or scope == "root" or affected >= 2 or trigger in (
            "method_blocked", "method_verdict_BLOCKED", "model_change", "algorithm_change",
            "track_change", "data_split_change", "objective_change", "constraints_change",
        ):
            mode, why = "fresh_dossier", "root cause / context lost / multi-subproblem"
        elif scope == "local" or affected <= 1:
            mode, why = "resume", "local scoped fix"
        else:
            mode, why = "fresh_dossier", "cannot classify; conservative fresh"
    elif role == "reviewer":
        if human_request:
            mode, why = "fresh_independent", "human second opinion"
        elif context_lost or scope == "root":
            mode, why = "fresh", "root change / context lost"
        elif scope == "local" and round_no <= 1:
            mode, why = "resume", "R1 local fix; full re-read still required"
        elif round_no >= 2:
            mode, why = "fresh", "R2 / repeated round; fresh eyes"
        else:
            mode, why = "fresh", "default reviewer fresh"
    else:
        raise KernelError(f"freshness 只支持 solver/reviewer，不支持 {role}")
    decision = {
        "at": now_iso(), "role": role, "trigger": trigger, "scope": scope, "affected_subproblems": affected,
        "context_lost": context_lost, "human_request": human_request, "mode": mode, "reason": why,
        "child_id": child_id, "round": round_no,
    }
    state.setdefault("freshness_decisions", []).append(decision)
    if child_id:
        state.setdefault("subagent_ids", {})[role] = child_id
    if role == "solver" and state.get("rework", {}).get("active"):
        state["rework"]["mode"] = mode
    save_state(root, state, "freshness.decided", decision)
    return {"ok": True, "decision": decision}


def route(root: Path) -> dict:
    state = load_state(root)
    stale = state.get("stale_stages", [])
    target = None
    for candidate in ("METHOD", "FIGURES", "WRITING", "REVIEW"):
        if candidate in stale:
            target = candidate
            break
    if target is None:
        target = "COMPLIANCE"
    state.setdefault("rework", {})["return_to"] = target
    save_state(root, state, "rework.route", {"return_to": target, "stale": stale})
    return {"ok": True, "return_to": target, "stale_stages": stale}


# ---------- CLI ----------

def parse_args(argv):
    parser = argparse.ArgumentParser(description="Phase 1 modeling pipeline kernel")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("start")
    p.add_argument("--project-root", required=True)
    p.add_argument("--track", required=True, choices=["opt", "stats"])
    p.add_argument("--profile", default="balanced", choices=["quality", "balanced", "economy"])
    p.add_argument("--contest-profile", default="cumcm", choices=["cumcm", "shuwei_zh", "shuwei_en"])
    p.add_argument("--run-id", default=None)
    p.add_argument("--contest-year", type=int, default=None)
    p.add_argument("--force", action="store_true")

    p = sub.add_parser("status")
    p.add_argument("--project-root", required=True)
    p.add_argument("--view", default="brief", choices=["full", "brief", "gate", "budget", "artifacts"])

    p = sub.add_parser("submit")
    p.add_argument("--project-root", required=True)
    p.add_argument("--stage", required=True)
    p.add_argument("--role", required=True)
    p.add_argument("--produced-by", required=True)
    p.add_argument("--summary", default="")
    p.add_argument("--no-checks", action="store_true", help="TEST ONLY: skip checks and advance state")

    p = sub.add_parser("gate")
    p.add_argument("--project-root", required=True)
    p.add_argument("--gate", required=True, choices=["G0", "G1", "G2", "G3", "G4", "G5"])
    p.add_argument("--decision", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--return-target", default=None)
    p.add_argument("--scope", default="root", choices=["local", "root"])
    p.add_argument("--root-cause", default="unknown")

    p = sub.add_parser("check")
    p.add_argument("--project-root", required=True)
    p.add_argument("--stage", required=True)

    p = sub.add_parser("freshness")
    p.add_argument("--project-root", required=True)
    p.add_argument("--role", required=True, choices=["solver", "reviewer"])
    p.add_argument("--trigger", required=True)
    p.add_argument("--scope", default="local", choices=["local", "root"])
    p.add_argument("--affected", type=int, default=1)
    p.add_argument("--context-lost", action="store_true")
    p.add_argument("--human-request", action="store_true")
    p.add_argument("--child-id", default=None)
    p.add_argument("--round", type=int, default=1)

    sub.add_parser("validate-rework-plan").add_argument("--project-root", required=True)
    sub.add_parser("run-regressions").add_argument("--project-root", required=True)
    sub.add_parser("route").add_argument("--project-root", required=True)
    return parser.parse_args(argv)


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    args = parse_args(argv)
    root = Path(args.project_root).resolve()
    fw = load_framework()
    ck = load_checks()
    try:
        if args.command == "start":
            result = start(root, args.track, args.profile, args.contest_profile,
                           args.run_id, args.contest_year, args.force)
            print(json.dumps({"ok": True, "state": result}, ensure_ascii=False, indent=2))
        elif args.command == "status":
            print(json.dumps(status(root, args.view), ensure_ascii=False, indent=2))
        elif args.command == "submit":
            result = submit(root, args.stage, args.role, args.produced_by, ck, fw,
                            no_checks=args.no_checks, summary=args.summary)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if not result.get("ok"):
                return 1
        elif args.command == "gate":
            result = gate(root, args.gate, args.decision, args.reason, ck, fw,
                          return_target=args.return_target, scope=args.scope, root_cause=args.root_cause)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == "check":
            state = load_state(root)
            result = run_stage_checks(root, state, args.stage, ck, fw)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if not result.get("ok"):
                return 1
        elif args.command == "freshness":
            result = freshness(root, args.role, args.trigger, args.scope, args.affected,
                               args.context_lost, args.human_request, args.child_id, args.round)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == "validate-rework-plan":
            result = validate_rework_plan_internal(root)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if result.get("status") != "pass":
                return 1
        elif args.command == "run-regressions":
            result = run_regressions_internal(root)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if result.get("status") != "pass":
                return 1
        elif args.command == "route":
            print(json.dumps(route(root), ensure_ascii=False, indent=2))
        else:
            raise KernelError(f"未知命令：{args.command}")
    except KernelError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
