# -*- coding: utf-8 -*-
"""统计 8x8 字库实际使用的像素列范围，用于确定字符单元格宽度。"""
import io, re

SPL = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\1-软件安装包\标准库\STM32F10x_StdPeriph_Lib_V3.6.0\Utilities\STM32_EVAL\Common\fonts.c"
src = io.open(SPL, encoding="utf-8", errors="ignore").read()
body = re.search(r"ASCII8x8_Table\s*\[\s*\]\s*=\s*\{(.*?)\};", src, re.S).group(1)
vals = [int(t, 16) for t in re.findall(r"0x([0-9a-fA-F]{1,4})", body)][:760]

minc, maxc = 99, -1
wide = []
for i in range(95):
    g = vals[i * 8:i * 8 + 8]
    cols = [c for c in range(8) for r in g if (r >> (7 - c)) & 1]
    if cols:
        lo, hi = min(cols), max(cols)
        minc = min(minc, lo)
        maxc = max(maxc, hi)
        if hi - lo + 1 > 5:
            wide.append((chr(0x20 + i), lo, hi))
print("所有字形用到的列范围:  col", minc, "~", maxc)
print("宽度 >5px 的字符:", wide if wide else "无")
