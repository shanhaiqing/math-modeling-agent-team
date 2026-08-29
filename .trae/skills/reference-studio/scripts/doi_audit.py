#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
doi_audit.py — 参考文献 DOI/URL 可达性批量核验（reference-studio 审计通道）

补上惯例 二.3「参考文献可查证」长期无核查者的缺口。两种用法：

  模式 A（预筛查，写作初期淘汰死链）：
      python doi_audit.py precheck <拟引清单.txt>
      清单每行一个 DOI（10.xxxx/...）或 URL（https?://...）。
      输出逐条结果 + 通过率；通过率 <90% → 退出码 1（换来源）。

  模式 B（扫描，交付前/机查兜底）：
      python doi_audit.py scan <paper.tex 或 ref.bib>
      从 thebibliography 环境（\\bibitem 文本）或 .bib 条目（doi=/url= 字段）
      提取全部 DOI/URL 并批量请求。
      输出：控制台逐条（级别 [规则] 说明）+ 末尾 JSON 汇总行。
      退出码：0 = 无 ERROR；1 = 有 ERROR；2 = 用法错误。

级别判定（网络环境不稳定，区分「确定死链」与「网络存疑」）：
  ERROR = 确定不可达（HTTP 404/410、域名解析失败）——文献必须替换；
  WARN  = 超时/连接失败/HTTP 403（反爬）/条目无 DOI/URL——人工裁定；
  PASS  = HTTP <400（含重定向后可达）。
"""
import json
import re
import socket
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
TIMEOUT = 10
PASS_RATE_THRESHOLD = 0.9

DOI_PAT = re.compile(r"\b10\.\d{4,9}/[^\s}\],;\"']+")
URL_PAT = re.compile(r"https?://[^\s}\],;\"']+")


# ============================================================
# 条目提取
# ============================================================

def extract_from_bib(bib_path):
    """从 .bib 提取 [(key, doi_or_url)]：doi= 字段优先，url= 兜底。"""
    text = Path(bib_path).read_text(encoding="utf-8", errors="replace")
    entries = []
    for m in re.finditer(r"@\w+\s*\{([^,]*),(.*?)(?=@\w+\s*\{|\Z)", text, re.S):
        key, body = m.group(1).strip(), m.group(2)
        doi = re.search(r"doi\s*=\s*[\"{]?([^}\"]+)", body, re.I)
        url = re.search(r"url\s*=\s*[\"{]?(https?://[^}\"]+)", body, re.I)
        if doi:
            entries.append((key, "https://doi.org/" + doi.group(1).strip()))
        elif url:
            entries.append((key, url.group(1).strip()))
        else:
            entries.append((key, None))
    return entries


def extract_from_tex(tex_path):
    """从 tex 提取 [(key, doi_or_url)]：thebibliography 环境内 \\bibitem 文本中的
    DOI/URL；无 thebibliography 时回退到 \\bibliography{...} 指向的 .bib。"""
    text = Path(tex_path).read_text(encoding="utf-8", errors="replace")
    entries = []
    env = re.search(r"\\begin\{thebibliography\}.*?\\end\{thebibliography\}", text, re.S)
    if env:
        for m in re.finditer(r"\\bibitem(?:\[[^\]]*\])?\{([^}]*)\}(.*?)(?=\\bibitem|\\end\{thebibliography\})",
                             env.group(0), re.S):
            key, body = m.group(1).strip(), m.group(2)
            doi = DOI_PAT.search(body)
            url = URL_PAT.search(body)
            if doi:
                entries.append((key, "https://doi.org/" + doi.group(0)))
            elif url:
                entries.append((key, url.group(0)))
            else:
                entries.append((key, None))
        return entries
    m = re.search(r"\\bibliography\{([^}]+)\}", text)
    if m:
        bib = Path(tex_path).parent / (m.group(1) + ".bib")
        if bib.is_file():
            return extract_from_bib(bib)
    return entries


# ============================================================
# 可达性检查
# ============================================================

def check_url(url):
    """返回 (级别, 说明)：PASS/ERROR/WARN 三级（见模块 docstring 判定规则）。"""
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=TIMEOUT) as resp:
            code = resp.getcode()
            if code < 400:
                return ("PASS", f"HTTP {code}")
            return ("WARN", f"HTTP {code}——非常规响应，人工打开确认")
    except HTTPError as e:
        if e.code in (404, 410):
            return ("ERROR", f"HTTP {e.code}——确定死链，须替换来源")
        if e.code == 403:
            return ("WARN", "HTTP 403——疑似反爬拦截，人工浏览器打开确认")
        return ("WARN", f"HTTP {e.code}——人工打开确认")
    except URLError as e:
        reason = str(e.reason)
        if isinstance(e.reason, socket.gaierror) or "getaddrinfo failed" in reason \
                or "Name or service not known" in reason:
            return ("ERROR", "域名解析失败——确定不可达，须替换来源")
        return ("WARN", f"连接失败（{reason[:60]}）——网络存疑，人工裁定")
    except (socket.timeout, TimeoutError):
        return ("WARN", f"超时（>{TIMEOUT}s）——网络存疑，人工裁定")
    except Exception as e:
        return ("WARN", f"请求异常（{type(e).__name__}: {str(e)[:60]}）——人工裁定")


def audit_entries(entries):
    """批量检查 [(key, url)]，逐条打印，返回 (findings, n_err)。"""
    findings = []
    for key, url in entries:
        if not url:
            findings.append(("WARN", "无出处", f"{key}: 条目无 DOI/URL 字段——无法机查，人工核对可查证性"))
            continue
        level, detail = check_url(url)
        rule = {"PASS": "可达", "ERROR": "死链", "WARN": "存疑"}[level]
        findings.append((level, rule, f"{key}: {url[:70]} — {detail}"))
    for lv, rule, msg in findings:
        print(f"{lv} [{rule}] {msg}")
    n_err = sum(1 for lv, _, _ in findings if lv == "ERROR")
    return findings, n_err


# ============================================================
# 两种模式
# ============================================================

def precheck(list_file):
    """模式 A：拟引清单预筛查，通过率 <90% 退出码 1。"""
    p = Path(list_file)
    if not p.is_file():
        print(f"用法错误：清单不存在 {list_file}")
        sys.exit(2)
    lines = [ln.strip() for ln in p.read_text(encoding="utf-8", errors="replace").splitlines()
             if ln.strip() and not ln.strip().startswith("#")]
    if not lines:
        print("用法错误：清单为空")
        sys.exit(2)
    entries = []
    for i, ln in enumerate(lines, 1):
        url = ln if ln.startswith("http") else ("https://doi.org/" + ln if DOI_PAT.match(ln) else None)
        entries.append((f"line{i}", url))
    print(f"预筛查 {len(entries)} 条拟引来源...")
    findings, n_err = audit_entries(entries)
    n_pass = sum(1 for lv, _, _ in findings if lv == "PASS")
    rate = n_pass / len(entries)
    print(f"\n通过率: {n_pass}/{len(entries)} = {rate:.0%}（要求 ≥{PASS_RATE_THRESHOLD:.0%}）")
    print(json.dumps({"checker": "doi_audit", "mode": "precheck", "total": len(entries),
                      "pass": n_pass, "rate": round(rate, 3), "errors": n_err}, ensure_ascii=False))
    sys.exit(1 if rate < PASS_RATE_THRESHOLD else 0)


def scan(target):
    """模式 B：扫描 tex/bib 全量条目，有 ERROR 退出码 1。"""
    p = Path(target)
    if not p.is_file():
        print(f"用法错误：文件不存在 {target}")
        sys.exit(2)
    entries = extract_from_bib(p) if p.suffix == ".bib" else extract_from_tex(p)
    if not entries:
        print(f"WARN [无条目] {target} 中未提取到任何参考文献条目——存在性由 check_bibliography 另行检查")
        print(json.dumps({"checker": "doi_audit", "mode": "scan", "total": 0, "errors": 0},
                         ensure_ascii=False))
        sys.exit(0)
    print(f"扫描 {len(entries)} 条参考文献的 DOI/URL 可达性...")
    findings, n_err = audit_entries(entries)
    n_warn = sum(1 for lv, _, _ in findings if lv == "WARN")
    print(json.dumps({"checker": "doi_audit", "mode": "scan", "target": str(target),
                      "total": len(entries), "errors": n_err, "warns": n_warn}, ensure_ascii=False))
    sys.exit(1 if n_err else 0)


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "precheck":
        precheck(sys.argv[2])
    elif len(sys.argv) >= 3 and sys.argv[1] == "scan":
        scan(sys.argv[2])
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
