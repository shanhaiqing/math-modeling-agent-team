#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
convert_problem.py — HG0 赛题转写（编排器执行，禁止 subagent 自行抽 PDF）

把赛题 PDF 与说明类附件（.docx/.doc）转成后续 agent 直接 Read 的 Markdown，
并按页导出嵌入图到 赛题/题面图/。xlsx/csv 数据附件不转写。

用法:
  python convert_problem.py --project-root <项目根> [--pdf 路径]
         [--attachments-dir 路径] [--out-dir 路径]
退出码: 0 = 成功（允许 WARN）；1 = ERROR；2 = 用法错误
产出: <out-dir>/题面.md + ingest_report.json
      条件: 附件/*.md、题面图/*.png
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

MIN_STATEMENT_CHARS = 200  # 须与 check_pipeline_manifest.MIN_STATEMENT_CHARS 一致
MIN_PAGE_CHARS = 50
MIN_IMG_PX = 40

PDF_DENY_SUBSTR = (
    "paper", "format", "fig_", "支撑", "工具使用",
    "ingest", "visual_qa",
)
PDF_DENY_DIRS = {
    "figures", "result_bundle", "project", "decision_logs", "支撑材料",
    ".trae", ".git", ".venv", "venv",
}
DOCX_DENY_SUBSTR = ("工具使用", "format")
SEARCH_SUBDIRS = ("B题", "C题", "赛题", "题目", "problem", "题面")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _name_denied(name: str, needles) -> bool:
    n = name.lower().replace(" ", "")
    return any(s.replace(" ", "") in n for s in needles)


def discover_pdf(root: Path) -> Path | None:
    candidates: list[Path] = []

    def consider(p: Path):
        if p.suffix.lower() != ".pdf" or not p.is_file():
            return
        try:
            rel_parts = {x.lower() for x in p.relative_to(root).parts[:-1]}
        except ValueError:
            rel_parts = set()
        if rel_parts & PDF_DENY_DIRS:
            return
        if _name_denied(p.name, PDF_DENY_SUBSTR):
            return
        candidates.append(p)

    for p in root.glob("*.pdf"):
        consider(p)
    for sub in SEARCH_SUBDIRS:
        d = root / sub
        if d.is_dir():
            for p in d.glob("*.pdf"):
                consider(p)
            for p in d.glob("*/*.pdf"):
                consider(p)
    if not candidates:
        return None

    def rank(p: Path):
        stem = p.stem
        hit = 0 if ("题" in stem or stem.lower() in {"problem", "statement"}) else 1
        return (hit, len(p.parts), str(p))

    return sorted(candidates, key=rank)[0]


def discover_docx(root: Path, pdf: Path | None, extra_dir: Path | None) -> list[Path]:
    dirs: list[Path] = []
    if extra_dir:
        dirs.append(extra_dir)
    if pdf:
        dirs.extend([pdf.parent, pdf.parent / "附件"])
    dirs.extend([root / "附件", root])
    seen: set[Path] = set()
    out: list[Path] = []
    for d in dirs:
        if not d.is_dir():
            continue
        for pat in ("*.docx", "*.doc"):
            for p in d.glob(pat):
                if p.name.startswith("~$"):
                    continue
                if _name_denied(p.name, DOCX_DENY_SUBSTR):
                    continue
                key = p.resolve()
                if key in seen:
                    continue
                seen.add(key)
                out.append(p)
    return out


def extract_pdf_tables_md(page) -> str:
    try:
        finder = page.find_tables()
    except Exception:
        return ""
    tables = getattr(finder, "tables", None) or []
    chunks = []
    for ti, tab in enumerate(tables, 1):
        try:
            data = tab.extract()
        except Exception:
            continue
        if not data:
            continue
        rows = [[(c or "").replace("\n", " ").strip() for c in row] for row in data]
        width = max((len(r) for r in rows), default=0)
        if width == 0:
            continue
        norm = [(r + [""] * width)[:width] for r in rows]
        header, body = norm[0], norm[1:]
        lines = [
            f"*（第 {ti} 张表，由 PDF 表格检测导出，若错位以源 PDF 为准）*",
            "| " + " | ".join(header) + " |",
            "| " + " | ".join("---" for _ in header) + " |",
        ]
        for r in body:
            lines.append("| " + " | ".join(r) + " |")
        chunks.append("\n".join(lines))
    return "\n\n".join(chunks)


def save_pixmap(pix, dest: Path) -> bool:
    try:
        import fitz
        if pix.n - pix.alpha > 3:
            pix = fitz.Pixmap(fitz.csRGB, pix)
        if pix.width < MIN_IMG_PX or pix.height < MIN_IMG_PX:
            return False
        dest.parent.mkdir(parents=True, exist_ok=True)
        pix.save(str(dest))
        return dest.is_file() and dest.stat().st_size > 0
    except Exception:
        return False


def extract_page_images(doc, page, img_dir: Path, page_no: int) -> list[str]:
    saved = []
    seen: set[int] = set()
    try:
        images = page.get_images(full=True)
    except Exception:
        return saved
    import fitz
    for i, img in enumerate(images, 1):
        xref = img[0]
        if xref in seen:
            continue
        seen.add(xref)
        try:
            pix = fitz.Pixmap(doc, xref)
        except Exception:
            continue
        name = f"p{page_no:02d}_img{i:02d}.png"
        if save_pixmap(pix, img_dir / name):
            saved.append(name)
    return saved


def render_scan_page(page, img_dir: Path, page_no: int) -> str | None:
    import fitz
    try:
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
    except Exception:
        return None
    name = f"p{page_no:02d}_scan.png"
    if save_pixmap(pix, img_dir / name):
        return name
    return None


def convert_pdf(pdf: Path, out_dir: Path, img_dir: Path) -> dict:
    import fitz
    doc = fitz.open(str(pdf))
    page_blocks = []
    scan_pages = []
    image_files = []
    total_chars = 0
    n_pages = doc.page_count
    for i, page in enumerate(doc, 1):
        text = (page.get_text("text") or "").replace("\x00", "")
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        nchars = len(re.sub(r"\s+", "", text))
        total_chars += nchars
        imgs = extract_page_images(doc, page, img_dir, i)
        image_files.extend(imgs)
        tables_md = extract_pdf_tables_md(page)
        scan_name = None
        if nchars < MIN_PAGE_CHARS:
            scan_name = render_scan_page(page, img_dir, i)
            if scan_name:
                image_files.append(scan_name)
                scan_pages.append(i)
        parts = [f"## 第 {i} 页", ""]
        if text:
            parts.append(text)
        else:
            parts.append("*[本页文本提取为空或过短，疑似扫描件或纯图]*")
        if tables_md:
            parts.extend(["", tables_md])
        for name in imgs:
            parts.append(f"\n![第{i}页嵌入图 {name}](题面图/{name})")
        if scan_name:
            parts.append(f"\n![第{i}页扫描渲染 {scan_name}](题面图/{scan_name})")
        page_blocks.append("\n".join(parts).rstrip())
    doc.close()

    if n_pages == 0:
        mode = "empty"
    elif len(scan_pages) == n_pages:
        mode = "scan"
    elif scan_pages:
        mode = "mixed"
    else:
        mode = "digital"

    header = [
        "---",
        f"source_pdf: {pdf.as_posix()}",
        f"pages: {n_pages}",
        f"extracted_at: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"mode: {mode}",
        "---",
        "",
        "# 题面转写（原文，未经改写）",
        "",
        "> 本文件由编排器 HG0 从赛题 PDF 抽取，供后续 agent 阅读。**禁止改写本题面。**",
        "> 公式、表格若乱码或错位，以源 PDF 为准。几何题请同时查看 `赛题/题面图/`。",
        "",
    ]
    md = "\n".join(header) + "\n\n".join(page_blocks) + "\n"
    (out_dir / "题面.md").write_text(md, encoding="utf-8")
    return {
        "pages": n_pages,
        "chars": total_chars,
        "mode": mode,
        "scan_suspect_pages": scan_pages,
        "images_extracted": image_files,
    }


def iter_docx_blocks(doc):
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    for child in doc.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, doc)
        elif isinstance(child, CT_Tbl):
            yield Table(child, doc)


def table_to_md(table) -> str:
    rows = []
    for row in table.rows:
        rows.append([c.text.replace("\n", " ").strip() for c in row.cells])
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [(r + [""] * width)[:width] for r in rows]
    header, body = rows[0], rows[1:]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for r in body:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


def convert_docx(path: Path) -> str:
    from docx import Document
    doc = Document(str(path))
    chunks = [
        f"# {path.stem}（原文转写，未经改写）",
        "",
        f"> 源文件：`{path.as_posix()}`",
        "",
    ]
    for block in iter_docx_blocks(doc):
        from docx.table import Table
        from docx.text.paragraph import Paragraph
        if isinstance(block, Paragraph):
            t = block.text.strip()
            if t:
                chunks.append(t)
                chunks.append("")
        elif isinstance(block, Table):
            md = table_to_md(block)
            if md:
                chunks.append(md)
                chunks.append("")
    return "\n".join(chunks).rstrip() + "\n"


def convert_doc_fallback(path: Path) -> str:
    """旧版 .doc：尽量抽 XML/zip 失败则声明无法转写。"""
    if path.suffix.lower() == ".docx":
        raise RuntimeError("docx 应走 python-docx")
    return (
        f"# {path.stem}\n\n"
        f"> 源文件 `{path.as_posix()}` 为旧版 .doc，本脚本无法可靠转写。"
        "请用 Word 另存为 .docx 后重跑 convert_problem.py，或直接阅读源文件。\n"
    )


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--pdf", default=None)
    ap.add_argument("--attachments-dir", default=None)
    ap.add_argument("--out-dir", default=None)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    if not root.is_dir():
        print(f"FATAL: 项目根不存在 {root}")
        sys.exit(2)

    out_dir = Path(args.out_dir).resolve() if args.out_dir else root / "赛题"
    img_dir = out_dir / "题面图"
    att_dir = out_dir / "附件"
    out_dir.mkdir(parents=True, exist_ok=True)

    errors, warns = [], []
    pdf = Path(args.pdf).resolve() if args.pdf else discover_pdf(root)
    extra_att = Path(args.attachments_dir).resolve() if args.attachments_dir else None

    report = {
        "checker": "convert_problem",
        "source_pdf": str(pdf) if pdf else None,
        "source_sha256": None,
        "pages": 0,
        "chars": 0,
        "mode": None,
        "scan_suspect_pages": [],
        "attachments_converted": [],
        "images_extracted": [],
        "error_count": 0,
        "warn_count": 0,
        "errors": errors,
        "warns": warns,
    }

    if pdf is None or not pdf.is_file():
        errors.append("未找到赛题 PDF（可用 --pdf 指定；已排除 paper/format/figures 等）")
    else:
        try:
            import fitz  # noqa: F401
        except ImportError:
            errors.append("缺少 pymupdf，无法抽取 PDF")
        else:
            try:
                report["source_sha256"] = sha256_file(pdf)
                info = convert_pdf(pdf, out_dir, img_dir)
                report.update({k: info[k] for k in (
                    "pages", "chars", "mode", "scan_suspect_pages", "images_extracted")})
                if info["chars"] < MIN_STATEMENT_CHARS:
                    errors.append(
                        f"题面有效汉字过少（{info['chars']} < {MIN_STATEMENT_CHARS}）"
                        "——疑似扫描件或抽取出错")
                if info["scan_suspect_pages"]:
                    warns.append(
                        f"疑似扫描页：{info['scan_suspect_pages']}，已导出 题面图/pXX_scan.png")
            except Exception as e:
                errors.append(f"PDF 转写失败：{e}")

    att_files = discover_docx(root, pdf, extra_att)

    for src in att_files:
        try:
            if src.suffix.lower() == ".docx":
                md = convert_docx(src)
            else:
                md = convert_doc_fallback(src)
                warns.append(f"{src.name} 为 .doc，未做结构化转写")
            dest = att_dir / (src.stem + ".md")
            att_dir.mkdir(parents=True, exist_ok=True)
            dest.write_text(md, encoding="utf-8")
            report["attachments_converted"].append(str(dest.relative_to(out_dir)).replace("\\", "/"))
        except Exception as e:
            warns.append(f"附件转写失败 {src.name}：{e}")

    report["error_count"] = len(errors)
    report["warn_count"] = len(warns)
    (out_dir / "ingest_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
