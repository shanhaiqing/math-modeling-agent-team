#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data_explore.py — 附件数据剖析
输出：规模/字段类型/缺失值/异常值(±3σ)/分布摘要/前后各10行样例
结论打印输出，剖析报告写入 results/data_profile.json。
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))   # project 目录
DATA = os.path.join(HERE, "data")
RESULTS = os.path.join(HERE, "results")
F1 = os.path.join(DATA, "附件一：作战节点与通路数据.xlsx")
F2 = os.path.join(DATA, "附件二：红警装备参数表.xlsx")


def profile_series(s: pd.Series) -> dict:
    """对单列做分布摘要 + 3σ 异常值检测。"""
    out = {"dtype": str(s.dtype), "n_missing": int(s.isna().sum())}
    if pd.api.types.is_numeric_dtype(s):
        out.update({
            "min": float(s.min()), "max": float(s.max()),
            "mean": round(float(s.mean()), 4), "std": round(float(s.std()), 4),
            "median": float(s.median()),
        })
        mu, sd = s.mean(), s.std()
        if sd and sd > 0:
            outliers = s[(s - mu).abs() > 3 * sd]
            out["outliers_3sigma"] = [float(v) for v in outliers.tolist()]
        else:
            out["outliers_3sigma"] = []
    else:
        vc = s.value_counts()
        out["unique"] = int(s.nunique())
        out["top_values"] = {str(k): int(v) for k, v in vc.head(10).items()}
    return out


def main():
    report = {}

    # ---------- 附件一 ----------
    nodes = pd.read_excel(F1, sheet_name="节点信息")
    edges = pd.read_excel(F1, sheet_name="通路信息")
    equip = pd.read_excel(F2, sheet_name="装备参数")

    print("=" * 60)
    print("附件一 sheet 节点信息:", nodes.shape)
    print(nodes.dtypes)
    print("前10行:\n", nodes.head(10).to_string())
    print("后10行:\n", nodes.tail(10).to_string())
    print("=" * 60)
    print("附件一 sheet 通路信息:", edges.shape)
    print(edges.dtypes)
    print("前10行:\n", edges.head(10).to_string())
    print("后10行:\n", edges.tail(10).to_string())
    print("=" * 60)
    print("附件二 sheet 装备参数:", equip.shape)
    print(equip.to_string())
    print("=" * 60)

    report["nodes"] = {"shape": list(nodes.shape),
                       "columns": list(nodes.columns),
                       "profile": {c: profile_series(nodes[c]) for c in nodes.columns}}
    report["edges"] = {"shape": list(edges.shape),
                       "columns": list(edges.columns),
                       "profile": {c: profile_series(edges[c]) for c in edges.columns}}
    report["equip"] = {"shape": list(equip.shape),
                       "columns": list(equip.columns),
                       "raw": equip.fillna("").astype(str).to_dict(orient="records")}

    # 交叉完整性检查：通路端点是否都在节点集合内
    id_col = nodes.columns[0]
    node_ids = set(nodes[id_col].tolist())
    e_from, e_to = edges.columns[1], edges.columns[2]
    bad_from = set(edges[e_from]) - node_ids
    bad_to = set(edges[e_to]) - node_ids
    report["edge_endpoint_check"] = {
        "edges_with_unknown_from": sorted(bad_from)[:20],
        "edges_with_unknown_to": sorted(bad_to)[:20],
        "n_bad_from": len(bad_from), "n_bad_to": len(bad_to),
    }
    # 重复边检查
    dup = edges.duplicated(subset=[e_from, e_to]).sum()
    report["duplicate_edges"] = int(dup)

    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "data_profile.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print("数据剖析报告已写入 results/data_profile.json")


if __name__ == "__main__":
    main()
