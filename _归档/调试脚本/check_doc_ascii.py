# -*- coding: utf-8 -*-
"""检查接口文档里有没有 ASCII 快捷命令表 —— 加了 W 命令后可能需要同步。"""
import zipfile
import re

DOC = r'D:\STM32_Project\docs\片内片外FLASH读写_接口文档.docx'

z = zipfile.ZipFile(DOC)
xml = z.read('word/document.xml').decode('utf-8')
texts = re.findall(r'<w:t[^>]*>(.*?)</w:t>', xml, re.S)
full = ''.join(texts)
print('document text length:', len(full))
print()

KWS = ['快捷命令', 'ASCII', '翻转', 'K25', '发K', 'L/R/B/D', 'T + ', 'S / C / P',
       '标定', '命令行', 'L1', 'W1']

for kw in KWS:
    hits = list(re.finditer(re.escape(kw), full))
    print('%-10s x%d' % (kw, len(hits)))
    for m in hits[:3]:
        s = max(0, m.start() - 90)
        e = min(len(full), m.end() + 90)
        print('    ...' + full[s:e].replace('\n', ' ') + '...')
    if hits:
        print()
