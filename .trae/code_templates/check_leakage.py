#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_leakage.py — 数据泄漏启发式机查（C 系统专属，WARN 级不阻塞）

[契约] AGENTS.md 数据题泄漏防线（预处理统计量只在训练集拟合，惯例 数.3）；
       与 data_modeling_template.py 的 CORE 函数 split_data / preprocess_fit_transform 配套。
[背景] 双模型评审共识 C-维度三：C 的泄漏防线只有"机制层"（CORE 模板）是真的，
       而 CORE 只对走模板的题型生效；solver 自写主流程绕过防线时无机查兜底。
       本脚本扫描求解代码文本，捕捉"划分前对全量数据拟合统计量"等典型泄漏形态。
[定位] 启发式——只报 WARN，不阻塞流水线；裁定权按惯例 五.1 归 reviewer。
       设计纪律：宁可漏报不可误报（参照 check_reflection.py 三轮消误报的教训）。
       SANCTIONED 函数（CORE 防线）一律不报，它们是正确路径。
检查项（均为 WARN）：
  W1 疑似在测试/验证集上拟合统计量（fit 的参数含 test/val 标识，且非 CORE 防线调用）
  W2 对全量数据 fit_transform 后再 train_test_split（划分前泄漏的经典形态）
  W3 用了预处理拟合但全文未见任何划分调用（无法确认统计量仅在训练集拟合）
用法:
  python check_leakage.py <代码目录> [--report leakage_check_report.json]
退出码: 恒为 0（纯 WARN 级，不阻塞）；2 = 用法错误
输出:   **默认仅终端输出，不落盘**（与 check_reflection.py / check_machine_checks.py
        同为 WARN 级脚本的一致约定，避免在项目根产生未注册文件）；
        需留证时用 --report 显式指定路径。
"""
import json
import re
import sys
from pathlib import Path

# CORE 防线函数：调用它们即正确路径，永不报警
SANCTIONED = ("preprocess_fit_transform", "split_data")

# 预处理拟合信号（sklearn 风格，CORE 防线之外）
FIT_RE = re.compile(r"\.fit_transform\(|\.fit\(|StandardScaler|MinMaxScaler|RobustScaler|LabelEncoder|OrdinalEncoder")
# 划分信号：出现任一即认为该文件有划分机制
SPLIT_RE = re.compile(r"train_test_split|split_data|preprocess_fit_transform|TimeSeriesSplit|\.iloc\[:\s*cut|KFold|GroupKFold")
# 测试/验证集标识（用于 W1）
TEST_RE = re.compile(r"\btest\b|_te\b|_test\b|\bXte\b|\byte\b|\bval\b|valid", re.IGNORECASE)
# fit_transform 赋值：捕获输出变量名（W2）
FIT_ASSIGN_RE = re.compile(r"^\s*(\w+)\s*(?:,\s*\w+\s*)?=\s*[\w.\(\)]*\.fit_transform\(")

FINDINGS = []


def warn(loc, msg):
    FINDINGS.append({"level": "WARN", "location": loc, "message": msg})


def check_file(path):
    try:
        source = path.read_text(encoding="utf-8-sig")
    except Exception:
        source = path.read_text(encoding="utf-8", errors="replace")
    lines = source.splitlines()
    n_warn = 0

    # W1：疑似在测试/验证集上拟合（排除 CORE 防线调用与 fitted= 复用）
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if any(fn in s for fn in SANCTIONED):     # CORE 防线，正确路径
            continue
        if "fitted=" in s:                        # 复用已拟合统计量，正确
            continue
        if FIT_RE.search(s) and TEST_RE.search(s) and ".transform(" not in s:
            warn(f"{path.name}:{i}", f"W1 疑似在测试/验证集上拟合统计量：{s[:80]}")
            n_warn += 1

    # W2：对 fit_transform 输出变量再做 train_test_split（划分前泄漏）
    fitted_vars = set()
    for i, line in enumerate(lines, 1):
        m = FIT_ASSIGN_RE.match(line)
        if m and not any(fn in line for fn in SANCTIONED):
            fitted_vars.add((m.group(1), i))
    for var, defline in fitted_vars:
        for j, line in enumerate(lines, 1):
            if j <= defline:
                continue
            if "train_test_split" in line and re.search(rf"\b{re.escape(var)}\b", line):
                warn(f"{path.name}:{j}",
                     f"W2 变量 {var}（L{defline} 由 fit_transform 产出）在 L{j} 被 train_test_split 划分——"
                     f"划分前已用全量数据拟合统计量，属泄漏")
                n_warn += 1
                break

    # W3：有预处理拟合但全文无划分机制（无法确认仅训练集拟合）
    has_fit = any(FIT_RE.search(l) and not any(fn in l for fn in SANCTIONED) for l in lines)
    has_split = any(SPLIT_RE.search(l) for l in lines)
    if has_fit and not has_split:
        warn(f"{path.name}", "W3 使用预处理拟合（scaler/fit_transform）但全文未见任何划分调用，"
             "无法确认统计量仅在训练集拟合——请人工核对是否走 CORE 防线")
        n_warn += 1

    return n_warn


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--report")]
    if not args:
        print("用法：python check_leakage.py <代码目录> [--report 路径]")
        sys.exit(2)
    root = Path(args[0])
    if not root.is_dir():
        print(f"用法错误：目录不存在 {root}")
        sys.exit(2)
    report_path = None
    if "--report" in sys.argv:
        report_path = Path(sys.argv[sys.argv.index("--report") + 1])

    files = sorted(root.rglob("*.py"))
    total = 0
    for f in files:
        total += check_file(f)

    for f in FINDINGS[:50]:
        print(f"{f['level']:4s} {f['location']} {f['message']}")
    if len(FINDINGS) > 50:
        print(f"...（共 {len(FINDINGS)} 条，余略，详见报告）")
    if total == 0:
        print(f"扫描 {len(files)} 个 .py 文件，未检出泄漏形态（启发式，不替代人工核对）")
    else:
        print(f"汇总：{total} WARN / {len(files)} 文件扫描（WARN 级不阻塞，按惯例 五.1 交 reviewer 裁定）")

    if report_path is not None:
        report_path.write_text(json.dumps(
            {"checker": "check_leakage", "scanned": len(files),
             "error": 0, "warn_count": total, "findings": FINDINGS},
            ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"报告已写入: {report_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
