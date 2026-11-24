# -*- coding: utf-8 -*-
import zipfile, shutil, os
from lxml import etree
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
def q(t): return W + t

SRC = r"D:/STM32_Project/docs/串口数据控制测试_接口文档.docx"
DST = r"D:/STM32_Project/docs/串口数据控制测试_接口文档_标准版V2.docx"

with zipfile.ZipFile(SRC) as z:
    xml = z.read('word/document.xml')
root = etree.fromstring(xml)
body = root.find(q('body'))

def text_of(el):
    return ''.join(t.text or '' for t in el.iter(q('t')))

def set_text(el, txt):
    ts = list(el.iter(q('t')))
    if ts:
        ts[0].text = txt
        for t in ts[1:]:
            t.text = ''
        return
    # 空单元格/空段落：没有任何 w:t，造一个 <w:r><w:t> 放进第一个 w:p
    ps = el.findall('.//' + q('p')) or ([el] if etree.QName(el).localname == 'p' else [])
    assert ps, 'no paragraph to hold text: %s' % etree.QName(el).localname
    r = etree.SubElement(ps[0], q('r'))
    t = etree.SubElement(r, q('t'))
    t.text = txt

def headings():
    out = []
    for e in body:
        if etree.QName(e).localname != 'p':
            continue
        st = e.find(q('pPr') + '/' + q('pStyle'))
        if st is not None and st.get(q('val')) in ('00001e', '000020', '000021'):
            t = text_of(e).strip()
            if t:
                out.append(t)
    return out

before_h = headings()
before_p = len([e for e in body if etree.QName(e).localname == 'p'])
before_t = len([e for e in body if etree.QName(e).localname == 'tbl'])

def find_p(pred):
    for e in body:
        if etree.QName(e).localname == 'p' and pred(text_of(e).strip()):
            return e
    raise RuntimeError('paragraph not found')

def find_tbl(pred):
    for e in body:
        if etree.QName(e).localname == 'tbl' and pred(e):
            return e
    raise RuntimeError('table not found')

def rows(tbl):
    return tbl.findall(q('tr'))

def cells(tr):
    return [''.join(t.text or '' for t in tc.iter(q('t'))) for tc in tr.findall(q('tc'))]

# ---------- 1. 修订记录加一行 ----------
rev = find_tbl(lambda t: text_of(t).startswith('日期版本'))
r1 = rows(rev)[1]
new = etree.fromstring(etree.tostring(r1))
vals = ['2026.09.16', 'V2.0',
        '按任务书标准版对齐：协议帧带异或校验；功能聚焦左右转向灯、蜂鸣器与 KEY2 呼吸灯；删除 OLED/字库/存储相关章节', '']
for tc, v in zip(new.findall(q('tc')), vals):
    set_text(tc, v)
r1.addnext(new)

# ---------- 2. 简介文字 ----------
set_text(find_p(lambda t: t.startswith('本文档适用于基于 STM32F103ZET6')),
 '本文档适用于基于 STM32F103ZET6 与 STM32F10x 标准外设库 V3.6 的串口数据控制测试工程（任务书标准版）。'
 '覆盖任务书要求：上位机按 55 FF 03 06 控制单元 开关状态 异或校验 的帧格式下发命令，'
 '下位机校验通过后控制左转向灯、右转向灯与蜂鸣器；LED1 呼吸灯由板上 KEY2 按键开关。')
set_text(find_p(lambda t: t.startswith('本工程为嵌入式培训课程串口章节')),
 '本工程为嵌入式培训课程串口章节的实践任务。上位机通过串口助手按自定义协议下发数据帧，'
 '下位机逐字节解析并做异或校验，校验通过后控制左转向灯、右转向灯与蜂鸣器。')

# ---------- 3. 系统组成表 ----------
syscomp = find_tbl(lambda t: text_of(t).startswith('组成实现'))
for tr in rows(syscomp):
    cs = cells(tr)
    if cs and cs[0] == '下位机':
        set_text(tr.findall(q('tc'))[2], '解析协议帧并做异或校验，控制板载外设')
    if cs and cs[0] == '执行与显示':
        set_text(tr.findall(q('tc'))[2], 'LED1、LED2、有源蜂鸣器、按键 KEY2')

# ---------- 4. 分层设计表 ----------
layer = find_tbl(lambda t: text_of(t).startswith('层次目录'))
for tr in rows(layer):
    cs = cells(tr)
    if cs and cs[0] == '应用层':
        set_text(tr.findall(q('tc'))[2], '初始化、协议解析与校验、命令分发、状态维护、按键扫描')

# ---------- 5. 模块设计表：删 OLED/字库/存储，改 LED 行，加按键/呼吸灯行 ----------
mods = find_tbl(lambda t: text_of(t).startswith('模块源文件'))
removed_rows = 0
for tr in list(rows(mods)):
    txt = text_of(tr)
    if any(k in txt for k in ('oled_drv', 'font8x8', 'flash_drv')):
        mods.remove(tr)
        removed_rows += 1
assert removed_rows == 3, 'module rows removed=%d' % removed_rows
led_row = None
for tr in rows(mods):
    cs = cells(tr)
    if cs and cs[0] == 'LED 与 RGB 模块':
        led_row = tr
        set_text(tr.findall(q('tc'))[0], 'LED 驱动模块')
        set_text(tr.findall(q('tc'))[2], 'LED1、LED2 的开关与翻转')
        set_text(tr.findall(q('tc'))[3], 'PG14、PG15')
assert led_row is not None
def add_mod_row(after_tr, vals):
    nr = etree.fromstring(etree.tostring(after_tr))
    for tc, v in zip(nr.findall(q('tc')), vals):
        set_text(tc, v)
    after_tr.addnext(nr)
    return nr
r2 = add_mod_row(led_row, ['按键扫描模块', 'key_drv.c / .h', 'KEY1~KEY3 按键扫描、消抖与单击事件', 'PG3、PG4、PG5'])
add_mod_row(r2, ['呼吸灯 PWM 模块', 'pwm_drv.c / .h', 'TIM2 定时中断 + 软件 PWM 驱动 LED1 呼吸', 'PG14'])

# ---------- 6. 初始化清单：删 RGB/OLED 行，加 Key/Breath 行 ----------
p = find_p(lambda t: t.startswith('RGB_Init();'))
p.getparent().remove(p)
set_text(find_p(lambda t: t.startswith('OLED_Init();')), 'Key_Init();    // 按键扫描，KEY2 触发呼吸灯')
p_usart = find_p(lambda t: t.startswith('Usart_Init('))
br = etree.fromstring(etree.tostring(p_usart))
set_text(br, 'Breath_Init(); // TIM2 呼吸灯初始化（不启动）')
p_usart.addnext(br)

# ---------- 7. 协议帧格式表：改说明 + 加校验行 ----------
proto = find_tbl(lambda t: text_of(t).startswith('字段字节数取值'))
for tr in rows(proto):
    cs = cells(tr)
    if cs and cs[0] == '数据域长度':
        set_text(tr.findall(q('tc'))[2], 'N（控制命令帧固定 0x03）')
    if cs and cs[0] == '数据':
        set_text(tr.findall(q('tc'))[2], '见 3.1.2')
        set_text(tr.findall(q('tc'))[3], '控制命令帧为 控制单元＋开关状态')
        chk = etree.fromstring(etree.tostring(tr))
        for tc, v in zip(chk.findall(q('tc')),
                         ['校验', '1', '1 字节异或值', '帧头0^帧头1^长度^功能字^数据各字节异或']):
            set_text(tc, v)
        tr.addnext(chk)

# ---------- 8. 校验说明段 ----------
set_text(find_p(lambda t: t.startswith('数据域后面允许再跟校验字节')),
 '校验字节是前面所有字节的异或：帧头0 ^ 帧头1 ^ 长度 ^ 功能字 ^ 控制单元 ^ 开关状态。'
 '解析器收满一帧后先验校验，不对则丢弃本帧并回发错误提示，不影响后续帧的接收。'
 '帧内相邻两字节间隔超过 200ms 视为半截帧，直接丢弃并重新等待帧头。')

# ---------- 9. 功能字表：删 0x07/0x08，改示例 ----------
funcs = find_tbl(lambda t: text_of(t).startswith('功能字含义'))
for tr in list(rows(funcs)):
    cs = cells(tr)
    if cs and cs[0] in ('0x07', '0x08'):
        funcs.remove(tr)
    if cs and cs[0] == '0x06':
        set_text(tr.findall(q('tc'))[3], '55 FF 03 06 02 01 AC 蜂鸣器开（02 00 AD 关）')

# ---------- 10. 控制单元表：删 0x03 LED 行 ----------
units = find_tbl(lambda t: text_of(t).startswith('控制单元设备'))
for tr in list(rows(units)):
    cs = cells(tr)
    if cs and cs[0] == '0x03':
        units.remove(tr)

# ---------- 11. 删存储操作码表 + 引导句 ----------
p = find_p(lambda t: t == '存储操作码取值如下：')
p.getparent().remove(p)
store_tbl = find_tbl(lambda t: text_of(t).startswith('操作码含义'))
store_tbl.getparent().remove(store_tbl)

# ---------- 12. 命令语义段 / 快捷命令段 / 状态上报 ----------
set_text(find_p(lambda t: t.startswith('控制命令按帧内的开关状态字节')),
 '控制命令按帧内的开关状态字节直接设置设备：0x00 为关、0x01 为开。'
 '转向灯打开后以 500ms 为半周期闪烁。呼吸灯运行期间 LED1 由 TIM2 中断独占，'
 '串口的左转向灯命令会先退出呼吸模式再执行。校验不通过的命令不执行，回发错误提示。')
set_text(find_p(lambda t: t.startswith('为方便调试，固件额外支持 ASCII')),
 '为方便调试，固件额外支持 ASCII 快捷命令（仅在空闲态识别，不影响协议帧）：'
 'L1/L0 开/关左转向灯，R1/R0 开/关右转向灯，D1/D0 开/关蜂鸣器；'
 '字母后不跟数字则翻转一次（如单独发 L）。呼吸灯由板上 KEY2 按键开关。')
set_text(find_p(lambda t: t.startswith('STATUS LEFT_TURN')),
 'STATUS  LEFT_TURN=ON  RIGHT_TURN=OFF  BEEP=OFF  BREATH=OFF')

# ---------- 13. 人机交互模块引言 ----------
set_text(find_p(lambda t: t.startswith('本模块包含板载 LED、RGB 灯条')),
 '本模块包含板载 LED、有源蜂鸣器、按键与呼吸灯四类外设，向上提供开关、翻转、'
 '事件扫描与呼吸控制等接口，应用层不接触任何 GPIO 或定时器寄存器。')

# ---------- 14. 整段删除 3.2.3+3.2.4（OLED/字库）与 3.4（存储） ----------
def delete_range(start_pred, stop_pred):
    els = list(body)
    si = ti = None
    for i, e in enumerate(els):
        t = text_of(e).strip()
        if si is None and etree.QName(e).localname == 'p' and start_pred(t):
            si = i
        if ti is None and etree.QName(e).localname == 'p' and stop_pred(t):
            ti = i
    assert si is not None and ti is not None and si < ti, (si, ti)
    n = 0
    for e in els[si:ti]:
        body.remove(e)
        n += 1
    return n

n1 = delete_range(lambda t: t.startswith('3.2.3 OLED'),
                  lambda t: t.startswith('3.3 串口通信模块'))
n2 = delete_range(lambda t: t.startswith('3.4 存储模块'),
                  lambda t: t.startswith('3.5 系统时基模块'))
print('deleted elements:', n1, n2)

# ---------- 15. 插入新章节 3.2.3 呼吸灯与按键驱动接口 ----------
h33 = find_p(lambda t: t.startswith('3.3 串口通信模块'))
h_buzz = find_p(lambda t: t.startswith('3.2.2 蜂鸣器驱动接口'))

def clone_heading(anchor_h, txt):
    nh = etree.fromstring(etree.tostring(anchor_h))
    set_text(nh, txt)
    return nh

def clone_para(anchor_txt, txt):
    ap = find_p(lambda t: t.startswith(anchor_txt))
    np_ = etree.fromstring(etree.tostring(ap))
    set_text(np_, txt)
    return np_

def clone_fn_table(src_tbl, proto, desc, param, ret):
    nt = etree.fromstring(etree.tostring(src_tbl))
    trs = nt.findall(q('tr'))
    assert len(trs) == 4, 'template table rows=%d' % len(trs)
    for tr, v in zip(trs, [proto, desc, param, ret]):
        set_text(tr.findall(q('tc'))[1], v)
    return nt

h_new = clone_heading(h_buzz, '3.2.3 呼吸灯与按键驱动接口')
i1 = clone_para('板上是 5V 有源蜂鸣器',
 '呼吸灯用 TIM2 定时中断加软件 PWM 实现：PG14 没有定时器通道，无法输出硬件 PWM，'
 '因此由 TIM2 产生 20kHz 中断，在中断里按占空比翻转引脚，等效出 200Hz 的 PWM 波；'
 '占空比每 20ms 调整 2 级，一亮一暗 2 秒一个来回。按键由主循环每 10ms 扫描一次，'
 '消抖后产生单击事件，KEY2 用于开关呼吸灯。')
fn_led = find_tbl(lambda t: text_of(t).startswith('函数原型void LED_Init'))
i2 = clone_para('板上是 5V 有源蜂鸣器', '呼吸灯控制接口如下：')
t1 = clone_fn_table(fn_led, 'void Breath_Start(void)',
                    '启动 LED1 呼吸灯（TIM2 软件 PWM 独占 PG14）', '无', '无')
i3 = clone_para('板上是 5V 有源蜂鸣器', '呼吸灯停止接口如下：')
t2 = clone_fn_table(fn_led, 'void Breath_Stop(void)',
                    '停止呼吸灯，LED1 熄灭，TIM2 中断关闭', '无', '无')
i4 = clone_para('板上是 5V 有源蜂鸣器', '按键扫描接口如下：')
t3 = clone_fn_table(fn_led, 'KeyEvent Key_Scan(void)',
                    '扫描 KEY1~KEY3，消抖后返回按键事件（每 10ms 调用一次）', '无',
                    'KeyEvent 事件：KEY_EVT_NONE / KEY_EVT_KEY1_CLICK / KEY_EVT_KEY2_CLICK / KEY_EVT_KEY3_CLICK')
for el in [h_new, i1, i2, t1, i3, t2, i4, t3]:
    h33.addprevious(el)

# ---------- 16. 时基章节重编号 ----------
set_text(find_p(lambda t: t.startswith('3.5 系统时基模块')), '3.4 系统时基模块及接口说明')
set_text(find_p(lambda t: t.startswith('3.5.1 SysTick')), '3.4.1 SysTick 接口')

# ---------- 17. 缩略语表去掉 OLED/Flash 行 ----------
abbr = find_tbl(lambda t: text_of(t).startswith('缩略语英文'))
for tr in list(rows(abbr)):
    txt = text_of(tr)
    if ('OLED' in txt) or ('Flash' in txt) or ('SSD1306' in txt):
        abbr.remove(tr)

# ---------- 自检 ----------
after_h = headings()
after_p = len([e for e in body if etree.QName(e).localname == 'p'])
after_t = len([e for e in body if etree.QName(e).localname == 'tbl'])
allowed_gone = ('3.2.3 OLED', '3.2.4', '3.4.1 内部', '3.4.2', '3.4 存储模块及接口说明')
gone = [h for h in before_h if h not in after_h and not h.startswith('3.5')]
bad = [h for h in gone if not any(h.startswith(k) for k in allowed_gone)]
assert not bad, 'unexpected heading loss: %r' % bad
assert '3.2.3 呼吸灯与按键驱动接口' in after_h, after_h
assert '3.4 系统时基模块及接口说明' in after_h and '3.4.1 SysTick 接口' in after_h
assert not any(('OLED' in h) or ('字库' in h) or ('存储模块' in h) for h in after_h), after_h
assert after_t == before_t - 18 + 3, 'tables %d->%d' % (before_t, after_t)
print('headings %d->%d  paras %d->%d  tables %d->%d' % (len(before_h), len(after_h), before_p, after_p, before_t, after_t))
for h in after_h:
    print(' H:', h)

# ---------- 保存 ----------
out = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
tmp = DST + '.tmp'
with zipfile.ZipFile(SRC) as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        data = out if item.filename == 'word/document.xml' else zin.read(item.filename)
        zout.writestr(item, data)
os.replace(tmp, DST)
print('SAVED:', DST)
