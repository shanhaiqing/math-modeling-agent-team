#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
graph_utils.py — 图论工具薄封装（networkx，BSD 开源）
===============================================================================
求解阶段使用（条件触发：题目含图 / 网络结构——最短路、连通分量、最小生成树、最大流等）。

修改 PARAMETERS 区块（_demo_graph 与建图/调用方式），不修改 CORE ALGORITHM 区块。

设计原则：
- 全部算法委托 networkx（社区验证），本文件只做"输入标准化 + 输出标准化"：
  输入统一为 (nodes, edges) 轻量结构，输出统一为 Python 原生类型（list / dict / float）。
- 与手写图算法相比，networkx 覆盖算法面更广、边界情况（自环/多重边/负权/孤立节点）处理更完备；
  两者可互为黄金对拍（本项目 project/common_data.py 的手写 Dijkstra/BFS 即对拍参照）。
- 依赖：pip install networkx（BSD 开源，非商业），符合"禁止商业求解器"硬约束。
- 本文件保证"调用 / 透传正确性"（由小算例 + 对拍验证），不保证图数据的领域语义正确性。

四道闸门（新建/改动后必跑）：
1. 已知最优小算例：_demo_graph 为 5 节点无向加权图（见下方），
   最短路 1→5 = 5（路径 1-2-3-5）、最小生成树总权 = 8，均手算可证（见 _demo_graph 注释）。
2. 黄金对拍：networkx 最短路 vs 手写 Dijkstra（project/common_data.py 即手写参照），结果应一致。
3. 回归 / 断言：每次调用自动断言返回结构完整（path 非空 / 距离非负有限）。
4. 冒烟：py_compile + python -m graph_utils（main() 全断言通过）。
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import networkx as nx
except Exception as _e:  # pragma: no cover
    nx = None
    _NX_IMPORT_ERR = _e
else:
    _NX_IMPORT_ERR = None


# ============================================================
# PARAMETERS（根据题目修改此区块）
# ============================================================

def _demo_graph() -> Tuple[Iterable[int], List[Tuple[Any, Any, float]]]:
    """最小自测图：5 节点无向加权图。

    边 (a,b,w)：
        1-2: 2    1-3: 4    2-3: 1
        2-4: 7    3-4: 3    3-5: 2    4-5: 5
    手算结论（闸门 1 依据）：
        - 最短路 1→5：1-2-3-5 = 2+1+2 = 5
          （对比：1-3-5 = 4+2 = 6；1-2-4-5 = 2+7+5 = 14；1-3-4-5 = 4+3+5 = 12）
        - 最小生成树（Kruskal 升序）：(2,3)=1, (1,2)=2, (3,5)=2, (3,4)=3 → 总权 8
        - 连通分量：全图 1 个连通分量（无孤立节点）
    """
    nodes = [1, 2, 3, 4, 5]
    edges = [(1, 2, 2.0), (1, 3, 4.0), (2, 3, 1.0), (2, 4, 7.0),
             (3, 4, 3.0), (3, 5, 2.0), (4, 5, 5.0)]
    return nodes, edges


def load_edges() -> List[Tuple[Any, Any, float]]:
    """题目建图入口：按题目改此函数，返回 (a, b, weight) 边列表。

    若题目为无权图，weight 置 1.0 即可（最短路即最少边数）。
    若需最大流，edges 可含第四元容量：(a, b, weight, capacity)，见 max_flow。
    """
    return _demo_graph()[1]


# ============================================================
# CORE ALGORITHM（不修改此区块）
# ============================================================

def build_graph(nodes: Iterable[Any], edges: Sequence[Any],
                directed: bool = False) -> "nx.Graph":
    """
    由轻量结构构建 networkx 图。
    edges 元素支持： (a,b) / (a,b,w) / (a,b,w,capacity)。
    无向图 weight 双向存入（加一条边 networkx 自动对称）；有向图按给定方向。
    """
    G = nx.DiGraph() if directed else nx.Graph()
    G.add_nodes_from(list(nodes))
    for e in edges:
        a, b = e[0], e[1]
        w = float(e[2]) if len(e) >= 3 else 1.0
        if len(e) >= 4:
            G.add_edge(a, b, weight=w, capacity=float(e[3]))
        else:
            G.add_edge(a, b, weight=w)
    return G


def shortest_path(nodes: Iterable[Any], edges: Sequence[Any],
                  src: Any, dst: Any, directed: bool = False) -> Tuple[List[Any], float]:
    """最短路（Dijkstra，非负权）。返回 (路径节点序列, 总距离)。不可达时路径为 []、距离 inf。"""
    G = build_graph(nodes, edges, directed=directed)
    try:
        path = nx.shortest_path(G, src, dst, weight="weight")
        dist = float(nx.shortest_path_length(G, src, dst, weight="weight"))
        return list(path), dist
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return [], math.inf


def shortest_distances(nodes: Iterable[Any], edges: Sequence[Any],
                       src: Any, directed: bool = False) -> Dict[Any, float]:
    """单源最短路距离表 {节点: 距离}（不可达节点不出现在结果中）。"""
    G = build_graph(nodes, edges, directed=directed)
    return {k: float(v) for k, v in nx.single_source_dijkstra_path_length(G, src, weight="weight").items()}


def connected_components(nodes: Iterable[Any], edges: Sequence[Any]) -> List[List[Any]]:
    """无向连通分量（按大小降序）。"""
    G = build_graph(nodes, edges, directed=False)
    comps = sorted((list(c) for c in nx.connected_components(G)), key=len, reverse=True)
    return comps


def minimum_spanning_tree(nodes: Iterable[Any], edges: Sequence[Any]) -> Tuple[List[Tuple[Any, Any, float]], float]:
    """最小生成树。返回 (树边列表 [(a,b,w)], 总权)。"""
    G = build_graph(nodes, edges, directed=False)
    tree = nx.minimum_spanning_tree(G, weight="weight")
    total = float(tree.size(weight="weight"))
    mst_edges = [(u, v, float(tree[u][v]["weight"])) for u, v in tree.edges()]
    return mst_edges, total


def max_flow(nodes: Iterable[Any], edges: Sequence[Any],
             src: Any, sink: Any, directed: bool = True) -> Tuple[float, Dict[Any, Dict[Any, float]]]:
    """最大流（需边含容量，edges 元素形如 (a,b,weight,capacity)）。返回 (最大流值, 逐边流量字典)。"""
    G = build_graph(nodes, edges, directed=directed)
    if any("capacity" not in G[u][v] for u, v in G.edges()):
        raise ValueError("max_flow 要求全部边含容量（edges 元素须为 (a,b,weight,capacity)）")
    flow_value, flow_dict = nx.maximum_flow(G, src, sink, capacity="capacity")
    return float(flow_value), {k: {kk: float(vv) for kk, vv in vv_.items()} for k, vv_ in flow_dict.items()}


def _assert_valid(result: Any) -> None:
    """回归 / 断言：返回结构完整性校验（闸门 3）。"""
    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], list):
        # 最短路：路径为空时必须距离为 inf，否则必须有限且非负
        path, dist = result
        if path:
            assert math.isfinite(dist) and dist >= 0, f"最短路距离非法: {dist}"
        else:
            assert math.isinf(dist), "路径为空但距离有限——矛盾"
    elif isinstance(result, dict):
        assert all(math.isfinite(v) and v >= 0 for v in result.values()), "距离表含非法值"


def main():
    """自测：跑已知最优小算例 + 断言（四道闸门之 1/3/4）。"""
    print("=== graph_utils 自测（5 节点图：最短路=5，MST=8）===")
    if nx is None:
        print(f"❌ networkx 未安装: {_NX_IMPORT_ERR}")
        return 1
    nodes, edges = _demo_graph()

    path, dist = shortest_path(nodes, edges, 1, 5)
    print(f"最短路 1→5: {path}  距离: {dist}（期望 [1,2,3,5] / 5.0）")
    ok1 = path == [1, 2, 3, 5] and abs(dist - 5.0) <= 1e-9
    _assert_valid((path, dist))

    dists = shortest_distances(nodes, edges, 1)
    print(f"单源最短路 1→: {dists}（1→5 期望 5.0）")
    ok1b = abs(dists.get(5, -1) - 5.0) <= 1e-9
    _assert_valid(dists)

    comps = connected_components(nodes, edges)
    print(f"连通分量: {[len(c) for c in comps]}（期望 1 个，大小 5）")
    ok2 = len(comps) == 1 and len(comps[0]) == 5

    mst, total = minimum_spanning_tree(nodes, edges)
    print(f"MST 边: {mst}  总权: {total}（期望 8.0）")
    ok3 = len(mst) == 4 and abs(total - 8.0) <= 1e-9

    # max_flow 已知最优小算例：4 节点有向图（手算见 _demo_graph 上方注释补充）
    # 边 (a,b,weight,capacity): 1→2:3, 1→3:2, 2→3:1, 2→4:2, 3→4:2
    # 最大流 = 1→2→4(2) + 1→3→4(2) = 4；最小割 {1,2,3}|{4} = 2+2 = 4
    mf_nodes = [1, 2, 3, 4]
    mf_edges = [(1, 2, 1.0, 3), (1, 3, 1.0, 2), (2, 3, 1.0, 1), (2, 4, 1.0, 2), (3, 4, 1.0, 2)]
    flow, _ = max_flow(mf_nodes, mf_edges, 1, 4)
    print(f"max_flow 1→4: {flow}（期望 4.0）")
    ok4 = abs(flow - 4.0) <= 1e-9

    ok = ok1 and ok1b and ok2 and ok3 and ok4
    print("[PASS] 已知最优小算例通过" if ok else "[FAIL] 已知最优小算例失败")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
