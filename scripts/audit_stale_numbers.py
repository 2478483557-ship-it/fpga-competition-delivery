# -*- coding: utf-8 -*-
"""全库过期数字扫描。

为什么单独写一个脚本
--------------------
"改数字要全库同步"这件事，靠人记必然漏。真实项目里同一组数字
（LUT 7891 → 7886、WNS +0.677 → +0.613）在 10 多份文档里出现过，
每次改都要手动搜一遍，前后做了四次。

三条硬规矩（都是踩过才知道的）
-----------------------------
1. **先分类「当前状态 / 历史记录」**。描述当前状态的必须改；
   带日期的历史记录（当时的测试报告、日志）保留原值，否则毁掉证据链。
2. **顺路扫同类陈旧值**。改一个数字时，往往同一批还有别的旧值没改。
3. **防重复命中**。`7891` 可能出现在 `17891`、某个端口号里；
   更麻烦的是"新值里包含旧值"（`7886` 里没有 `7891` 但 `37.9` 和 `37.91` 有包含关系）。
   对策：给每条映射配一个 `context`（必须同时出现的词），或 `exact_word`。

用法
----
    python audit_stale_numbers.py <根目录>
    python audit_stale_numbers.py <根目录> --map stale_map.json
    python audit_stale_numbers.py <根目录> --map stale_map.json --strict

stale_map.json 支持两种写法
---------------------------
简单版（值 → 新值）：
    {"7891": "7886", "0.677": "0.613"}

带上下文版（推荐，防误命中）：
    {
      "7891": {"new": "7886", "context": "LUT"},
      "0.677": {"new": "0.613", "context": "WNS"},
      "7368": {"new": "7886", "context": "LUT", "exclude_after": "→"}
    }

    context       同一行必须同时出现该词，才判为命中
    exclude_after 命中位置之后紧跟该符号时跳过（用于排除"旧值→新值"这种对照表行）

退出码
------
    0  命中 0 处
    1  有命中
    2  参数错误
"""
import fnmatch
import json
import os
import re
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEFAULT_EXTS = [".md", ".txt", ".py", ".v", ".sv", ".bat", ".c", ".h",
                ".json", ".csv", ".tcl", ".xdc"]

# 目录名黑名单：工具产物、版本库、缓存
SKIP_DIRS = {".git", "__pycache__", ".idea", ".vscode", "node_modules",
             "tts_cache", "_清理暂存", "_archive"}

# 目录名前缀黑名单：Vivado 工程产物（wavecore.runs / wavecore.cache …）
SKIP_DIR_PREFIX = ("wavecore.", )

# 文件名特征黑名单：历史日志类，默认不扫
HIST_PATTERNS = ["session_summary", "progress_log", "llm_collab_log",
                 "video_subtitle", "changelog", "CHANGELOG"]


def is_hist(rel):
    return any(h in rel for h in HIST_PATTERNS)


def load_map(path):
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    out = []
    for old, spec in raw.items():
        if isinstance(spec, str):
            out.append({"old": old, "new": spec, "context": None,
                        "exclude_after": None})
        else:
            out.append({"old": old,
                        "new": spec.get("new", "?"),
                        "context": spec.get("context"),
                        "exclude_after": spec.get("exclude_after")})
    return out


def scan(root, rules, exts, include_hist, strict):
    hits = []
    skipped = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d not in SKIP_DIRS
                       and not d.startswith(SKIP_DIR_PREFIX)]
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in exts:
                continue
            p = os.path.join(dirpath, fn)
            rel = os.path.relpath(p, root).replace("\\", "/")
            if is_hist(rel) and not include_hist:
                skipped.append(rel)
                continue
            try:
                with open(p, encoding="utf-8") as f:
                    lines = f.read().split("\n")
            except (UnicodeDecodeError, OSError):
                continue

            for ln, text in enumerate(lines, 1):
                # 「旧值 + 下一行写当前值」是历史记录最常见的写法，
                # 只查本行会把它误判成必须改的红项。
                near = text + (lines[ln] if ln < len(lines) else "")
                for rule in rules:
                    pos = 0
                    while True:
                        i = text.find(rule["old"], pos)
                        if i < 0:
                            break
                        pos = i + len(rule["old"])
                        # context 门禁
                        if rule["context"] and rule["context"] not in text:
                            continue
                        # exclude_after 门禁（排除对照表行）
                        if rule["exclude_after"]:
                            tail = text[pos:pos + 3]
                            if rule["exclude_after"] in tail:
                                continue
                        # strict：本行或下一行已给出新值，说明这已是"旧→新"对照，
                        # 大概率是历史记录，标记出来但不计红
                        flag = ""
                        if not strict and rule["new"] in near:
                            flag = "（邻近已有新值，疑似历史对照）"
                        hits.append({
                            "file": rel, "line": ln,
                            "old": rule["old"], "new": rule["new"],
                            "text": text.strip()[:100], "flag": flag,
                        })
    return hits, skipped


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    root = args[0]
    if not os.path.isdir(root):
        print("目录不存在: %s" % root)
        return 2

    map_path = None
    for i, a in enumerate(sys.argv):
        if a == "--map" and i + 1 < len(sys.argv):
            map_path = sys.argv[i + 1]
    if not map_path:
        print("必须给 --map stale_map.json")
        return 2

    rules = load_map(map_path)
    rules.sort(key=lambda r: -len(r["old"]))       # 长值优先，避免短值抢先匹配

    hits, skipped = scan(root, rules,
                         set(DEFAULT_EXTS),
                         "--include-hist" in sys.argv,
                         "--strict" in sys.argv)

    print("=" * 66)
    print("  过期数字扫描  %s" % root)
    print("=" * 66)
    print("  规则 %d 条 ｜ 命中 %d 处 ｜ 跳过历史文件 %d 个"
          % (len(rules), len(hits), len(skipped)))

    if skipped and "--show-skipped" in sys.argv:
        print()
        print("  跳过的历史文件：")
        for s in skipped[:20]:
            print("    %s" % s)

    if not hits:
        print()
        print("  全部干净 ✓")
        return 0

    print()
    by_file = {}
    for h in hits:
        by_file.setdefault(h["file"], []).append(h)

    for f in sorted(by_file):
        print("  %s" % f)
        for h in sorted(by_file[f], key=lambda x: x["line"]):
            print("    L%-5d %s → %s %s"
                  % (h["line"], h["old"], h["new"], h["flag"]))
            print("           %s" % h["text"])
        print()

    hard = [h for h in hits if not h["flag"]]
    print("=" * 66)
    print("  需处理 %d 处，疑似历史对照 %d 处" % (len(hard), len(hits) - len(hard)))
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())
