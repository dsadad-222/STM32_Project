# -*- coding: utf-8 -*-
"""接口文档 标准版V2.1 -> V2.2：删十六进制协议帧与异或校验，改为 L/R/D+0/1 简洁命令"""
import zipfile, os
from lxml import etree
import copy

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
def q(t): return W + t

SRC = r"D:/STM32_Project/docs/串口数据控制测试_接口文档_标准版V2.1.docx"
DST = r"D:/STM32_Project/docs/串口数据控制测试_接口文档_标准版V2.2.docx"

with zipfile.ZipFile(SRC) as z:
    root = etree.fromstring(z.read('word/document.xml'))
body = root.find(q('body'))

def ptext(e):
    return ''.join(t.text or '' for t in e.iter(q('t')))

def set_text(el, txt):
    ts = list(el.iter(q('t')))
    if not ts:
        r = etree.SubElement(el, q('r'))
        t = etree.SubElement(r, q('t')); t.text = txt
        return
    ts[0].text = txt
    for t in ts[1:]:
        t.text = ''

def set_cell(tc, txt):
    # 单元格：改第一个段落文本，清空同格其余段落
    ps = tc.findall(q('p'))
    set_text(ps[0], txt)
    for p in ps[1:]:
        set_text(p, '')

def find_p(pred):
    for e in body.iter(q('p')):
        if pred(ptext(e).strip()):
            return e
    raise RuntimeError('paragraph not found')

def find_tbl(pred):
    for e in body.iter(q('tbl')):
        if pred(ptext(e)):
            return e
    raise RuntimeError('table not found')

def row_cells(tr):
    return tr.findall(q('tc'))

n = [0]
def sub(el, old, new):
    t = ptext(el)
    if old in t:
        set_text(el, t.replace(old, new))
        n[0] += 1
        return True
    return False

# ---------- 1. 修订记录：V2.0 行克隆出 V2.2 行 ----------
rev = find_tbl(lambda t: t.startswith('日期版本'))
v20_row = None
for tr in rev.findall(q('tr')):
    if 'V2.0' in ptext(tr):
        v20_row = tr
        break
assert v20_row is not None
new_row = copy.deepcopy(v20_row)
for tc, v in zip(row_cells(new_row), ['2026.09.16', 'V2.2',
        '删除十六进制协议帧与异或校验，串口命令简化为 L/R/D + 0/1 两字符 ASCII 命令', '']):
    set_cell(tc, v)
v20_row.addnext(new_row)

# ---------- 2. 简介两段 ----------
set_text(find_p(lambda t: t.startswith('本文档适用于基于 STM32F103ZET6')),
 '本文档适用于基于 STM32F103ZET6 与 STM32F10x 标准外设库 V3.6 的串口数据控制测试工程（简洁命令版）。'
 '上位机用串口助手按 115200-8-N-1 发送两字符命令（L/R/D + 0/1），'
 '下位机解析后控制左转向灯、右转向灯与蜂鸣器。')
set_text(find_p(lambda t: t.startswith('本工程为嵌入式培训课程串口章节')),
 '本工程为嵌入式培训课程串口章节的实践任务。命令就是两个普通字符，不设帧头与校验：'
 '字母选设备（L 左转向灯、R 右转向灯、D 蜂鸣器），数字定开关（1 开、0 关），'
 '解析通过后控制对应外设。')

# ---------- 3. 系统组成表 / 分层表 ----------
syscomp = find_tbl(lambda t: t.startswith('组成实现'))
for tr in syscomp.findall(q('tr')):
    t = ptext(tr)
    if '下发协议帧' in t:
        set_cell(row_cells(tr)[2], '按 115200-8-N-1 打开虚拟串口，手工或脚本下发命令')
    if '异或校验' in t:
        set_cell(row_cells(tr)[2], '解析 ASCII 命令，控制板载外设')
layer = find_tbl(lambda t: t.startswith('层次目录'))
for tr in layer.findall(q('tr')):
    if '命令分发' in ptext(tr):
        set_cell(row_cells(tr)[2], '初始化、串口命令解析、命令分发、状态维护、按键扫描')

# ---------- 4. 时基引言 / 初始化注释 ----------
sub(find_p(lambda t: '供闪烁与帧超时使用' in t), '供闪烁与帧超时使用', '供闪烁与命令超时使用')
sub(find_p(lambda t: '半截帧超时' in t and '转向灯 500ms' in t),
    '协议解析 200ms 半截帧超时', '命令解析 3 秒超时')

# ---------- 5. 3.1.1 标题 + 帧格式表 -> 命令表 ----------
set_text(find_p(lambda t: t == '3.1.1 协议帧格式'), '3.1.1 串口命令格式')
fmt = find_tbl(lambda t: t.startswith('字段字节数取值'))
rows = fmt.findall(q('tr'))
new_rows = [
    ['命令字母', '1', '单个字符 L / R / D', '选设备：L 左转向灯、R 右转向灯、D 蜂鸣器'],
    ['命令数字', '1', '单个字符 0 / 1', '0 = 关，1 = 开'],
    ['示例', '—', 'L1 / R0 / D1', '左灯开 / 右灯关 / 蜂鸣器开'],
    ['翻转', '—', '只发字母不发数字', '该设备开变关、关变开（如单独发 L）'],
    ['超时', '—', '字母后 3 秒内无数字', '字母作废，重新等下一条命令'],
    ['容错', '—', '其他字符', '不认识的字母回发 ERROR: unknown cmd，不影响后续命令'],
]
# 表头重写
for tc, v in zip(row_cells(rows[0]), ['字段', '长度', '取值', '说明']):
    set_cell(tc, v)
# 复用现有行，不够就克隆最后一行
while len(rows) - 1 < len(new_rows):
    clone = copy.deepcopy(rows[-1])
    rows[-1].addnext(clone)
    rows = fmt.findall(q('tr'))
for tr, vals in zip(rows[1:], new_rows):
    for tc, v in zip(row_cells(tr), vals):
        set_cell(tc, v)
for tr in rows[1 + len(new_rows):]:
    fmt.remove(tr)

# ---------- 6. 校验段 -> 命令时序段 ----------
set_text(find_p(lambda t: t.startswith('校验字节是前面所有字节的异或')),
 '命令没有帧头和校验字节，就是两个普通字符。解析器空闲时收到 L/R/D 记下设备，'
 '等到的下一个字符若为 0/1 直接执行并回发状态；若为其他字符则按"翻转一次"执行，'
 '该字符再按空闲态重新解析。字母后 3 秒内没等到数字，字母作废。')

# ---------- 7. 3.1.2 标题 + 删功能字表 + 设备对照表 ----------
set_text(find_p(lambda t: t == '3.1.2 功能字与命令示例'), '3.1.2 命令与设备对照')
ftbl = find_tbl(lambda t: t.startswith('功能字含义'))
ftbl.getparent().remove(ftbl)
sub(find_p(lambda t: t == '控制单元取值如下：'), '控制单元取值如下：', '设备与命令对照如下：')
dev = find_tbl(lambda t: t.startswith('控制单元设备引脚'))
for tr in dev.findall(q('tr')):
    cs = row_cells(tr)
    t = ptext(tr)
    if t.startswith('控制单元'):
        set_cell(cs[0], '命令字母')
    elif '0x00' in t:
        set_cell(cs[0], 'L')
    elif '0x01' in t:
        set_cell(cs[0], 'R')
    elif '0x02' in t:
        set_cell(cs[0], 'D')

# ---------- 8. 执行说明 / 删 ASCII 补充段 ----------
set_text(find_p(lambda t: t.startswith('控制命令按帧内的开关状态字节')),
 '命令中的数字位直接设置设备：1 为开、0 为关。转向灯打开后以 500ms 为半周期闪烁。'
 '呼吸灯运行期间左转向灯由 TIM2 中断独占，串口的 L 命令会先退出呼吸模式再执行。'
 '不认识的字母不执行，回发 ERROR: unknown cmd。')
p_ascii = find_p(lambda t: t.startswith('为方便调试，固件额外支持 ASCII'))
p_ascii.getparent().remove(p_ascii)

# ---------- 9. 自检（修订记录的历史行允许保留旧描述） ----------
rev_txt = ptext(find_tbl(lambda t: t.startswith('日期版本')))
allt = ''.join(t.text or '' for t in body.iter(q('t')))
body_only = allt.replace(rev_txt, '', 1)
assert '55 FF' not in body_only, '仍残留 55 FF'
assert '异或' not in body_only, '仍残留 异或'
assert '0x06' not in body_only and '功能字' not in body_only, '仍残留功能字'
assert 'L/R/D + 0/1' in body_only
assert 'ERROR: unknown cmd' in body_only
assert '帧内' not in body_only and '半截帧' not in body_only
print('自检通过，文本替换', n[0], '处')

out = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
with zipfile.ZipFile(SRC) as zin, zipfile.ZipFile(DST + '.tmp', 'w', zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        data = out if item.filename == 'word/document.xml' else zin.read(item.filename)
        zout.writestr(item, data)
os.replace(DST + '.tmp', DST)
print('SAVED:', DST)
