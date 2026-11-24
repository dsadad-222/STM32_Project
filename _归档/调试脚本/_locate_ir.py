# -*- coding: utf-8 -*-
"""定位原理图里"两路红外避障"所在页与坐标，并渲染高清图。"""
import pymupdf as fitz

PDF = r"E:\xwechat_files\wxid_ifph2dohbkn729_0e86\msg\attach\b210afea97fa72feb07be4d21bb47dae\2026-09\Rec\73d4323699de8e41\F\1\任务实训11.pdf"
SCH = None
import glob, os
# 找原理图 PDF
for c in [r"D:\STM32_Project\*.pdf", r"D:\STM32_Project\**\*.pdf"]:
    for p in glob.glob(c, recursive=True):
        if "原理" in p or "sch" in p.lower() or "YB" in p:
            print("候选原理图:", p)
            SCH = p

if not SCH:
    print("未找到原理图 PDF，列 D:\\STM32_Project 下所有 pdf:")
    for p in glob.glob(r"D:\STM32_Project\**\*.pdf", recursive=True):
        print("  ", p)
    raise SystemExit(0)

d = fitz.open(SCH)
print("原理图: %s  页数: %d" % (os.path.basename(SCH), d.page_count))
KEYS = ["两路红外避障", "红外", "Ultrasonic", "LIGHT"]
for i, pg in enumerate(d):
    for k in KEYS:
        hits = pg.search_for(k)
        for r in hits:
            print("  page %d  %-10s  rect=(%.0f,%.0f,%.0f,%.0f)" % (i + 1, k, r.x0, r.y0, r.x1, r.y1))
