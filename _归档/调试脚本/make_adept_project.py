# -*- coding: utf-8 -*-
"""从 SerialAdv_Full 复制出 AdcTemp_Full 工程，并改名 + 挂上新增驱动。"""
import os
import shutil

SRC = r'D:\STM32_Project\SerialAdv_Full'
DST = r'D:\STM32_Project\AdcTemp_Full'
BS = chr(92)                     # 反斜杠，避免转义歧义

SKIP_DIRS = {'Objects', 'Listings', '__pycache__'}

if os.path.exists(DST):
    shutil.rmtree(DST)

copied = 0
for root, dirs, files in os.walk(SRC):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
    rel = os.path.relpath(root, SRC)
    tgt = DST if rel == '.' else os.path.join(DST, rel)
    os.makedirs(tgt, exist_ok=True)
    for f in files:
        if f.endswith('.uvguix') or '.uvguix.' in f:
            continue
        shutil.copy2(os.path.join(root, f), os.path.join(tgt, f))
        copied += 1
print('copied:', copied)

old_proj = os.path.join(DST, 'Project', 'SerialAdv_Full.uvprojx')
new_proj = os.path.join(DST, 'Project', 'AdcTemp_Full.uvprojx')
xml = open(old_proj, encoding='utf-8').read()
xml = xml.replace('<OutputName>SerialAdv_Full</OutputName>',
                  '<OutputName>AdcTemp_Full</OutputName>')
xml = xml.replace('SerialAdv_Full.', 'AdcTemp_Full.')

anchor = ('            <File>' + chr(10) +
          '              <FileName>font8x8.c</FileName>' + chr(10) +
          '              <FileType>1</FileType>' + chr(10) +
          '              <FilePath>..' + BS + 'Drv_Common' + BS + 'font8x8.c</FilePath>' + chr(10) +
          '            </File>')
assert anchor in xml, 'anchor not found'

tpl = (chr(10) + '            <File>' + chr(10) +
       '              <FileName>%s</FileName>' + chr(10) +
       '              <FileType>1</FileType>' + chr(10) +
       '              <FilePath>..' + BS + 'Drv_Common' + BS + '%s</FilePath>' + chr(10) +
       '            </File>')

add = anchor
for name in ('adc_drv.c', 'key_drv.c', 'pwm_drv.c'):
    add += tpl % (name, name)
xml = xml.replace(anchor, add, 1)
open(new_proj, 'w', encoding='utf-8').write(xml)
os.remove(old_proj)

old_opt = os.path.join(DST, 'Project', 'SerialAdv_Full.uvoptx')
if os.path.exists(old_opt):
    t = open(old_opt, encoding='utf-8', errors='ignore').read()
    t = t.replace('SerialAdv_Full', 'AdcTemp_Full')
    open(os.path.join(DST, 'Project', 'AdcTemp_Full.uvoptx'), 'w', encoding='utf-8').write(t)
    os.remove(old_opt)

print('project file :', os.path.basename(new_proj))
print('output name  :', 'AdcTemp_Full' in xml)
print('new sources  :', [n for n in ('adc_drv.c', 'key_drv.c', 'pwm_drv.c') if n in xml])
print('Project dir  :', os.listdir(os.path.join(DST, 'Project')))
