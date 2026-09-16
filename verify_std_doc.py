import zipfile
from lxml import etree
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
with zipfile.ZipFile(r"D:/STM32_Project/docs/串口数据控制测试_接口文档_标准版V2.docx") as z:
    root = etree.fromstring(z.read('word/document.xml'))
body = root.find(W+'body')
els = list(body)
txt = lambda e: ''.join(t.text or '' for t in e.iter(W+'t'))
# spot checks
joined = txt(body)
checks = {
  '校验行(表)': '帧头0^帧头1^长度^功能字^数据各字节异或' in joined,
  'L1/L0 命令': 'L1/L0' in joined,
  'KEY2 呼吸': 'KEY2 用于开关呼吸灯' in joined,
  'STATUS 新格式': 'BREATH=OFF' in joined,
  '旧文本0x07 已删': '55 FF 06 07 HELLO' not in joined,
  '旧存储码已删': '55 FF 02 08 02' not in joined,
  'OLED 段已删': 'OLED_ShowString' not in joined,
  'Flash 段已删': 'StoreRecord_t' not in joined,
  'RGB 行已删(控制单元)': '55 FF 03 06 03' not in joined,
  '修订行 V2.0': '按任务书标准版对齐' in joined,
  '呼吸灯接口表': 'void Breath_Start(void)' in joined,
  '按键接口表': 'KeyEvent Key_Scan(void)' in joined,
}
for k, v in checks.items():
    print(('OK ' if v else 'FAIL ') + k)
# module table rows
for e in els:
    if etree.QName(e).localname == 'tbl' and txt(e).startswith('模块源文件'):
        for tr in e.findall(W+'tr'):
            print('  MOD |', ' | '.join(''.join(t.text or '' for t in tc.iter(W+'t')) for tc in tr.findall(W+'tc')))
print('ALL PASS' if all(checks.values()) else 'SOME FAILED')
