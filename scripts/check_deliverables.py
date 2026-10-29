# -*- coding: utf-8 -*-
"""交付目录体检。

检查四类问题，全部机械可判：
  1. 必需文件是否齐全（--required 给了才查）
  2. 空文件 / 大小异常
  3. 文件名含中文（多数竞赛要求仓库与提交件用纯英文命名）
  4. 过程文档残留（答辩稿、提词卡、提交清单之类不该混在交付目录顶层）

用法
----
    python check_deliverables.py <交付目录>
    python check_deliverables.py <交付目录> --required required.json
    python check_deliverables.py <交付目录> --required required.json --json

required.json 格式
------------------
    {
      "required": [
        {"name": "技术文档.pdf", "min_mb": 0.1, "max_mb": 50},
        {"name": "源代码.rar",   "min_mb": 0.5, "max_mb": 200}
      ],
      "allow_dirs": ["_过程文档"]
    }

    min_mb / max_mb 可省略；不写就只查存在性。

退出码
------
    0  全部通过
    1  发现红项（缺件 / 空文件 / 中文名 / 过程文档残留）
"""
import json
import os
import re
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 不该出现在交付目录顶层的文件名特征
PROCESS_PATTERNS = [
    "答辩稿", "答辩提词", "提词卡", "提交清单", "重录操作单",
    "操作单", "考核准备", "练习清单", "分镜表", "字幕",
    "海报", "竞品", "对标", "差距分析", "复盘",
]

RED, YEL, GRN, RST = "\033[31m", "\033[33m", "\033[32m", "\033[0m"
if sys.platform == "win32" and not os.environ.get("WT_SESSION"):
    RED = YEL = GRN = RST = ""


def human(n):
    if n < 1024:
        return "%d B" % n
    if n < 1024 ** 2:
        return "%.1f KB" % (n / 1024)
    return "%.2f MB" % (n / 1024.0 / 1024.0)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = [a for a in sys.argv[1:] if a.startswith("--")]
    if not args:
        print(__doc__)
        return 2
    root = args[0]
    as_json = "--json" in flags

    req_path = None
    for i, a in enumerate(sys.argv):
        if a == "--required" and i + 1 < len(sys.argv):
            req_path = sys.argv[i + 1]

    if not os.path.isdir(root):
        print("%s目录不存在: %s%s" % (RED, root, RST))
        return 1

    red, yellow, green = [], [], []

    # ---------- 清点 ----------
    entries = []
    for name in sorted(os.listdir(root)):
        p = os.path.join(root, name)
        if os.path.isfile(p):
            entries.append((name, os.path.getsize(p), "file"))
        elif os.path.isdir(p):
            n = sum(len(fs) for _, _, fs in os.walk(p))
            entries.append((name, n, "dir"))

    # ---------- 1) 必需文件 ----------
    req = []
    if req_path and os.path.isfile(req_path):
        with open(req_path, encoding="utf-8") as f:
            spec = json.load(f)
        req = spec.get("required", [])
        names = {e[0] for e in entries}
        for item in req:
            nm = item["name"]
            if nm not in names:
                red.append(("缺件", nm, "必需文件不存在"))
                continue
            size_mb = os.path.getsize(os.path.join(root, nm)) / 1048576.0
            lo = item.get("min_mb")
            hi = item.get("max_mb")
            if lo is not None and size_mb < lo:
                red.append(("大小异常", nm,
                            "%.2f MB < 下限 %.2f MB（可能截断）" % (size_mb, lo)))
            elif hi is not None and size_mb > hi:
                yellow.append(("大小偏大", nm,
                               "%.2f MB > 上限 %.2f MB" % (size_mb, hi)))
    elif req_path:
        red.append(("配置", os.path.basename(req_path), "required.json 读不到"))

    # ---------- 2) 空文件 ----------
    for name, size, kind in entries:
        if kind == "file" and size == 0:
            red.append(("空文件", name, "0 字节"))

    # ---------- 3) 中文文件名 ----------
    for name, size, kind in entries:
        if re.search(r"[\u4e00-\u9fff]", name):
            yellow.append(("中文名", name,
                           "若竞赛要求纯英文命名则需改名"))

    # ---------- 4) 过程文档残留 ----------
    allow_dirs = set()
    if req_path and os.path.isfile(req_path):
        with open(req_path, encoding="utf-8") as f:
            allow_dirs = set(json.load(f).get("allow_dirs", []))
    req_names = {i["name"] for i in req}

    for name, size, kind in entries:
        if kind != "file":
            continue
        if req_names and name in req_names:
            continue
        for pat in PROCESS_PATTERNS:
            if pat in name:
                red.append(("过程文档", name,
                            "命中「%s」，应移出顶层或删掉" % pat))
                break

    # ---------- 输出 ----------
    print("=" * 66)
    print("  交付目录体检  %s" % root)
    print("=" * 66)
    print()
    print("  %-44s %-10s %s" % ("名称", "大小", "类型"))
    print("  " + "-" * 62)
    for name, size, kind in entries:
        sz = human(size) if kind == "file" else "%d 项" % size
        print("  %-44s %-10s %s" % (name, sz, "文件" if kind == "file" else "目录"))

    print()
    print("=" * 66)
    if not (red or yellow):
        print("  %s全部通过：无缺件、无空文件、无过程文档残留%s" % (GRN, RST))
        return 0

    if red:
        print("  %s红项 %d 个（必须处理）%s" % (RED, len(red), RST))
        for tag, name, why in red:
            print("    %s[%s]%s %s" % (RED, tag, RST, name))
            print("         %s" % why)
        print()
    if yellow:
        print("  %s黄项 %d 个（自行判断）%s" % (YEL, len(yellow), RST))
        for tag, name, why in yellow:
            print("    %s[%s]%s %s" % (YEL, tag, RST, name))
            print("         %s" % why)

    return 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
