# -*- coding: utf-8 -*-
"""匿名版工程 SerialCmd_Test：改工程名 + 重组 Drv_Common 源文件列表"""
import io
import os

PRJ = r'D:\STM32_Project\SerialCmd_Test\Project'

# ---------- 1. 重命名 .uvprojx / .uvoptx ----------
for old, new in (('SerialCtrl_Full.uvprojx', 'SerialCmd_Test.uvprojx'),
                 ('SerialCtrl_Full.uvoptx', 'SerialCmd_Test.uvoptx')):
    so, sn = os.path.join(PRJ, old), os.path.join(PRJ, new)
    if os.path.exists(so):
        os.replace(so, sn)
        print('renamed', old, '->', new)

# ---------- 2. 改 uvprojx 内容 ----------
P = os.path.join(PRJ, 'SerialCmd_Test.uvprojx')
s = io.open(P, 'r', encoding='utf-8').read()

s = s.replace('SerialCtrl_Full', 'SerialCmd_Test')

OLD_FILES = (
    '            <File>\n'
    '              <FileName>led_drv.c</FileName>\n'
    '              <FileType>1</FileType>\n'
    '              <FilePath>..\\Drv_Common\\led_drv.c</FilePath>\n'
    '            </File>\n'
    '            <File>\n'
    '              <FileName>beep_drv.c</FileName>\n'
    '              <FileType>1</FileType>\n'
    '              <FilePath>..\\Drv_Common\\beep_drv.c</FilePath>\n'
    '            </File>\n'
    '            <File>\n'
    '              <FileName>usart_drv.c</FileName>\n'
    '              <FileType>1</FileType>\n'
    '              <FilePath>..\\Drv_Common\\usart_drv.c</FilePath>\n'
    '            </File>\n'
    '            <File>\n'
    '              <FileName>systick_drv.c</FileName>\n'
    '              <FileType>1</FileType>\n'
    '              <FilePath>..\\Drv_Common\\systick_drv.c</FilePath>\n'
    '            </File>\n'
)
if OLD_FILES not in s:
    OLD_FILES = OLD_FILES.replace('\n', '\r\n')

NEW_FILES = (
    '            <File>\n'
    '              <FileName>tick.c</FileName>\n'
    '              <FileType>1</FileType>\n'
    '              <FilePath>..\\Drv_Common\\tick.c</FilePath>\n'
    '            </File>\n'
    '            <File>\n'
    '              <FileName>board.c</FileName>\n'
    '              <FileType>1</FileType>\n'
    '              <FilePath>..\\Drv_Common\\board.c</FilePath>\n'
    '            </File>\n'
    '            <File>\n'
    '              <FileName>uart.c</FileName>\n'
    '              <FileType>1</FileType>\n'
    '              <FilePath>..\\Drv_Common\\uart.c</FilePath>\n'
    '            </File>\n'
)
assert OLD_FILES in s, 'Drv_Common 旧文件清单没找到'
s = s.replace(OLD_FILES, NEW_FILES)
io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('uvprojx patched')

# ---------- 3. 改 uvoptx 内容 ----------
Q = os.path.join(PRJ, 'SerialCmd_Test.uvoptx')
if os.path.exists(Q):
    t = io.open(Q, 'r', encoding='utf-8').read()
    t = t.replace('SerialCtrl_Full', 'SerialCmd_Test')
    t = t.replace('led_drv.c', 'tick.c').replace('beep_drv.c', 'board.c')
    t = t.replace('usart_drv.c', 'uart.c').replace('systick_drv.c', 'board.c')
    io.open(Q, 'w', encoding='utf-8', newline='').write(t)
    print('uvoptx patched')
