#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_viz_tests.py — 绘图板块测试冒烟机查

用途：绘图共享代码（visualization_style.py / figure-studio/）改动后，运行回归测试，任一失败判 ERROR；跑后清理测试残留 _test_out/。
      根治"测试脚本未纳入机查、API 脱节无人发现"的问题（2026-08 批次）。

用法：python check_viz_tests.py [code_templates_dir]
退出码：0 = 全部通过；1 = 存在失败。
"""
import subprocess
import sys
import shutil
from pathlib import Path

VIS_TESTS = [
    "test_scienceplots.py",
    "test_cmasher.py",
    "test_visualization.py",
    "test_fontfamily.py",
    "test_visual_qa_profile.py",
]


def main():
    here = Path(__file__).resolve().parent
    failures = []
    for name in VIS_TESTS:
        r = subprocess.run([sys.executable, str(here / name)], cwd=str(here),
                           capture_output=True, text=True)
        marker = "OK" if r.returncode == 0 else "FAIL"
        print(f"{marker}  {name}  (exit {r.returncode})")
        if r.returncode != 0:
            failures.append(name)
            detail = (r.stdout + r.stderr).strip().splitlines()[-8:]
            for line in detail:
                print(f"      {line}")

    # 清理测试残留（test_cmasher / test_visualization 会生成 _test_out/）
    residue = here / "_test_out"
    if residue.exists():
        shutil.rmtree(residue)

    if failures:
        print(f"ERROR: {len(failures)} 个绘图测试失败: {failures}")
        sys.exit(1)
    print("OK: 全部绘图测试通过")
    sys.exit(0)


if __name__ == "__main__":
    main()