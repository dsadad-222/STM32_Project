# -*- coding: utf-8 -*-
"""用矢量线段(引脚线)的精确 y 来锚定 引脚名 <-> 网络名 配对。
Altium 惯例：引脚号画在引脚线上方，引脚名与引脚线同 y。"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymupdf

PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
doc = pymupdf.open(PDF)
page = doc[2]

# 1) 收集水平线段(引脚线)
hlines = []
for d in page.get_drawings():
    for it in d["items"]:
        if it[0] == "l":
            p1, p2 = it[1], it[2]
            if abs(p1.y - p2.y) < 0.3 and abs(p2.x - p1.x) > 8:
                hlines.append((round(p1.y, 2), round(min(p1.x, p2.x), 2), round(max(p1.x, p2.x), 2)))
        elif it[0] == "re":
            r = it[1]
            if r.height < 0.5 and r.width > 8:
                hlines.append((round(r.y0, 2), round(r.x0, 2), round(r.x1, 2)))

# 2) 收集文字
texts = []
for b in page.get_text("dict")["blocks"]:
    if b.get("type") != 0:
        continue
    for l in b["lines"]:
        for s in l["spans"]:
            t = s["text"].strip()
            if t:
                texts.append({"t": t, "x0": s["bbox"][0], "y": (s["bbox"][1] + s["bbox"][3]) / 2.0})

def near(y, xlo, xhi, dy=1.6):
    """返回 y 附近 [xlo,xhi] 内的文字"""
    out = []
    for tx in texts:
        if abs(tx["y"] - y) <= dy and xlo <= tx["x0"] <= xhi:
            out.append(tx["t"])
    return out

# 只看 MCU 符号左右两侧的引脚线（x 在 240~320 之间是符号体，线从 254/308 向外）
print("=== 引脚线(水平段) 与 网络名 配对 ===")
seen = set()
for y, xa, xb in sorted(hlines):
    key = (y, xa, xb)
    if key in seen:
        continue
    seen.add(key)
    # 左列引脚线：x 大致 254->241? 右列：308->330
    names = near(y, 250, 300)      # 引脚名(符号体内)
    nums = near(y - 2.4, 296, 308, dy=1.4)  # 引脚号(线上方)
    nums2 = near(y, 296, 308, dy=1.6)
    nets = near(y, 308, 360)       # 网络名(符号体外)
    if nets or names:
        print("y=%7.2f  line[%.0f..%.0f]  name=%-18s num=%-8s num2=%-8s net=%s"
              % (y, xa, xb, ",".join(names), ",".join(nums), ",".join(nums2), ",".join(nets)))

doc.close()
