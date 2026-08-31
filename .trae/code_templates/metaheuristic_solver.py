#!/usr/bin/env python3
"""
元启发式求解模板（遗传算法 + 模拟退火）
求解阶段使用。修改 PARAMETERS 和 fitness 函数，不修改 CORE ALGORITHM。
"""

import numpy as np
import json
import matplotlib
matplotlib.use("Agg")  # 无头环境兜底（Bash 执行/比赛环境无显示，防止 TkAgg 崩溃）
import matplotlib.pyplot as plt
from typing import Callable

# 设置中文字体（与 visualization_style.py 的候选一致：Microsoft YaHei 优先）
# 提示：若需完整期刊风格（SciencePlots/CMasher），请调用 visualization_style.setup_style()
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# ============================================================
# PARAMETERS（根据题目修改此区块）
# ============================================================

# 问题参数
N_VARIABLES = 20  # 决策变量数
VAR_LOWER = -10   # 变量下界（标量，逐维不同请改为等长数组）
VAR_UPPER = 10    # 变量上界（同上）

# 算法参数
POP_SIZE = 100      # 种群大小
N_GENERATIONS = 300 # 迭代代数
CROSSOVER_PROB = 0.8 # 交叉概率
MUTATION_PROB = 0.05 # 变异概率
N_RUNS = 5           # 独立运行次数

# 模拟退火参数
SA_INIT_TEMP = 1000  # 初始温度
SA_COOLING = 0.95    # 冷却率
SA_TERM_TEMP = 0.01  # 终止温度

# ============================================================
# FITNESS FUNCTION（根据题目修改此函数）
# ============================================================

def fitness(individual: np.ndarray) -> float:
    """
    适应度函数（最小化问题，返回目标值）。
    根据题目定义此函数。
    """
    # 示例：简单的二次函数
    return np.sum(individual ** 2)


# ============================================================
# CORE ALGORITHM（不修改此区块）
# ============================================================

def genetic_algorithm(fitness_fn: Callable, seed: int = 42) -> dict:
    """遗传算法主循环"""
    np.random.seed(seed)
    
    # 初始化种群（边界内均匀采样）
    pop = np.random.uniform(VAR_LOWER, VAR_UPPER, size=(POP_SIZE, N_VARIABLES))
    best_fitness_history = []
    
    for gen in range(N_GENERATIONS):
        # 评估适应度
        fits = np.array([fitness_fn(ind) for ind in pop])
        
        # 精英保留
        elite_idx = np.argmin(fits)
        best_fitness_history.append(fits[elite_idx])
        
        # 选择（锦标赛）
        new_pop = np.zeros_like(pop)
        new_pop[0] = pop[elite_idx]  # 精英
        
        for i in range(1, POP_SIZE):
            # 锦标赛选择
            candidates = np.random.choice(POP_SIZE, size=3, replace=False)
            parent_idx = candidates[np.argmin(fits[candidates])]
            parent = pop[parent_idx]
            
            # 交叉
            if np.random.random() < CROSSOVER_PROB:
                partner_idx = np.random.choice(POP_SIZE)
                partner = pop[partner_idx]
                mask = np.random.random(N_VARIABLES) < 0.5
                child = np.where(mask, parent, partner)
            else:
                child = parent.copy()
            
            # 变异（越界裁剪回边界）
            mutation_mask = np.random.random(N_VARIABLES) < MUTATION_PROB
            child[mutation_mask] += np.random.normal(0, 1, size=np.sum(mutation_mask))
            child = np.clip(child, VAR_LOWER, VAR_UPPER)
            
            new_pop[i] = child
        
        pop = new_pop
    
    return {
        "best_fitness": best_fitness_history[-1],
        "best_individual": pop[0].tolist(),
        "history": best_fitness_history
    }


def simulated_annealing(fitness_fn: Callable, seed: int = 42) -> dict:
    """模拟退火"""
    np.random.seed(seed)
    
    current = np.random.uniform(VAR_LOWER, VAR_UPPER, size=N_VARIABLES)
    current_fit = fitness_fn(current)
    best = current.copy()
    best_fit = current_fit
    
    temp = SA_INIT_TEMP
    history = [current_fit]
    
    while temp > SA_TERM_TEMP:
        # 生成邻域解（越界裁剪回边界）
        neighbor = current + np.random.normal(0, temp / SA_INIT_TEMP, size=N_VARIABLES)
        neighbor = np.clip(neighbor, VAR_LOWER, VAR_UPPER)
        neighbor_fit = fitness_fn(neighbor)
        
        # 接受准则
        delta = neighbor_fit - current_fit
        if delta < 0 or np.random.random() < np.exp(-delta / temp):
            current = neighbor
            current_fit = neighbor_fit
        
        if current_fit < best_fit:
            best = current.copy()
            best_fit = current_fit
        
        history.append(best_fit)
        temp *= SA_COOLING
    
    return {
        "best_fitness": best_fit,
        "best_individual": best.tolist(),
        "history": history
    }


def run_multiple_times(algorithm_fn: Callable, n_runs: int = N_RUNS) -> dict:
    """多次独立运行，统计结果"""
    results = []
    for run in range(n_runs):
        result = algorithm_fn(fitness, seed=run)
        results.append(result["best_fitness"])
    
    return {
        "best": float(np.min(results)),
        "mean": float(np.mean(results)),
        "std": float(np.std(results)),
        "cv": float(np.std(results) / np.mean(results) * 100) if np.mean(results) != 0 else 0,
        "all_runs": [float(r) for r in results]
    }


def plot_convergence(ga_result: dict, sa_result: dict, save_path: str = "figures/convergence.pdf"):
    """绘制收敛曲线"""
    fig, axes = plt.subplots(1, 2, figsize=(5.75, 2.4))  # 0.9\textwidth=5.75in（=viz CU_TEXTWIDTH_IN），高按原 12:5 等比
    
    # 遗传算法收敛曲线
    axes[0].plot(ga_result["history"], 'b-', linewidth=1)
    axes[0].set_xlabel("迭代次数")
    axes[0].set_ylabel("最优适应度")
    axes[0].set_title("(a)")
    axes[0].grid(True, alpha=0.3)
    
    # 模拟退火收敛曲线
    axes[1].plot(sa_result["history"], 'r-', linewidth=1)
    axes[1].set_xlabel("迭代次数")
    axes[1].set_ylabel("最优适应度")
    axes[1].set_title("(b)")
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    plt.savefig(save_path.replace('.pdf', '.png'), dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ 收敛曲线已保存至 {save_path}")


def main():
    """主入口"""
    # 运行遗传算法
    print("运行遗传算法（5 次独立运行）...")
    ga_stats = run_multiple_times(genetic_algorithm)
    print(f"  GA - 最优: {ga_stats['best']:.4f}, 均值: {ga_stats['mean']:.4f}, "
          f"标准差: {ga_stats['std']:.4f}, CV: {ga_stats['cv']:.1f}%")
    
    # 运行模拟退火
    print("运行模拟退火（5 次独立运行）...")
    sa_stats = run_multiple_times(simulated_annealing)
    print(f"  SA - 最优: {sa_stats['best']:.4f}, 均值: {sa_stats['mean']:.4f}, "
          f"标准差: {sa_stats['std']:.4f}, CV: {sa_stats['cv']:.1f}%")
    
    # 单次运行取收敛曲线
    ga_result = genetic_algorithm(fitness, seed=42)
    sa_result = simulated_annealing(fitness, seed=42)
    plot_convergence(ga_result, sa_result)
    
    # 保存统计结果
    stats = {"GA": ga_stats, "SA": sa_stats}
    with open("results/metaheuristic_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    return stats


if __name__ == "__main__":
    main()