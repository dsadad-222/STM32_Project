# -*- coding: utf-8 -*-
"""
生成 16x16 汉字点阵字库（C 源文件）+ 中文提示字节串 + 预览图。

字库只包含工程里真正用到的字，Flash 占用约 (字数 x 32) 字节。
字模格式：每行 2 字节（高位在左），共 16 行 32 字节，1 = 亮点。
"""

import ctypes
import struct
import sys
import zlib
from ctypes import wintypes

gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

# 默认输出到 chapter8 原工程（不带参数运行时行为完全不变）。
# 用法：python gen_cn_font.py [输出工程根目录] [--radar]
#   --radar 追加"倒车雷达"用到的汉字与新消息宏，不污染原工程字库。
OUT_DIR = r"D:\STM32_Project\AdcTemp_Full"
PREVIEW_PNG = r"C:\Users\y7000\Desktop\嵌入式\中文字库16x16_预览.png"

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
RADAR_MODE = ("--radar" in sys.argv)
if ARGS:
    OUT_DIR = ARGS[0]
    PREVIEW_PNG = OUT_DIR + r"\Doc\中文字库16x16_预览.png"


class BITMAP(ctypes.Structure):
    _fields_ = [("bmType", ctypes.c_long), ("bmWidth", ctypes.c_long),
                ("bmHeight", ctypes.c_long), ("bmWidthBytes", ctypes.c_long),
                ("bmPlanes", ctypes.c_ushort), ("bmBitsPixel", ctypes.c_ushort),
                ("bmBits", ctypes.c_void_p)]


gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateBitmap.restype = wintypes.HBITMAP
gdi32.CreateBitmap.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint,
                               ctypes.c_uint, ctypes.c_void_p]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.CreateFontW.restype = wintypes.HFONT
gdi32.CreateFontW.argtypes = [ctypes.c_int] * 13 + [wintypes.LPCWSTR]
gdi32.GetObjectW.argtypes = [wintypes.HGDIOBJ, ctypes.c_int, ctypes.c_void_p]
gdi32.GetBitmapBits.argtypes = [wintypes.HBITMAP, ctypes.c_long, ctypes.c_void_p]
gdi32.TextOutW.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int,
                           wintypes.LPCWSTR, ctypes.c_int]
gdi32.PatBlt.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                         ctypes.c_int, wintypes.DWORD]
gdi32.SetBkColor.argtypes = [wintypes.HDC, wintypes.COLORREF]
gdi32.SetTextColor.argtypes = [wintypes.HDC, wintypes.COLORREF]

WHITENESS = 0x00FF0062
GB2312_CHARSET = 134
NONANTIALIASED_QUALITY = 3

FONT_NAME = "SimSun"
FONT_SIZE = 16


def render(ch):
    """返回 32 字节点阵（1 = 亮点），行优先、每行 2 字节、高位在左"""
    hdc = gdi32.CreateCompatibleDC(0)
    hbmp = gdi32.CreateBitmap(16, 16, 1, 1, None)
    oldbmp = gdi32.SelectObject(hdc, hbmp)

    gdi32.PatBlt(hdc, 0, 0, 16, 16, WHITENESS)
    gdi32.SetBkColor(hdc, 0x00FFFFFF)
    gdi32.SetTextColor(hdc, 0x00000000)

    hfont = gdi32.CreateFontW(-FONT_SIZE, 0, 0, 0, 400, 0, 0, 0,
                              GB2312_CHARSET, 0, 0, NONANTIALIASED_QUALITY, 0, FONT_NAME)
    oldfont = gdi32.SelectObject(hdc, hfont)
    gdi32.TextOutW(hdc, 0, 0, ch, 1)

    bm = BITMAP()
    gdi32.GetObjectW(hbmp, ctypes.sizeof(BITMAP), ctypes.byref(bm))
    wb = bm.bmWidthBytes
    total = wb * bm.bmHeight
    buf = ctypes.create_string_buffer(total)
    gdi32.GetBitmapBits(hbmp, total, buf)
    raw = bytearray(buf.raw)

    gdi32.SelectObject(hdc, oldfont)
    gdi32.DeleteObject(hfont)
    gdi32.SelectObject(hdc, oldbmp)
    gdi32.DeleteObject(hbmp)
    gdi32.DeleteDC(hdc)

    out = bytearray()
    for y in range(16):
        b0 = 0
        b1 = 0
        for x in range(16):
            rawbit = (raw[y * wb + (x >> 3)] >> (7 - (x & 7))) & 1
            lit = 0 if rawbit else 1          # 单色位图里 0 = 黑 = 文字
            if lit:
                if x < 8:
                    b0 |= (0x80 >> x)
                else:
                    b1 |= (0x80 >> (x - 8))
        out.append(b0)
        out.append(b1)
    return bytes(out)


# --------------------------- 字集 ---------------------------
CHARS = (
    "温度芯片电压采样值页面左转右蜂鸣灯条开关呼吸自检中错误超报警"
    "当前数据存储读取无标定完成清除失败效果常偏高已保正在启动信号"
)

# 倒车雷达新增字（只在 --radar 时并入，原工程字库保持一行不变）
CHARS_RADAR = (
    "距离安全注意接近危险雷达停车启闭无回波太远太近"
)

if RADAR_MODE:
    CHARS += CHARS_RADAR

CHARS = "".join(dict.fromkeys(CHARS))       # 去重，保持顺序

# 中文提示（串口 + OLED 共用一份 GBK 字节表）
MESSAGES = {
    "CN_BOOT_OK":      "系统启动完成",
    "CN_BOOTING":      "正在启动",
    "CN_BOOT_FLASH":   "读取存储",
    "CN_NO_FLASH":     "无存储数据",
    "CN_CAL_OK":       "标定完成",
    "CN_CAL_SKIP":     "读数无效",
    "CN_CAL_CLEAR":    "标定清除",
    "CN_FLASH_ERR":    "存储失败",
    "CN_SAVED":        "已保存",
    "CN_CLEARED":      "已清除",
    "CN_CTRL_OK":      "控制完成",
    "CN_BAD_CODE":     "指令错误",
    "CN_BREATH_ON":    "呼吸开",
    "CN_BREATH_OFF":   "呼吸关",
    "CN_TEMP":         "温度",
    "CN_VDDA_WARN":    "警告供电偏高",
}

# 倒车雷达提示词（只在 --radar 时输出）
MESSAGES_RADAR = {
    "CN_R_DIST":       "距离",
    "CN_R_ON":         "雷达开启",
    "CN_R_OFF":        "雷达关闭",
    "CN_R_SAFE":       "安全",
    "CN_R_CARE":       "注意",
    "CN_R_CLOSE":      "接近",
    "CN_R_DANGER":     "危险",
    "CN_R_NOECHO":     "无回波",
}

if RADAR_MODE:
    MESSAGES = dict(MESSAGES)
    MESSAGES.update(MESSAGES_RADAR)

# 只在串口打印、不上 OLED 的词（字库里没有这些字，也不需要）
EXTRA_MESSAGES = [
    ("CN_CAL_NONE",  "温度未标定"),
    ("CN_CAL_HINT",  "发K加室温回车标定"),
    ("CN_CAL_USE",   "标定生效"),
    ("CN_SUMMARY",   "小结"),
    ("CN_VOLT",      "电压"),
    ("CN_RAWVAL",    "原始值"),
    ("CN_DIE_TEMP",  "芯片结温"),
    ("CN_CALED",     "已标定"),
    ("CN_UNCAL",     "未标定"),
]


def to_c_bytes(s):
    """把字符串转成 C 的 \\xHH 转义（逐字节，避免源码编码问题）"""
    return "".join("\\x%02X" % b for b in s.encode("gbk"))


def gbk_code(s):
    b = s.encode("gbk")
    assert len(b) == 2, s
    return (b[0] << 8) | b[1]


def write_font_header():
    path = OUT_DIR + r"\Drv_Common\cn_font16.h"
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write('''/**
  ******************************************************************************
  * @file    Drv_Common/cn_font16.h
  * @brief   16x16 汉字点阵字库（只含本工程用到的字，按需生成）
  *
  *          字形由 PC 端 gen_cn_font.py 用 Windows 宋体取模生成。
  *          每个字 32 字节：16 行 x 每行 2 字节，高位在左，1 = 亮点。
  *
  *          屏上显示时按“请求的 GBK 双字节 -> 查表”取字模，找不到就画方块。
  ******************************************************************************
  */

#ifndef __CN_FONT16_H
#define __CN_FONT16_H

#include "stm32f10x.h"

#define CN_FONT16_W         16                  /* 汉字宽（像素）*/
#define CN_FONT16_H         16                  /* 汉字高（像素）*/

typedef struct
{
    uint16_t gbk;                               /* GBK 双字节编码（高字节在前）*/
    uint8_t  data[32];                          /* 16 行 x 2 字节点阵 */
} CnGlyph16_t;

extern const CnGlyph16_t g_cnFont16[];
extern const uint16_t    g_cnFont16Count;

/* 按 GBK 双字节查字模，找不到返回 0 */
const CnGlyph16_t *CnFont16_Lookup(uint16_t gbk);

#endif /* __CN_FONT16_H */
''')
    print("写出：", path)


def write_font_source(glyphs):
    path = OUT_DIR + r"\Drv_Common\cn_font16.c"
    lines = []
    lines.append('''/**
  ******************************************************************************
  * @file    Drv_Common/cn_font16.c
  * @brief   16x16 汉字点阵字库数据（由 gen_cn_font.py 自动生成，请勿手改）
  *
  *          重新生成：在 PC 上运行 D:\\\\STM32_Project\\\\gen_cn_font.py
  *          增删字只需改脚本里的 CHARS 字符串。
  ******************************************************************************
  */

#include "cn_font16.h"

const CnGlyph16_t g_cnFont16[] =
{''')
    for ch, gbk, data in glyphs:
        rows = []
        for i in range(0, 32, 8):
            rows.append(", ".join("0x%02X" % b for b in data[i:i + 8]))
        body = (",\n              ".join(rows))
        lines.append("    {0x%04X, {%s}},   /* %s */" % (gbk, body, ch))
    lines.append('''};

const uint16_t g_cnFont16Count = (uint16_t)(sizeof(g_cnFont16) / sizeof(g_cnFont16[0]));

const CnGlyph16_t *CnFont16_Lookup(uint16_t gbk)
{
    uint16_t i;

    for (i = 0; i < g_cnFont16Count; i++)
    {
        if (g_cnFont16[i].gbk == gbk)
        {
            return &g_cnFont16[i];
        }
    }

    return 0;
}''')
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\n".join(lines) + "\n")
    print("写出：", path)


def write_msg_header():
    path = OUT_DIR + r"\App_User\cn_msg.h"
    with open(path, "w", encoding="utf-8", newline="\r\n") as f:
        f.write('''/**
  ******************************************************************************
  * @file    App_User/cn_msg.h
  * @brief   中文提示的 GBK 字节串（由 gen_cn_font.py 自动生成，请勿手改）
  *
  *          串口助手把编码设成 GBK/ANSI 就能直接看到这些汉字；
  *          OLED 显示时由 OLED_ShowCNString() 按 GBK 双字节查字库渲染。
  *
  *          全部写成 \\xHH 转义，源码里不出现中文字节，
  *          这样无论 Keil 用什么源码编码编译，发出去的字节都一模一样。
  ******************************************************************************
  */

#ifndef __CN_MSG_H
#define __CN_MSG_H

''')
        for name, text in MESSAGES.items():
            f.write('#define %-16s "%s"   /* %s */\n' % (name, to_c_bytes(text), text))

        f.write('/* ↓ 下面这些只在串口用（OLED 字库里没有这几个字，也无需加）*/\n')
        for name, text in EXTRA_MESSAGES:
            f.write('#define %-16s "%s"   /* %s */\n' % (name, to_c_bytes(text), text))

        f.write("\n#endif /* __CN_MSG_H */\n")
    print("写出：", path)


# --------------------------- 预览图（纯 Python 写 PNG）---------------------------
def write_png(path, width, height, pixels):
    raw = b""
    for y in range(height):
        raw += b"\x00" + bytes(pixels[y * width:(y + 1) * width])

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    print("写出：", path)


def render_preview(glyphs, scale=6, cols=10, pad=6):
    cell_w = 16 * scale
    cell_h = 16 * scale
    rows = (len(glyphs) + cols - 1) // cols
    W = cols * (cell_w + pad) + pad
    H = rows * (cell_h + pad) + pad
    px = bytearray([255] * (W * H))          # 白底

    for idx, (ch, gbk, data) in enumerate(glyphs):
        cx = pad + (idx % cols) * (cell_w + pad)
        cy = pad + (idx // cols) * (cell_h + pad)
        for y in range(16):
            for x in range(16):
                bit = (data[y * 2 + (x >> 3)] >> (7 - (x & 7))) & 1
                if not bit:
                    continue
                for dy in range(scale):
                    for dx in range(scale):
                        px[(cy + y * scale + dy) * W + (cx + x * scale + dx)] = 0
        # 格子边框
        for x in range(cell_w + 1):
            px[cy * W + cx + x] = 200
            px[(cy + cell_h) * W + cx + x] = 200
        for y in range(cell_h + 1):
            px[(cy + y) * W + cx] = 200
            px[(cy + y) * W + cx + cell_w] = 200

    write_png(PREVIEW_PNG, W, H, px)


if __name__ == "__main__":
    glyphs = []
    for ch in CHARS:
        glyphs.append((ch, gbk_code(ch), render(ch)))

    write_font_header()
    write_font_source(glyphs)
    write_msg_header()
    render_preview(glyphs)

    print()
    print("字数 %d，字模数据 %d 字节（Flash 占用，含结构体对齐约 %d 字节）"
          % (len(glyphs), len(glyphs) * 32, len(glyphs) * 34))
    print("字符集：", CHARS)
