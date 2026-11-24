# -*- coding: utf-8 -*-
"""抽取左侧引脚表的 (脚号, 脚名, 外部网标) 三元组。"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymupdf

PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
doc = pymupdf.open(PDF)
page = doc[2]
clip = pymupdf.Rect(0, 195, page.rect.width, 275)
ws = page.get_text("words", clip=clip)

# 列 x 边界（由上一轮坐标实测）
#  185=X  195=网标  228=网标2  241=脚号  254=脚名  284=右侧脚名  297=右侧脚号ID  312=右侧网标  331=右侧网标2  359=X
def band(x):
    for lo, hi, name in ((180, 192, "X"), (192, 222, "NET"), (222, 236, "NET2"),
                         (236, 250, "NUM"), (250, 278, "PINNAME"),
                         (278, 294, "RNUM"), (294, 308, "RID"),
                         (308, 340, "RNET"), (340, 375, "RX")):
        if lo <= x < hi:
            return name
    return "?"

rows = {}
for w in ws:
    key = round(w[1] / 2.6)
    rows.setdefault(key, []).append((w[0], w[4]))

print("%-6s | %-26s | %-30s" % ("y", "左半: 网标 / 脚名", "脚号 | 右半"))
print("-" * 90)
for k in sorted(rows):
    items = sorted(rows[k])
    left = [t for x, t in items if band(x) in ("NET", "NET2", "PINNAME", "X")]
    num  = [t for x, t in items if band(x) == "NUM"]
    rid  = [t for x, t in items if band(x) == "RID"]
    rnet = [t for x, t in items if band(x) in ("RNET", "RNUM")]
    if not (left or num or rid or rnet):
        continue
    print("y=%-6.1f | %-26s | %-6s | %s" % (k * 2.6, " ".join(left), " ".join(num), " ".join(rid + rnet)))

doc.close()
