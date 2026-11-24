# -*- coding: utf-8 -*-
"""精确配对：MCU 符号第1部分 右列 引脚名(x 280~300) <-> 网络名(x 308~365)，
并同时给出引脚号(x 296~308)的原始 y，判断 Altium 的"号在线上面"偏移。"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymupdf

PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
doc = pymupdf.open(PDF)
page = doc[2]

names, nums, nets = [], [], []
for b in page.get_text("dict")["blocks"]:
    if b.get("type") != 0:
        continue
    for l in b["lines"]:
        for s in l["spans"]:
            t = s["text"].strip()
            if not t:
                continue
            x0 = s["bbox"][0]
            yc = (s["bbox"][1] + s["bbox"][3]) / 2.0
            if t.startswith("PIU"):
                continue
            if 275 <= x0 <= 300:
                names.append((yc, t, x0))
            elif 296 <= x0 <= 307:
                nums.append((yc, t, x0))
            elif 308 <= x0 <= 370:
                nets.append((yc, t, x0))

names.sort(); nums.sort(); nets.sort()

print("=== 右列：引脚名 <-> 引脚号 <-> 网络名（按 y 排序）===")
for yc, t, x0 in names:
    n_num = [n for n in nums if abs(n[0] - yc) <= 3.5]
    n_net = [n for n in nets if abs(n[0] - yc) <= 1.2]
    n_net2 = [n for n in nets if abs(n[0] - yc) <= 3.5]
    print("y=%7.2f name=%-8s num=%-22s net(1.2)=%-20s net(3.5)=%s"
          % (yc, t,
             " ".join("%s@%.1f" % (n[1], n[0]) for n in n_num),
             ",".join(n[1] for n in n_net),
             ",".join(n[1] for n in n_net2)))

doc.close()
