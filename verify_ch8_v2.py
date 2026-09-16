# -*- coding: utf-8 -*-
"""校验 chapter8 接口文档 v2：结构完整性 + 标题未被正文覆盖 + 关键内容到位。"""
import zipfile
import sys
from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
q = lambda t: '{%s}%s' % (W, t)
HS = {'00001e': 'H1', '000020': 'H2', '000021': 'H3', '000022': 'H4', '000026': 'TT'}


def load(p):
    z = zipfile.ZipFile(p)
    root = etree.fromstring(z.read('word/document.xml'))
    return root, list(root.find(q('body')))


def para(e):
    return ''.join(x.text or '' for x in e.iter(q('t'))).strip()


def style(e):
    ppr = e.find(q('pPr'))
    if ppr is None:
        return None
    s = ppr.find(q('pStyle'))
    return s.get(q('val')) if s is not None else None


v1r, v1 = load('docs/ADC内部温度采集_接口文档.docx')
v2r, v2 = load('docs/ADC内部温度采集_接口文档_v2.docx')

print('v1 段落/表格: %d/%d   v2 段落/表格: %d/%d'
      % (len(v1), v1r.getroottree() is None or len(v1r.findall('.//' + q('tbl'))),
         len(v2), len(v2r.findall('.//' + q('tbl')))))

# ---- 1. 标题未被正文覆盖（标题段落文本过长即为伤亡） ----
print('\n[1] 标题段完整性检查')
bad = 0
for i, e in enumerate(v2):
    st = style(e)
    if st in HS and st != '000026':
        t = para(e)
        if len(t) > 40 and not t[0].isdigit():
            print('   !! 标题被覆盖 b%d [%s] %s' % (i, HS[st], t[:60]))
            bad += 1
if not bad:
    print('   OK 无标题段被正文覆盖')

# ---- 2. 原有标题是否全部保留 ----
print('\n[2] 原文档标题保留情况')
old = {para(e) for e in v1 if style(e) in ('00001e', '000020', '000021') and para(e)}
new = {para(e) for e in v2 if style(e) in ('00001e', '000020', '000021') and para(e)}
miss = sorted(x for x in old if x not in new)
print('   缺失标题:', miss if miss else '无')

# ---- 3. 目录树 ----
print('\n[3] v2 目录树')
for e in v2:
    st = style(e)
    if st in HS:
        t = para(e)
        if t:
            ind = {'H1': '', 'H2': '  ', 'H3': '    ', 'H4': '      '}.get(HS[st], '')
            print('   %s%s %s' % (ind, HS[st], t))

# ---- 4. 关键内容 ----
print('\n[4] 关键内容抽查')
full = ''.join(x.text or '' for x in v2r.iter(q('t')))
keys = ['calOffsetX100', 'RGB2_Init', 'RGB2_Set', 'Adc_GetVddaMv', 'Breath_GetDuty',
        'Breath_GetPwmCnt', 'OLED_ShowStringBig', 'OLED_ShowChinese', 'OLED_ShowCNString',
        'Adc_SetCalOffsetX100', 'Adc_GetCalOffsetX100',
        'PE2', 'PE3', 'PE4', 'PG0', 'PG1', 'PG2', '彩虹', 'GBK', '丢弃首次',
        '1800', '4600', '-FL07F800', 'g_cnFont16', 'CN_CAL_HINT', '16x16',
        '去极值', '239.5', 'V25', '4.3mV', 'TSVREFE', '1.43']
for k in keys:
    print('   %-22s %s' % (k, 'OK' if k in full else '** MISSING **'))

# ---- 5. 编号连续性（3.x 小节） ----
print('\n[5] 3.x 小节编号序列')
import re
seq = []
for e in v2:
    if style(e) in ('000020', '000021'):
        t = para(e)
        m = re.match(r'^(\d+(?:\.\d+)*)\s', t)
        if m:
            seq.append(m.group(1))
print('   ' + ' '.join(seq))
