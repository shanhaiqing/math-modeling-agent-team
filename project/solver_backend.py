#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
solver_backend.py — 统一求解后端（开源确定性求解器）

用途：各求解脚本统一调用。以结构化建模声明为输入，
统一封装 pulp（MIP/LP）与 cvxpy（凸优化 LP/QP），自动选择 HiGHS / CBC 开源后端，
并透传求解器的**原生元数据**（status / mip_gap / solve_time / 活跃约束 slack），
最优性信息以求解器原生输出为准。

说明：
- 建模声明为结构化字典（变量/目标/约束），求解逻辑与模型声明分离。
- 结果字段固定为 objective_value / status / MIPGap / active_constraints / solver
  等通用字段。
- 通用求解引擎，不含题目特定逻辑。
- 依赖：pulp >= 3.0（自带 CBC，可选 HiGHS_CMD）、cvxpy >= 1.5（内置 HiGHS）。
  安装：`pip install pulp cvxpy`（HiGHS 由 highspy 提供）。

适用范围：
- 本后端仅覆盖线性 / MIP / 凸 LP / 凸 QP。结构化声明基于线性规划标准形式
  （{变量/目标/约束} + 系数 + 上下界 + 约束类型）。
- 非线性（NLP / MIQP / MINLP）或含复杂逻辑约束的问题不适用本后端，
  应改用 NLP 求解器 / 启发式 / 枚举方案。
- 本后端保证代数正确性，领域语义正确性由建模阶段保证。

用法简要（详见各函数 docstring）：
    from solver_backend import solve_mip, solve_lp, SolveResult
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np

try:
    import pulp
except Exception as _e:  # pragma: no cover
    pulp = None
    _PULP_IMPORT_ERR = _e
else:
    _PULP_IMPORT_ERR = None

try:
    import cvxpy as cp
except Exception as _e:  # pragma: no cover
    cp = None
    _CVXPY_IMPORT_ERR = _e
else:
    _CVXPY_IMPORT_ERR = None


# ============================================================
# 数据容器
# ============================================================

@dataclass
class SolveResult:
    """统一求解结果。"""
    status: str                    # optimal / feasible / infeasible / time_limit / error
    objective_value: Optional[float]
    mip_gap: Optional[float]       # 原生最优性间隙（精确算法核心指标）
    solve_time: float              # 秒
    variable_values: Dict[str, float] = field(default_factory=dict)
    active_constraints: List[Dict[str, Any]] = field(default_factory=list)
    solver: str = ""               # 实际使用的求解器名（如 HiGHS / CBC / CLARABEL）
    detail: str = ""               # 附加说明（如 IIS / 冲突约束提示）

    def to_summary_dict(self) -> Dict[str, Any]:
        """转为标准字段摘要字典。"""
        return {
            "status": self.status,
            "objective_value": self.objective_value,
            "MIPGap": self.mip_gap,
            "solve_time": round(self.solve_time, 4),
            "solver": self.solver,
            "active_constraints": self.active_constraints,
        }


# ============================================================
# 求解后端探测
# ============================================================

def detect_backend() -> Dict[str, bool]:
    """返回当前环境可用的求解后端。"""
    info = {"pulp": pulp is not None, "cvxpy": cp is not None,
            "cbc": False, "highs": False}
    if _PULP_IMPORT_ERR:
        info["pulp_detail"] = str(_PULP_IMPORT_ERR)
    if _CVXPY_IMPORT_ERR:
        info["cvxpy_detail"] = str(_CVXPY_IMPORT_ERR)
    if pulp is not None:
        try:
            info["cbc"] = pulp.PULP_CBC_CMD().available()
        except Exception:
            info["cbc"] = False
        try:
            info["highs"] = pulp.HiGHS_CMD().available()
        except Exception:
            info["highs"] = False
    if cp is not None:
        try:
            info["highs"] = info["highs"] or ("HIGHS" in cp.installed_solvers())
        except Exception:
            pass
    return info


def _pick_solver(prob: "pulp.LpProblem", prefer: str = "auto",
                 gap_rel: float = 0.01,
                 time_limit: Optional[float] = None) -> "Callable":
    """为 pulp 问题选择可用后端。auto 优先 HiGHS，回退 CBC。
    gap_rel / time_limit 透传给求解器原生参数（gapRel / timeLimit）。"""
    kwargs: Dict[str, Any] = {"msg": False, "gapRel": gap_rel}
    if time_limit is not None:
        kwargs["timeLimit"] = time_limit
    if prefer == "highs" and pulp is not None and pulp.HiGHS_CMD().available():
        return pulp.HiGHS_CMD(**kwargs)
    if prefer == "cbc" and pulp is not None and pulp.PULP_CBC_CMD().available():
        return pulp.PULP_CBC_CMD(**kwargs)
    # auto
    if pulp is not None and pulp.HiGHS_CMD().available():
        return pulp.HiGHS_CMD(**kwargs)
    if pulp is not None and pulp.PULP_CBC_CMD().available():
        return pulp.PULP_CBC_CMD(**kwargs)
    return None


# ============================================================
# MIP / LP 求解接口
# ============================================================

def solve_mip(problem: Dict[str, Any],
              mip_gap: float = 0.01,
              time_limit: int = 3600,
              backend: str = "auto") -> SolveResult:
    """
    求解 MIP / LP（使用 pulp + HiGHS/CBC）。

    参数 problem 为结构化建模声明：
        {
          "name": "mip_model",
          "sense": "min" | "max",
          "variables": [ {"name": "x_0_0", "low": 0, "high": None, "cat": "Binary"|"Integer"|"Continuous"} ],
          "objective": {"coefficients": {var_name: coeff}, "constant": 0.0},
          "constraints": [ {"name": "c0", "coeffs": {var_name: coeff}, "sense": "<="|"=="|">=", "rhs": value} ]
        }
    """
    if pulp is None:
        return SolveResult("error", None, None, 0.0, detail=f"pulp 未安装: {_PULP_IMPORT_ERR}")
    t0 = time.time()
    sense = problem.get("sense", "min")
    prob = pulp.LpProblem(problem.get("name", "mip_model"),
                          pulp.LpMinimize if sense == "min" else pulp.LpMaximize)

    # 变量
    var_objs = {}
    for v in problem.get("variables", []):
        cat_map = {"Binary": pulp.LpBinary, "Integer": pulp.LpInteger,
                   "Continuous": pulp.LpContinuous}
        var_objs[v["name"]] = pulp.LpVariable(
            v["name"], lowBound=v.get("low"), upBound=v.get("high"),
            cat=cat_map.get(v.get("cat", "Continuous"), pulp.LpContinuous))

    # 目标
    obj = problem.get("objective", {})
    coeffs = obj.get("coefficients", {})
    constant = obj.get("constant", 0.0)
    expr = pulp.lpSum(coeffs[k] * var_objs[k] for k in coeffs if k in var_objs) + constant
    prob.setObjective(expr)

    # 约束（pulp 3.x：用 += 一次性设定表达式 + 操作符 + rhs）
    for c in problem.get("constraints", []):
        cexpr = pulp.lpSum(c["coeffs"][k] * var_objs[k] for k in c["coeffs"] if k in var_objs)
        sense_op = c.get("sense", "<=")
        if sense_op == "<=":
            prob += cexpr <= c["rhs"], c["name"]
        elif sense_op == ">=":
            prob += cexpr >= c["rhs"], c["name"]
        else:
            prob += cexpr == c["rhs"], c["name"]

    solver = _pick_solver(prob, backend, gap_rel=mip_gap, time_limit=time_limit)
    if solver is None:
        return SolveResult("error", None, None, time.time() - t0,
                           detail="无可用求解后端（需 pulp 自带 CBC 或 HiGHS）")

    prob.solve(solver)
    elapsed = time.time() - t0
    return _collect_pulp_result(prob, var_objs, elapsed, time_limit=time_limit)


def _collect_pulp_result(prob, var_objs, elapsed, time_limit=None) -> SolveResult:
    """从 pulp 求解结果提取统一结果与活跃约束。"""
    st = pulp.LpStatus.get(prob.status, "error")
    status_map = {"Optimal": "optimal", "Not Solved": "error", "Infeasible": "infeasible",
                  "Unbounded": "unbounded", "Undefined": "error"}
    status = status_map.get(st, "feasible")
    # time_limit 中断识别：pulp 对超时只报 Not Solved，按耗时贴近上限启发式归类
    if status == "error" and time_limit is not None and elapsed >= 0.95 * time_limit:
        status = "time_limit"
    try:
        solver_name = type(prob.solver).__name__.replace("_CMD", "") if prob.solver else "unknown"
    except Exception:
        solver_name = "unknown"

    obj_raw = None
    try:
        obj_raw = prob.objective.value() if prob.objective is not None else None
    except Exception:
        obj_raw = None
    if status not in ("optimal", "feasible", "time_limit") or obj_raw is None:
        # 非可信解状态（infeasible/unbounded/error）时求解器回报的目标值不可采信，统一置 None；
        # time_limit 有 incumbent 时保留（真实可行解，但最优性未证明，由 validate 提示）
        detail = {"unbounded": "目标无界——模型缺约束或变量上下界缺失，须回建模阶段修正",
                  "infeasible": "模型不可行——检查约束冲突",
                  "time_limit": f"达到时间上限 {time_limit}s 且无可用 incumbent 解",
                  }.get(status, "求解器未返回可行解")
        return SolveResult(status, None, None, elapsed, solver=solver_name, detail=detail)

    # 目标值与求解时间
    obj_val = float(obj_raw)
    sol_time = elapsed
    try:
        if prob.solver is not None and hasattr(prob.solver, "timeLimit"):
            sol_time = float(prob.solver.timeLimit - prob.solver.timeRemaining)
            if sol_time <= 0:
                sol_time = elapsed
    except Exception:
        sol_time = elapsed
    # MIPGap：status=optimal 即已证明最优，语义 gap=0；time_limit 中断时无法从 CMD 后端取原生 gap，
    # 标记为 None 并提示人工依据 status 判定最优性（避免伪造 gap）。
    gap = 0.0 if status == "optimal" else None

    # 变量取值
    var_values = {}
    for name, v in var_objs.items():
        try:
            var_values[name] = float(v.value())
        except Exception:
            var_values[name] = None

    # 活跃约束：取 slack 为 0（或接近）的约束
    active = []
    for cname, c in prob.constraints.items():
        try:
            slack = float(c.slack)  # 对 <= 为 rhs - lhs
            if abs(slack) <= 1e-6:
                active.append({"constraint": cname, "slack": round(slack, 6), "active": True})
            else:
                active.append({"constraint": cname, "slack": round(slack, 6), "active": False})
        except Exception:
            continue

    return SolveResult(status, obj_val, gap, sol_time, var_values, active, solver_name)


def solve_lp(problem: Dict[str, Any],
             solver: str = "HIGHS",
             time_limit: int = 3600) -> SolveResult:
    """
    求解凸优化 LP / QP（使用 cvxpy）。

    参数 problem 为结构化声明：
        {
          "name": "lp_model",
          "sense": "min" | "max",
          "rect": {"x": [low, high]},          # 简单变量下界/上界
          "objective": {"linear": {var: coeff}, "quadratic": {var: coeff}, "constant": 0.0},
          "constraints": [ {"expr": {var: coeff}, "sense": "<="|"=="|">=", "rhs": value} ]
        }
    本接口主要面向凸 LP/QP；一般 MIP 优先用 solve_mip。
    """
    if cp is None:
        return SolveResult("error", None, None, 0.0, detail=f"cvxpy 未安装: {_CVXPY_IMPORT_ERR}")
    t0 = time.time()
    obj = problem.get("objective", {})
    linear = obj.get("linear", {})
    quad = obj.get("quadratic", {})
    constant = obj.get("constant", 0.0)

    # 变量（含 rect 界定）
    rect = problem.get("rect", {})
    x = {}
    for vname in set(list(linear.keys()) + list(quad.keys()) + list(rect.keys())):
        lo, hi = rect.get(vname, (None, None))
        x[vname] = cp.Variable(name=vname)
        if lo is not None or hi is not None:
            pass  # 由约束表达 bounds

    # 目标表达式
    sense = problem.get("sense", "min")
    expr = constant
    for v, coeff in linear.items():
        if v in x:
            expr = expr + coeff * x[v]
    for v, coeff in quad.items():
        if v in x:
            expr = expr + coeff * cp.square(x[v])
    objective = cp.Minimize(expr) if sense == "min" else cp.Maximize(expr)

    # 约束
    constraints = []
    for vr, (lo, hi) in rect.items():
        if vr in x:
            if lo is not None:
                constraints.append(x[vr] >= lo)
            if hi is not None:
                constraints.append(x[vr] <= hi)
    for c in problem.get("constraints", []):
        cexpr = 0.0
        for v, coeff in c.get("expr", {}).items():
            if v in x:
                cexpr = cexpr + coeff * x[v]
        s = c["sense"]
        if s == "<=":
            constraints.append(cexpr <= c["rhs"])
        elif s == ">=":
            constraints.append(cexpr >= c["rhs"])
        else:
            constraints.append(cexpr == c["rhs"])

    prob = cp.Problem(objective, constraints)
    try:
        prob.solve(solver=solver, verbose=False, time_limit=time_limit)
    except Exception as e:
        return SolveResult("error", None, None, time.time() - t0, detail=str(e))

    elapsed = time.time() - t0
    if prob.status in (cp.OPTIMAL,):
        status = "optimal"
    elif prob.status == cp.INFEASIBLE:
        status = "infeasible"
    elif prob.status == cp.UNBOUNDED:
        status = "unbounded"
    elif prob.status == cp.OPTIMAL_INACCURATE:
        status = "feasible"
    else:
        status = "error"

    var_values = {v: float(x[v].value) for v in x if x[v].value is not None}

    # 活跃约束（active/slack 状态 + 数值）：按声明重算 slack
    active = []
    if var_values:
        for vr, (lo, hi) in rect.items():
            if vr not in var_values:
                continue
            xv = var_values[vr]
            if lo is not None:
                active.append({"constraint": f"bound_{vr}_lo", "slack": round(xv - lo, 6),
                               "active": abs(xv - lo) <= 1e-6})
            if hi is not None:
                active.append({"constraint": f"bound_{vr}_hi", "slack": round(hi - xv, 6),
                               "active": abs(hi - xv) <= 1e-6})
        for idx, c in enumerate(problem.get("constraints", [])):
            lhs = sum(coeff * var_values.get(v, 0.0) for v, coeff in c.get("expr", {}).items())
            rhs, s = c["rhs"], c["sense"]
            slack = {"<=": rhs - lhs, ">=": lhs - rhs}.get(s, abs(lhs - rhs))
            active.append({"constraint": c.get("name", f"c{idx}"), "slack": round(float(slack), 6),
                           "active": abs(slack) <= 1e-6})

    return SolveResult(status, float(prob.value) if prob.value is not None else None,
                       None, elapsed, var_values, active, solver)


# ============================================================
# 校验
# ============================================================

def validate(result: SolveResult, tolerance: float = 1e-6) -> List[str]:
    """统一合理性校验，返回问题列表（空 = 通过）。"""
    problems = []
    if result.status in ("error", "infeasible", "unbounded"):
        problems.append(f"求解状态异常: {result.status} — {result.detail}")
        return problems
    if result.objective_value is None:
        problems.append("缺少目标值")
        return problems
    if not (np.isfinite(result.objective_value)):
        problems.append("目标值为非有限值")
    if result.status == "time_limit":
        problems.append("求解因时间上限中断、最优性未证明——须延长时限或增大规模校验，禁止当作最优解引用")
    if result.status == "optimal" and result.mip_gap is not None and result.mip_gap > 0.05:
        problems.append(f"MIPGap={result.mip_gap:.4f} 超过 5%，建议延长求解时间")
    return problems


# ============================================================
# 主入口示例
# ============================================================

def _demo_problem() -> Dict[str, Any]:
    """最小 MIP 示例：任务分配（2 任务 × 2 工人）。"""
    n_tasks, m_workers = 2, 2
    cost = np.array([[10, 80], [60, 20]])
    variables = [{"name": f"x_{i}_{j}", "low": 0, "high": 1, "cat": "Binary"}
                 for i in range(n_tasks) for j in range(m_workers)]
    objective = {"coefficients": {f"x_{i}_{j}": float(cost[i, j])
                                  for i in range(n_tasks) for j in range(m_workers)},
                 "constant": 0.0}
    constraints = []
    for i in range(n_tasks):  # 每个任务必须分配
        constraints.append({"name": f"task_{i}", "coeffs": {f"x_{i}_{j}": 1.0 for j in range(m_workers)},
                            "sense": "==", "rhs": 1.0})
    for j in range(m_workers):  # 每个工人至多 1 个任务
        constraints.append({"name": f"worker_{j}", "coeffs": {f"x_{i}_{j}": 1.0 for i in range(n_tasks)},
                            "sense": "<=", "rhs": 1.0})
    return {"name": "demo_assignment", "sense": "min", "variables": variables,
            "objective": objective, "constraints": constraints}


def main():
    """自测：求解最小示例并校验。"""
    print("可用后端:", detect_backend())
    prob = _demo_problem()
    res = solve_mip(prob)
    print("状态:", res.status)
    print("目标值:", res.objective_value)
    print("MIPGap:", res.mip_gap)
    print("求解器:", res.solver)
    print("变量:", res.variable_values)
    print("活跃约束:", [c for c in res.active_constraints if c["active"]])
    problems = validate(res)
    print("校验:", "通过" if not problems else problems)


if __name__ == "__main__":
    main()