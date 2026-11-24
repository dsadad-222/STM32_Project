# -*- coding: utf-8 -*-
import sys, io, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymupdf
cands = glob.glob(r"E:\xwechat_files\**\任务实训10.pdf", recursive=True)
print("found:", cands)
for c in cands[:1]:
    d = pymupdf.open(c)
    for i in range(d.page_count):
        print("\n========== 第 %d 页 ==========" % (i+1))
        print(d[i].get_text())
    d.close()
