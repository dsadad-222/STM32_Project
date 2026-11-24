# -*- coding: utf-8 -*-
"""检查接口文档里有没有描述 OLED 第 4 行显示中文提示的内容。"""
import zipfile
import re

DOC = r'D:\STM32_Project\docs\片内片外FLASH读写_接口文档.docx'

z = zipfile.ZipFile(DOC)
xml = z.read('word/document.xml').decode('utf-8')
texts = re.findall(r'<w:t[^>]*>(.*?)</w:t>', xml, re.S)
full = ''.join(texts)
print('document text length:', len(full))
print()

KWS = ['OLED', '第 4 行', '第4行', '指令错误', '已保存', '正在启动', '已清除',
       '标定完成', '存储失败', '控制完成', '读取存储', '呼吸开', '呼吸关']

for kw in KWS:
    hits = list(re.finditer(re.escape(kw), full))
    print('%-8s x%d' % (kw, len(hits)))
    for m in hits[:4]:
        s = max(0, m.start() - 70)
        e = min(len(full), m.end() + 70)
        print('    ...' + full[s:e].replace('\n', ' ') + '...')
    if hits:
        print()
