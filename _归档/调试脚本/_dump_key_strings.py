# -*- coding: utf-8 -*-
"""把 main.c 里几条关键串口字符串的 GBK 转义精确解出来，供文档核对。"""
import re

SRC = r'D:/STM32_Project/RadarFlash_Full/App_User/main.c'
src = open(SRC, encoding='utf-8', errors='replace').read()

CALL = re.compile(r'Usart_SendString\((.*?)\);', re.S)
LIT = re.compile(r'"((?:[^"\\]|\\.)*)"')


def unesc(s):
    out = bytearray()
    i = 0
    while i < len(s):
        c = s[i]
        if c == '\\' and i + 1 < len(s):
            n = s[i + 1]
            if n == 'x':
                out.append(int(s[i + 2:i + 4], 16)); i += 4; continue
            simple = {'n': 10, 'r': 13, 't': 9, '"': 34, '\\': 92, '0': 0}
            if n in simple:
                out.append(simple[n]); i += 2; continue
        out.append(ord(c)); i += 1
    return bytes(out)


WANT = ('RadarFlash', 'ack ok', 'JEDEC', 'sector 1 ready', 'record #',
        'MEASURE:', 'KEY2 : record', 'no distance record')

print('=== main.c 里 Usart_SendString 的完整字符串（已按 GBK 解码）===')
seen = set()
for m in CALL.finditer(src):
    lits = LIT.findall(m.group(1))
    if not lits:
        continue
    raw = b''.join(unesc(x) for x in lits)
    txt = raw.decode('gbk', errors='replace').strip()
    if not txt or txt in seen:
        continue
    if any(w in txt for w in WANT):
        seen.add(txt)
        print('  %s' % txt)
