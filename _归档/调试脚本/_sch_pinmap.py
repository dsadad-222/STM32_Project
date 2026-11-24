# -*- coding: utf-8 -*-
"""从 YB-DSF01 原理图第3页(MCU页)重建 引脚号 <-> 网络名 对照表。
思路：取出所有 text span 的 bbox，按 y 分行(容差 3pt)，同一行内按 x 排序，
然后对每个"纯数字"span(引脚号) 找同行右侧最近的网络名 span。"""
import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymupdf

PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
doc = pymupdf.open(PDF)

page = doc[2]  # 第3页
print("page size:", page.rect)

spans = []
d = page.get_text("dict")
for b in d["blocks"]:
    if b.get("type") != 0:
        continue
    for l in b["lines"]:
        for s in l["spans"]:
            t = s["text"].strip()
            if not t:
                continue
            x0, y0, x1, y1 = s["bbox"]
            spans.append({"t": t, "x0": x0, "y0": y0, "x1": x1, "y1": y1, "size": s["size"]})

# 按 y 分行
spans.sort(key=lambda s: (round(s["y0"] / 3.0), s["x0"]))
rows = []
for s in spans:
    placed = False
    for r in rows:
        if abs(r["y"] - s["y0"]) <= 3.0:
            r["items"].append(s)
            r["y"] = (r["y"] * (len(r["items"]) - 1) + s["y0"]) / len(r["items"])
            placed = True
            break
    if not placed:
        rows.append({"y": s["y0"], "items": [s]})

rows.sort(key=lambda r: r["y"])
print("总行数:", len(rows))

NUM = re.compile(r"^\d{1,3}$")
for r in rows:
    items = sorted(r["items"], key=lambda s: s["x0"])
    nums = [it for it in items if NUM.match(it["t"]) and 1 <= int(it["t"]) <= 144]
    if not nums:
        continue
    line = " | ".join("%s@%.0f" % (it["t"], it["x0"]) for it in items)
    print("y=%6.1f  %s" % (r["y"], line))

doc.close()
