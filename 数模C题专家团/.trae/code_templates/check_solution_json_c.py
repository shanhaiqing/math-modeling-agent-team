#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
check_solution_json_c.py — C 版 solution.json 契约校验器（机查版）

把以下判据从"靠注意力执行的 prompt 检查"转为确定性机器检查：
  [契约]  AGENTS.md "handoff 契约"节 —— 子问题必填字段存在性
          prompt 位置：.trae/agents/modeling-solver.md "打包产出"节
  [数.3]  papers/数据题专项惯例.md —— 泄漏禁区：train_test_isolation 声明存在性
          + 泄漏嫌疑字段名扫描 + 时序随机划分检测
          prompt 位置：.trae/agents/modeling-solver.md 阶段 2 GQ3 + 步骤 3.3
  [数.4]  papers/数据题专项惯例.md —— 指标-任务匹配（task_type × 指标族矩阵）
          prompt 位置：.trae/agents/modeling-solver.md 步骤 3.3 求解验证
  [数.5]  papers/数据题专项惯例.md —— 数据扰动灵敏度字段存在性
          prompt 位置：.trae/agents/modeling-solver.md 步骤 3.3 灵敏度分析
  [数.6]  papers/数据题专项惯例.md —— 基线对比（model.selection 含 baseline）
          prompt 位置：.trae/agents/modeling-solver.md 步骤 3.1 算法选择
  [一.1]  papers/国赛公开惯例.md —— monte_carlo.convergence 与 std/mean 一致性（题型无关，复用）
  [一.11] papers/国赛公开惯例.md —— 题目原文核心参数逐字回读（题型无关，复用）；
          读取 modeling_plan.json 的 source_parameters 与 project/*.py 硬编码值比对
  [一.13] papers/国赛公开惯例.md —— 指标量纲一致性核查四元组判定

同步维护条款（T-1）：新增或修改机查项时，须同步核对对应 agent prompt 是否已下达该要求。
机查要求集不得超出 prompt 要求集（详见 .trae/papers/国赛公开惯例.md 五.2）。

用法:
  python check_solution_json_c.py <solution.json路径> [project_results目录]

退出码: 0 = 无 ERROR（可有 WARN）；1 = 存在 ERROR；2 = 用法/读取错误
输出:   控制台逐条打印 + 在 solution.json 同目录写 contract_check_report.json
分级:   ERROR = 必须当场修复（阻塞打包）；WARN = 需人工判定；PASS = 通过
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


# ---------- 检查 1：handoff 契约字段存在性 ----------

REQUIRED = ["task_type", "objective_or_goal", "metrics", "model", "validation",
            "preprocessing", "data_lineage", "sensitivity", "monte_carlo"]

TASK_TYPES = {"prediction", "classification", "clustering", "evaluation",
              "forecasting", "statistical_inference", "descriptive",
              "optimization_downstream", "regression", "inference"}


def find_subproblems(data):
    if isinstance(data, dict) and "task_type" in data and "metrics" in data:
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


def norm_task(v):
    s = str(v).strip().lower()
    return s


def check_contract(data):
    subs = find_subproblems(data)
    if not subs:
        warn("契约", "$", "未识别子问题结构（未找到含 ≥3 个契约字段的字典），必填字段检查跳过")
        return []
    seen = []
    for name, sub in subs.items():
        score = sum(1 for f in REQUIRED if f in sub)
        if score == 0:
            continue
        missing = [f for f in REQUIRED if f not in sub]
        if missing:
            error("契约", name, f"子问题缺必填字段: {', '.join(missing)}")
        else:
            ok("契约", f"{name}: 必填字段齐全（{len(REQUIRED)} 项）")
        tt = sub.get("task_type")
        if tt is not None:
            t = norm_task(tt)
            if t not in TASK_TYPES:
                warn("契约", f"{name}.task_type",
                     f"task_type 值 '{tt}' 不在契约枚举内（{sorted(TASK_TYPES)}）——请人工确认")
            seen.append((name, t, sub))
    return seen


# ---------- 检查 2：数.4 指标-任务匹配矩阵 ----------

METRIC_FAMILIES = {
    "prediction": re.compile(r"rmse|mae|mape|r2|r_squared|mse|smape", re.I),
    "regression": re.compile(r"rmse|mae|mape|r2|r_squared|mse|smape", re.I),
    "forecasting": re.compile(r"rmse|mae|mape|smape|backtest|rolling", re.I),
    "classification": re.compile(r"accuracy|f1|auc|precision|recall|confusion|roc", re.I),
    "clustering": re.compile(r"silhouette|calinski|ch_index|davies|db_index|ari|nmi", re.I),
    "evaluation": re.compile(r"score|ranking|rank|weight|robustness|sensitivity_rank", re.I),
    "statistical_inference": re.compile(r"p_value|pvalue|ci_|confidence|effect_size|statistic", re.I),
    "inference": re.compile(r"p_value|pvalue|ci_|confidence|effect_size|statistic", re.I),
    "descriptive": re.compile(r"mean|std|median|quantile|distribution|missing", re.I),
    "optimization_downstream": re.compile(r"objective|profit|cost|revenue|value", re.I),
}


def _metric_names(metrics):
    names = []
    if isinstance(metrics, dict):
        for k, v in metrics.items():
            names.append(k)
            if isinstance(v, dict):
                names.extend(v.keys())
    elif isinstance(metrics, list):
        for item in metrics:
            if isinstance(item, dict):
                names.extend(item.keys())
            elif isinstance(item, str):
                names.append(item)
    return names


def check_metric_task_match(seen):
    for name, t, sub in seen:
        pat = METRIC_FAMILIES.get(t)
        if pat is None:
            continue
        names = _metric_names(sub.get("metrics"))
        if not names:
            error("数.4", f"{name}.metrics", "metrics 字段为空或结构异常——契约要求 指标名+数值+split 口径")
            continue
        hits = [n for n in names if pat.search(n)]
        if not hits:
            error("数.4", f"{name}.metrics",
                  f"task_type='{t}' 但指标名（{', '.join(names[:6])}）无一匹配该任务指标族 {pat.pattern}——指标-任务不匹配（数.4）")
        else:
            ok("数.4", f"{name}: 指标族匹配（{', '.join(hits[:4])}）")


# ---------- 检查 3：validation 与过拟合自查字段 ----------

def check_validation(seen):
    for name, t, sub in seen:
        val = sub.get("validation")
        if val is None:
            continue
        if not isinstance(val, dict):
            error("契约", f"{name}.validation", "validation 字段应为 dict（method/scores/overfitting_check）")
            continue
        missing = [f for f in ("method", "scores", "overfitting_check") if f not in val]
        if missing:
            error("契约", f"{name}.validation", f"validation 缺子字段: {', '.join(missing)}")
        else:
            ok("契约", f"{name}.validation: method/scores/overfitting_check 齐全")
        oc = val.get("overfitting_check")
        if isinstance(oc, str) and len(oc.strip()) < 10:
            warn("数.5", f"{name}.validation.overfitting_check",
                 "过拟合自查仅一句话，缺 train/test 差距数值——请人工确认（数.5/卡片 05 防线）")


# ---------- 检查 4：数.3 预处理四子项 + 隔离声明 + 泄漏嫌疑扫描 ----------

LEAK_SUSPECT = re.compile(
    r"fit_on_full|fit_all|preprocess_full|random_kfold|random_split|shuffle_split"
    r"|scaler_all|leak", re.I)
TIME_HINT = re.compile(r"forecast|time_series|时序|rolling", re.I)
RANDOM_HINT = re.compile(r"random.*(split|kfold|fold)|shuffle", re.I)


def check_preprocessing(seen):
    for name, t, sub in seen:
        pp = sub.get("preprocessing")
        if pp is None:
            continue
        if not isinstance(pp, dict):
            error("数.3", f"{name}.preprocessing", "preprocessing 字段应为 dict")
            continue
        missing = [f for f in ("missing", "outliers", "encoding", "scaling") if f not in pp]
        if missing:
            error("数.3", f"{name}.preprocessing",
                  f"预处理四子项缺失: {', '.join(missing)}（数.2/数.3，不适用须显式填 'none' 并说明）")
        iso = pp.get("train_test_isolation")
        if iso is None:
            error("数.3", f"{name}.preprocessing.train_test_isolation",
                  "缺训练/测试隔离声明——泄漏禁区（数.3）")
        elif isinstance(iso, str) and len(iso.strip()) < 15:
            warn("数.3", f"{name}.preprocessing.train_test_isolation",
                 "隔离声明过短，须含'预处理统计量仅在训练集拟合'语义——请人工确认")
        else:
            ok("数.3", f"{name}.preprocessing: 四子项与隔离声明齐全")
        # 泄漏嫌疑字段名扫描（全树）
        suspects = [p for p, k, v, _ in walk(sub) if LEAK_SUSPECT.search(k)]
        if suspects:
            warn("数.3", name,
                 f"检出泄漏嫌疑字段名 {suspects[:5]}——请人工确认未在全数据上拟合预处理/未随机划分（数.3）")
        # 时序任务随机划分检测
        blob = json.dumps(sub, ensure_ascii=False)
        if TIME_HINT.search(t + blob) and RANDOM_HINT.search(blob):
            warn("数.3", name,
                 "时序相关任务中检出 random split/kfold 字样——时间序列禁止随机划分（卡片 04/10），请人工确认验证方案保序")


# ---------- 检查 5：数.5 灵敏度 + 数.6 基线 ----------

def check_sensitivity_baseline(seen):
    for name, t, sub in seen:
        sens = sub.get("sensitivity")
        if sens is None:
            continue
        if isinstance(sens, str) and sens.strip().lower() in ("none", "null", "不适用"):
            warn("数.5", f"{name}.sensitivity", "灵敏度标注不适用——需确认已附理由（数.5 三选一）")
        model = sub.get("model")
        if isinstance(model, dict):
            sel = model.get("selection")
            if sel is None:
                error("数.6", f"{name}.model.selection",
                      "缺 selection 字段——契约要求 ≥2 候选对比 + 基线 + 选择理由（数.6）")
            else:
                s = json.dumps(sel, ensure_ascii=False).lower()
                if "baseline" not in s and "基线" not in s:
                    error("数.6", f"{name}.model.selection",
                          "selection 未含基线对比——基线对比强制（数.6）")
                else:
                    ok("数.6", f"{name}.model.selection: 含基线对比")


# ---------- 检查 6：数值自洽（指标值域） ----------

RANGE_RULES = [
    (re.compile(r"^r2$|r_squared", re.I), None, 1.0, "R² 不应 > 1"),
    (re.compile(r"accuracy|f1|auc|precision|recall", re.I), 0.0, 1.0, "应在 [0,1]"),
    (re.compile(r"silhouette", re.I), -1.0, 1.0, "轮廓系数应在 [-1,1]"),
    (re.compile(r"rmse|mae|mape|mse", re.I), 0.0, None, "误差应 ≥ 0"),
    (re.compile(r"p_value|pvalue", re.I), 0.0, 1.0, "p 值应在 [0,1]"),
]


def check_numeric_sanity(seen):
    n = 0
    for name, t, sub in seen:
        for p, k, v, _ in walk(sub.get("metrics")):
            if not is_num(v):
                continue
            for pat, lo, hi, desc in RANGE_RULES:
                if not pat.search(k):
                    continue
                n += 1
                fv = float(v)
                if (lo is not None and fv < lo - 1e-9) or (hi is not None and fv > hi + 1e-9):
                    error("自洽", f"{name}.metrics.{p}",
                          f"指标 '{k}'={v} 越界：{desc}——数值自洽检查拦截")
    if n:
        ok("自洽", f"指标值域扫描 {n} 处")


# ---------- 检查 7：一.1 convergence 判定（题型无关，复用） ----------

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
        elif "converged" in low or "收敛" in conv:
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
                ok("一.1", f"{p}: 正确报告未收敛（std/mean={f'{cv:.2%}' if cv is not None else '未报告'}）")
        else:
            if cv is not None and cv > thr:
                error("一.1", f"{p}.convergence",
                      f"字段值含 'converged' 但 std/mean={cv:.2%} > 阈值 {thr:.0%}，禁止硬编码 'converged'")
            elif cv is None:
                warn("一.1", f"{p}.convergence",
                     "字段值未含 std/mean 实际数值，疑似硬编码")
            else:
                ok("一.1", f"{p}: convergence 与 std/mean={cv:.2%} 一致")


# ---------- 检查 8：一.11 题目原文核心参数逐字回读（复用） ----------

def check_source_parameters(modeling_plan, project_code_dir):
    if not isinstance(modeling_plan, dict):
        return
    sp = modeling_plan.get("source_parameters")
    if sp is None:
        warn("一.11", "$.modeling_plan.source_parameters",
             "source_parameters 字段缺失——'题目原文核心参数逐字回读' 未执行")
        return
    if not isinstance(sp, dict) or not sp:
        warn("一.11", "$.modeling_plan.source_parameters",
             "source_parameters 字段为空或类型异常")
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
        warn("一.11", "", f"未在 {project_code_dir} 找到 .py 文件——比对跳过")
        return
    n_ok = n_err = 0
    num_pat = re.compile(r"(?<![\w.])(\d+\.?\d*)(?![\w])")
    for name, value in sp.items():
        if not is_num(value):
            warn("一.11", f"source_parameters.{name}", "参数值非数值，跳过比对")
            continue
        cand_patterns = []
        if float(value).is_integer():
            iv = int(value)
            cand_patterns.append(re.compile(rf"(?<![\w.]){iv}(?![\w.])"))
            cand_patterns.append(re.compile(rf"(?<![\w.]){iv}\.0+(?![\w.])"))
        else:
            fv = float(value)
            cand_patterns.append(re.compile(rf"(?<![\w.]){re.escape(repr(fv))}(?![\w.])"))
            cand_patterns.append(re.compile(rf"(?<![\w.]){re.escape(str(fv))}(?![\w.])"))
        found = any(pat.search(text) for _, text in py_texts for pat in cand_patterns)
        if found:
            n_ok += 1
            continue
        similar = []
        seen_vals = set()
        for fname, text in py_texts:
            for m in num_pat.finditer(text):
                try:
                    x = float(m.group(1))
                except Exception:
                    continue
                if x == value or x in seen_vals:
                    continue
                if abs(x - value) <= max(abs(value) * 0.2, 5):
                    seen_vals.add(x)
                    similar.append((Path(fname).name, x))
        n_err += 1
        if similar:
            ss = "; ".join(f"{f}: 含 {x}" for f, x in similar[:3])
            error("一.11", f"source_parameters.{name}",
                  f"题目参数 {name}={value} 未在代码中找到精确匹配，但找到相近值（{ss}）——疑似读题误读")
        else:
            error("一.11", f"source_parameters.{name}",
                  f"题目参数 {name}={value} 未在代码中找到——需人工核查")
    ok("一.11", f"source_parameters 扫描完成：{n_ok} 个匹配，{n_err} 个不一致")


# ---------- 检查 9：一.13 指标量纲一致性核查（复用） ----------

def check_indicator_dimension(modeling_plan):
    if not isinstance(modeling_plan, dict):
        return
    idc = modeling_plan.get("indicator_dimension_check")
    if idc is None:
        warn("一.13", "$.modeling_plan.indicator_dimension_check",
             "indicator_dimension_check 字段缺失——指标量纲一致性核查未执行")
        return
    if not isinstance(idc, list) or not idc:
        warn("一.13", "$.modeling_plan.indicator_dimension_check", "字段为空或类型异常")
        return
    n_ok = 0
    for i, item in enumerate(idc):
        if not isinstance(item, dict):
            continue
        name = (item.get("indicator_name") or item.get("指标名") or item.get("name") or f"item_{i}")
        judgment = str(item.get("judgment") or item.get("判定") or "").strip()
        if judgment == "✓":
            n_ok += 1
        elif judgment == "✗":
            error("一.13", f"indicator_dimension_check[{i}]",
                  f"指标 '{name}' 量纲判定为 ✗——拦截")
        else:
            warn("一.13", f"indicator_dimension_check[{i}]",
                 f"指标 '{name}' 判定字段值无法解析：'{judgment}'")
    if n_ok:
        ok("一.13", f"indicator_dimension_check: {n_ok} 个指标量纲一致 ✓")


# ---------- 主流程 ----------

def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    target = Path(sys.argv[1])
    results_dir = sys.argv[2] if len(sys.argv) > 2 else None
    if not target.is_file():
        print(f"✗ 文件不存在: {target}")
        sys.exit(2)
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"✗ JSON 解析失败: {e}")
        sys.exit(2)

    seen = check_contract(data)
    check_metric_task_match(seen)
    check_validation(seen)
    check_preprocessing(seen)
    check_sensitivity_baseline(seen)
    check_numeric_sanity(seen)
    check_convergence(data)

    modeling_plan_path = target.parent / "modeling_plan.json"
    modeling_plan = None
    if modeling_plan_path.is_file():
        try:
            modeling_plan = json.loads(modeling_plan_path.read_text(encoding="utf-8"))
        except Exception as e:
            warn("一.11/一.13", str(modeling_plan_path), f"modeling_plan.json 解析失败：{e}")
    else:
        warn("一.11/一.13", "", f"未找到 modeling_plan.json（期望 {modeling_plan_path}），回读/量纲机查跳过")

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

    n_err = sum(1 for f in FINDINGS if f["level"] == "ERROR")
    n_warn = sum(1 for f in FINDINGS if f["level"] == "WARN")
    n_pass = sum(1 for f in FINDINGS if f["level"] == "PASS")

    icon = {"ERROR": "✗", "WARN": "⚠", "PASS": "✓"}
    for f in FINDINGS:
        loc = f" {f['location']}" if f["location"] else ""
        print(f"{icon[f['level']]} {f['level']:<5} [{f['rule']}]{loc} {f['message']}")
    print(f"\n汇总: {n_err} ERROR / {n_warn} WARN / {n_pass} PASS")

    report = {"target": str(target),
              "summary": {"ERROR": n_err, "WARN": n_warn, "PASS": n_pass},
              "findings": FINDINGS}
    out = target.parent / "contract_check_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"报告已写入: {out}")
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()
