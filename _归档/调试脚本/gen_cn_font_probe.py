# -*- coding: utf-8 -*-
"""
用 Windows GDI + 宋体生成 16x16 汉字点阵（取模），并打印 ASCII 预览核对方向/极性。

点阵数据格式（标准取模格式，方便和 PCtoLCD2002 对照）：
  每行 16 个像素，按“行优先、每行高位在左、每行 2 字节、共 16 行”存 32 字节。
  也就是  data[0] = 第 1 行左边 8 个像素，data[1] = 第 1 行右边 8 个像素。
"""

import ctypes
from ctypes import wintypes

gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)

class BITMAP(ctypes.Structure):
    _fields_ = [("bmType", ctypes.c_long),
                ("bmWidth", ctypes.c_long),
                ("bmHeight", ctypes.c_long),
                ("bmWidthBytes", ctypes.c_long),
                ("bmPlanes", ctypes.c_ushort),
                ("bmBitsPixel", ctypes.c_ushort),
                ("bmBits", ctypes.c_void_p)]

gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateBitmap.restype = wintypes.HBITMAP
gdi32.CreateBitmap.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint,
                               ctypes.c_uint, ctypes.c_void_p]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.CreateFontW.restype = wintypes.HFONT
gdi32.CreateFontW.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                              ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                              ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                              ctypes.c_int, wintypes.LPCWSTR]
gdi32.GetObjectW.argtypes = [wintypes.HGDIOBJ, ctypes.c_int, ctypes.c_void_p]
gdi32.GetBitmapBits.argtypes = [wintypes.HBITMAP, ctypes.c_long, ctypes.c_void_p]
gdi32.TextOutW.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int,
                           wintypes.LPCWSTR, ctypes.c_int]
gdi32.PatBlt.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                         ctypes.c_int, wintypes.DWORD]
gdi32.SetBkColor.argtypes = [wintypes.HDC, wintypes.COLORREF]
gdi32.SetTextColor.argtypes = [wintypes.HDC, wintypes.COLORREF]
gdi32.DeleteDC.argtypes = [wintypes.HDC]

WHITENESS = 0x00FF0062
GB2312_CHARSET = 134
NONANTIALIASED_QUALITY = 3
ANTIALIASED_QUALITY = 4


def render(ch, fontname="SimSun", size=16, quality=NONANTIALIASED_QUALITY):
    """把一个汉字渲染成 16x16 点阵，返回 (rows, 原始字节)"""
    hdc = gdi32.CreateCompatibleDC(0)
    hbmp = gdi32.CreateBitmap(16, 16, 1, 1, None)
    oldbmp = gdi32.SelectObject(hdc, hbmp)

    gdi32.PatBlt(hdc, 0, 0, 16, 16, WHITENESS)      # 白底
    gdi32.SetBkColor(hdc, 0x00FFFFFF)
    gdi32.SetTextColor(hdc, 0x00000000)             # 黑字

    hfont = gdi32.CreateFontW(-size, 0, 0, 0, 400, 0, 0, 0,
                              GB2312_CHARSET, 0, 0, quality, 0, fontname)
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

    # 拆成 16x16 的像素矩阵，同时判断极性（黑字在白底上 -> 哪个位值代表“亮”）
    rows = []
    for y in range(16):
        row = []
        for x in range(16):
            byte = raw[y * wb + (x >> 3)]
            bit = (byte >> (7 - (x & 7))) & 1
            row.append(bit)
        rows.append(row)

    return rows, raw, wb


def to_ascii(rows):
    return "\n".join("".join("#" if v else "." for v in r) for r in rows)


if __name__ == "__main__":
    test = "中三温A"
    for ch in test:
        rows, raw, wb = render(ch)
        ones = sum(sum(r) for r in rows)
        print("== %s ==  bmWidthBytes=%d  亮像素=%d  （先按 1=亮 画）" % (ch, wb, ones))
        print(to_ascii(rows))
        print()
