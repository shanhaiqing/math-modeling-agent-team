#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
蒙特卡洛仿真验证模板（国赛公开惯例）

用途：
    对解析/点估计结果进行蒙特卡洛仿真交叉验证，作为"模型验证"维度（与"样本外性能验证"独立）。
    适用于含随机性 / 不确定性 / 抽样波动 / 输入噪声的问题。

使用方法：
    1. 复制此模板到 project/ 目录
    2. 修改 PARAMETERS 区块：填入题目参数和解析结果
    3. 修改 simulate_once 函数：定义单次仿真的逻辑
    4. 运行脚本，输出仿真次数、收敛情况、偏差、偏差原因分析

⚠️ 蒙特卡洛仿真是"模型验证"，与"样本外性能验证"（交叉验证/留出验证）是两个独立维度，不可相互替代。
"""

import numpy as np
import json
from pathlib import Path

# ============================================================
# PARAMETERS 区块（用户修改）
# ============================================================

# 题目参数（从 solution.json 或 术语表.json 读取）
PARAMS = {
    # 示例：比率指标估计场景（如不合格率/转化率/发生率）
    "p_true": 0.10,       # 总体真实比率（理论值）
    "n_sample": 200,      # 单次抽样样本量
    "noise_std": 0.0,     # 观测噪声标准差（若含测量误差则 >0）
}

# 解析结果（从 solution.json 读取，用于对比）
ANALYTICAL_RESULT = {
    "p_estimate": 0.10,   # 解析/点估计值（如 p_hat 的理论期望）
    # 可添加更多解析结果字段
}

# 仿真参数
N_SIMULATIONS = 10000    # 仿真次数（小样本时 ≥10000）
BATCH_SIZE = 1000        # 批次大小（用于收敛分析）
RANDOM_SEED = 42         # 随机种子（可复现）
CONVERGENCE_THRESHOLD = 0.05  # 收敛阈值：平均值的标准差 / 平均值 < 5%
DEVIATION_THRESHOLD = 0.05    # 偏差阈值：|仿真-解析| / 解析 < 5%


# ============================================================
# CORE SIMULATION（用户修改 simulate_once 函数）
# ============================================================

def simulate_once(params: dict, rng: np.random.Generator) -> dict:
    """
    单次仿真：从总体中抽取 n_sample 个样本，返回该次的点估计值。

    用户需根据具体问题修改此函数。以下示例为"比率指标估计"的仿真逻辑：
    总体真实比率 p_true，每次抽取 n_sample 个样本，可叠加观测噪声。

    Args:
        params: 参数字典
        rng: numpy 随机数生成器

    Returns:
        dict: 单次仿真结果，至少含 "estimate" 字段
    """
    # 示例：二项抽样 + 可选观测噪声
    n = params["n_sample"]
    p = params["p_true"]

    # 步骤1：抽样（每个样本以概率 p 取 1）
    k = rng.binomial(n, p)
    p_hat = k / n

    # 步骤2：观测噪声（若 noise_std > 0，模拟测量误差）
    if params["noise_std"] > 0:
        p_hat = p_hat + rng.normal(0.0, params["noise_std"])

    return {"estimate": p_hat, "k": k}


# ============================================================
# 仿真引擎（用户一般不需修改）
# ============================================================

def run_monte_carlo(params: dict, n_simulations: int, batch_size: int,
                    random_seed: int) -> dict:
    """
    运行蒙特卡洛仿真，返回统计结果。

    Returns:
        dict: {
            "n_simulations": 仿真次数,
            "mean": 平均值,
            "std": 标准差,
            "std_of_mean": 平均值的标准差,
            "convergence_ratio": std_of_mean / |mean|,
            "batch_means": 批次平均值列表（用于收敛分析）,
            "all_results": 所有仿真结果
        }
    """
    rng = np.random.default_rng(random_seed)
    all_estimates = []
    batch_means = []

    for batch_start in range(0, n_simulations, batch_size):
        batch_end = min(batch_start + batch_size, n_simulations)
        batch_estimates = []
        for _ in range(batch_end - batch_start):
            result = simulate_once(params, rng)
            batch_estimates.append(result["estimate"])
        all_estimates.extend(batch_estimates)
        batch_means.append(np.mean(batch_estimates))

    all_estimates = np.array(all_estimates)
    mean = np.mean(all_estimates)
    std = np.std(all_estimates, ddof=1)
    std_of_mean = std / np.sqrt(n_simulations)
    convergence_ratio = std_of_mean / abs(mean) if mean != 0 else float('inf')

    return {
        "n_simulations": n_simulations,
        "mean": float(mean),
        "std": float(std),
        "std_of_mean": float(std_of_mean),
        "convergence_ratio": float(convergence_ratio),
        "batch_means": [float(x) for x in batch_means],
        "all_results": all_estimates.tolist()
    }


def compare_with_analytical(simulation_result: dict, analytical_result: dict,
                             deviation_threshold: float) -> dict:
    """
    对比仿真结果与解析结果。

    Returns:
        dict: {
            "analytical_value": 解析值,
            "simulation_mean": 仿真平均值,
            "deviation": 偏差,
            "deviation_ratio": 偏差比例,
            "is_within_threshold": 是否在阈值内,
            "convergence_status": 收敛状态,
            "analysis": 偏差原因分析（若超出阈值）
        }
    """
    analytical_value = analytical_result.get("p_estimate", 0)
    simulation_mean = simulation_result["mean"]
    deviation = simulation_mean - analytical_value
    deviation_ratio = abs(deviation) / abs(analytical_value) if analytical_value != 0 else float('inf')
    is_within_threshold = deviation_ratio < deviation_threshold
    convergence_status = "收敛" if simulation_result["convergence_ratio"] < CONVERGENCE_THRESHOLD else "未收敛"

    analysis = ""
    if not is_within_threshold:
        # 偏差超过阈值，分析原因
        analysis = f"偏差 {deviation_ratio*100:.2f}% 超过阈值 {deviation_threshold*100:.2f}%，可能原因：\n"
        analysis += "1. 抽样模型设定有误：样本生成机制与假设不符（如存在分层/聚类结构未考虑）\n"
        analysis += "2. 独立性假设不成立：样本间存在相关性，方差被低估\n"
        analysis += "3. 解析推导有误：估计量期望或公式中的参数项计算错误\n"
        analysis += "4. 仿真次数不足：增加 N_SIMULATIONS 后重新运行\n"
        analysis += "5. 估计量本身有偏：所用估计量在小样本下有偏（如比率/方差估计），需偏差修正或换无偏估计量\n"
    elif convergence_status == "未收敛":
        analysis = f"仿真未收敛（convergence_ratio={simulation_result['convergence_ratio']:.4f}），"
        analysis += f"建议增加仿真次数至 {int(simulation_result['n_simulations'] * (simulation_result['convergence_ratio']/CONVERGENCE_THRESHOLD)**2)}"

    return {
        "analytical_value": float(analytical_value),
        "simulation_mean": float(simulation_mean),
        "deviation": float(deviation),
        "deviation_ratio": float(deviation_ratio),
        "is_within_threshold": bool(is_within_threshold),
        "convergence_status": convergence_status,
        "convergence_ratio": float(simulation_result["convergence_ratio"]),
        "analysis": analysis
    }


def save_results(simulation_result: dict, comparison_result: dict,
                 output_path: str = "results/monte_carlo_result.json"):
    """保存仿真结果和对比结果到 JSON 文件。"""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    output = {
        "simulation": {
            "n_simulations": simulation_result["n_simulations"],
            "mean": simulation_result["mean"],
            "std": simulation_result["std"],
            "std_of_mean": simulation_result["std_of_mean"],
            "convergence_ratio": simulation_result["convergence_ratio"],
            "convergence_status": comparison_result["convergence_status"]
        },
        "comparison": comparison_result,
        "parameters": PARAMS,
        "analytical_result": ANALYTICAL_RESULT
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"✓ 仿真结果已保存到 {output_path}")


def print_summary(simulation_result: dict, comparison_result: dict):
    """打印仿真摘要。"""
    print("=" * 60)
    print("蒙特卡洛仿真验证摘要")
    print("=" * 60)
    print(f"仿真次数: {simulation_result['n_simulations']}")
    print(f"仿真平均值: {simulation_result['mean']:.4f}")
    print(f"仿真标准差: {simulation_result['std']:.4f}")
    print(f"平均值的标准差: {simulation_result['std_of_mean']:.4f}")
    print(f"收敛比例 (std_of_mean/|mean|): {simulation_result['convergence_ratio']:.4f}")
    print(f"收敛状态: {comparison_result['convergence_status']}")
    print("-" * 60)
    print(f"解析值: {comparison_result['analytical_value']:.4f}")
    print(f"仿真值: {comparison_result['simulation_mean']:.4f}")
    print(f"偏差: {comparison_result['deviation']:.4f}")
    print(f"偏差比例: {comparison_result['deviation_ratio']*100:.2f}%")
    print(f"是否在阈值内 (<{DEVIATION_THRESHOLD*100:.2f}%): {'是' if comparison_result['is_within_threshold'] else '否'}")
    print("-" * 60)
    if comparison_result['analysis']:
        print("偏差原因分析:")
        print(comparison_result['analysis'])
    print("=" * 60)


# ============================================================
# 主函数
# ============================================================

def main():
    """主函数：运行蒙特卡洛仿真验证。"""
    print("开始蒙特卡洛仿真验证...")
    print(f"参数: {PARAMS}")
    print(f"解析结果: {ANALYTICAL_RESULT}")
    print(f"仿真次数: {N_SIMULATIONS}")
    print()

    # 运行仿真
    simulation_result = run_monte_carlo(
        params=PARAMS,
        n_simulations=N_SIMULATIONS,
        batch_size=BATCH_SIZE,
        random_seed=RANDOM_SEED
    )

    # 对比解析结果
    comparison_result = compare_with_analytical(
        simulation_result=simulation_result,
        analytical_result=ANALYTICAL_RESULT,
        deviation_threshold=DEVIATION_THRESHOLD
    )

    # 打印摘要
    print_summary(simulation_result, comparison_result)

    # 保存结果
    save_results(simulation_result, comparison_result)

    return simulation_result, comparison_result


if __name__ == "__main__":
    main()
