#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
蒙特卡洛仿真验证模板

用途：
    对解析/枚举结果进行蒙特卡洛仿真交叉验证，作为"模型验证"维度（与"最优性验证"独立）。
    适用于含随机性 / 不确定性 / 稳态假设的问题。

使用方法：
    1. 复制此模板到 project/ 目录
    2. 修改 PARAMETERS 区块：填入题目参数和解析结果
    3. 修改 simulate_once 函数：定义单次仿真的逻辑
    4. 运行脚本，输出仿真次数、收敛情况、偏差、偏差原因分析

[注意] 蒙特卡洛仿真是"模型验证"，与"最优性验证"（MIPGap/枚举完备性）是两个独立维度，不可相互替代。
"""

import numpy as np
import json
from pathlib import Path

# ============================================================
# PARAMETERS 区块（用户修改）
# ============================================================

# 题目参数（从求解结果或参数表读取）
PARAMS = {
    # 示例：配件次品率
    "p1": 0.10,           # 配件1次品率
    "p2": 0.10,           # 配件2次品率
    "p成品": 0.10,        # 成品次品率（不含配件次品）
    # 示例：成本参数
    "c_test": 2,          # 单个配件检测成本（元/件）
    "c_assemble": 8,      # 装配成本（元/件）
    "c_disassemble": 6,   # 拆解成本（元/件）
    "c_replace": 30,      # 调换损失（元/件）
    "market_price": 200,  # 成品市场售价（元/件）
    # 示例：决策变量（从求解结果读取最优策略）
    "x1": 0,  # 是否检测配件1
    "x2": 0,  # 是否检测配件2
    "x3": 0,  # 是否检测成品
    "x4": 1,  # 是否拆解不合格品
}

# 解析结果（从求解结果读取，用于对比）
ANALYTICAL_RESULT = {
    "expected_profit_per_unit": 20.86,  # 期望利润（元/件）
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
    单次仿真：模拟一个成品从配件到销售的全流程，返回该次的利润。

    用户需根据具体问题修改此函数。以下示例为"生产决策问题"的仿真逻辑。

    Args:
        params: 参数字典
        rng: numpy 随机数生成器

    Returns:
        dict: 单次仿真结果，至少含 "profit" 字段
    """
    # 示例：模拟单个成品的生产-销售流程
    p1 = params["p1"]
    p2 = params["p2"]
    p_成品 = params["p成品"]

    # 步骤1：配件检测（若 x1=1，检测出次品则更换为合格品）
    if params["x1"] == 1:
        # 检测配件1，若次品则更换（成本 = 检测成本 + 次品更换成本）
        accessory1_defective = False  # 检测后必为合格
        cost_accessory1 = params["c_test"] + (p1 * params["c_test"])  # 检测 + 次品重检
    else:
        # 不检测，直接使用（可能次品）
        accessory1_defective = rng.random() < p1
        cost_accessory1 = 0

    if params["x2"] == 1:
        accessory2_defective = False
        cost_accessory2 = params["c_test"] + (p2 * params["c_test"])
    else:
        accessory2_defective = rng.random() < p2
        cost_accessory2 = 0

    # 步骤2：装配
    cost_assemble = params["c_assemble"]

    # 步骤3：成品检测（若 x3=1，检测出次品则进入拆解或废弃）
    if accessory1_defective or accessory2_defective:
        # 配件次品导致成品次品
        product_defective = True
    else:
        # 配件合格，成品仍可能因装配误差次品
        product_defective = rng.random() < p_成品

    if params["x3"] == 1:
        # 检测成品
        cost_test_product = params["c_test"]  # 成品检测成本（假设与配件相同，可修改）
        if product_defective:
            # 检测出次品，进入拆解或废弃
            if params["x4"] == 1:
                # 拆解：回收配件，可重新使用
                revenue = 0  # 不销售
                cost_disassemble = params["c_disassemble"]
                profit = -cost_accessory1 - cost_accessory2 - cost_assemble - cost_test_product - cost_disassemble
            else:
                # 废弃
                revenue = 0
                profit = -cost_accessory1 - cost_accessory2 - cost_assemble - cost_test_product
        else:
            # 成品合格，销售
            revenue = params["market_price"]
            profit = revenue - cost_accessory1 - cost_accessory2 - cost_assemble - cost_test_product
    else:
        # 不检测成品，直接销售
        cost_test_product = 0
        if product_defective:
            # 次品售出后被调换
            revenue = params["market_price"]
            cost_replace = params["c_replace"]
            profit = revenue - cost_accessory1 - cost_accessory2 - cost_assemble - cost_replace
        else:
            # 合格品正常销售
            revenue = params["market_price"]
            profit = revenue - cost_accessory1 - cost_accessory2 - cost_assemble

    return {"profit": profit, "product_defective": product_defective}


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
    all_profits = []
    batch_means = []

    for batch_start in range(0, n_simulations, batch_size):
        batch_end = min(batch_start + batch_size, n_simulations)
        batch_profits = []
        for _ in range(batch_end - batch_start):
            result = simulate_once(params, rng)
            batch_profits.append(result["profit"])
        all_profits.extend(batch_profits)
        batch_means.append(np.mean(batch_profits))

    all_profits = np.array(all_profits)
    mean = np.mean(all_profits)
    std = np.std(all_profits, ddof=1)
    std_of_mean = std / np.sqrt(n_simulations)
    convergence_ratio = std_of_mean / abs(mean) if mean != 0 else float('inf')

    return {
        "n_simulations": n_simulations,
        "mean": float(mean),
        "std": float(std),
        "std_of_mean": float(std_of_mean),
        "convergence_ratio": float(convergence_ratio),
        "batch_means": [float(x) for x in batch_means],
        "all_results": all_profits.tolist()
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
    analytical_value = analytical_result.get("expected_profit_per_unit", 0)
    simulation_mean = simulation_result["mean"]
    deviation = simulation_mean - analytical_value
    deviation_ratio = abs(deviation) / abs(analytical_value) if analytical_value != 0 else float('inf')
    is_within_threshold = deviation_ratio < deviation_threshold
    convergence_status = "收敛" if simulation_result["convergence_ratio"] < CONVERGENCE_THRESHOLD else "未收敛"

    analysis = ""
    if not is_within_threshold:
        # 偏差超过阈值，分析原因
        analysis = f"偏差 {deviation_ratio*100:.2f}% 超过阈值 {deviation_threshold*100:.2f}%，可能原因：\n"
        analysis += "1. 稳态假设不成立：仿真未达到稳态循环（如拆解后的配件重新进入流程）\n"
        analysis += "2. 独立性假设不成立：配件次品与成品次品存在相关性\n"
        analysis += "3. 解析推导有误：公式中的概率或成本项计算错误\n"
        analysis += "4. 仿真次数不足：增加 N_SIMULATIONS 后重新运行\n"
        analysis += "5. 循环稳态未达到：拆解后的配件多次循环后达到稳态，需使用稳态假设而非单次仿真\n"
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

    print(f"[OK] 仿真结果已保存到 {output_path}")


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
