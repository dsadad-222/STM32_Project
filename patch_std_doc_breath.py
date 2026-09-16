# -*- coding: utf-8 -*-
"""接口文档 标准版V2 -> V2.1：呼吸灯描述改为 左转向灯(PG14+顶部RGB大灯)"""
import zipfile, os
from lxml import etree

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
def q(t): return W + t

SRC = r"D:/STM32_Project/docs/串口数据控制测试_接口文档_标准版V2.docx"
DST = r"D:/STM32_Project/docs/串口数据控制测试_接口文档_标准版V2.1.docx"

REPL = [
    # (旧全文, 新全文)
    ('TIM2 定时中断 + 软件 PWM 驱动 LED1 呼吸',
     'TIM2 定时中断 + 软件 PWM 驱动左转向灯呼吸（PG14 小灯与顶部 RGB 大灯同步）'),
    ('启动 LED1 呼吸灯（TIM2 软件 PWM 独占 PG14）',
     '启动左转向灯呼吸灯（PG14 与顶部 RGB 大灯同步呼吸，TIM2 软件 PWM 独占左转灯引脚）'),
    ('停止呼吸灯，LED1 熄灭，TIM2 中断关闭',
     '停止呼吸灯，左转向灯（含顶部 RGB 大灯）熄灭，TIM2 中断关闭'),
    ('LED1、LED2、有源蜂鸣器、按键 KEY2',
     'LED1、LED2、顶部 RGB 大灯（PG0/1/2）、有源蜂鸣器、按键 KEY2'),
]

# 长段落按子串替换（保留段落其余内容）
SUBST = [
    ('呼吸灯运行期间 LED1 由 TIM2 中断独占',
     '呼吸灯运行期间左转向灯由 TIM2 中断独占'),
    ('在中断里按占空比翻转引脚，等效出 200Hz 的 PWM 波；',
     '在中断里按占空比同时翻转 PG14 与顶部 RGB 大灯三色引脚（PG0/PG1/PG2），等效出 200Hz 的 PWM 波；'),
    ('板上那颗大灯（左上角）挂在 RGB 三色上',
     '顶部左边那颗大灯挂在 RGB 三色（PG0/PG1/PG2）上'),
]


def set_text(el, txt):
    ts = list(el.iter(q('t')))
    if not ts:
        r = etree.SubElement(el, q('r'))
        t = etree.SubElement(r, q('t'))
        t.text = txt
        return
    ts[0].text = txt
    for t in ts[1:]:
        t.text = ''


with zipfile.ZipFile(SRC) as z:
    root = etree.fromstring(z.read('word/document.xml'))
body = root.find(q('body'))

def ptext(e):
    return ''.join(t.text or '' for t in e.iter(q('t')))

n_full = n_sub = 0
for e in body.iter(q('p')):
    t = ptext(e).strip()
    hit = False
    for old, new in REPL:
        if t == old:
            set_text(e, new)
            n_full += 1
            hit = True
            break
    if not hit:
        for old, new in SUBST:
            if old in t:
                set_text(e, ptext(e).replace(old, new))
                n_sub += 1
                break

print('整段替换:', n_full, ' 子串替换:', n_sub)
assert n_full == len(REPL), f'整段替换缺 {len(REPL)-n_full} 处'
assert n_sub >= 2, f'子串替换仅 {n_sub} 处'

out = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
with zipfile.ZipFile(SRC) as zin, zipfile.ZipFile(DST + '.tmp', 'w', zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        data = out if item.filename == 'word/document.xml' else zin.read(item.filename)
        zout.writestr(item, data)
os.replace(DST + '.tmp', DST)

# 回读自检
with zipfile.ZipFile(DST) as z:
    body2 = etree.fromstring(z.read('word/document.xml')).find(q('body'))
allt = ''.join(t.text or '' for t in body2.iter(q('t')))
assert '顶部 RGB 大灯' in allt
assert '驱动 LED1 呼吸' not in allt
print('SAVED:', DST)
