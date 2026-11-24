# -*- coding: utf-8 -*-
import os
import codecs

D = r'C:\Users\y7000\Desktop\chapter9串口工具'
BAT = os.path.join(D, '启动.bat')
PS1 = os.path.join(D, 'send.ps1')

# .bat 必须是纯 ASCII + CRLF：cmd 默认按 ANSI/GBK 解码，
# 里面写中文注释会让字节被错解析成控制字符，整批命令结构崩坏。
bat_text = (
    '@echo off\r\n'
    'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0send.ps1"\r\n'
    'echo.\r\n'
    'pause\r\n'
)
with open(BAT, 'wb') as f:
    f.write(bat_text.encode('ascii'))

# .ps1 必须带 UTF-8 BOM：Windows PowerShell 5.1 读无 BOM 的 .ps1 会按 GBK 解码，
# 中文提示会全变乱码。
raw = open(PS1, 'rb').read()
if not raw.startswith(codecs.BOM_UTF8):
    with open(PS1, 'wb') as f:
        f.write(codecs.BOM_UTF8 + raw)
    print('BOM added')
else:
    print('BOM already present')

print('bat :', os.path.getsize(BAT), 'bytes, ascii-only =',
      all(c < 128 for c in open(BAT, 'rb').read()))
print('ps1 :', os.path.getsize(PS1), 'bytes, bom =',
      open(PS1, 'rb').read(3) == codecs.BOM_UTF8)
