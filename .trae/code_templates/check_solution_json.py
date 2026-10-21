#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
check_solution_json.py — solution.json 契约校验器（机查版）

把以下判据从"靠注意力执行的 prompt 检查"转为确定性机器检查：
  [契约]  AGENTS.md "handoff 契约"节 —— 子问题必填字段存在性
          prompt 位置：.trae/agents/modeling-solver.md "打包产出"节
  [一.1]  papers/国赛公开惯例.md —— monte_carlo.convergence 字段值与 std/mean 一致性（禁硬编码）
          prompt 位置：.trae/agents/modeling-solver.md 阶段 3 步骤 3.3 + 一.1
  [一.8]  papers/国赛公开惯例.md —— 字段命名四分类（上界/期望值/代表性值/实际值）禁止混用
          prompt 位置：.trae/agents/modeling-solver.md "打包产出"节 字段命名准确性
  [一.10] papers/国赛公开惯例.md —— 字段值语义合理性判例（偏离收益<合作收益、min_observed 等）
          prompt 位置：.trae/agents/modeling-solver.md 阶段 3 步骤 3.3 字段值语义合理性自查
  [一.11] papers/国赛公开惯例.md —— 题目原文核心参数逐字回读（A-01 机查化，C-02）
          读取 modeling_plan.json 的 source_parameters 字段，与 project/*.py 硬编码值逐项比对；
          缺字段 → WARN；任一不一致或仅找到相近值 → ERROR
          prompt 位置：.trae/agents/modeling-solver.md S1 必查项 4
  [一.13] papers/国赛公开惯例.md —— 指标量纲一致性核查（A-03 半机查化，C-03）
          检查 modeling_plan.json 的 indicator_dimension_check 字段四元组判定；
          缺字段 → WARN；任一 ✗ → ERROR
          prompt 位置：.trae/agents/modeling-solver.md 阶段 2 P0 强制约束第 7 项
  [P-1]   papers/国赛公开惯例.md 一.6 —— 活跃约束附派生量数值（2015B 校准反馈，条件触发）
          active_constraints 每条约束条目须含数值型派生量字段（slack/边际响应/局部灵敏度等候选名）；
          含其他数值字段但无候选名 → WARN；无任何数值字段 → ERROR
          prompt 位置：.trae/agents/modeling-solver.md 步骤 3.3 活跃约束标注 + rules handoff 契约
  [P-2]   modeling-solver S3 必查项1 —— 叙述性文本内嵌数值纳入一致性核查（2015B 校准反馈）
          提取两个 JSON 字符串字段与 project/*.py 注释中的数值声明，与结构化数值比对；
          未匹配 → WARN 汇总（人工核对陈旧口径；历史演进口径标注"早期估计"者跳过）
          prompt 位置：.trae/agents/modeling-solver.md S3 必查项1
  [P-3]   papers/国赛公开惯例.md 一.1 —— 不确定性参数"登记-传播"映射（2015B 校准反馈，条件触发）
          modeling_plan 登记清单与映射表（含 propagation 字段）计数一致性；
          缺映射表或计数不符 → WARN（合并处理的显式声明不可机查，留人工）
          prompt 位置：.trae/agents/modeling-solver.md 步骤 3.3 模型验证（按惯例一.1 执行）
  [P11-S] 总审批清单 P11 —— 灵敏度覆盖与扰动幅度
          每子问题 sensitivity 须含 ≥1 扰动参数；参数名可机读百分比时最大幅度须 ≥10%
          （prompt 要求 ±5%/±10%/±20% 扰动）；幅度无法机读 → WARN 人工确认
          prompt 位置：.trae/agents/modeling-solver.md 步骤 3.3 灵敏度分析
  [P11-M] 总审批清单 P11 —— 蒙特卡洛仿真次数下限
          monte_carlo.n_sim ≥1000；"小样本 ≥10000"依赖场景判断不可机查，留人工
          prompt 位置：.trae/agents/modeling-solver.md 步骤 3.3 模型验证

同步维护条款（T-1）：新增或修改机查项时，须同步核对对应 agent prompt 是否已下达该要求。
机查要求集不得超出 prompt 要求集（详见 .trae/papers/国赛公开惯例.md 五.2）。

用法:
  python check_solution_json.py <solution.json路径> [project_results目录]
                                [--selfcheck] [--report 路径]

  自动查找同名目录下的 modeling_plan.json 作为 A-01/A-03 检查依据；
  从 project_results 目录推导同级 project/ 目录作为代码扫描范围。

  --selfcheck  subagent 自检模式：**只打印不落盘**，禁止覆写编排器权威报告。
               paper-writer 步骤 0 等 subagent 侧调用必须带此开关
               （orchestrator §4"机查收归编排器，不得委托 subagent 自检代替"）。
  --report     指定报告落盘路径（默认项目根 contract_check_report.json）。

退出码: 0 = 无 ERROR（可有 WARN）；1 = 存在 ERROR；2 = 用法/读取错误
输出:   控制台逐条打印 + 在项目根写 contract_check_report.json
        （规范路径见 orchestrator.md §4 与产物注册表；solution.json 位于
        {项目根}/result_bundle/ 时项目根 = 其父级的父级，否则回退同目录）
        --selfcheck 时不落盘，权威报告仅由编排器不带该开关的运行产生
分级:   ERROR = 必须当场修复（阻塞打包/进入下一阶段）；WARN = 需人工判定；PASS = 通过
"""
import json
import re
import sys
from pathlib import Path

FINDINGS = []


def error(rule, loc, msg):
    FINDINGS.append({"level": "ERROR", "rule": rule, "location": loc, "message": msg})


def warn(rule, loc, msg):
    FINDINGS.append({"level": "WARN", "rule": rule, "location": loc, "message": msg})


def ok(rule, msg):
    FINDINGS.append({"level": "PASS", "rule": rule, "location": "", "message": msg})


# ---------- 工具 ----------

def walk(node, path="$"):
    """递归产生 (路径, 键, 值, 父dict)。"""
    if isinstance(node, dict):
        for k, v in node.items():
            p = f"{path}.{k}"
            yield p, k, v, node
            yield from walk(v, p)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}[{i}]")


def is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _has_key(node, key):
    if isinstance(node, dict):
        if key in node:
            return True
        return any(_has_key(v, key) for v in node.values())
    if isinstance(node, list):
        return any(_has_key(v, key) for v in node)
    return False


def common_prefix_len(a, b):
    n = 0
    for ca, cb in zip(a, b):
        if ca != cb:
            break
        n += 1
    return n


# ---------- 检查 1：handoff 契约字段存在性 ----------

REQUIRED = ["objective_value", "decision_variables", "solver", "optimality",
            "active_constraints", "sensitivity", "critical_points", "monte_carlo"]


def find_subproblems(data):
    """先找合格子问题（≥3 个契约字段的最外层 dict），再将其同层所有 dict 兄弟都视为子问题——
    结构残缺的兄弟会在 check_contract 中被判缺字段。"""
    if isinstance(data, dict) and "objective_value" in data:
        return {"$": data}
    qualified = {}

    def rec(node, path):
        if not isinstance(node, dict):
            return
        score = sum(1 for f in REQUIRED if f in node)
        if score >= 3:
            qualified[path] = node
            return
        for k, v in node.items():
            rec(v, f"{path}.{k}" if path != "$" else k)

    rec(data, "$")
    if not qualified:
        return {}
    # 合格子问题的共同父层：取最深的那个父路径（兄弟都在这一层）
    parents = {p.rsplit(".", 1)[0] if "." in p else "" for p in qualified}
    parent_path = max(parents, key=len)
    container = data
    if parent_path:
        for part in parent_path.split("."):
            container = container.get(part, {}) if isinstance(container, dict) else {}
    subs = {}
    if isinstance(container, dict):
        for k, v in container.items():
            if isinstance(v, dict):
                subs[f"{parent_path}.{k}" if parent_path else k] = v
    return subs


def check_contract(data):
    subs = find_subproblems(data)
    if not subs:
        if _has_key(data, "task_type"):
            error("契约", "$", "含 task_type，属 stats 契约，不能用 check_solution_json.py")
        else:
            warn("契约", "$", "未识别子问题结构（未找到含 ≥3 个契约字段的字典），必填字段检查跳过")
        return
    for name, sub in subs.items():
        score = sum(1 for f in REQUIRED if f in sub)
        if score == 0:
            continue  # 非子问题字典（如 metadata），跳过
        missing = [f for f in REQUIRED if f not in sub]
        if missing:
            error("契约", name, f"子问题缺必填字段: {', '.join(missing)}")
        else:
            if sub.get("monte_carlo") is None:
                warn("契约", name, "monte_carlo 为 null——需确认已附'不适用'说明（机查无法判定说明文字）")
            else:
                ok("契约", f"{name}: 必填字段齐全（{len(REQUIRED)} 项）")


# ---------- 检查 2：一.1 convergence 判定 ----------

NUM_PCT = re.compile(r"std/mean\s*=\s*([\d.]+)\s*%")
THR_PCT = re.compile(r"([\d.]+)\s*%\s*threshold")


def check_convergence(data):
    nodes = [(p, v) for p, k, v, _ in walk(data) if k == "monte_carlo"]
    for p, mc in nodes:
        if mc is None:
            continue
        if not isinstance(mc, dict) or "convergence" not in mc:
            warn("一.1", p, "monte_carlo 缺 convergence 字段或结构异常")
            continue
        conv = str(mc["convergence"])
        low = conv.lower()
        if "not converged" in low or "未收敛" in conv:
            state = "not"
        elif "converged" in low or "已收敛" in conv or "收敛" in conv:
            state = "yes"
        else:
            warn("一.1", f"{p}.convergence", f"字段值不含 converged 标识，格式无法解析: {conv[:60]!r}")
            continue
        cv = None
        for cand in ("std_mean_ratio", "std_mean", "cv", "coefficient_of_variation"):
            if is_num(mc.get(cand)):
                cv = float(mc[cand])
                break
        m = NUM_PCT.search(conv)
        if m:
            cv = float(m.group(1)) / 100.0
        thr = 0.05
        t = THR_PCT.search(conv)
        if t:
            thr = float(t.group(1)) / 100.0
        if state == "not":
            if cv is not None and cv <= thr:
                error("一.1", f"{p}.convergence",
                      f"字段值 'not converged' 但 std/mean={cv:.2%} ≤ 阈值 {thr:.0%}，字段值与统计量矛盾")
            else:
                cvs = f"{cv:.2%}" if cv is not None else "未报告"
                ok("一.1", f"{p}: 正确报告未收敛（std/mean={cvs}）")
        else:
            if cv is not None and cv > thr:
                error("一.1", f"{p}.convergence",
                      f"字段值含 'converged' 但 std/mean={cv:.2%} > 阈值 {thr:.0%}，字段值与统计量矛盾（禁止硬编码 'converged'）")
            elif cv is None:
                warn("一.1", f"{p}.convergence",
                     "字段值未含 std/mean 实际数值，疑似硬编码（应为 'converged (std/mean=X% < Y% threshold)'）")
            else:
                ok("一.1", f"{p}: convergence 与 std/mean={cv:.2%} 一致")


# ---------- 检查 3：一.8 命名四分类 ----------

CAT_PATTERNS = {
    "上界": re.compile(r"upper_bound|perfect_information", re.I),
    "期望值": re.compile(r"expected|expectation", re.I),
    "代表性值": re.compile(r"representative", re.I),
    "实际值": re.compile(r"actual", re.I),
}
EXPECT_WORDS = re.compile(r"expected|expectation|期望", re.I)
UB_WORDS = re.compile(r"upper\s*bound|上界|perfect\s*information", re.I)


def check_naming(data):
    n_fields = 0
    for p, k, v, parent in walk(data):
        cats = [c for c, pat in CAT_PATTERNS.items() if pat.search(k)]
        if not cats:
            continue
        n_fields += 1
        has_note = isinstance(parent, dict) and (f"{k}_note" in parent or "_note" in parent)
        texts = []
        if isinstance(parent, dict):
            for sk, sv in parent.items():
                if sk in ("method", f"{k}_note", "_note") and isinstance(sv, str):
                    texts.append(sv)
        if isinstance(v, str):
            texts.append(v)
        joined = " ".join(texts)
        for c in cats:
            # 冲突判定：命名属[c]类但文本含对立语义；文本同时含两类语义时为歧义（降 WARN）
            if c == "期望值" and UB_WORDS.search(joined):
                if EXPECT_WORDS.search(joined):
                    warn("一.8", p,
                         f"字段 '{k}'（期望值类）的 method/note 同时含上界与期望语义，命名归属需人工确认（若确为期望值建议附 _note 与上界字段区分）")
                elif has_note:
                    warn("一.8", p,
                         f"字段 '{k}'（期望值类）与 method 文本语义交叉，但已附 _note——请人工确认该说明成立")
                else:
                    error("一.8", p,
                          f"字段命名 '{k}' 属[期望值]类，但 method/文本仅含上界语义——命名四分类禁止混用（上界须命名为 *_upper_bound），且缺 _note 说明")
            elif c == "上界" and EXPECT_WORDS.search(joined) and not UB_WORDS.search(joined):
                if has_note:
                    warn("一.8", p,
                         f"字段 '{k}'（上界类）与 method 文本语义交叉，但已附 _note——请人工确认该说明成立")
                else:
                    error("一.8", p,
                          f"字段命名 '{k}' 属[上界]类，但 method/文本仅含期望语义——命名四分类禁止混用，且缺 _note 说明")
        if len(cats) > 1 and not has_note:
            warn("一.8", p, f"字段 '{k}' 同时匹配多类（{'/'.join(cats)}），缺 _note 子字段说明数值来源与适用条件")
    ok("一.8", f"命名四分类扫描 {n_fields} 个分类字段")


# ---------- 检查 4：一.10 语义判例 ----------

def is_dev_key(k):
    lk = k.lower()
    return "deviation" in lk and "std" not in lk


def is_coop_key(k):
    return "cooperation" in k.lower()


def is_min_key(k):
    return "min_observed" in k.lower()


def check_semantics(data, results_dir):
    items = list(walk(data))
    # 判例 1：偏离收益 < 合作收益（博弈类）
    devs = [(p, k, v) for p, k, v, _ in items if is_dev_key(k) and is_num(v) and "obj" in k.lower()]
    coops = [(p, k, v) for p, k, v, _ in items if is_coop_key(k) and is_num(v)]
    for p, k, v in devs:
        best = None
        for cp, ck, cvv in coops:
            score = common_prefix_len(p, cp)
            if best is None or score > best[0]:
                best = (score, cp, ck, cvv)
        if best is None:
            warn("一.10", p, "发现偏离收益字段但未找到对应合作收益字段，需人工核查偏离收益对比")
            continue
        _, cp, ck, cvv = best
        if float(v) >= float(cvv):
            error("一.10", p,
                  f"偏离收益 {v} ≥ 合作收益 {ck}={cvv}——偏离收益必须 < 合作收益才能维持合作均衡（逻辑错误，须重求解）")
        else:
            ok("一.10", f"{p}: 偏离收益 {v} < {ck}={cvv} ✓")
    # 判例 2：min_observed 取自全路径最小值
    mins = [(p, float(v)) for p, k, v, _ in items if is_min_key(k) and is_num(v)]
    if not mins:
        return
    series = load_numeric_series(results_dir) if results_dir else []
    if not series:
        src = f"所给目录 {results_dir} 未加载到数值序列" if results_dir else "未提供数据目录（可传 project/results 作第二参数）"
        warn("一.10", "", f"发现 {len(mins)} 个 min_observed 字段——{src}，请人工确认取自全路径最小值")
        return
    unmatched = [(p, v) for p, v in mins
                 if not any(abs(min(s) - v) < 1e-9 for s in series if s)]
    n_matched = len(mins) - len(unmatched)
    if n_matched:
        ok("一.10", f"{n_matched} 个 min_observed 与数据序列最小值一致")
    if unmatched:
        locs = "; ".join(f"{p}={v}" for p, v in unmatched[:8])
        more = f" 等 {len(unmatched)} 处" if len(unmatched) > 8 else ""
        warn("一.10", "",
             f"{len(unmatched)} 个 min_observed 未匹配到数据序列最小值，需人工核查是否取自全路径最小值: {locs}{more}")


def load_numeric_series(results_dir):
    series = []
    rd = Path(results_dir)
    if not rd.is_dir():
        return series
    for f in rd.rglob("*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for _, _, v, _ in walk(d):
            if not (isinstance(v, list) and len(v) >= 2):
                continue
            if all(is_num(x) for x in v):
                series.append([float(x) for x in v])
            elif all(isinstance(x, dict) for x in v):
                common = set.intersection(*[set(x) for x in v])
                for kk in common:
                    col = [x[kk] for x in v if is_num(x.get(kk))]
                    if len(col) >= 2:
                        series.append([float(x) for x in col])
    return series


# ---------- 检查 5：一.11 题目原文核心参数逐字回读（A-01 机查化，C-02） ----------

def check_source_parameters(modeling_plan, project_code_dir):
    """读取 modeling_plan.json 的 source_parameters 字段，
    与 project/*.py 中硬编码数值常量逐项比对；
    任一题目参数值在代码中找不到或仅找到相近值 → ERROR；字段缺失 → WARN。"""
    if not isinstance(modeling_plan, dict):
        return
    sp = modeling_plan.get("source_parameters")
    if sp is None:
        warn("一.11", "$.modeling_plan.source_parameters",
             "source_parameters 字段缺失——A-01 '题目原文核心参数逐字回读' 未执行")
        return
    if not isinstance(sp, dict):
        warn("一.11", "$.modeling_plan.source_parameters",
             f"source_parameters 字段类型异常：{type(sp).__name__}，期望 dict{{name: value}}")
        return
    if not sp:
        warn("一.11", "$.modeling_plan.source_parameters",
             "source_parameters 字段为空——A-01 未执行或题目无数值参数")
        return

    py_texts = []
    if project_code_dir:
        pcd = Path(project_code_dir)
        if pcd.is_dir():
            for f in pcd.rglob("*.py"):
                try:
                    py_texts.append((str(f), f.read_text(encoding="utf-8", errors="ignore")))
                except Exception:
                    pass
    if not py_texts:
        warn("一.11", "",
             f"未在 {project_code_dir} 找到 .py 文件——source_parameters 比对跳过")
        return

    n_ok = 0
    n_err = 0
    num_pat = re.compile(r"(?<![\w.])(\d+\.?\d*)(?![\w])")
    for name, value in sp.items():
        if not is_num(value) or isinstance(value, bool):
            warn("一.11", f"source_parameters.{name}",
                 f"参数值非数值类型：{type(value).__name__}，跳过比对")
            continue
        # 候选正则：110 / 110.0 / 110.00 等都视为等价，必须带数字边界检查
        # （字符串 in 操作会把 "110" 误匹配到 "1100"，导致读题误读漏判）
        cand_patterns = []
        if float(value).is_integer():
            iv = int(value)
            # 整数形式：110（前后均不是 [\w.]，避免误匹配 1100/abc110 等）
            cand_patterns.append(re.compile(rf"(?<![\w.]){iv}(?![\w.])"))
            # 浮点形式：110.0 / 110.00 / 110.000 等（后不跟数字或点）
            cand_patterns.append(re.compile(rf"(?<![\w.]){iv}\.0+(?![\w.])"))
        else:
            fv = float(value)
            cand_patterns.append(re.compile(rf"(?<![\w.]){re.escape(repr(fv))}(?![\w.])"))
            cand_patterns.append(re.compile(rf"(?<![\w.]){re.escape(str(fv))}(?![\w.])"))

        found = False
        for fname, text in py_texts:
            for pat in cand_patterns:
                if pat.search(text):
                    found = True
                    break
            if found:
                break
        if found:
            n_ok += 1
            ok("一.11", f"source_parameters.{name}={value}: 在代码中找到 ✓")
            continue

        # 找不到精确匹配 → 扫描相近值（疑似读题误读）
        similar = []
        seen = set()
        for fname, text in py_texts:
            for m in num_pat.finditer(text):
                try:
                    x = float(m.group(1))
                except Exception:
                    continue
                if x == value:
                    continue
                # 相近判定：差距 <= max(|value|*0.2, 5) 视为疑似误读
                diff = abs(x - value)
                threshold = max(abs(value) * 0.2, 5)
                if diff <= threshold and x not in seen:
                    seen.add(x)
                    similar.append((fname, m.group(1), x, diff))
        if similar:
            similar_str = "; ".join(
                f"{Path(f).name}: 含 {s} (差 {d:.2f})" for f, s, x, d in similar[:3])
            n_err += 1
            error("一.11", f"source_parameters.{name}",
                  f"题目参数 {name}={value} 未在代码中找到精确匹配，但找到相近值（{similar_str}）——疑似读题误读（A-01 拦截）")
        else:
            n_err += 1
            error("一.11", f"source_parameters.{name}",
                  f"题目参数 {name}={value} 未在代码中找到——需人工核查（A-01 拦截）")
    ok("一.11", f"source_parameters 扫描完成：{n_ok} 个匹配，{n_err} 个不一致")


# ---------- 检查 6：一.13 指标量纲一致性核查（A-03 半机查化，C-03） ----------

def check_indicator_dimension(modeling_plan):
    """检查 modeling_plan.json 的 indicator_dimension_check 字段，
    每个四元组（指标名→题目原义量纲→实际量纲→判定）的 judgment 不得为 ✗；
    字段缺失 → WARN；含 ✗ → ERROR。"""
    if not isinstance(modeling_plan, dict):
        return
    idc = modeling_plan.get("indicator_dimension_check")
    if idc is None:
        warn("一.13", "$.modeling_plan.indicator_dimension_check",
             "indicator_dimension_check 字段缺失——A-03 '指标量纲一致性核查' 未执行")
        return
    if not isinstance(idc, list) or not idc:
        warn("一.13", "$.modeling_plan.indicator_dimension_check",
             f"indicator_dimension_check 字段为空或类型异常：{type(idc).__name__}，期望 list")
        return

    n_ok = 0
    n_fail = 0
    for i, item in enumerate(idc):
        if not isinstance(item, dict):
            warn("一.13", f"indicator_dimension_check[{i}]",
                 f"四元组类型异常：{type(item).__name__}，期望 dict")
            continue
        # 支持中英文字段命名
        name = (item.get("indicator_name") or item.get("指标名")
                or item.get("name") or f"item_{i}")
        intended = (item.get("intended_dimension") or item.get("题目原义量纲")
                    or item.get("intended") or "")
        actual = (item.get("actual_dimension") or item.get("论文实际量纲")
                  or item.get("actual") or "")
        judgment = str(item.get("judgment") or item.get("判定")
                       or item.get("judgement") or "").strip()

        if judgment == "✓":
            n_ok += 1
        elif judgment == "✗":
            n_fail += 1
            error("一.13", f"indicator_dimension_check[{i}]",
                  f"指标 '{name}' 量纲判定为 ✗（题目原义：{intended}，论文实际：{actual}）——A-03 拦截")
        else:
            warn("一.13", f"indicator_dimension_check[{i}]",
                 f"指标 '{name}' 判定字段值无法解析：'{judgment}'，期望 ✓ 或 ✗")

    if n_ok:
        ok("一.13", f"indicator_dimension_check: {n_ok} 个指标量纲一致 ✓")


# ---------- 检查 7：P-1 活跃约束附派生量数值（条件触发，惯例 一.6） ----------

DERIVED_KEYS = re.compile(
    r"slack|margin|marginal|local_sensitivity|sensitivity|response|derived"
    r"|improvement|min_observed|max_observed|amplitude|gain|ratio", re.I)


def leaf_constraint_dicts(node, path):
    """递归取 active_constraints 下的叶子约束条目（含数值或字符串标量的 dict）。"""
    if isinstance(node, dict):
        if any(is_num(v) or isinstance(v, str) for v in node.values()):
            yield path, node
        else:
            for k, v in node.items():
                if isinstance(v, (dict, list)):
                    yield from leaf_constraint_dicts(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            if isinstance(v, dict):
                yield from leaf_constraint_dicts(v, f"{path}[{i}]")


def check_active_derived(data):
    nodes = [(p, v) for p, k, v, _ in walk(data) if k == "active_constraints"]
    for p, ac in nodes:
        if ac is None or isinstance(ac, str) or not ac:
            continue
        n = n_ok = 0
        had_finding = False
        for ep, ev in leaf_constraint_dicts(ac, p):
            n += 1
            nums = [(k, v) for k, v in ev.items() if is_num(v)]
            derived = [(k, v) for k, v in nums if DERIVED_KEYS.search(k)]
            if derived:
                n_ok += 1
            elif nums:
                had_finding = True
                names = ", ".join(k for k, _ in nums[:5])
                warn("P-1", ep,
                     f"约束条目含数值字段（{names}）但无 slack/边际响应/局部灵敏度候选名——请人工确认是否已附最优解处派生量数值（惯例 一.6）")
            else:
                had_finding = True
                error("P-1", ep,
                      "约束条目仅含状态/文本、无任何数值型派生量字段——契约要求 active/slack 状态 + 最优解处派生量数值（slack 量/边际响应/局部灵敏度其一，惯例 一.6）")
        if n and not had_finding:
            ok("P-1", f"{p}: 活跃约束派生量扫描 {n} 条（含派生量 {n_ok} 条）")


# ---------- 检查 8：P-2 叙述性文本内嵌数值核查（S3 必查项1 扩展） ----------

TEXT_NUM = re.compile(r"(?<![\w.])(\d+\.\d+|\d{3,})(?![\w.])|(?<![\w.])(\d+(?:\.\d+)?)\s*%")
SKIP_STR_KEYS = re.compile(r"source|url|link|reference|citation|convergence|path|file", re.I)
HIST_LABELS = ("早期估计", "演进", "历史口径")


def _text_numbers(s):
    """从叙述文本提取候选数值声明 (值, 是否百分数)；过滤年份噪声。"""
    out = []
    for m in TEXT_NUM.finditer(s):
        if m.group(2) is not None:
            try:
                out.append((float(m.group(2)), True))
            except Exception:
                pass
        else:
            try:
                v = float(m.group(1))
            except Exception:
                continue
            if 1900 <= v <= 2099:
                continue  # 年份/日期（含 2014.1 类浮点日期）
            out.append((v, False))
    return out


def _num_universe(*trees):
    vals = set()
    for t in trees:
        if t is None:
            continue
        for _, _, v, _ in walk(t):
            if is_num(v):
                vals.add(round(float(v), 9))
    return vals


def _in_universe(v, pct, universe):
    cands = {round(v, 9)}
    if pct:
        cands.add(round(v / 100.0, 9))
    return bool(cands & universe)


def check_narrative_numbers(data, modeling_plan, project_code_dir):
    universe = _num_universe(data, modeling_plan)
    # (a) JSON 字符串字段内嵌数值
    for tag, tree in (("solution.json", data), ("modeling_plan.json", modeling_plan)):
        if not isinstance(tree, dict):
            continue
        unmatched = []
        n_txt = 0
        for p, k, v, _ in walk(tree):
            if not isinstance(v, str) or len(v) < 20:
                continue
            if SKIP_STR_KEYS.search(k):
                continue
            nums = _text_numbers(v)
            if not nums:
                continue
            n_txt += 1
            if any(lbl in v for lbl in HIST_LABELS):
                continue
            for val, pct in nums:
                if not _in_universe(val, pct, universe):
                    unmatched.append((p, val, pct))
        unmatched = sorted(set(unmatched))
        if unmatched:
            ex = "; ".join(f"{p} 含 {v}{'%' if pc else ''}" for p, v, pc in unmatched[:8])
            more = f" 等 {len(unmatched)} 处" if len(unmatched) > 8 else ""
            warn("P-2", tag,
                 f"叙述性字符串字段内嵌数值 {len(unmatched)} 个未匹配任何结构化字段值（{ex}{more}）——请人工核对是否为陈旧口径并列入 S3 必查项1 核查记录；历史演进口径须标注'早期估计'字样")
        elif n_txt:
            ok("P-2", f"{tag}: {n_txt} 个叙述性字符串字段内嵌数值均匹配结构化字段或已标注历史口径")
    # (b) 代码注释中的参数取值声明 vs 同文件实现
    if not project_code_dir:
        return
    pcd = Path(project_code_dir)
    if not pcd.is_dir():
        return
    n_comment = 0
    n_bad_files = 0
    for f in pcd.rglob("*.py"):
        try:
            lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        code_text = "\n".join(l.split("#", 1)[0] for l in lines)
        code_nums = set()
        for m in TEXT_NUM.finditer(code_text):
            g = m.group(2) if m.group(2) is not None else m.group(1)
            try:
                code_nums.add(round(float(g), 9))
            except Exception:
                pass
        unmatched_c = []
        for ln, line in enumerate(lines, 1):
            if "#" not in line:
                continue
            comment = line.split("#", 1)[1]
            if len(comment) < 8:
                continue
            for val, pct in _text_numbers(comment):
                n_comment += 1
                cands = {round(val, 9)}
                if pct:
                    cands.add(round(val / 100.0, 9))
                if not (cands & code_nums):
                    unmatched_c.append((ln, val, pct))
        unmatched_c = sorted(set(unmatched_c))
        if unmatched_c:
            n_bad_files += 1
            ex = "; ".join(f"第{ln}行 {v}{'%' if pc else ''}" for ln, v, pc in unmatched_c[:5])
            more = f" 等 {len(unmatched_c)} 处" if len(unmatched_c) > 5 else ""
            warn("P-2", f.name,
                 f"注释中 {len(unmatched_c)} 个数值声明未在同文件代码实现中找到（{ex}{more}）——请人工核对注释与实现是否一致（P-2）")
    if n_comment and n_bad_files == 0:
        ok("P-2", f"代码注释数值声明扫描 {n_comment} 处：均与同文件实现一致")


# ---------- 检查 9：P-3 不确定性参数"登记-传播"映射（条件触发，惯例 一.1） ----------

REG_KEYS = re.compile(r"uncertain|random_param|stochastic", re.I)
MAP_KEYS = re.compile(r"propagation", re.I)


def check_uncertainty_propagation(modeling_plan, data):
    reg, reg_path = [], ""
    for p, k, v, _ in walk(modeling_plan):
        if (REG_KEYS.search(k) and isinstance(v, list) and v
                and all(isinstance(x, (str, dict)) for x in v) and len(v) > len(reg)):
            reg, reg_path = v, p
    if not reg:
        return  # 未登记不确定性参数——条件不触发
    maps = []
    for src in (modeling_plan, data):
        if not isinstance(src, dict):
            continue
        for p, k, v, _ in walk(src):
            if MAP_KEYS.search(k) and isinstance(v, (dict, list)) and v:
                maps.append((p, v))
    if not maps:
        warn("P-3", reg_path,
             f"读题阶段登记了 {len(reg)} 个不确定性/随机参数，但未检出'登记-传播'映射表字段——模型验证阶段须给出映射表（惯例 一.1，P-3）；若 MC 不适用并已附说明，可忽略")
        return
    mp, mv = maps[0]
    if len(mv) == len(reg):
        ok("P-3", f"不确定性登记-传播映射计数一致（{len(reg)} 项，{mp}）")
    else:
        warn("P-3", f"{reg_path} vs {mp}",
             f"登记参数 {len(reg)} 个 vs 映射表 {len(mv)} 项计数不一致——若属合并处理，请确认验证记录中已显式声明覆盖缺口（P-3）；否则须补映射")


# ---------- 检查 P11-S：灵敏度覆盖与扰动幅度 ----------

PCT_PAT = re.compile(r"(\d+(?:\.\d+)?)\s*%")


def _sens_param_names(sens):
    """从 sensitivity 结构提取扰动参数名列表（兼容两种布局）。"""
    names = []
    if not isinstance(sens, dict):
        return names
    if isinstance(sens.get("parameters"), list):
        names += [str(p) for p in sens["parameters"]]
    for v in sens.values():
        if isinstance(v, dict) and isinstance(v.get("perturbations"), list):
            names += [str(p.get("param", "")) for p in v["perturbations"]
                      if isinstance(p, dict)]
    return names


def check_sensitivity_coverage(data):
    subs = find_subproblems(data)
    for name, sub in subs.items():
        score = sum(1 for f in REQUIRED if f in sub)
        if score == 0 or "sensitivity" not in sub:
            continue
        names = _sens_param_names(sub["sensitivity"])
        if not names:
            error("P11-S", name, "sensitivity 无任何扰动参数（须对核心参数做扰动）")
            continue
        pcts = [float(m) for n in names for m in PCT_PAT.findall(n)]
        if pcts:
            if max(pcts) < 10:
                error("P11-S", name, f"最大扰动幅度 {max(pcts)}% < 10%（prompt 要求 ±5%/±10%/±20%）")
            else:
                ok("P11-S", f"{name}: {len(names)} 个扰动参数，最大幅度 {max(pcts)}%")
        else:
            warn("P11-S", name, f"{len(names)} 个扰动参数但幅度无法机读（参数名无百分比），人工确认是否覆盖 ±10% 以上")


# ---------- 检查 P11-M：蒙特卡洛次数下限 ----------

def check_mc_count(data):
    nodes = [(p, v) for p, k, v, _ in walk(data) if k == "monte_carlo"]
    for p, mc in nodes:
        if mc is None:
            continue
        n = mc.get("n_sim") if isinstance(mc, dict) else None
        if not is_num(n):
            warn("P11-M", p, "monte_carlo 缺 n_sim 字段，无法校验仿真次数")
        elif n < 1000:
            error("P11-M", p, f"仿真次数 {int(n)} < 1000（prompt 要求 ≥1000）")
        else:
            ok("P11-M", f"{p}: n_sim={int(n)} ≥1000")


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    # 开关与位置参数分离：--selfcheck 只打印不落盘；--report 指定落盘路径
    selfcheck = "--selfcheck" in sys.argv
    report_override = None
    if "--report" in sys.argv:
        i = sys.argv.index("--report")
        if i + 1 >= len(sys.argv):
            print("✗ 用法错误：--report 后须跟路径")
            sys.exit(2)
        report_override = Path(sys.argv[i + 1])
    positional = [a for a in sys.argv[1:]
                  if not a.startswith("--") and a != str(report_override or "")]
    target = Path(positional[0])
    results_dir = positional[1] if len(positional) > 1 else None
    if not target.is_file():
        print(f"✗ 文件不存在: {target}")
        sys.exit(2)
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"✗ JSON 解析失败: {e}")
        sys.exit(2)

    check_contract(data)
    check_convergence(data)
    check_naming(data)
    check_semantics(data, results_dir)
    check_active_derived(data)
    check_sensitivity_coverage(data)
    check_mc_count(data)

    # C-02/C-03: modeling_plan.json 字段检查（A-01/A-03 机查化）
    # 自动查找同名目录下的 modeling_plan.json
    modeling_plan_path = target.parent / "modeling_plan.json"
    modeling_plan = None
    if modeling_plan_path.is_file():
        try:
            modeling_plan = json.loads(modeling_plan_path.read_text(encoding="utf-8"))
        except Exception as e:
            warn("一.11/一.13", str(modeling_plan_path),
                 f"modeling_plan.json 解析失败：{e}")
    else:
        warn("一.11/一.13", "",
             f"未找到 modeling_plan.json（期望 {modeling_plan_path}），A-01/A-03 机查跳过")

    # 推导 project 代码目录（project_code_dir）
    project_code_dir = None
    if results_dir:
        rd = Path(results_dir)
        if rd.name == "results" and rd.parent.name == "project":
            project_code_dir = str(rd.parent)
        else:
            for cand in [rd / "project", rd.parent / "project"]:
                if cand.is_dir():
                    project_code_dir = str(cand)
                    break

    if modeling_plan is not None:
        check_source_parameters(modeling_plan, project_code_dir)
        check_indicator_dimension(modeling_plan)
        check_uncertainty_propagation(modeling_plan, data)
    check_narrative_numbers(data, modeling_plan, project_code_dir)

    n_err = sum(1 for f in FINDINGS if f["level"] == "ERROR")
    n_warn = sum(1 for f in FINDINGS if f["level"] == "WARN")
    n_pass = sum(1 for f in FINDINGS if f["level"] == "PASS")

    icon = {"ERROR": "✗", "WARN": "⚠", "PASS": "✓"}
    for f in FINDINGS:
        loc = f" {f['location']}" if f["location"] else ""
        print(f"{icon[f['level']]} {f['level']:<5} [{f['rule']}]{loc} {f['message']}")
    print(f"\n汇总: {n_err} ERROR / {n_warn} WARN / {n_pass} PASS")

    report = {"target": str(target),
              "selfcheck": selfcheck,
              "summary": {"ERROR": n_err, "WARN": n_warn, "PASS": n_pass},
              "findings": FINDINGS}
    if selfcheck:
        # subagent 自检：禁止落盘，避免覆写编排器 MODELING 门的权威报告
        print("\n[selfcheck] 自检模式：结果仅打印，不写 contract_check_report.json"
              "（权威报告仅由编排器不带 --selfcheck 的运行产生）")
        sys.exit(1 if n_err else 0)
    # 报告规范路径 = 项目根（orchestrator.md §4 / 产物注册表）；
    # solution.json 规范位置为 {项目根}/result_bundle/solution.json
    if report_override is not None:
        out = report_override
    elif target.parent.name == "result_bundle":
        out = target.parent.parent / "contract_check_report.json"
    else:
        out = target.parent / "contract_check_report.json"
        print(f"⚠ WARN  [契约] solution.json 不在 result_bundle/ 下，报告回退落盘同目录: {out}")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"报告已写入: {out}")
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()
