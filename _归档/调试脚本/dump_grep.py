import zipfile
from lxml import etree
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
with zipfile.ZipFile(r"D:/STM32_Project/docs/串口数据控制测试_接口文档.docx") as z:
    root = etree.fromstring(z.read('word/document.xml'))
for e in root.find(W+'body'):
    if etree.QName(e).localname == 'p':
        t = ''.join(x.text or '' for x in e.iter(W+'t')).strip()
        if '蜂鸣器' in t and '接口' not in t:
            print(repr(t[:80]))
