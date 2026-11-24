# -*- coding: utf-8 -*-
"""SerialAdv_Full.uvprojx: 改 OutputName + Drv_Common 组补 3 个新驱动。"""
import re, io

P = r'D:\STM32_Project\SerialAdv_Full\Project\SerialAdv_Full.uvprojx'
s = io.open(P, encoding='utf-8', errors='ignore').read()
orig = s

# 1) 输出名
s = s.replace('<OutputName>SerialCtrl_Full</OutputName>',
              '<OutputName>SerialAdv_Full</OutputName>')
assert '<OutputName>SerialAdv_Full</OutputName>' in s, 'OutputName 未替换'

# 2) Drv_Common 组补文件
NEW_FILES = ['oled_drv.c', 'flash_drv.c', 'font8x8.c']

m = re.search(r'(<Group>\s*<GroupName>Drv_Common</GroupName>.*?)(</Group>)', s, re.S)
assert m, '没找到 Drv_Common 组'
block = m.group(1)
indent = '              '
extra = ''
for fn in NEW_FILES:
    if fn in block:
        continue
    extra += (
        '            <File>\r\n'
        f'              <FileName>{fn}</FileName>\r\n'
        '              <FileType>1</FileType>\r\n'
        f'              <FilePath>..\\Drv_Common\\{fn}</FilePath>\r\n'
        '            </File>\r\n'
    )
assert extra, '新驱动已经在组里了？'

# 插到该组最后一个 </File> 之后
idx = block.rfind('</File>') + len('</File>') + 2      # 跳过行尾换行
insert_at = m.start(1) + idx
s = s[:insert_at] + extra + s[insert_at:]

io.open(P, 'w', encoding='utf-8', newline='').write(s)
print('patched ->', P)
print('改动字节数 =', len(s) - len(orig))
print('新增文件 =', NEW_FILES)
