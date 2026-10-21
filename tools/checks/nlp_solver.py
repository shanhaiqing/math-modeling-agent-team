#!/usr/bin/env python3
"""
多起点 NLP 求解模板（scipy SLSQP，连续非线性规划）
求解阶段使用（条件触发：problem_type = NLP_Convex / NLP_Nonconvex）。
修改 PARAMETERS、objective、build_constraints，不修改 CORE ALGORITHM。

纪律：非凸问题必须依赖多起点统计——禁止以单起点结果作结论（对齐启发式 ≥5 次运行要求）；
spread 大说明非凸性强，论文须注明"局部最优"并报告收敛起点占比。
"""

import numpy as np
import json
import matplotlib
matplotlib.use("Agg")  # 无头环境兜底（Bash 执行/比赛环境无显示，防止 TkAgg 崩溃）
import matplotlib.pyplot as plt
from scipy.optimize import minimize

# 设置中文字体（与 visualization_style.py 的候选一致：Microsoft YaHei 优先）
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# PARAMETERS（根据题目修改此区块）
# ============================================================

# 问题参数
N_VARIABLES = 5     # 决策变量数
VAR_LOWER = -5.0    # 变量下界（标量，逐维不同请改为等长数组并在 CORE 外预处理）
VAR_UPPER = 5.0     # 变量上界（同上）

# 算法参数
N_STARTS = 20       # 多起点数（非凸 ≥20；已证凸的问题可降为 1 并在论文说明）
MAXITER = 500
FTOL = 1e-9

# ============================================================
# OBJECTIVE & CONSTRAINTS（根据题目修改此区块）
# ============================================================

def objective(x: np.ndarray) -> float:
    """
    目标函数（最小化，返回标量）。
    根据题目定义此函数。示例为多峰非凸函数：sum(x^2) + 2*sum(sin(3x)^2)。
    """
    return float(np.sum(x ** 2) + 2.0 * np.sum(np.sin(3.0 * x) ** 2))


def build_constraints() -> list:
    """
    scipy 约束列表（SLSQP 支持等式/不等式）。默认空——盒约束已由 bounds 承担。
    不等式示例：{"type": "ineq", "fun": lambda x: x[0] + x[1] - 1.0}  # fun(x) ≥ 0 为可行
    等式示例：  {"type": "eq",   "fun": lambda x: np.sum(x) - 1.0}   # fun(x) = 0
    """
    return []


# ============================================================
# CORE ALGORITHM（不修改此区块）
# ============================================================

def multi_start_slsqp(seed: int = 42) -> dict:
    """多起点 SLSQP 主循环：均匀采样起点，逐点求解，收集统计量。"""
    rng = np.random.default_rng(seed)
    starts = rng.uniform(VAR_LOWER, VAR_UPPER, size=(N_STARTS, N_VARIABLES))
    bounds = [(VAR_LOWER, VAR_UPPER)] * N_VARIABLES
    cons = build_constraints()

    runs = []
    for x0 in starts:
        r = minimize(objective, x0, method="SLSQP", bounds=bounds, constraints=cons,
                     options={"maxiter": MAXITER, "ftol": FTOL})
        runs.append({"x0": x0.tolist(), "x": r.x.tolist(), "fun": float(r.fun),
                     "success": bool(r.success), "nit": int(r.nit)})

    feas = [r for r in runs if r["success"]]
    if not feas:
        raise RuntimeError("全部起点未收敛——检查 objective/constraints 定义或增大 MAXITER")
    best = min(feas, key=lambda r: r["fun"])
    vals = np.array([r["fun"] for r in feas])
    return {
        "best_x": best["x"], "best_f": best["fun"],
        "n_starts": N_STARTS, "n_converged": len(feas),
        "mean_f": float(vals.mean()), "std_f": float(vals.std()),
        "spread": float(vals.max() - vals.min()),  # 起点散布：非凸性强弱证据
        "runs": runs,
    }


def plot_multistart(res: dict, save_path: str = "figures/nlp_multistart.pdf"):
    """多起点结果可视化：收敛值直方图 + 迭代次数分布（非凸性/收敛性证据图）。"""
    feas_vals = [r["fun"] for r in res["runs"] if r["success"]]
    feas_nits = [r["nit"] for r in res["runs"] if r["success"]]

    fig, axes = plt.subplots(1, 2, figsize=(5.75, 2.4))  # 0.9\textwidth=5.75in（=viz CU_TEXTWIDTH_IN），高按原 12:5 等比
    axes[0].hist(feas_vals, bins=15, color="steelblue", edgecolor="white")
    axes[0].axvline(res["best_f"], color="red", linestyle="--",
                    label=f"最优 {res['best_f']:.4f}（{res['n_converged']}/{res['n_starts']} 收敛）")
    axes[0].set_xlabel("收敛目标值")
    axes[0].set_ylabel("起点数")
    axes[0].set_title("(a)")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].hist(feas_nits, bins=15, color="darkorange", edgecolor="white")
    axes[1].set_xlabel("SLSQP 迭代次数")
    axes[1].set_ylabel("起点数")
    axes[1].set_title("(b)")
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.savefig(save_path.replace('.pdf', '.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ 多起点分布图已保存至 {save_path}")


def main():
    """主入口"""
    res = multi_start_slsqp(seed=42)
    print(f"多起点 SLSQP（{res['n_starts']} 起点，{res['n_converged']} 收敛）:")
    print(f"  最优值: {res['best_f']:.6f}  均值: {res['mean_f']:.6f}  "
          f"标准差: {res['std_f']:.6f}  散布: {res['spread']:.6f}")
    print(f"  最优解: {[round(v, 4) for v in res['best_x']]}")
    if res["spread"] > max(1e-6, abs(res["best_f"]) * 0.01):
        print("  [警告] 起点散布显著——非凸性强，论文须注明局部最优并给出收敛起点占比")

    plot_multistart(res)
    with open("results/nlp_stats.json", "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in res.items() if k != "runs"}, f, indent=2, ensure_ascii=False)
    return res


if __name__ == "__main__":
    main()
