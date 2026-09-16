# -*- coding: utf-8 -*-
"""修正 SerialCtrl_Full.uvprojx：输出名 + Drv_Common 源文件分组"""
import io

P = r'D:\STM32_Project\SerialCtrl_Full\Project\SerialCtrl_Full.uvprojx'
s = io.open(P, 'r', encoding='utf-8').read()

s = s.replace('<OutputName>KeyScan_Demo</OutputName>',
              '<OutputName>SerialCtrl_Full</OutputName>')

OLD = (
    '            <File>\r\n'
    '              <FileName>key_drv.c</FileName>\r\n'
    '              <FileType>1</FileType>\r\n'
    '              <FilePath>..\\Drv_Common\\key_drv.c</FilePath>\r\n'
    '            </File>\r\n'
)
if OLD not in s:
    OLD = OLD.replace('\r\n', '\n')

NEW = (
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
)
assert OLD in s, 'key_drv.c 片段没找到'
s = s.replace(OLD, NEW)

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('patched OK')
