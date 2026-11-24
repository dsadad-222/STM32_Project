# -*- coding: utf-8 -*-
"""修正 IrAvoid_Full/App_User/main.c 启动横幅里过时的「按键:」行。
原行还是需求4时代的映射（KEY1 测距+存外部FLASH），与上方新增的 KEY: 行冲突。
字节级替换：main.c 是 UTF-8 + CRLF，中文字面量是 GBK 转义字节。
"""
import io
import sys

SRC = r"D:\STM32_Project\IrAvoid_Full\App_User\main.c"

OLD = (b'    Usart_SendString("\\xB0\\xB4\\xBC\\xFC: KEY1 \\xB2\\xE2\\xBE\\xE0+\\xB4\\xE6\\xCD\\xE2\\xB2\\xBF"'
       b' "FLASH" "   KEY2 \\xB6\\xC1\\xCF\\xC2\\xD2\\xBB\\xCC\\xF5+\\xC1\\xAA\\xB6\\xAF   KEY3 \\xB6\\xC1\\xCD\\xE2\\xB2\\xBF\\xCE\\xC4\\xB1\\xBE\\r\\n");')

HEXD = "0123456789abcdefABCDEF"


def cstr(s):
    """ASCII 可见字符原样保留，其余按 GBK 转 \\xXX；\\xXX 后紧跟十六进制字符时断开字面量。"""
    parts = []
    for ch in s:
        o = ord(ch)
        if 0x20 <= o <= 0x7E and ch not in '"\\':
            parts.append(("c", ch))
        else:
            for b in ch.encode("gbk"):
                parts.append(("x", "\\x%02X" % b))
    out = []
    prev_x = False
    for kind, val in parts:
        if prev_x and kind == "c" and val in HEXD:
            out.append('" "')
        out.append(val)
        prev_x = (kind == "x")
    return '"' + "".join(out) + '"'


NEW_TEXT = ("按键: KEY1/2/3 已让给红外(见上)  "
            "原 KEY1 测距+存FLASH -> O  "
            "原 KEY2 读下一条 -> N  "
            "原 KEY3 读外部文本 -> E")
NEW = ('    Usart_SendString(' + cstr(NEW_TEXT) + ' "\\r\\n");').encode("ascii")

with open(SRC, "rb") as f:
    data = f.read()

n = data.count(OLD)
print("命中次数 =", n)
assert n == 1, "旧行未唯一命中，中止"
assert data.count(NEW) == 0, "新行已存在？"

data = data.replace(OLD, NEW)
with open(SRC, "wb") as f:
    f.write(data)

print("已替换。新行 =")
print("   ", NEW.decode("ascii"))
print("文件大小 =", len(data))
