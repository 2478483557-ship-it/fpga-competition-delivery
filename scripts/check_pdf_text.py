# -*- coding: utf-8 -*-
"""从 PDF 反抽文字做合规扫描。

为什么必须扫 PDF 而不是源文件
-----------------------------
评委看的是 PDF。源文件改对了但 PDF 没重建 —— 看起来改了，交上去还是旧版。
这个项目里真实发生过：源文件内容正确，PDF 滞后 4 天没重建。

同时顺带查三件文本扫描能查的事
-----------------------------
1. 禁项（校名 / 队伍编号 / 指导教师 / 学校 Logo 文字）
2. 过期数字
3. **近空白页**（正文不足 N 字）—— 通常是分页符重复、图独占页造成的排版事故

查不出来的（必须人眼过）
-----------------------
- 照片背景里的文字（学院名、书院名、门牌、屏幕上的内容）
- 图里嵌进去的文字
- 版式问题（图被裁、文字压图）

用法
----
    python check_pdf_text.py <pdf> --banned banned.txt
    python check_pdf_text.py <pdf> --banned banned.txt --stale stale.txt
    python check_pdf_text.py <pdf> --banned banned.txt --blank-threshold 60

banned.txt / stale.txt 都是**一行一个词**，`#` 开头为注释。
stale.txt 支持 `旧值=新值` 写法，便于报告里直接给出正确值。

退出码
------
    0  全部通过
    1  命中禁项 / 过期值 / 空白页
    2  参数或依赖错误
"""
import os
import re
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def load_words(path):
    """一行一个词，支持 `旧=新` 与 # 注释。"""
    out = []
    if not path or not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8") as f:
        for raw in f:
            s = raw.strip()
            if not s or s.startswith("#"):
                continue
            if "=" in s:
                old, new = s.split("=", 1)
                out.append((old.strip(), new.strip()))
            else:
                out.append((s, None))
    return out


def norm(s):
    """去掉所有空白，避免"Vivado 2020.2" vs "Vivado2020.2" 这类漏检。"""
    return re.sub(r"[\s\u3000]+", "", s)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    pdf = args[0]
    if not os.path.isfile(pdf):
        print("PDF 不存在: %s" % pdf)
        return 2

    try:
        import pdfplumber
    except ImportError:
        print("缺依赖: pip install pdfplumber")
        return 2

    banned_path = stale_path = None
    blank_th = 60
    for i, a in enumerate(sys.argv):
        if a == "--banned" and i + 1 < len(sys.argv):
            banned_path = sys.argv[i + 1]
        if a == "--stale" and i + 1 < len(sys.argv):
            stale_path = sys.argv[i + 1]
        if a == "--blank-threshold" and i + 1 < len(sys.argv):
            blank_th = int(sys.argv[i + 1])

    banned = load_words(banned_path)
    stale = load_words(stale_path)

    pages = []
    with pdfplumber.open(pdf) as doc:
        n_page = len(doc.pages)
        for pg in doc.pages:
            t = pg.extract_text() or ""
            pages.append({
                "text": t,
                "flat": norm(t),
                "nchar": len(norm(t)),
                "nimg": len(pg.images),
            })

    whole = norm("".join(p["text"] for p in pages))

    print("=" * 66)
    print("  PDF 文字审计  %s" % os.path.basename(pdf))
    print("=" * 66)
    print("  %d 页 ｜ %.2f MB ｜ 正文 %d 字（去空白）"
          % (n_page, os.path.getsize(pdf) / 1048576.0, len(whole)))

    red = []

    # ---------- 禁项 ----------
    hit_ban = []
    for w, _ in banned:
        if norm(w) and norm(w) in whole:
            ctx = ""
            k = whole.find(norm(w))
            ctx = whole[max(0, k - 30):k + len(norm(w)) + 30]
            hit_ban.append((w, ctx))
    if hit_ban:
        red.append(("禁项", len(hit_ban)))

    # ---------- 过期值 ----------
    hit_stale = []
    for old, new in stale:
        if norm(old) and norm(old) in whole:
            k = whole.find(norm(old))
            ctx = whole[max(0, k - 30):k + len(norm(old)) + 30]
            hit_stale.append((old, new, ctx))
    if hit_stale:
        red.append(("过期值", len(hit_stale)))

    # ---------- 近空白页 ----------
    # 有图的近空白页多半是"图独占页"，属于正常排版（例如实物大图占满一页），
    # 只提示不计红。没有图的才是真事故：分页符重复、空段落独占一页。
    blanks_img = [(i + 1, p["nchar"], p["nimg"])
                  for i, p in enumerate(pages)
                  if p["nchar"] < blank_th and p["nimg"] > 0]
    blanks_bare = [(i + 1, p["nchar"])
                   for i, p in enumerate(pages)
                   if p["nchar"] < blank_th and p["nimg"] == 0]
    if blanks_bare:
        red.append(("真空页", len(blanks_bare)))

    # ---------- 输出 ----------
    if hit_ban:
        print()
        print("  禁项命中 %d 个：" % len(hit_ban))
        for w, ctx in hit_ban:
            print("    ★ %s" % w)
            print("      …%s…" % ctx)

    if hit_stale:
        print()
        print("  过期值命中 %d 个：" % len(hit_stale))
        for old, new, ctx in hit_stale:
            tail = ("  → 应为 %s" % new) if new else ""
            print("    ★ %s%s" % (old, tail))
            print("      …%s…" % ctx)

    if blanks_bare:
        print()
        print("  真空页（正文 < %d 字且无图）：" % blank_th)
        for pg, n in blanks_bare:
            print("    第 %d 页  %d 字  ← 查分页符重复 / 空段落独占页" % (pg, n))

    if blanks_img:
        print()
        print("  文字偏少但有图（多半是图独占页，属正常）：")
        for pg, n, ni in blanks_img:
            print("    第 %d 页  %d 字 / %d 图" % (pg, n, ni))

    print()
    print("=" * 66)
    if not red:
        print("  全部通过：无禁项、无过期值、无异常空白页 ✓")
    else:
        print("  " + " ｜ ".join("%s %d" % (k, v) for k, v in red))
    print()
    print("  提示：照片背景里的文字、图内嵌字、版式问题本脚本查不出，")
    print("        交付前必须人眼过一遍所有含照片的页。")

    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
