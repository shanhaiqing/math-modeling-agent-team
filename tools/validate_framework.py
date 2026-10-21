#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_framework.py — Phase 0 框架规格自洽性校验（0 token）

检查 system/framework.json、system/checks.json、system/schemas/*.json 的：
  1. JSON 可解析、顶层字段齐全
  2. ID 唯一、引用存在（stage/gate/role/artifact/check）
  3. 状态图可达、终态无出边、循环有上限
  4. 门的选项与转移一致、门卡存在
  5. 产物 producer/consumer/validator/schema 存在
  6. 机查命令占位符合法、脚本存在、run_after 顺序正确、manifest 与 machine_checks 收尾
  7. 模型路由为单一 deepseek-flash + effort，profile 覆盖全部角色
  8. 文档/门卡/schema/tabletop 文件存在，框架章节齐全
  9. 预算、limits、concurrency、guards 结构完整

用法：
  python tools/validate_framework.py [--json] [--report PATH] [--strict]
退出码：0 = 无 ERROR；1 = 存在 ERROR（--strict 时 WARN 也算）；2 = 读取失败
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SYSTEM = ROOT / "system"
FRAMEWORK_PATH = SYSTEM / "framework.json"
CHECKS_PATH = SYSTEM / "checks.json"
SCHEMAS_DIR = SYSTEM / "schemas"

ERRORS = []
WARNS = []


def err(code, message):
    ERRORS.append({"code": code, "message": message})


def warn(code, message):
    WARNS.append({"code": code, "message": message})


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:  # noqa: BLE001
        err("json", f"{path}: {exc}")
        return None


def as_list(value):
    return value if isinstance(value, list) else []


def check_file(rel_path, code, label):
    path = ROOT / rel_path
    if not path.exists():
        err(code, f"{label} 不存在：{rel_path}")
        return False
    return True


def parse_gate_on(on):
    match = re.fullmatch(r"gate:(G[0-5])=([a-z_]+)", str(on))
    return (match.group(1), match.group(2)) if match else (None, None)


def collect_ids(items, key="id"):
    return [item.get(key) for item in items if isinstance(item, dict) and item.get(key)]


def unique_ids(items, kind, code):
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            err(code, f"{kind} 数组含非对象项")
            continue
        item_id = item.get("id")
        if not item_id:
            err(code, f"{kind} 缺少 id：{item}")
            continue
        if item_id in seen:
            err(code, f"{kind} id 重复：{item_id}")
        seen.add(item_id)
    return seen


def validate_top_level(fw, ck):
    required = [
        "framework_version", "schema_version", "name", "scope", "paths", "model_routing",
        "run_profiles", "freshness_policy", "stages", "transitions", "gates", "roles", "artifacts",
        "resources", "handoff", "budgets", "limits", "concurrency", "guards",
        "checks_manifest", "docs",
    ]
    for key in required:
        if key not in fw:
            err("top", f"framework.json 缺顶层字段：{key}")
    if fw.get("checks_manifest") != "checks.json":
        err("top", "checks_manifest 应为 checks.json")
    check_file("system/checks.json", "top", "checks.json")
    if not isinstance(ck, dict):
        err("top", "checks.json 根应为对象")
        return
    for key in ("checks_version", "python", "placeholders", "execution_order", "checks", "asset_maintenance", "retired", "report_shapes"):
        if key not in ck:
            err("top", f"checks.json 缺顶层字段：{key}")


def validate_stages(fw, ck):
    stages = as_list(fw.get("stages"))
    stage_ids = unique_ids(stages, "stage", "stage")
    roles = {r.get("id") for r in as_list(fw.get("roles")) if isinstance(r, dict)}
    gates = {g.get("id") for g in as_list(fw.get("gates")) if isinstance(g, dict)}
    artifacts = {a.get("id") for a in as_list(fw.get("artifacts")) if isinstance(a, dict)}
    checks = {c.get("id") for c in as_list(ck.get("checks")) if isinstance(c, dict)}
    token_sum = 0.0
    for stage in stages:
        if not isinstance(stage, dict):
            continue
        sid = stage.get("id")
        owner = stage.get("owner")
        if owner not in roles:
            err("stage", f"{sid}: owner 不存在：{owner}")
        for support in as_list(stage.get("support_roles")):
            if support not in roles:
                err("stage", f"{sid}: support_role 不存在：{support}")
        if stage.get("human_gate") is not None and stage.get("human_gate") not in gates:
            err("stage", f"{sid}: human_gate 不存在：{stage.get('human_gate')}")
        if not as_list(stage.get("exit")):
            err("stage", f"{sid}: exit 为空")
        for art in as_list(stage.get("artifacts_out")):
            if art not in artifacts:
                err("stage", f"{sid}: artifacts_out 引用不存在：{art}")
        for cid in as_list(stage.get("checks")):
            if cid not in checks:
                err("stage", f"{sid}: checks 引用不存在：{cid}")
        budget = stage.get("budget") if isinstance(stage.get("budget"), dict) else {}
        wall = budget.get("wall_minutes")
        if not isinstance(wall, (int, float)) or wall < 0:
            err("stage", f"{sid}: budget.wall_minutes 非法：{wall}")
        share = budget.get("token_share")
        if not isinstance(share, (int, float)) or not (0 <= share <= 1):
            err("stage", f"{sid}: budget.token_share 非法：{share}")
        else:
            token_sum += float(share)
        sub = budget.get("sub_phases")
        if isinstance(sub, dict):
            for key, minutes in sub.items():
                if not isinstance(minutes, (int, float)) or minutes <= 0:
                    err("stage", f"{sid}: sub_phase {key} 非法：{minutes}")
        on_fail = stage.get("on_fail")
        if on_fail is not None and on_fail not in stage_ids:
            err("stage", f"{sid}: on_fail 不存在：{on_fail}")
    if not (0.95 <= token_sum <= 1.05):
        err("budget", f"stage token_share 合计 {token_sum:.3f} 不在 0.95-1.05")
    terminal = {"DELIVERED", "STOPPED"}
    for sid in terminal:
        if sid not in stage_ids:
            err("stage", f"缺少终态：{sid}")
    if "INIT" not in stage_ids:
        err("stage", "缺少 INIT")
    return stage_ids, terminal


def validate_transitions(fw, stage_ids, terminal):
    transitions = as_list(fw.get("transitions"))
    unique_ids(transitions, "transition", "transition")
    gates = {g.get("id"): g for g in as_list(fw.get("gates")) if isinstance(g, dict)}
    limits = fw.get("limits") if isinstance(fw.get("limits"), dict) else {}
    kinds = {"auto", "gate", "gate_loop", "auto_loop", "failure", "repair", "recovery"}
    has_out = {sid: False for sid in stage_ids}
    for tr in transitions:
        if not isinstance(tr, dict):
            continue
        tid = tr.get("id", "?")
        src, dst, on, kind = tr.get("from"), tr.get("to"), tr.get("on"), tr.get("kind")
        if src not in stage_ids:
            err("transition", f"{tid}: from 不存在：{src}")
            continue
        has_out[src] = True
        if kind not in kinds:
            err("transition", f"{tid}: kind 非法：{kind}")
        if not on or not tr.get("guard"):
            err("transition", f"{tid}: on/guard 为空")
        if dst in ("$resume_target", "$return_target"):
            targets = as_list(tr.get("allowed_targets"))
            if not targets:
                err("transition", f"{tid}: {dst} 缺 allowed_targets")
            for target in targets:
                if target not in stage_ids:
                    err("transition", f"{tid}: allowed_target 不存在：{target}")
        elif dst not in stage_ids:
            err("transition", f"{tid}: to 不存在：{dst}")
        if kind in ("gate", "gate_loop"):
            gid, decision = parse_gate_on(on)
            if not gid:
                err("transition", f"{tid}: gate 转移 on 格式应为 gate:Gx=decision")
            elif gid not in gates:
                err("transition", f"{tid}: gate 不存在：{gid}")
            else:
                options = {o.get("id"): o.get("to") for o in as_list(gates[gid].get("options")) if isinstance(o, dict)}
                if decision not in options:
                    err("transition", f"{tid}: gate {gid} 无选项 {decision}")
                elif options.get(decision) != dst:
                    err("transition", f"{tid}: 门选项 {decision} 去向 {options.get(decision)} 与转移 {dst} 不一致")
        if kind in ("gate_loop", "auto_loop"):
            key = tr.get("limit_key")
            if key not in limits:
                err("transition", f"{tid}: limit_key 不存在于 limits：{key}")
            max_value = tr.get("max")
            if not isinstance(max_value, int) or max_value <= 0:
                err("transition", f"{tid}: max 非法：{max_value}")
            elif key in limits and max_value > int(limits[key]):
                err("transition", f"{tid}: max {max_value} 超过 limits.{key}={limits[key]}")
    for sid in terminal:
        if has_out.get(sid):
            err("transition", f"终态 {sid} 不应有出边")
    # reachability
    graph = {sid: set() for sid in stage_ids}
    for tr in transitions:
        if not isinstance(tr, dict):
            continue
        src = tr.get("from")
        if src not in graph:
            continue
        dst = tr.get("to")
        if dst in ("$resume_target", "$return_target"):
            for target in as_list(tr.get("allowed_targets")):
                if target in graph:
                    graph[src].add(target)
        elif dst in graph:
            graph[src].add(dst)
    seen = set()
    stack = ["INIT"]
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        stack.extend(graph.get(node, ()))
    unreachable = sorted(s for s in stage_ids if s not in seen)
    if unreachable:
        err("transition", f"不可从 INIT 到达的状态：{', '.join(unreachable)}")
    return graph


def validate_gates(fw, stage_ids):
    gates = as_list(fw.get("gates"))
    gate_ids = unique_ids(gates, "gate", "gate")
    stage_map = {s.get("id"): s for s in as_list(fw.get("stages")) if isinstance(s, dict)}
    gate_cards = list((SYSTEM / "gates").glob("*.md")) if (SYSTEM / "gates").is_dir() else []
    for gate in gates:
        if not isinstance(gate, dict):
            continue
        gid = gate.get("id")
        stage_id = gate.get("stage")
        if stage_id not in stage_ids:
            err("gate", f"{gid}: stage 不存在：{stage_id}")
        elif stage_map.get(stage_id, {}).get("human_gate") != gid:
            err("gate", f"{gid}: 与 stage.human_gate 不一致")
        mode = gate.get("mode")
        if mode not in ("mandatory", "conditional"):
            err("gate", f"{gid}: mode 非法：{mode}")
        if not as_list(gate.get("packet_sections")):
            err("gate", f"{gid}: packet_sections 为空")
        options = as_list(gate.get("options"))
        if not options:
            err("gate", f"{gid}: options 为空")
        option_ids = unique_ids(options, f"gate {gid} option", "gate")
        for opt in options:
            if opt.get("to") not in stage_ids:
                err("gate", f"{gid}: option {opt.get('id')} 去向不存在：{opt.get('to')}")
        if not isinstance(gate.get("timebox_minutes"), (int, float)) or gate.get("timebox_minutes", 0) <= 0:
            err("gate", f"{gid}: timebox_minutes 非法")
        if not gate.get("record"):
            err("gate", f"{gid}: record 为空")
        if gate.get("owner") is None:
            err("gate", f"{gid}: owner 为空")
        if mode == "conditional":
            if not as_list(gate.get("trigger")):
                err("gate", f"{gid}: 条件门缺 trigger")
            if not gate.get("auto_rule"):
                err("gate", f"{gid}: 条件门缺 auto_rule")
        if gid and not any(p.name.startswith(f"{gid}-") for p in gate_cards):
            err("gate", f"{gid}: 缺门卡 system/gates/{gid}-*.md")
    return gate_ids


def validate_roles(fw):
    roles = as_list(fw.get("roles"))
    role_ids = unique_ids(roles, "role", "role")
    routing_roles = fw.get("model_routing", {}).get("roles")
    route_names = set(routing_roles.keys()) if isinstance(routing_roles, dict) else set()
    stage_map = {s.get("id"): s for s in as_list(fw.get("stages")) if isinstance(s, dict)}
    professional = {"specialist", "teammate"}
    for role in roles:
        if not isinstance(role, dict):
            continue
        rid = role.get("id")
        kind = role.get("kind")
        if kind not in ("lead", "specialist", "teammate", "kernel", "human"):
            err("role", f"{rid}: kind 非法：{kind}")
        if role.get("context") not in ("persistent", "fresh", "fresh_then_resume", "none"):
            err("role", f"{rid}: context 非法：{role.get('context')}")
        route = role.get("model_route")
        if kind in ("lead",) or kind in professional:
            if route not in route_names:
                err("role", f"{rid}: model_route 不存在：{route}")
            if kind in professional and not role.get("skill"):
                if rid != "gate_packet":
                    err("role", f"{rid}: 专业角色缺 skill")
        for sid in as_list(role.get("stage_owner")):
            if sid not in stage_map:
                err("role", f"{rid}: stage_owner 不存在：{sid}")
            elif stage_map[sid].get("owner") != rid:
                err("role", f"{rid}: 声称拥有 {sid}，但 stage.owner={stage_map[sid].get('owner')}")
        if not as_list(role.get("writes")) and kind not in ("gate_packet", "human") and rid != "gate_packet":
            warn("role", f"{rid}: writes 为空")
        if not as_list(role.get("outputs")) and kind not in ("gate_packet", "human"):
            warn("role", f"{rid}: outputs 为空")
    return role_ids


def validate_artifacts(fw, stage_ids, role_ids):
    artifacts = as_list(fw.get("artifacts"))
    unique_ids(artifacts, "artifact", "artifact")
    paths = set()
    pseudo_consumers = {"human", "kernel", "fallback_checkers"}
    for art in artifacts:
        if not isinstance(art, dict):
            continue
        aid = art.get("id")
        path = art.get("path")
        if not path:
            err("artifact", f"{aid}: path 为空")
        if path in paths:
            err("artifact", f"{aid}: path 重复：{path}")
        paths.add(path)
        if art.get("producer") not in role_ids:
            err("artifact", f"{aid}: producer 不存在：{art.get('producer')}")
        for consumer in as_list(art.get("consumers")):
            if consumer not in role_ids and consumer not in pseudo_consumers:
                err("artifact", f"{aid}: consumer 不存在：{consumer}")
        stage = art.get("stage")
        if stage not in stage_ids and stage != "MULTI":
            err("artifact", f"{aid}: stage 非法：{stage}")
        if not isinstance(art.get("required"), bool):
            err("artifact", f"{aid}: required 应为 bool")
        if art.get("blocking") not in ("ERROR", "WARN", "NONE"):
            err("artifact", f"{aid}: blocking 非法：{art.get('blocking')}")
        validators = as_list(art.get("validators"))
        if not validators:
            err("artifact", f"{aid}: validators 为空")
        for validator in validators:
            if validator in ("kernel", "human"):
                continue
            if isinstance(validator, str) and validator.startswith("schema:"):
                schema_rel = validator.split(":", 1)[1]
                if not (SYSTEM / schema_rel).exists():
                    err("artifact", f"{aid}: schema 不存在：{schema_rel}")
                continue
            if isinstance(validator, str) and (validator.startswith(".trae/") or validator.startswith("tools/")):
                if not (ROOT / validator).exists():
                    err("artifact", f"{aid}: validator 不存在：{validator}")
                continue
            warn("artifact", f"{aid}: 未识别的 validator：{validator}")
        schema = art.get("schema")
        if schema:
            if not (SYSTEM / schema).exists():
                err("artifact", f"{aid}: schema 字段指向不存在文件：{schema}")
        if not art.get("required") and not art.get("condition"):
            warn("artifact", f"{aid}: 非必填但未写 condition")
    return paths


def validate_model_routing(fw):
    routing = fw.get("model_routing")
    if not isinstance(routing, dict):
        return
    main = routing.get("current_main_model") if isinstance(routing.get("current_main_model"), dict) else {}
    if main.get("model") != "deepseek-flash":
        err("model", "current_main_model.model 应为 deepseek-flash（V4.1-Flash 当前主力）")
    if not main.get("provider") or not main.get("label"):
        err("model", "current_main_model 缺 provider/label")
    roles = routing.get("roles") if isinstance(routing.get("roles"), dict) else {}
    efforts = {"off", "low", "high", "max"}
    for rid, route in roles.items():
        if not isinstance(route, dict):
            err("model", f"route {rid} 应为对象")
            continue
        if route.get("model") != "deepseek-flash":
            err("model", f"route {rid} 不是 deepseek-flash：{route.get('model')}")
        if route.get("effort") not in efforts:
            err("model", f"route {rid} effort 非法：{route.get('effort')}")
    if roles.get("writer", {}).get("inherits") != "lead":
        warn("model", "writer route 应声明 inherits=lead（持久成员继承 Lead effort）")
    profiles = routing.get("profiles") if isinstance(routing.get("profiles"), dict) else {}
    for profile in ("quality", "balanced", "economy"):
        if profile not in profiles:
            err("model", f"缺运行档位：{profile}")
            continue
        for rid in roles:
            if rid not in profiles[profile]:
                err("model", f"{profile} 档缺角色 route：{rid}")
            elif profiles[profile][rid] not in efforts:
                err("model", f"{profile}.{rid} effort 非法：{profiles[profile][rid]}")
    if routing.get("default_profile") not in profiles:
        err("model", "default_profile 不在 profiles 中")
    upgrade = routing.get("upgrade_policy")
    if not isinstance(upgrade, dict) or not as_list(upgrade.get("steps")) or not as_list(upgrade.get("forbidden")):
        err("model", "upgrade_policy 缺 steps/forbidden")
    unused = as_list(routing.get("unused_models"))
    if not any(isinstance(u, dict) and u.get("model") == "deepseek-v4-pro" for u in unused):
        warn("model", "unused_models 未说明 deepseek-v4-pro 的处置")


def validate_freshness(fw):
    policy = fw.get("freshness_policy")
    if not isinstance(policy, dict):
        err("freshness", "freshness_policy 缺失")
        return
    modes = set(as_list(policy.get("modes")))
    expected_modes = {"fresh", "resume", "fresh_dossier", "fresh_independent"}
    if not expected_modes <= modes:
        err("freshness", f"freshness modes 缺：{sorted(expected_modes - modes)}")
    defaults = policy.get("defaults") if isinstance(policy.get("defaults"), dict) else {}
    for key in (
        "solver_initial", "solver_local_rework", "solver_root_rework", "solver_context_lost",
        "reviewer_initial", "reviewer_r1_local", "reviewer_r1_root", "reviewer_r2_default",
        "reviewer_r2_high_failure", "reviewer_second_opinion",
    ):
        if key not in defaults:
            err("freshness", f"freshness.defaults 缺：{key}")
        elif defaults[key] not in modes:
            err("freshness", f"freshness.defaults.{key} 非法：{defaults[key]}")
    for key in ("local_triggers", "root_cause_triggers", "reviewer_fresh_triggers"):
        if not as_list(policy.get(key)):
            err("freshness", f"freshness.{key} 为空")
    anti = policy.get("anti_recurrence") if isinstance(policy.get("anti_recurrence"), dict) else {}
    artifacts = {a.get("id") for a in as_list(fw.get("artifacts")) if isinstance(a, dict)}
    for art in as_list(anti.get("artifacts")):
        if art not in artifacts:
            err("freshness", f"anti_recurrence artifact 不存在：{art}")
    if not isinstance(anti.get("max_plan_revisions"), int) or anti.get("max_plan_revisions", 0) <= 0:
        err("freshness", "anti_recurrence.max_plan_revisions 应为正整数")
    if not anti.get("plan_gate") or not anti.get("repeat_failure"):
        err("freshness", "anti_recurrence 缺 plan_gate/repeat_failure")
    roles = {r.get("id"): r for r in as_list(fw.get("roles")) if isinstance(r, dict)}
    for rid in ("solver", "reviewer"):
        role = roles.get(rid)
        if not role or not isinstance(role.get("context_policy"), dict):
            err("freshness", f"{rid}: 缺 context_policy")
            continue
        for key, value in role["context_policy"].items():
            if value not in modes and value != "escalate":
                err("freshness", f"{rid}.context_policy.{key} 非法：{value}")


def validate_checks(ck, fw, stage_ids):
    checks = as_list(ck.get("checks"))
    check_ids = unique_ids(checks, "check", "check")
    placeholders = set(as_list(ck.get("placeholders")))
    report_shapes = set((ck.get("report_shapes") or {}).keys())
    when_keys = {"track", "profile", "compile_mode", "mode", "artifact", "freshness", "rework"}
    by_id = {c.get("id"): c for c in checks if isinstance(c, dict)}
    stage_checks = {s.get("id"): as_list(s.get("checks")) for s in as_list(fw.get("stages")) if isinstance(s, dict)}
    artifacts = {a.get("id") for a in as_list(fw.get("artifacts")) if isinstance(a, dict)}
    timeout_limit = 3600
    for check in checks:
        if not isinstance(check, dict):
            continue
        cid = check.get("id")
        stage = check.get("stage")
        if stage not in stage_ids:
            err("check", f"{cid}: stage 非法：{stage}")
        if not isinstance(check.get("order"), int):
            err("check", f"{cid}: order 应为整数")
        command = check.get("command")
        if not isinstance(command, list) or not command:
            err("check", f"{cid}: command 为空")
        else:
            for token in command:
                for ph in re.findall(r"\{([a-z_]+)\}", str(token)):
                    if ph not in placeholders:
                        err("check", f"{cid}: 未知占位符 {{{ph}}}")
                if isinstance(token, str) and token.startswith("{repo}/"):
                    rel = token.replace("{repo}/", "", 1)
                    if not (ROOT / rel).exists():
                        err("check", f"{cid}: 命令引用的路径不存在：{rel}")
        reports = check.get("reports")
        if not isinstance(reports, list):
            err("check", f"{cid}: reports 应为数组")
        if check.get("blocking") not in ("ERROR", "WARN", "NONE"):
            err("check", f"{cid}: blocking 非法：{check.get('blocking')}")
        timeout = check.get("timeout_seconds")
        if not isinstance(timeout, int) or timeout <= 0 or timeout > timeout_limit:
            err("check", f"{cid}: timeout_seconds 非法：{timeout}")
        when = check.get("when")
        if when is not None:
            if not isinstance(when, dict):
                err("check", f"{cid}: when 应为对象")
            else:
                for key, value in when.items():
                    if key not in when_keys:
                        err("check", f"{cid}: when.{key} 未知")
                    if key == "track" and value not in ("opt", "stats"):
                        err("check", f"{cid}: when.track 非法：{value}")
                    if key == "profile" and value not in ("cumcm", "shuwei_zh", "shuwei_en"):
                        err("check", f"{cid}: when.profile 非法：{value}")
                    if key == "mode" and value not in ("kernel", "fallback"):
                        err("check", f"{cid}: when.mode 非法：{value}")
                    if key == "artifact" and value not in artifacts:
                        err("check", f"{cid}: when.artifact 不存在：{value}")
                    if key == "freshness" and value not in ("fresh", "resume", "fresh_dossier", "fresh_independent"):
                        err("check", f"{cid}: when.freshness 非法：{value}")
                    if key == "rework" and value not in ("true", "false", "fresh", "local"):
                        err("check", f"{cid}: when.rework 非法：{value}")
        if check.get("on_error") not in (None, "external_compile", "block_after_retry", "pause", "repair"):
            err("check", f"{cid}: on_error 非法：{check.get('on_error')}")
        if check.get("defer_on") not in (None, "external_compile"):
            err("check", f"{cid}: defer_on 非法：{check.get('defer_on')}")
        shape = check.get("report_shape")
        if shape not in report_shapes:
            err("check", f"{cid}: report_shape 未知：{shape}")
        run_after = check.get("run_after")
        if not isinstance(run_after, list):
            err("check", f"{cid}: run_after 应为数组")
        else:
            for dep in run_after:
                if dep not in check_ids:
                    err("check", f"{cid}: run_after 引用不存在：{dep}")
                elif by_id.get(dep, {}).get("order", 0) >= check.get("order", 0):
                    err("check", f"{cid}: run_after {dep} 的 order 不小于本检查")
        if check.get("phase") == "gate_pre":
            gate = check.get("gate")
            gates = {g.get("id") for g in as_list(fw.get("gates")) if isinstance(g, dict)}
            if gate not in gates:
                err("check", f"{cid}: gate_pre 引用的门不存在：{gate}")
    # every check referenced by at least one stage
    referenced = {cid for ids in stage_checks.values() for cid in ids}
    for cid in check_ids:
        if cid not in referenced:
            warn("check", f"{cid}: 未被任何 stage.checks 引用")
    # per-stage ordering: manifest last among business, machine_checks last
    for stage, ids in stage_checks.items():
        if not ids:
            continue
        ordered = sorted([by_id[i] for i in ids if i in by_id], key=lambda c: c.get("order", 0))
        for index, check in enumerate(ordered):
            cid = check.get("id")
            later = ordered[index + 1:]
            if cid and cid.endswith("_manifest"):
                for other in later:
                    if not str(other.get("id", "")).endswith("_machine_checks"):
                        err("check", f"{stage}: manifest {cid} 之后仍有业务机查：{other.get('id')}")
            if cid and cid.endswith("_machine_checks") and later:
                err("check", f"{stage}: machine_checks {cid} 不是最后一条")
    # asset maintenance
    for check in as_list(ck.get("asset_maintenance")):
        if not isinstance(check, dict):
            continue
        cid = check.get("id")
        if check.get("when") != "asset_changed":
            warn("check", f"asset {cid}: when 不是 asset_changed")
        if check.get("blocking") not in ("WARN", "NONE", "ERROR"):
            err("check", f"asset {cid}: blocking 非法")
        for token in check.get("command") or []:
            if isinstance(token, str) and token.startswith("{repo}/"):
                rel = token.replace("{repo}/", "", 1)
                if not (ROOT / rel).exists():
                    err("check", f"asset {cid}: 路径不存在：{rel}")
    # retired
    for item in as_list(ck.get("retired")):
        if not isinstance(item, dict):
            continue
        if item.get("disposition") not in ("retire", "move_to_evolution", "move_to_tests"):
            err("check", f"retired {item.get('id')}: disposition 非法")
        path = item.get("path")
        if isinstance(path, str) and "*" not in path and not (ROOT / path).exists():
            warn("check", f"retired {item.get('id')}: 文件不存在（可能已清理）：{path}")


def validate_schemas():
    expected = [
        "run-state.schema.json",
        "gate-decision.schema.json",
        "artifact-manifest.schema.json",
        "check-report.schema.json",
        "cost-report.schema.json",
        "failure-dossier.schema.json",
        "rework-plan.schema.json",
    ]
    ids = set()
    for name in expected:
        path = SCHEMAS_DIR / name
        if not path.exists():
            err("schema", f"缺 schema：{name}")
            continue
        data = load_json(path)
        if not isinstance(data, dict):
            continue
        if not str(data.get("$schema", "")).startswith("https://json-schema.org/"):
            err("schema", f"{name}: $schema 缺失或非法")
        if data.get("type") != "object":
            err("schema", f"{name}: 顶层 type 应为 object")
        if not isinstance(data.get("properties"), dict):
            err("schema", f"{name}: properties 缺失")
        required = data.get("required")
        if not isinstance(required, list):
            err("schema", f"{name}: required 应为数组")
        else:
            for key in required:
                if key not in data.get("properties", {}):
                    err("schema", f"{name}: required 字段 {key} 不在 properties")
        sid = data.get("$id")
        if sid:
            if sid in ids:
                err("schema", f"{name}: $id 重复：{sid}")
            ids.add(sid)


def validate_docs(fw):
    for rel, label in [
        ("system/README.md", "README"),
        ("system/framework.md", "framework.md"),
        ("system/migration-map.md", "migration-map.md"),
        ("system/tabletop-tests.md", "tabletop-tests.md"),
    ]:
        check_file(rel, "doc", label)
    framework_md = (SYSTEM / "framework.md").read_text(encoding="utf-8") if (SYSTEM / "framework.md").exists() else ""
    for number in range(0, 17):
        if f"## {number}." not in framework_md:
            err("doc", f"framework.md 缺章节 ## {number}.")
    mig = (SYSTEM / "migration-map.md").read_text(encoding="utf-8") if (SYSTEM / "migration-map.md").exists() else ""
    for keyword in ("规则覆盖", "机查资产处置", "无 orphan", "安全步"):
        if keyword not in mig:
            err("doc", f"migration-map.md 缺关键内容：{keyword}")
    table = (SYSTEM / "tabletop-tests.md").read_text(encoding="utf-8") if (SYSTEM / "tabletop-tests.md").exists() else ""
    scenarios = re.findall(r"^## T(\d+)\b", table, flags=re.MULTILINE)
    if len(scenarios) != 8:
        err("doc", f"tabletop-tests.md 场景数应为 8，实际 {len(scenarios)}")
    readme = (SYSTEM / "README.md").read_text(encoding="utf-8") if (SYSTEM / "README.md").exists() else ""
    if "validate_framework.py" not in readme:
        err("doc", "README.md 未提到 validate_framework.py")
    if "fresh_dossier" not in framework_md or "失败档案" not in framework_md:
        err("doc", "framework.md 未描述 fresh_dossier / 失败档案")
    if not fw.get("docs"):
        err("doc", "framework.json 缺 docs")


def validate_budget_limits(fw):
    budgets = fw.get("budgets") if isinstance(fw.get("budgets"), dict) else {}
    run = budgets.get("run") if isinstance(budgets.get("run"), dict) else {}
    if run.get("wall_minutes") != 4320:
        err("budget", "run.wall_minutes 应为 4320（72h）")
    if not isinstance(run.get("soft_multiplier"), (int, float)) or run.get("soft_multiplier", 0) <= 1:
        err("budget", "run.soft_multiplier 应 > 1")
    if not isinstance(run.get("hard_multiplier"), (int, float)) or run.get("hard_multiplier", 0) <= run.get("soft_multiplier", 1):
        err("budget", "run.hard_multiplier 应大于 soft_multiplier")
    limits = fw.get("limits") if isinstance(fw.get("limits"), dict) else {}
    for key in ("g0_fix", "method_rollbacks_per_critique", "modeling_rework_total", "figure_returns", "writing_returns", "review_rounds", "agent_retries", "plan_revisions", "fresh_rework_per_root_cause"):
        if key not in limits:
            err("budget", f"limits 缺 {key}")
    if not isinstance(limits.get("repeat_failure_escalation"), bool):
        err("budget", "limits.repeat_failure_escalation 应为 bool")
    concurrency = fw.get("concurrency") if isinstance(fw.get("concurrency"), dict) else {}
    if concurrency.get("main_line") != "serial":
        err("budget", "concurrency.main_line 应为 serial")
    stage_ids = {s.get("id") for s in as_list(fw.get("stages")) if isinstance(s, dict)}
    for pair in as_list(concurrency.get("forbidden_parallel")):
        if not isinstance(pair, list) or len(pair) != 2:
            err("budget", f"forbidden_parallel 项应为二元数组：{pair}")
            continue
        for sid in pair:
            if sid not in stage_ids:
                err("budget", f"forbidden_parallel 引用不存在状态：{sid}")
    guards = fw.get("guards") if isinstance(fw.get("guards"), dict) else {}
    if not as_list(guards.get("protected_paths")):
        err("budget", "guards.protected_paths 为空")
    stale = guards.get("stale_propagation") if isinstance(guards.get("stale_propagation"), dict) else {}
    for stage in stale.keys():
        if stage not in stage_ids:
            err("budget", f"stale_propagation 引用不存在状态：{stage}")
    handoff = fw.get("handoff") if isinstance(fw.get("handoff"), dict) else {}
    if not isinstance(handoff.get("brief_max_bytes"), int) or handoff.get("brief_max_bytes", 0) > 8192:
        err("budget", "handoff.brief_max_bytes 应 ≤8192")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--report", default=None, help="写入验证报告路径")
    parser.add_argument("--strict", action="store_true", help="WARN 也算失败")
    args = parser.parse_args()

    fw = load_json(FRAMEWORK_PATH)
    ck = load_json(CHECKS_PATH)
    if fw is None or ck is None:
        print("FATAL: 无法读取 framework.json / checks.json")
        sys.exit(2)
    validate_top_level(fw, ck)
    stage_ids, terminal = validate_stages(fw, ck)
    validate_transitions(fw, stage_ids, terminal)
    validate_gates(fw, stage_ids)
    role_ids = validate_roles(fw)
    validate_artifacts(fw, stage_ids, role_ids)
    validate_model_routing(fw)
    validate_freshness(fw)
    validate_checks(ck, fw, stage_ids)
    validate_schemas()
    validate_docs(fw)
    validate_budget_limits(fw)

    result = {
        "framework_version": fw.get("framework_version"),
        "schema_version": fw.get("schema_version"),
        "counts": {
            "stages": len(as_list(fw.get("stages"))),
            "transitions": len(as_list(fw.get("transitions"))),
            "gates": len(as_list(fw.get("gates"))),
            "roles": len(as_list(fw.get("roles"))),
            "artifacts": len(as_list(fw.get("artifacts"))),
            "checks": len(as_list(ck.get("checks"))),
            "asset_checks": len(as_list(ck.get("asset_maintenance"))),
            "retired": len(as_list(ck.get("retired"))),
            "schemas": len(list(SCHEMAS_DIR.glob("*.json"))),
        },
        "errors": ERRORS,
        "warns": WARNS,
        "error_count": len(ERRORS),
        "warn_count": len(WARNS),
    }
    if args.report:
        Path(args.report).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"framework {result['framework_version']} / schema {result['schema_version']}")
        print("counts: " + ", ".join(f"{k}={v}" for k, v in result["counts"].items()))
        for item in ERRORS:
            print(f"ERROR [{item['code']}] {item['message']}")
        for item in WARNS:
            print(f"WARN  [{item['code']}] {item['message']}")
        print(f"summary: {result['error_count']} ERROR / {result['warn_count']} WARN")
    failed = bool(ERRORS) or (args.strict and bool(WARNS))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
