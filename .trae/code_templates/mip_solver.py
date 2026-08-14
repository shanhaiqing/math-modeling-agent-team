#!/usr/bin/env python3
"""
MIP 求解模板（基于 solver_backend 统一求解后端，HiGHS/CBC 开源求解器）
求解阶段使用。修改 PARAMETERS 区块（含 build_model 的建模声明），不修改 CORE ALGORITHM 区块。
原模板基于 Gurobi（商业求解器，需 license），现已改为开源后端，无需 license。
依赖：pip install pulp cvxpy（solver_backend.py 自动选择 HiGHS/CBC）
"""

import json
import numpy as np

# 导入统一求解后端
from solver_backend import solve_mip, SolveResult, validate

# ============================================================
# PARAMETERS（根据题目修改此区块）
# ============================================================

# 问题规模
n_tasks = 10      # 任务数
m_workers = 5     # 工人数

# 成本矩阵
cost = np.random.randint(10, 100, size=(n_tasks, m_workers))

# 求解器参数
MIPGAP = 0.01     # 最优性间隙
TIME_LIMIT = 3600 # 时间上限（秒）


def build_problem():
    """
    构建结构化 MIP 建模声明（供 solver_backend.solve_mip 消费）。
    决策变量/目标/约束在此声明，符号与术语表对齐。
    """
    # 决策变量：x[i][j] = 是否将任务 i 分配给工人 j
    variables = [
        {"name": f"x_{i}_{j}", "low": 0, "high": 1, "cat": "Binary"}
        for i in range(n_tasks) for j in range(m_workers)
    ]

    # 目标函数：最小化总分配成本
    objective = {
        "coefficients": {f"x_{i}_{j}": float(cost[i, j])
                         for i in range(n_tasks) for j in range(m_workers)},
        "constant": 0.0,
    }

    constraints = []
    # 约束 1：每个任务必须分配且仅分配一次
    for i in range(n_tasks):
        constraints.append({
            "name": f"task_{i}_assigned",
            "coeffs": {f"x_{i}_{j}": 1.0 for j in range(m_workers)},
            "sense": "==", "rhs": 1.0,
        })
    # 约束 2：每个工人能力限制（至多分配 max_tasks_per_worker 个任务）
    max_tasks_per_worker = int(np.ceil(n_tasks / m_workers))
    for j in range(m_workers):
        constraints.append({
            "name": f"worker_{j}_capacity",
            "coeffs": {f"x_{i}_{j}": 1.0 for i in range(n_tasks)},
            "sense": "<=", "rhs": max_tasks_per_worker,
        })

    return {
        "name": "mip_assignment",
        "sense": "min",
        "variables": variables,
        "objective": objective,
        "constraints": constraints,
    }


# ============================================================
# CORE ALGORITHM（不修改此区块）
# ============================================================

def solve_and_extract(problem, mip_gap: float = MIPGAP,
                      time_limit: int = TIME_LIMIT) -> SolveResult:
    """调用统一求解后端求解。"""
    return solve_mip(problem, mip_gap=mip_gap, time_limit=time_limit)


def extract_solution(result: SolveResult) -> dict:
    """将统一求解结果转为标准结果结构。"""
    return {
        "status": result.status,
        "objective_value": result.objective_value,
        "MIPGap": result.mip_gap,
        "solve_time": result.solve_time,
        "solver": result.solver,
        "active_constraints": result.active_constraints,
        "assignments": [
            {"task": i, "worker": j, "cost": float(cost[i, j])}
            for i in range(n_tasks) for j in range(m_workers)
            if result.variable_values.get(f"x_{i}_{j}", 0) and result.variable_values[f"x_{i}_{j}"] > 0.5
        ],
    }


def verify_solution(result: SolveResult, solution: dict) -> None:
    """合理性验证（统一校验 + 量级检验）。"""
    problems = validate(result)
    assert not problems, f"求解校验失败: {problems}"

    obj = solution["objective_value"]
    assert obj is not None and obj > 0, "目标值应为正"
    assert obj < 1e9, "目标值异常大"

    # 约束满足检验：所有约束 slack 不得严重违反
    for c in result.active_constraints:
        assert c["slack"] >= -1e-6, f"约束 {c['constraint']} 违反: slack={c['slack']}"

    print("✅ 所有验证通过")


def main():
    """主入口"""
    problem = build_problem()
    result = solve_and_extract(problem)
    solution = extract_solution(result)

    if result.status in ("error", "infeasible"):
        print(f"❌ 求解失败: 状态={result.status}, {result.detail}")
        return solution

    verify_solution(result, solution)

    # 保存结果
    with open("results/result.json", "w", encoding="utf-8") as f:
        json.dump(solution, f, indent=2, ensure_ascii=False)

    print(f"\n目标值: {solution['objective_value']:.2f}")
    print(f"求解时间: {solution['solve_time']:.2f}s")
    print(f"MIPGap: {solution['MIPGap']}")
    print(f"分配数: {len(solution['assignments'])}")

    return solution


if __name__ == "__main__":
    main()