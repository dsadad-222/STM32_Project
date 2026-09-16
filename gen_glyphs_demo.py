# -*- coding: utf-8 -*-
"""由含信息版的 font8x8.c 重新排版，生成匿名版的 glyphs.h / glyphs.c。

刻意与含信息版拉开差异：小写十六进制、每行两个字模、注释用索引而不是字符标号、
接口名换成 glyphs_* 、数组名 g_glyph_8x8。
"""
import io, os, re

SRC = r"D:\STM32_Project\SerialAdv_Full\Drv_Common\font8x8.c"
DST = r"D:\STM32_Project\SerialAdv_Demo\Drv_Common"

src = io.open(SRC, encoding="utf-8").read()
body = src[src.index("{"):]
rows = re.findall(r"\{([^{}]*)\}", body)
font = []
for r in rows:
    v = [int(t, 16) for t in re.findall(r"0x([0-9A-Fa-f]{2})", r)]
    if len(v) == 8:
        font.append(v)
assert len(font) == 95, f"字库条数不对: {len(font)}"

FIRST, LAST = 0x20, 0x7E

# ---------------- glyphs.h ----------------
h = []
h.append("/**")
h.append("  ******************************************************************************")
h.append("  * @file    Drv_Common/glyphs.h")
h.append("  * @brief   Fixed 8x8 bitmap font covering the printable ASCII range.")
h.append("  *")
h.append("  *          Each entry holds 8 bytes, one byte per row, MSB is the left")
h.append("  *          most pixel of that row.")
h.append("  ******************************************************************************")
h.append("  */")
h.append("")
h.append("#ifndef GLYPHS_H")
h.append("#define GLYPHS_H")
h.append("")
h.append("#include <stdint.h>")
h.append("")
h.append("#define GLYPH_FIRST     0x20U       /* ' ' */")
h.append("#define GLYPH_LAST      0x7EU       /* '~' */")
h.append("#define GLYPH_W         8U          /* cell width in pixels  */")
h.append("#define GLYPH_H         8U          /* cell height in pixels */")
h.append("")
h.append("extern const uint8_t g_glyph_8x8[GLYPH_LAST - GLYPH_FIRST + 1U][GLYPH_H];")
h.append("")
h.append("#endif /* GLYPHS_H */")
h.append("")
io.open(os.path.join(DST, "glyphs.h"), "w", encoding="utf-8", newline="\r\n").write("\n".join(h))

# ---------------- glyphs.c ----------------
c = []
c.append("/**")
c.append("  ******************************************************************************")
c.append("  * @file    Drv_Common/glyphs.c")
c.append("  * @brief   8x8 font data, 95 printable ASCII glyphs.")
c.append("  *")
c.append("  *          Bit order per row is MSB first, so glyph[y] bit 7 is the pixel")
c.append("  *          in column 0 and bit 0 is the pixel in column 7.")
c.append("  ******************************************************************************")
c.append("  */")
c.append("")
c.append('#include "glyphs.h"')
c.append("")
c.append("const uint8_t g_glyph_8x8[GLYPH_LAST - GLYPH_FIRST + 1U][GLYPH_H] =")
c.append("{")
for i in range(0, len(font), 2):
    parts = []
    for j in (i, i + 1):
        if j >= len(font):
            break
        data = ",".join("0x%02x" % b for b in font[j])
        parts.append("/* 0x%02x */ {%s}" % (FIRST + j, data))
    c.append("    " + ",  ".join(parts) + ("," if i + 2 < len(font) else ""))
c.append("};")
c.append("")
io.open(os.path.join(DST, "glyphs.c"), "w", encoding="utf-8", newline="\r\n").write("\n".join(c))

print("written ->", os.path.join(DST, "glyphs.h"))
print("written ->", os.path.join(DST, "glyphs.c"))
print("字形数 =", len(font))
print()
print("--- glyphs.c 前 6 行数据 ---")
for line in c[7:15]:
    print(line)
