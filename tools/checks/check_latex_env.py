#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_latex_env.py — LaTeX 编译环境预检（机查版）

[契约] 总审批清单 2026-08-B1 P1-a：WRITING 启动前运行；xelatex / 关键宏包 /
       中文字体任一缺失即报告用户，禁止子代理自行安装 TeX 发行版。
[背景] 历史教训：无可用 xelatex 时曾临时安装约 200MB 便携版 MiKTeX，
       触发十余次格式重建与多轮字体试错，编译反复崩溃。
检查项：
  1. xelatex 可执行（ERROR 级）
  2. 关键宏包可定位：ctexart.cls / fvextra.sty / booktabs.sty / geometry.sty /
     setspace.sty / enumitem.sty / caption.sty（kpsewhich 可用时 ERROR 级；
     kpsewhich 不可用时降级 WARN，由冒烟测试兜底）
  3. 中文字体：Windows 检查 SimSun/SimHei 字体文件；其他平台尝试 fc-list；
     均不可判定时 WARN
用法:
  python check_latex_env.py [--contest-profile=cumcm|shuwei_zh|shuwei_en] [--report latex_env_report.json]
  --contest-profile 缺省 cumcm：检 xelatex + ctexart + 中文字体。
  shuwei_en：检 pdflatex + article.cls + vendored swmcmthesis.cls；中文字体缺失不升 ERROR。
退出码: 0 = 无 ERROR；1 = 存在 ERROR；2 = 用法错误
输出:   控制台逐条打印 + 写 latex_env_report.json（默认当前目录）
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

FINDINGS = []


def error(rule, msg):
    FINDINGS.append({"level": "ERROR", "rule": rule, "message": msg})


def warn(rule, msg):
    FINDINGS.append({"level": "WARN", "rule": rule, "message": msg})


def ok(rule, msg):
    FINDINGS.append({"level": "PASS", "rule": rule, "message": msg})


def run(cmd):
    """运行命令，返回 (returncode, stdout+stderr)；失败返回 (None, 错误信息)。"""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                           encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        return None, str(e)


def check_xelatex():
    exe = shutil.which("xelatex")
    if not exe:
        error("xelatex", "未找到 xelatex——请安装系统级 TeX 发行版（推荐 TeX Live scheme-full）"
                          "后重试；禁止子代理自行安装便携版发行版")
        return False
    rc, out = run([exe, "--version"])
    if rc != 0:
        error("xelatex", f"xelatex 存在但无法运行（{out.strip()[:200]}）")
        return False
    ok("xelatex", f"xelatex 可用：{out.splitlines()[0].strip()}")
    return True


REQUIRED_PACKAGES = [
    "ctexart.cls", "fvextra.sty", "booktabs.sty", "geometry.sty",
    "setspace.sty", "enumitem.sty", "caption.sty",
]

REQUIRED_PACKAGES_SHUWEI = [
    "article.cls", "fvextra.sty", "booktabs.sty", "geometry.sty",
    "enumitem.sty", "caption.sty",
]


def check_pdflatex():
    exe = shutil.which("pdflatex")
    if not exe:
        error("pdflatex", "未找到 pdflatex——shuwei_en 官方模板推荐 pdflatex；"
                          "请安装系统级 TeX 发行版后重试；禁止子代理自行安装便携版发行版")
        return False
    rc, out = run([exe, "--version"])
    if rc != 0:
        error("pdflatex", f"pdflatex 存在但无法运行（{out.strip()[:200]}）")
        return False
    ok("pdflatex", f"pdflatex 可用：{out.splitlines()[0].strip()}")
    return True


def check_packages(profile="cumcm"):
    pkgs = REQUIRED_PACKAGES_SHUWEI if profile == "shuwei_en" else REQUIRED_PACKAGES
    kpse = shutil.which("kpsewhich")
    if not kpse:
        warn("宏包", "kpsewhich 不可用，无法定位宏包——请以空模板冒烟编译结果为准")
    else:
        missing = []
        for pkg in pkgs:
            rc, out = run([kpse, pkg])
            if rc != 0 or not out.strip():
                missing.append(pkg)
        if missing:
            error("宏包", f"关键宏包缺失：{', '.join(missing)}——"
                          f"请用发行版包管理器安装（MiKTeX 需设为自动安装免询问）")
        else:
            ok("宏包", f"关键宏包齐全（{len(pkgs)} 个）")
    if profile == "shuwei_en":
        cls = Path(__file__).resolve().parent / "shuwei" / "swmcmthesis.cls"
        cfg = cls.with_suffix(".cfg")
        if cls.is_file() and cfg.is_file():
            ok("文档类", f"vendored swmcmthesis 在 {cls.parent}")
        else:
            error("文档类", f"缺少 {cls.name} 或 {cfg.name}——从 数维杯格式规范 拷贝至 tools/checks/shuwei/")


def check_fonts(profile="cumcm"):
    if profile == "shuwei_en":
        ok("中文字体", "shuwei_en 不要求 SimSun/SimHei（全文英文）")
        return
    if sys.platform == "win32":
        fonts_dir = Path("C:/Windows/Fonts")
        simsun = any(fonts_dir.glob(n) for n in ("simsun.ttc", "SimSun.ttf"))
        simhei = any(fonts_dir.glob(n) for n in ("simhei.ttf", "SimHei.ttf"))
        if simsun and simhei:
            ok("中文字体", "SimSun / SimHei 均在系统字体目录")
        else:
            lack = [n for n, has in (("SimSun", simsun), ("SimHei", simhei)) if not has]
            error("中文字体", f"中文字体缺失：{', '.join(lack)}——ctexart 中文排版将失败")
        return
    fc = shutil.which("fc-list")
    if not fc:
        warn("中文字体", "非 Windows 且无 fc-list，无法判定中文字体——请人工确认 SimSun/SimHei 或等价字体")
        return
    rc, out = run([fc])
    if rc == 0 and ("SimSun" in out or "Noto Sans CJK" in out):
        ok("中文字体", "检测到可用中文字体")
    else:
        error("中文字体", "未检测到 SimSun/Noto CJK 中文字体——请安装后重试")


def main():
    report_path = Path("latex_env_report.json")
    profile = "cumcm"
    argv = sys.argv[1:]
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--contest-profile="):
            v = a.split("=", 1)[1].strip().lower()
            profile = v if v in ("cumcm", "shuwei_zh", "shuwei_en") else "cumcm"
        elif a == "--report":
            if i + 1 >= len(argv):
                print("用法错误：--report 需要路径参数")
                sys.exit(2)
            report_path = Path(argv[i + 1])
            i += 1
        i += 1

    if profile == "shuwei_en":
        check_pdflatex()
    else:
        check_xelatex()
    check_packages(profile)
    check_fonts(profile)

    n_err = sum(1 for f in FINDINGS if f["level"] == "ERROR")
    n_warn = sum(1 for f in FINDINGS if f["level"] == "WARN")
    n_pass = sum(1 for f in FINDINGS if f["level"] == "PASS")
    for f in FINDINGS:
        print(f"{f['level']:5s} [{f['rule']}] {f['message']}")
    print(f"汇总：{n_err} ERROR / {n_warn} WARN / {n_pass} PASS")

    report_path.write_text(json.dumps(
        {"checker": "check_latex_env", "contest_profile": profile,
         "error": n_err, "warn": n_warn,
         "pass": n_pass, "findings": FINDINGS},
        ensure_ascii=False, indent=2), encoding="utf-8")
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()
