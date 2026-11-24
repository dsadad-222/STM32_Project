#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
render_keyoled_screens.py
-------------------------
把 KeyOled_Full 工程「真正编译进固件的那份字库」离线渲染成 OLED 预览图。

不是"按汉字重画一遍"——而是完整复刻 oled_drv.c 的算法：
    1. 解析 Drv_Common/cn_font16.c 里的 g_cnFont16[] 点阵数据（就是编进 bin 的那份）
    2. 按 OLED_ShowCNCharAt() 的位展开逻辑填 s_gram[4][128]
    3. 按 OLED_ShowCNStringCenter() 的居中算法算起点 x
    4. 按 SSD1306 页/列结构铺成 128x32 位图

所以图上是"屏上会是什么样"，不是"字应该长什么样"。
如果字库缺字，这里也会像固件一样画出 0x7E 示意方块。
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.join(HERE, "KeyOled_Full")
FONT_C = os.path.join(PROJ, "Drv_Common", "cn_font16.c")

OLED_W, OLED_H = 128, 32
PAGE_N = OLED_H // 8            # 4
CN_W = 16

# ---- 与 main.c 逐字节一致的 GBK 串 ----------------------------------------
CN_NAME = b"\xC0\xEE\xB5\xC7\xBB\xD4"      # 李登辉
CN_CALL = b"\xBD\xD0\xB0\xD6\xB0\xD6"      # 叫爸爸


def parse_font(path):
    """从 cn_font16.c 抽出 {gbk: [32 字节]}，与固件里的表一一对应。"""
    src = open(path, "r", encoding="utf-8", errors="replace").read()
    # 形如： {0xC0EE, {0x01, 0x00, ... 0x02, 0x00}},   /* 李 */
    pat = re.compile(r"\{\s*0x([0-9A-Fa-f]{4})\s*,\s*\{(.*?)\}\s*\}", re.S)
    table = {}
    for m in pat.finditer(src):
        gbk = int(m.group(1), 16)
        nums = re.findall(r"0x([0-9A-Fa-f]{2})", m.group(2))
        if len(nums) != 32:
            print("!! %04X 点阵字节数 = %d（应为 32）" % (gbk, len(nums)))
            continue
        table[gbk] = [int(n, 16) for n in nums]
    return table


def show_cn_char_at(gram, x, page, gbk, table):
    """复刻 OLED_ShowCNCharAt()：16 列 x 16 行 -> 上下两页，位展开。"""
    if (x + CN_W) > OLED_W or page >= (PAGE_N - 1):
        return
    glyph = table.get(gbk)

    for i in range(CN_W):
        if glyph is None:
            lo = hi = 0x7E                     # 与固件同款"缺字方块"
        else:
            lo = hi = 0
            for y in range(8):
                if (glyph[y * 2 + (i >> 3)] >> (7 - (i & 7))) & 1:
                    lo |= (1 << y)
            for y in range(8):
                if (glyph[(y + 8) * 2 + (i >> 3)] >> (7 - (i & 7))) & 1:
                    hi |= (1 << y)
        gram[page][x + i] = lo
        gram[page + 1][x + i] = hi


def show_cn_string_center(gram, page, gbks, table):
    """复刻 OLED_ShowCNStringCenter()：按像素宽度水平居中。"""
    n = len(gbks) // 2
    w = n * CN_W
    x = 0 if w > OLED_W else (OLED_W - w) // 2
    for k in range(n):
        gbk = (gbks[k * 2] << 8) | gbks[k * 2 + 1]
        show_cn_char_at(gram, x, page, gbk, table)
        x += CN_W
    return x


def build(gram, table, gbks, page):
    gram.clear()
    gram.extend([bytearray(OLED_W) for _ in range(PAGE_N)])
    show_cn_string_center(gram, page, gbks, table)
    return gram


def render_png(screens, out_png, scale=6):
    """把多屏拼成一张图：每屏 128x32 放大 scale 倍，上下留标题带。"""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("!! 需要 Pillow：pip install pillow")
        return False

    pad, band = 12, 26
    cols = len(screens)
    W = pad + cols * OLED_W * scale + (cols - 1) * pad + pad
    H = pad + band + OLED_H * scale + pad

    img = Image.new("RGB", (W, H), (24, 26, 32))
    d = ImageDraw.Draw(img)

    for idx, (title, gram) in enumerate(screens):
        ox = pad + idx * (OLED_W * scale + pad)
        oy = pad + band

        d.text((ox, pad + 4), title, fill=(210, 216, 230))

        # 屏底色（SSD1306 是黑底 + 蓝白像素）
        d.rectangle([ox - 1, oy - 1, ox + OLED_W * scale, oy + OLED_H * scale],
                    outline=(70, 78, 96), fill=(0, 0, 0))

        for page in range(PAGE_N):
            for x in range(OLED_W):
                b = gram[page][x]
                for y in range(8):
                    if (b >> y) & 1:
                        px = ox + x * scale
                        py = oy + (page * 8 + y) * scale
                        d.rectangle([px, py, px + scale - 1, py + scale - 1],
                                    fill=(150, 210, 255))

    img.save(out_png)
    print("已生成预览图: %s  (%dx%d)" % (out_png, W, H))
    return True


def ascii_dump(title, gram):
    """纯文本版预览，方便在终端里直接核对。"""
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)
    for y in range(OLED_H):
        page, bit = divmod(y, 8)
        line = "".join("#" if (gram[page][x] >> bit) & 1 else "." for x in range(OLED_W))
        print(line)


def main():
    table = parse_font(FONT_C)
    print("字库: %d 个汉字" % len(table))
    names = {0xC0EE: "李", 0xB5C7: "登", 0xBBD4: "辉",
             0xBDD0: "叫", 0xB0D6: "爸"}
    for g in sorted(table):
        print("  0x%04X  %s" % (g, names.get(g, "?")))

    # 校验：main.c 里用到的每个字节对都必须在字库里
    need = list(CN_NAME) + list(CN_CALL)
    missing = []
    for i in range(0, len(need), 2):
        gbk = (need[i] << 8) | need[i + 1]
        if gbk not in table:
            missing.append("0x%04X" % gbk)
    if missing:
        print("\n!! 字库缺字: %s" % ", ".join(missing))
        return 1
    print("\n字库自检通过：main.c 用到的字全部命中")

    gram = []
    s1 = build(gram, table, CN_NAME, page=1)
    g1 = [bytearray(c) for c in gram]
    s2 = build(gram, table, CN_CALL, page=1)
    g2 = [bytearray(c) for c in gram]

    ascii_dump("上电 / 第一次画面：李登辉  (page=1, 起点 x=%d)" % ((OLED_W - 48) // 2), g1)
    ascii_dump("按 KEY1 后：叫爸爸  (page=1, 起点 x=%d)" % ((OLED_W - 48) // 2), g2)

    out = os.path.join(PROJ, "Doc", "OLED_屏上预览_李登辉与叫爸爸.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    render_png([("Power-on  /  KEY1 x1:  Li Deng Hui", g1),
                ("KEY1 x2:  Jiao Ba Ba", g2)], out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
