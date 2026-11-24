# -*- coding: utf-8 -*-
"""
_extract_ir_strings.py —— 从固件 .hex 里把"串口将要发出去的字符串"抽出来

目的：需求5-2 要求"数据通过串口打印到PC"，而板载 USB-TTL 要插 USB 线才有 COM 口。
      在这之前，先用最硬的方式确认输出内容：直接把 .hex 解析成二进制，
      在 RO 段里搜出所有要发送的字符串常量（含 GBK 编码的中文），
      解码打印。这样即使没有串口，也能确认发出去的字节到底是什么。

用法：python _extract_ir_strings.py
"""

import io
import re

HEX = r'D:\STM32_Project\IrAvoid_Full\Project\Objects\IrAvoid_Full.hex'


def hex_to_bin(path):
    """解析 Intel HEX -> (起始地址, 字节串)"""
    data = {}
    base = 0
    lo, hi = 1 << 32, 0
    for line in io.open(path, 'r', encoding='ascii'):
        line = line.strip()
        if not line.startswith(':'):
            continue
        raw = bytes.fromhex(line[1:])
        n, addr, typ = raw[0], (raw[1] << 8) | raw[2], raw[3]
        payload = raw[4:4 + n]
        if typ == 0x00:
            a = base + addr
            for i, b in enumerate(payload):
                data[a + i] = b
            lo = min(lo, a)
            hi = max(hi, a + n)
        elif typ == 0x04:
            base = ((payload[0] << 8) | payload[1]) << 16
    buf = bytearray(hi - lo)
    for a, b in data.items():
        buf[a - lo] = b
    return lo, bytes(buf)


lo, blob = hex_to_bin(HEX)
print('固件基址 0x%08X，共 %d 字节' % (lo, len(blob)))

# 找连续的"可打印 ASCII 或 GBK 双字节"串，长度 >= 6
STR_RE = re.compile(rb'[\x20-\x7e\x81-\xfe]{6,}')

hits = []
for m in STR_RE.finditer(blob):
    s = m.group()
    if b'\x00' in s:
        continue
    try:
        txt = s.decode('gbk')
    except Exception:
        continue
    if not re.search(r'[\x20-\x7e]{3}', txt):
        continue
    hits.append((lo + m.start(), txt))

print('共抽出 %d 条字符串常量。下面是所有跟红外/需求5 相关的：\n' % len(hits))
KEY = ('IR', 'ir', 'diff', 'dark', 'lit', 'level', 'FAR', 'NEAR', 'MID',
       'blocked', 'clear', 'scan', 'LED_L')
for addr, txt in hits:
    if any(k in txt for k in KEY) and len(txt) < 220:
        print('  0x%08X  %s' % (addr, txt))

print('\n----- 完整字符串清单（只为确认没有乱码）-----')
for addr, txt in hits:
    if len(txt) < 130 and ('IR' in txt or '红外' in txt or 'ADC3' in txt or 'PE5' in txt
                           or 'PF9' in txt or 'onitor' in txt):
        print('  0x%08X  %s' % (addr, txt))
