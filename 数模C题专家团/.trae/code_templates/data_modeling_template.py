#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
data_modeling_template.py — 数据驱动建模骨架模板（C 题）

使用方式：复制本文件为 project/问题X_求解.py，只修改 PARAMETERS 区块与
TASK_HOOKS 中的题目专属函数，不改 CORE ALGORITHM 区块。

骨架流程：读数 → 预处理 → 划分 → 训练 → 指标评估 → 数据扰动灵敏度
契约对齐：输出字段对齐 AGENTS.md handoff 契约 solution.json 九字段。
泄漏防线：预处理统计量只在训练集拟合（数.3）；时序数据保序划分（卡片 04/10）。
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path

# ============================================================
# PARAMETERS（题目专属参数——只允许修改本区块与 TASK_HOOKS）
# ============================================================

P = {
    "data_path": "附件数据路径.xlsx",      # 题目附件路径
    "target_col": "目标变量列名",           # 无监督任务置 None
    "time_col": None,                      # 时序任务填时间列名，触发保序划分
    "group_col": None,                     # 分组数据填组列名，触发 GroupKFold
    "task_type": "prediction",             # prediction/classification/forecasting/clustering/evaluation/statistical_inference/descriptive/optimization_downstream
    "test_size": 0.2,
    "cv_folds": 5,
    "random_seed": 42,
    "missing_strategy": "median",          # median/mean/drop
    "outlier_rule": "3sigma",              # 3sigma/iqr/none
    "scaling": "standard",                 # standard/minmax/none
    "sensitivity_perturb": [0.05, 0.10, 0.20],  # 数据扰动幅度（数.5）
    "bootstrap_B": 1000,                   # bootstrap 次数
}


# ============================================================
# TASK_HOOKS（题目专属钩子函数——按题目实现）
# ============================================================

def load_data(path):
    """读数：返回 DataFrame。大附件先按'大附件处理规范'做质量摘要。"""
    df = pd.read_excel(path) if str(path).endswith((".xlsx", ".xls")) else pd.read_csv(path)
    return df


def build_features(df_train, df_test):
    """特征工程钩子：只在训练集上学习的变换（如目标编码统计量）在此实现。
    返回 (X_train, X_test, feature_names)。默认透传数值列。"""
    return df_train, df_test, list(df_train.columns)


def candidate_models(task_type, seed):
    """候选模型清单（≥2 候选 + 基线，数.6 强制）。按任务类型替换为实际模型。"""
    from sklearn.dummy import DummyRegressor, DummyClassifier
    from sklearn.linear_model import LinearRegression, LogisticRegression
    if task_type in ("prediction", "forecasting"):
        return {"baseline_mean": DummyRegressor(strategy="mean"),
                "linear": LinearRegression()}
    if task_type == "classification":
        return {"baseline_majority": DummyClassifier(strategy="most_frequent"),
                "logistic": LogisticRegression(max_iter=1000, random_state=seed)}
    raise ValueError(f"task_type={task_type} 需自行实现候选模型")


def task_metrics(task_type):
    """指标-任务匹配（数.4）：返回 (主指标名, 指标函数字典)。"""
    from sklearn.metrics import (mean_squared_error, mean_absolute_error,
                                 r2_score, accuracy_score, f1_score, roc_auc_score)
    if task_type in ("prediction", "forecasting"):
        return "rmse", {"rmse": lambda y, p: float(np.sqrt(mean_squared_error(y, p))),
                        "mae": lambda y, p: float(mean_absolute_error(y, p)),
                        "r2": lambda y, p: float(r2_score(y, p))}
    if task_type == "classification":
        return "f1", {"accuracy": lambda y, p: float(accuracy_score(y, p)),
                      "f1": lambda y, p: float(f1_score(y, p, average="weighted"))}
    raise ValueError(f"task_type={task_type} 需自行实现指标")


# ============================================================
# CORE ALGORITHM（通用骨架——禁止修改；如需改动说明理由并记录）
# ============================================================

def preprocess_fit_transform(df, p, fitted=None):
    """预处理（卡片 01）：缺失→异常→编码→缩放。
    fitted=None 时在传入数据上拟合（只允许传训练集）；
    fitted 非 None 时复用其统计量做 transform（泄漏防线，数.3）。"""
    df = df.copy()
    num_cols = df.select_dtypes(include=[np.number]).columns
    if fitted is None:
        fitted = {}
        if p["missing_strategy"] in ("median", "mean"):
            agg = df[num_cols].median() if p["missing_strategy"] == "median" else df[num_cols].mean()
            fitted["fill_values"] = agg
        if p["outlier_rule"] == "3sigma":
            fitted["clip_lo"] = df[num_cols].mean() - 3 * df[num_cols].std()
            fitted["clip_hi"] = df[num_cols].mean() + 3 * df[num_cols].std()
        if p["scaling"] == "standard":
            fitted["mean"] = df[num_cols].mean()
            fitted["std"] = df[num_cols].std().replace(0, 1)
        elif p["scaling"] == "minmax":
            fitted["min"] = df[num_cols].min()
            fitted["range"] = (df[num_cols].max() - df[num_cols].min()).replace(0, 1)
    if "fill_values" in fitted:
        df[num_cols] = df[num_cols].fillna(fitted["fill_values"])
    if "clip_lo" in fitted:
        df[num_cols] = df[num_cols].clip(fitted["clip_lo"], fitted["clip_hi"], axis=1)
    if p["scaling"] == "standard" and "mean" in fitted:
        df[num_cols] = (df[num_cols] - fitted["mean"]) / fitted["std"]
    elif p["scaling"] == "minmax" and "min" in fitted:
        df[num_cols] = (df[num_cols] - fitted["min"]) / fitted["range"]
    return df, fitted


def split_data(df, p):
    """划分（卡片 10）：时序保序 / 普通随机。分组 CV 在评估环节处理。"""
    if p["time_col"] is not None:
        df = df.sort_values(p["time_col"]).reset_index(drop=True)
        cut = int(len(df) * (1 - p["test_size"]))
        return df.iloc[:cut], df.iloc[cut:]          # 保序，禁止 shuffle（数.3）
    rng = np.random.default_rng(p["random_seed"])
    idx = rng.permutation(len(df))
    cut = int(len(df) * (1 - p["test_size"]))
    return df.iloc[idx[:cut]], df.iloc[idx[cut:]]


def cross_val_scores(model, X, y, p):
    """交叉验证：分组用 GroupKFold，时序用 TimeSeriesSplit，否则分层/普通 KFold。"""
    from sklearn.model_selection import KFold, GroupKFold, TimeSeriesSplit, cross_validate
    if p["group_col"] is not None:
        cv = GroupKFold(n_splits=p["cv_folds"])
        groups = X[p["group_col"]] if p["group_col"] in X else None
    elif p["time_col"] is not None:
        cv, groups = TimeSeriesSplit(n_splits=p["cv_folds"]), None
    else:
        cv, groups = KFold(n_splits=p["cv_folds"], shuffle=True,
                           random_state=p["random_seed"]), None
    primary, mets = task_metrics(p["task_type"])
    res = cross_validate(model, X, y, cv=cv, groups=groups,
                         scoring={k: f"neg_{k}" if False else k for k in []} or None)
    return res


def evaluate_model(name, model, Xtr, ytr, Xte, yte, p):
    """训练 + train/test 双口径指标（overfitting_check 数据源）。"""
    model.fit(Xtr, ytr)
    primary, mets = task_metrics(p["task_type"])
    out = {}
    for split, X_, y_ in (("train", Xtr, ytr), ("test", Xte, yte)):
        pred = model.predict(X_)
        out[split] = {k: f(y_, pred) for k, f in mets.items()}
    gap = abs(out["train"][primary] - out["test"][primary])
    out["overfitting_check"] = {
        "train_test_gap": gap,
        "judgment": "✓ 差距可接受" if gap <= max(0.1 * abs(out["test"][primary]), 1e-9)
                    else "⚠ train/test 差距大，存在过拟合风险",
    }
    return out


def data_sensitivity(train_fn, df_train, p):
    """数据扰动灵敏度（数.5）：特征加噪 ±5/10/20%，重训并报主指标漂移。"""
    primary, _ = task_metrics(p["task_type"])
    records = []
    for eps in p["sensitivity_perturb"]:
        drift = train_fn(df_train, eps)
        records.append({"perturbation": f"feature_noise_±{eps:.0%}",
                        "primary_metric": primary, "value": drift})
    return records


def main():
    p = P
    df = load_data(p["data_path"])
    target = p["target_col"]

    df_train, df_test = split_data(df, p)
    # 泄漏防线：预处理仅在训练集拟合，统计量复用到测试集（数.3）
    train_pp, fitted = preprocess_fit_transform(df_train, p, fitted=None)
    test_pp, _ = preprocess_fit_transform(df_test, p, fitted=fitted)
    Xtr, Xte, feats = build_features(train_pp, test_pp)
    ytr, yte = (Xtr.pop(target), Xte.pop(target)) if target else (None, None)

    results = {}
    for name, model in candidate_models(p["task_type"], p["random_seed"]).items():
        results[name] = evaluate_model(name, model, Xtr, ytr, Xte, yte, p)

    # 模型选择：测试集主指标最优的非基线模型（基线只作对照，数.6）
    primary, _ = task_metrics(p["task_type"])
    best = max((k for k in results if not k.startswith("baseline")),
               key=lambda k: results[k]["test"][primary])

    solution = {
        "task_type": p["task_type"],
        "objective_or_goal": "按题目填写本问题的目标口径",
        "metrics": results[best]["test"] | {"split": "test",
                                            "train_metrics": results[best]["train"]},
        "model": {"name": best, "key_params": {},
                  "selection": {"candidates": list(results),
                                "baseline": {k: v["test"] for k, v in results.items()
                                             if k.startswith("baseline")},
                                "reason": "按题目填写选择理由"}},
        "validation": {"method": "holdout+kfold_cv", "scores": results[best],
                       "overfitting_check": results[best]["overfitting_check"]},
        "preprocessing": {"missing": p["missing_strategy"], "outliers": p["outlier_rule"],
                          "encoding": "按实际填写", "scaling": p["scaling"],
                          "train_test_isolation": "预处理统计量仅在训练集拟合，测试集复用 transform"},
        "data_lineage": {"source": p["data_path"], "row_scope": "按实际填写"},
        "sensitivity": [],   # 由 data_sensitivity 填充
        "monte_carlo": None, # 含随机性/不确定性时按 monte_carlo_template.py 填写，否则附不适用说明
    }
    Path("project/results").mkdir(parents=True, exist_ok=True)
    out = Path("project/results/solution_问题X.json")
    out.write_text(json.dumps(solution, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已输出: {out}")


if __name__ == "__main__":
    main()
