#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""problem_track 合法性。

T5 之前编排器不得把本脚本当作 HG0 或 MODELING 的过门条件。
缺失、null、非法值退出码 1（将来不得进入 MODELING）。
opt / stats 退出码 0。

用法：
  python check_problem_track.py --value opt
  python check_problem_track.py --state path/to/pipeline_state.json
"""
import argparse
import json
import sys
from pathlib import Path

LEGAL = ("opt", "stats")


def status(value):
    if value is None:
        return "missing"
    if isinstance(value, str) and value.strip().lower() in ("", "null", "none"):
        return "missing"
    if str(value).strip() not in LEGAL:
        return "illegal"
    return "ok"


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--value", default=None)
    src.add_argument("--state", default=None)
    args = ap.parse_args()
    if args.state is not None:
        data = json.loads(Path(args.state).read_text(encoding="utf-8-sig"))
        value = data.get("problem_track") if isinstance(data, dict) else None
    else:
        value = args.value
    kind = status(value)
    print(kind)
    sys.exit(0 if kind == "ok" else 1)


if __name__ == "__main__":
    main()
