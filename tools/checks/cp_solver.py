#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cp_solver.py — CP-SAT 求解模板（Google OR-Tools：组合优化 / 约束满足 / 调度 / 路径）
===============================================================================
求解阶段使用（条件触发：problem_type = 组合调度 / 分配 / 路径 / 约束满足，
且 0-1/整数线性模型在 MILP 中表达低效——如复杂布尔关联、析取约束、全局约束——
或大规模下 pulp/HiGHS 难以在时限内收敛时）。

修改 PARAMETERS 区块（_demo_problem 与 build_problem 的建模声明），不修改 CORE ALGORITHM 区块。

设计原则（与 solver_backend.py / nlp_solver.py 同构）：
- PARAMETERS / CORE ALGORITHM 分离：建模声明在 PARAMETERS，求解逻辑在 CORE。
- 原生元数据透传：status / objective_value / best_bound / solve_time / solver
  全部取自求解器原生输出，最优性判定信任 CP-SAT 原生状态（OPTIMAL / FEASIBLE / INFEASIBLE）。
- 最优性证明：status == OPTIMAL 时 objective_value == best_bound，gap = 0（已证全局最优）；
  status == FEASIBLE 且未达 OPTIMAL 时，gap 取 (best_bound - objective)/|objective|，
  并提示"未证最优、禁止当作最优引用"（与 solver_backend.validate 同纪律）。

依赖：pip install ortools
  - Google 开源（Apache 2.0），非商业求解器，符合"禁止商业求解器"硬约束。
  - Python 3.13 需 ortools >= 9.11（2025 年起发布版本支持 3.13）。

适用范围与降级（建模决策依据）：
- 本模板面向离散决策：布尔/整数变量 + 线性约束（含布尔关联） + 线性目标。
- 连续决策 / 凸优化 / 大规模纯 LP：优先 solver_backend.py（pulp/cvxpy），本模板不用于连续问题。
- 本模板保证代数正确性，不保证领域语义正确性（语义正确性由问题分类与建模校验兜底）。

四道闸门（新建/改动后必跑）：
1. 已知最优小算例：_demo_problem 为 0-1 背包（物品 (重,价)=(2,3)(3,4)(4,5)(5,7)，容量 7），
   最优价值 = 10（手算：选 (2,3)+(5,7)，重量 2+5=7，价值 3+7=10；其余组合 ≤ 9）。
2. 黄金对拍：同一背包算例用 pulp（solver_backend.solve_mip）与 CP-SAT 各解一次，最优值应同为 10。
3. 回归 / validate：validate() 每次求解自动断言 status/gap/量级（见 CORE）。
4. 冒烟：py_compile + python -m cp_solver（main() 全断言通过）。
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

try:
    from ortools.sat.python import cp_model
except Exception as _e:  # pragma: no cover
    cp_model = None
    _CP_IMPORT_ERR = _e
else:
    _CP_IMPORT_ERR = None


# ============================================================
# PARAMETERS（根据题目修改此区块）
# ============================================================

# 求解器参数（可直接修改）
TIME_LIMIT = 60        # 时间上限（秒）
NUM_WORKERS = 8        # 并行线程数（多核环境）

# CP-SAT 变量缺省界（CP-SAT 的 NewIntVar 必须显式设界，缺省取 [0, 1e9]，
# 若题目变量的天然界不同，请在变量声明中显式给出 low/high）
DEFAULT_INT_HIGH = int(1e9)


def _demo_problem() -> Dict[str, Any]:
    """最小自测算例：0-1 背包，最优价值 10（手算可证，见文件头闸门说明）。"""
    items = [(2, 3), (3, 4), (4, 5), (5, 7)]   # (重量, 价值)
    capacity = 7
    variables = [{"name": f"x_{i}", "low": 0, "high": 1, "cat": "Binary"}
                 for i in range(len(items))]
    objective = {
        "coefficients": {f"x_{i}": float(v) for i, (_, v) in enumerate(items)},
        "constant": 0.0,
    }
    constraints = [{
        "name": "capacity",
        "coeffs": {f"x_{i}": float(w) for i, (w, _) in enumerate(items)},
        "sense": "<=",
        "rhs": float(capacity),
    }]
    return {"name": "demo_knapsack", "sense": "max",
            "variables": variables, "objective": objective, "constraints": constraints}


def build_problem() -> Dict[str, Any]:
    """题目建模声明入口：按题目改此函数，返回 solve_cp 可消费的结构化声明。

    声明格式（与 solver_backend.solve_mip 一致，便于两路黄金对拍）：
        {
          "name": "model_name",
          "sense": "min" | "max",
          "variables": [{"name": "x_0", "low": 0, "high": 1, "cat": "Binary"|"Integer"}],
          "objective": {"coefficients": {var_name: coeff}, "constant": 0.0},
          "constraints": [{"name": "c0", "coeffs": {var_name: coeff}, "sense": "<="|"=="|">=", "rhs": value}]
        }
    布尔关联约束（析取 / 蕴含）超出线性声明的表达范围时，可在 CORE 之外另行
    用 cp_model 的 AddXOr / AddImplication 扩展（见模板内注释），但主模型仍以线性声明为准。
    """
    return _demo_problem()


# ============================================================
# CORE ALGORITHM（不修改此区块）
# ============================================================

_STATUS_MAP = {
    cp_model.OPTIMAL: "optimal",
    cp_model.FEASIBLE: "feasible",
    cp_model.INFEASIBLE: "infeasible",
    cp_model.MODEL_INVALID: "model_invalid",
    cp_model.UNKNOWN: "unknown",
} if cp_model is not None else {}


def solve_cp(problem: Dict[str, Any],
             time_limit: int = TIME_LIMIT,
             num_workers: int = NUM_WORKERS) -> Dict[str, Any]:
    """
    求解组合优化 / 约束满足问题（使用 OR-Tools CP-SAT）。

    返回统一结果结构（字段与 solver_backend.SolveResult 对齐，便于下游消费）：
        status / objective_value / MIPGap / solve_time / solver / best_bound /
        variable_values / detail
    """
    if cp_model is None:
        return {"status": "error", "objective_value": None, "MIPGap": None,
                "solve_time": 0.0, "solver": "CP-SAT", "best_bound": None,
                "variable_values": {}, "detail": f"ortools 未安装: {_CP_IMPORT_ERR}"}
    t0 = time.time()
    model = cp_model.CpModel()
    sense = problem.get("sense", "min")

    # ---- 变量（CP-SAT 必须显式设界；Binary 用 BoolVar，其余用 IntVar）----
    var_objs: Dict[str, Any] = {}
    for v in problem.get("variables", []):
        name = v["name"]
        cat = v.get("cat", "Integer")
        lo = int(v.get("low", 0))
        hi = int(v.get("high", DEFAULT_INT_HIGH))
        if cat == "Binary":
            var_objs[name] = model.NewBoolVar(name)
        else:
            var_objs[name] = model.NewIntVar(lo, hi, name)

    # ---- 目标（线性，CP-SAT 要求整数系数/RHS，强制 int 转换）----
    coeffs = problem.get("objective", {}).get("coefficients", {})
    constant = int(problem.get("objective", {}).get("constant", 0.0))
    expr = cp_model.LinearExpr.Sum(
        [int(coeffs[k]) * var_objs[k] for k in coeffs if k in var_objs]) + constant
    if sense == "max":
        model.Maximize(expr)
    else:
        model.Minimize(expr)

    # ---- 约束（线性 <= / == / >=，CP-SAT 要求整数）----
    for c in problem.get("constraints", []):
        cexpr = cp_model.LinearExpr.Sum(
            [int(c["coeffs"][k]) * var_objs[k] for k in c["coeffs"] if k in var_objs])
        rhs = int(c["rhs"])
        s = c.get("sense", "<=")
        if s == "<=":
            model.Add(cexpr <= rhs)
        elif s == ">=":
            model.Add(cexpr >= rhs)
        else:
            model.Add(cexpr == rhs)

    # ---- 求解（原生元数据透传）----
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = num_workers
    solver.parameters.log_search_progress = False
    raw_status = solver.Solve(model)
    elapsed = time.time() - t0

    status = _STATUS_MAP.get(raw_status, "unknown")

    # 目标值与界：仅 OPTIMAL / FEASIBLE 才可信；INFEASIBLE / MODEL_INVALID / UNKNOWN 置 None
    if status in ("optimal", "feasible"):
        obj = float(solver.ObjectiveValue())
        best_bound = float(solver.BestObjectiveBound())
        # 最优性间隙：OPTIMAL 即已证最优（objective == best_bound），gap=0；
        # FEASIBLE 未证最优，报相对差距并提示不可当最优引用。
        if status == "optimal":
            gap = 0.0
        else:
            gap = (abs(best_bound - obj) / abs(obj)) if abs(obj) > 1e-9 else None
        var_values = {name: float(solver.Value(v)) for name, v in var_objs.items()}
        detail = ""
    else:
        obj = None
        best_bound = None
        gap = None
        var_values = {}
        detail = {
            "infeasible": "模型不可行——检查约束冲突（含布尔关联）",
            "model_invalid": "模型声明非法（变量界缺失/类型错误）——检查 PARAMETERS",
            "unknown": f"未在时限 {time_limit}s 内找到可行解——增大时限或检查模型",
        }.get(status, f"求解器返回状态 {raw_status}")

    return {
        "status": status,
        "objective_value": obj,
        "MIPGap": gap,
        "solve_time": round(elapsed, 4),
        "solver": f"CP-SAT (ortools {_ver()})",
        "best_bound": best_bound,
        "variable_values": var_values,
        "detail": detail,
    }


def _ver() -> str:
    try:
        import ortools
        return ortools.__version__
    except Exception:
        return "?"


def validate(result: Dict[str, Any], tolerance: float = 1e-6) -> List[str]:
    """统一合理性校验（与 solver_backend.validate 同纪律），返回问题列表（空 = 通过）。"""
    problems = []
    if result["status"] in ("error", "infeasible", "model_invalid", "unknown"):
        problems.append(f"求解状态异常: {result['status']} — {result['detail']}")
        return problems
    obj = result["objective_value"]
    if obj is None:
        problems.append("缺少目标值")
        return problems
    import math
    if not math.isfinite(obj):
        problems.append("目标值为非有限值")
    if result["status"] == "feasible":
        problems.append("FEASIBLE（未证最优）——禁止当作最优解引用，须延长时限或校验模型")
    if result["status"] == "optimal" and result["MIPGap"] is not None and result["MIPGap"] > 0.05:
        problems.append(f"MIPGap={result['MIPGap']:.4f} 超过 5%，建议延长求解时间")
    return problems


def main():
    """自测：跑已知最优小算例 + 校验（四道闸门之 1/3/4）。"""
    print("=== cp_solver 自测（0-1 背包，已知最优=10）===")
    if cp_model is None:
        print(f"❌ ortools 未安装: {_CP_IMPORT_ERR}")
        return 1
    prob = build_problem()
    res = solve_cp(prob)
    print(f"状态: {res['status']}")
    print(f"目标值: {res['objective_value']}（期望 10）")
    print(f"best_bound: {res['best_bound']}  MIPGap: {res['MIPGap']}")
    print(f"求解器: {res['solver']}  耗时: {res['solve_time']}s")
    print(f"变量: {res['variable_values']}")
    problems = validate(res)
    print("校验:", "通过" if not problems else problems)

    # 闸门 1：已知最优小算例断言
    ok = (res["status"] == "optimal" and res["objective_value"] is not None
          and abs(res["objective_value"] - 10.0) <= 1e-6 and res["MIPGap"] == 0.0)
    print("[PASS] 已知最优小算例通过" if ok else "[FAIL] 已知最优小算例失败")
    return 0 if (ok and not problems) else 1


if __name__ == "__main__":
    raise SystemExit(main())
