# -*- coding: utf-8 -*-
r"""从 main.c 里把横幅字符串抽出来，按 GBK 解码回中文，验证字节没写错。"""
import io
import re

path = r"D:\STM32_Project\AdcTemp_Full\App_User\main.c"
with io.open(path, "r", encoding="utf-8") as f:
    src = f.read()

start = src.find('Usart_SendString("\\r\\n=== AdcTemp Full')
end = src.find('Usart_SendString("Info : "', start)
block = src[start:end]

print("=" * 70)
print("固件开机横幅（按 GBK 解码回读）")
print("=" * 70)
for m in re.finditer(r'Usart_SendString\((.*?)\);', block, re.S):
    expr = m.group(1)
    parts = re.findall(r'"((?:[^"\\]|\\.)*)"', expr)
    raw = bytearray()
    for p in parts:
        i = 0
        while i < len(p):
            if p[i] == '\\' and i + 1 < len(p) and p[i + 1] in 'xX':
                raw.append(int(p[i + 2:i + 4], 16))
                i += 4
            elif p[i] == '\\' and i + 1 < len(p):
                raw.append({'r': 13, 'n': 10, 't': 9}.get(p[i + 1], ord(p[i + 1])))
                i += 2
            else:
                raw.append(ord(p[i]))
                i += 1
    try:
        text = bytes(raw).decode('gbk')
        flag = "OK "
    except UnicodeDecodeError as e:
        text = bytes(raw).decode('gbk', 'replace')
        flag = "ERR"
    print("[%s] %s" % (flag, text.replace('\r\n', '')))
print()
print("字节总数：%d" % len(block))
