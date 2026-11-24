# -*- coding: utf-8 -*-
import pymupdf
PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
doc = pymupdf.open(PDF)

def dump(pi, x0, y0, x1, y1, title):
    print("=" * 70)
    print(f"页{pi} 区域 ({x0},{y0})-({x1},{y1})  {title}")
    pg = doc[pi]
    ws = [w for w in pg.get_text("words") if x0 <= w[0] <= x1 and y0 <= w[1] <= y1]
    ws.sort(key=lambda w: (round(w[1] / 3), w[0]))
    for w in ws:
        print(f"   ({w[0]:7.1f},{w[1]:7.1f}) {w[4]}")

# 页1：J1 超声波座附近
dump(1, 130, 100, 240, 160, "J1 超声波座")
# 页2：MCU 页 ECHO 附近（找 TRIG / PF11/PF12）
dump(2, 150, 195, 280, 250, "MCU 页 ECHO 附近")
# 页2：HS0038B 附近
dump(2, 280, 130, 380, 180, "MCU 页 HS0038B 附近")
