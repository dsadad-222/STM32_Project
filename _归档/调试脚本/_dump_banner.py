# -*- coding: utf-8 -*-
"""把 main.c 里 Usart_SendString() 的 GBK 转义字符串解码成人能读的中文，
用来核对使用手册里的"开机横幅"与实际固件输出是否一致。

⚠ 横幅的每个 Usart_SendString 都跨 2~3 行、由多段相邻字面量拼接而成，
  按单行解析会漏掉后半段 —— 必须跨行匹配到 `);` 为止。
"""
import io
import re

CALL = re.compile(r'Usart_SendString\((.*?)\);', re.S)
LIT = re.compile(r'"((?:[^"\\]|\\.)*)"')
HEX = re.compile(r'\\x([0-9A-Fa-f]{2})')

src = io.open(r'D:/STM32_Project/RadarFlash_Full/App_User/main.c', encoding='utf-8').read()

for m in CALL.finditer(src):
    parts = LIT.findall(m.group(1))
    if not parts:
        continue
    buf = b''
    for p in parts:
        buf += HEX.sub(lambda g: chr(int(g.group(1), 16)), p).encode('latin-1', 'ignore')
    if not buf:
        continue
    try:
        text = buf.decode('gbk')
    except UnicodeDecodeError:
        text = repr(buf)
    if text.strip():
        print(text)
