# -*- coding: utf-8 -*-
"""从 SPL fonts.c 提取 ASCII8x8_Table(0x20~0x7E) 生成 font8x8.h / font8x8.c

字模格式（SPL 原始）：每字符 8 个 uint16_t(实际只用低 8 位)，一字节 = 一行，
bit7 = 该行最左像素。OLED 驱动负责转成 SSD1306 的页格式。
"""
import io, os, re

SPL = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\1-软件安装包\标准库\STM32F10x_StdPeriph_Lib_V3.6.0\Utilities\STM32_EVAL\Common\fonts.c"
DST = r"D:\STM32_Project\SerialAdv_Full\Drv_Common"

src = io.open(SPL, encoding="utf-8", errors="ignore").read()

m = re.search(r"ASCII8x8_Table\s*\[\s*\]\s*=\s*\{(.*?)\};", src, re.S)
assert m, "没找到 ASCII8x8_Table"
body = m.group(1)
vals = [int(t, 16) for t in re.findall(r"0x([0-9a-fA-F]{1,4})", body)]
print("原始字节数 =", len(vals), " 字符数 =", len(vals) // 8)

FIRST, LAST = 0x20, 0x7E
need = (LAST - FIRST + 1) * 8
assert len(vals) >= need, f"字库不够: {len(vals)} < {need}"
vals = vals[:need]

# 自检：index 33 应为 'A'，index 1 应为 '!'
def glyph(ch):
    i = (ord(ch) - FIRST) * 8
    return vals[i:i + 8]

def show(ch):
    rows = glyph(ch)
    print(f"  字符 {ch!r}: " + " ".join(f"{b:02X}" for b in rows))
    for r in rows:
        print("     " + "".join("#" if (r >> (7 - c)) & 1 else "." for c in range(8)))

print("自检 index33(应为A) / index1(应为!) / index0(应为空格):")
show("A"); show("!"); show(" ")

# ---------- 生成头文件 ----------
lines = []
lines.append("/**")
lines.append("  ******************************************************************************")
lines.append("  * @file    Drv_Common/font8x8.h")
lines.append("  * @brief   8x8 点阵 ASCII 字库 (0x20~0x7E)，用于 OLED 字符显示")
lines.append("  ******************************************************************************")
lines.append("  */")
lines.append("")
lines.append("#ifndef __FONT8X8_H")
lines.append("#define __FONT8X8_H")
lines.append("")
lines.append('#include "stm32f10x.h"')
lines.append("")
lines.append("#define FONT8X8_FIRST_CHAR   0x20        /* 字库里第一个字符: 空格 */")
lines.append("#define FONT8X8_LAST_CHAR    0x7E        /* 字库里最后一个字符: '~' */")
lines.append("#define FONT8X8_WIDTH        8           /* 字符点阵宽度（含 1 列间隔）*/")
lines.append("#define FONT8X8_HEIGHT       8           /* 字符点阵高度 */")
lines.append("")
lines.append("/* 每字符 8 字节：一个字节代表一行，bit7 为该行最左边的像素 */")
lines.append("extern const uint8_t g_font8x8[FONT8X8_LAST_CHAR - FONT8X8_FIRST_CHAR + 1][FONT8X8_HEIGHT];")
lines.append("")
lines.append("#endif /* __FONT8X8_H */")
lines.append("")

io.open(os.path.join(DST, "font8x8.h"), "w", encoding="utf-8", newline="\r\n").write("\n".join(lines))

# ---------- 生成源文件 ----------
out = []
out.append("/**")
out.append("  ******************************************************************************")
out.append("  * @file    Drv_Common/font8x8.c")
out.append("  * @brief   8x8 点阵 ASCII 字库数据")
out.append("  *")
out.append("  *          数据取自 STM32F10x_StdPeriph_Lib V3.6 自带的")
out.append("  *          Utilities/STM32_EVAL/Common/fonts.c 里的 ASCII8x8_Table，")
out.append("  *          截取 0x20~0x7E 共 95 个可显示字符，每字符 8 字节。")
out.append("  ******************************************************************************")
out.append("  */")
out.append("")
out.append('#include "font8x8.h"')
out.append("")
out.append("const uint8_t g_font8x8[FONT8X8_LAST_CHAR - FONT8X8_FIRST_CHAR + 1][FONT8X8_HEIGHT] =")
out.append("{")
for code in range(FIRST, LAST + 1):
    g = glyph(chr(code))
    body_txt = ",".join(f"0x{b:02X}" for b in g)
    if code == 0x20:
        tag = "空格"
    elif code == 0x7E:
        tag = "'~'"
    else:
        tag = f"'{chr(code)}'"
    out.append(f"    {{{body_txt}}},   /* 0x{code:02X} {tag} */")
out.append("};")
out.append("")

io.open(os.path.join(DST, "font8x8.c"), "w", encoding="utf-8", newline="\r\n").write("\n".join(out))

print()
print("written ->", os.path.join(DST, "font8x8.h"))
print("written ->", os.path.join(DST, "font8x8.c"))
print("字符数 =", LAST - FIRST + 1, " 数据字节 =", need)
