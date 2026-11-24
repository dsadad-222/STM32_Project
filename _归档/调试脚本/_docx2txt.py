# -*- coding: utf-8 -*-
"""把 0917 接口文档 docx 提取成纯文本，供阅读与写汇报稿引用。"""
import zipfile, re, sys

def docx_text(path):
    z = zipfile.ZipFile(path)
    xml = z.read('word/document.xml').decode('utf-8', 'ignore')
    xml = re.sub(r'</w:p>', '\n', xml)
    xml = re.sub(r'</w:tc>', ' | ', xml)
    xml = re.sub(r'<[^>]+>', '', xml)
    for a, b in [('&amp;', '&'), ('&lt;', '<'), ('&gt;', '>'),
                 ('&quot;', '"'), ('&apos;', "'")]:
        xml = xml.replace(a, b)
    return [l.strip() for l in xml.split('\n') if l.strip()]

src = r'C:\Users\y7000\Desktop\嵌入式\0917_片内片外FLASH读写\202417010304智能3班陈相林实现片内片外FLASH读写\片内片外FLASH读写_接口文档.docx'
out = r'D:\STM32_Project\_0917_doc.txt'
lines = docx_text(src)
with open(out, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print('总行数:', len(lines))
print('已写入:', out)

print('\n=== 章节标题 ===')
for l in lines[:400]:
    if re.match(r'^\d+(\.\d+)*\s+\S', l) and len(l) < 70:
        print('  ', l)

print('\n=== 关键词命中 ===')
for k in ['内部', '外部', 'W25Q', 'SPI', '数据页', '0x08', '功能字', '帧', '校验',
          'OLED', '串口', '温度', '掉电', '擦', '写', '读', '地址', '魔数', '累加和',
          'BAD', 'STORE', 'ERROR', '任务书', '验收']:
    c = sum(1 for l in lines if k in l)
    if c:
        print('   %-8s %d' % (k, c))
sys.stdout.flush()
