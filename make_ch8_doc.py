# -*- coding: utf-8 -*-
"""在 chapter7 接口文档基础上生成 chapter8 的接口文档：

  D:/STM32_Project/docs/串口数据控制测试_接口文档.docx
      -> D:/STM32_Project/docs/ADC内部温度采集_接口文档.docx

做法：全部用「克隆现有段落 / 表格再改文字」的方式，
      标题样式、编号文本、表格边框都与模板完全一致，不依赖任何自动编号。
"""
import copy
import zipfile
from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
XML = 'http://www.w3.org/XML/1998/namespace'
q = lambda t: '{%s}%s' % (W, t)

SRC = r'D:/STM32_Project/docs/串口数据控制测试_接口文档.docx'
DST = r'D:/STM32_Project/docs/ADC内部温度采集_接口文档.docx'

zin = zipfile.ZipFile(SRC)
root = etree.fromstring(zin.read('word/document.xml'))
body = root.find(q('body'))


def set_text(elem, text):
    ts = list(elem.iter(q('t')))
    if not ts:
        raise RuntimeError('no w:t')
    ts[0].text = text
    ts[0].set('{%s}space' % XML, 'preserve')
    for t in ts[1:]:
        t.text = ''
    return elem


def cell_text(tc):
    return ' '.join(''.join(t.text or '' for t in tc.iter(q('t'))).split())


set_cell = set_text


def clone(elem, text=None):
    new = copy.deepcopy(elem)
    if text is not None:
        set_text(new, text)
    return new


paras = [ch for ch in body if ch.tag == q('p')]
tbls = [ch for ch in body if ch.tag == q('tbl')]

H3_T = paras[167]           # "3.5 系统时基模块及接口说明"（克隆模板）
H4_T = paras[169]           # "3.5.1 SysTick 接口"
BODY_T = paras[168]         # 普通正文段
CODE_T = paras[132]         # 代码样式段（typedef enum ...）
IFACE_T = tbls[41]          # 4x2 接口表模板
INFO3_T = tbls[39]          # 3 列表格模板
LAST = tbls[43]             # 文档最后一个元素

log = []

# ============================ 第一部分：改既有内容 ============================

set_text(paras[0], 'ADC 内部温度采集方案文档（接口）')
log.append('封面标题')

tr = tbls[0].findall(q('tr'))[1]
set_cell(tr.findall(q('tc'))[0], '2026.09.16')
set_cell(tr.findall(q('tc'))[1], 'V1.0')
set_cell(tr.findall(q('tc'))[2], '首次发布：内部温度采集、呼吸灯、按键交互与温度数据上报')
log.append('修订记录')

set_text(paras[93],
         '本文档用于说明 ADC 内部温度采集工程的模块划分、对外接口与使用方法，'
         '作为开发、调试与验收的统一依据。本工程在串口数据控制测试工程的基础上，'
         '新增了芯片内部温度采集、按键触发呼吸灯、温度数据屏显与串口上报三部分功能。')
set_text(paras[95],
         '本文档适用于基于 STM32F103ZET6 与 STM32F10x 标准外设库 V3.6 的 ADC 内部温度采集工程，'
         '覆盖串口协议控制板载外设、串口文本屏显与内部 Flash 掉电保存三项既有功能，'
         '以及本次新增的要求：每 2 秒采集一次芯片内部温度传感器、按下 KEY2 让左转向灯呈现呼吸灯效果、'
         '每次采样完成后把 ADC 原始值、换算后的模拟量与温度值同时显示到 OLED 并通过串口发送到 PC。')
set_text(paras[97],
         '本工程为嵌入式培训课程 ADC 章节的实践任务，在串口章节工程的基础上扩展而来。'
         '温度传感器做在芯片内部，接在 ADC1 的通道 16 上，打开 TSVREFE 使能位后即可直接转换；'
         '温度按任务书给定公式 {(V25 - Vsense) / Avg_Slope} + 25 换算，其中 V25 = 1.43V、'
         'Avg_Slope = 4.3mV/℃。左转向灯接在 PG14，该引脚没有任何定时器复用功能，'
         '因此呼吸灯用 TIM2 定时中断产生软件 PWM 来实现。')
log.append('1.1 前言 / 1.2 范围 / 1.3 背景')

for abbr, en, cn in (('ADC', 'Analog-to-Digital Converter', '模数转换器，把模拟电压转换成数字量'),
                     ('PWM', 'Pulse Width Modulation', '脉冲宽度调制，用占空比调节输出功率，呼吸灯即靠它实现')):
    row = clone(tbls[1].findall(q('tr'))[-1])
    cs = row.findall(q('tc'))
    set_cell(cs[0], abbr)
    set_cell(cs[1], en)
    set_cell(cs[2], cn)
    tbls[1].append(row)
log.append('1.4 缩略语 +2 行')

for col, val, note in (
    ('温度采集', '芯片内部温度传感器', '接在 ADC1 的通道 16，无需任何外部器件，每 2 秒采样一次'),
    ('按键输入', '板载 KEY1 / KEY2 / KEY3', 'KEY2 触发左转向灯呼吸灯，KEY1 切换显示页，KEY3 立即采样'),
):
    row = clone(tbls[2].findall(q('tr'))[-1])
    cs = row.findall(q('tc'))
    set_cell(cs[0], col)
    set_cell(cs[1], val)
    set_cell(cs[2], note)
    tbls[2].append(row)
log.append('2.1 系统组成 +2 行')

for tc in tbls[3].iter(q('tc')):
    if cell_text(tc).startswith('把外设细节封装成函数接口'):
        set_cell(tc, '把外设细节封装成函数接口，向上屏蔽寄存器操作；本工程共 9 个驱动：'
                     'LED/RGB、蜂鸣器、OLED、串口、内部 Flash、SysTick、ADC、按键、软件 PWM')
log.append('2.2 分层设计')

for name, files, duty, pins in (
    ('ADC 采集模块', 'adc_drv.c / .h',
     'ADC1 通道 16 内部温度传感器采集、Vrefint 反推 VDDA、原始值换算电压与温度', '无（内部通道）'),
    ('按键模块', 'key_drv.c / .h',
     'KEY1 / KEY2 / KEY3 上拉输入、20ms 消抖与单击事件识别', 'PG3、PG4、PG5'),
    ('呼吸灯模块', 'pwm_drv.c / .h',
     'TIM2 定时中断产生软件 PWM，在左转向灯上输出呼吸效果', 'PG14（与 LED1 同一引脚）'),
):
    row = clone(tbls[4].findall(q('tr'))[-1])
    cs = row.findall(q('tc'))
    set_cell(cs[0], name)
    set_cell(cs[1], files)
    set_cell(cs[2], duty)
    set_cell(cs[3], pins)
    tbls[4].append(row)
log.append('2.3 模块设计 +3 行')

anchor = paras[114]
for line in ('Adc_Init(); // ADC1 + 内部温度传感器（通道 16）',
             'Key_Init(); // KEY1 / KEY2 / KEY3 上拉输入',
             'Breath_Init(); // TIM2 软件 PWM 时基（默认关闭）'):
    new = clone(paras[114], line)
    anchor.addnext(new)
    anchor = new
log.append('3.1 初始化序列 +3 行')

set_text(paras[115],
         '主循环采用中断收加主循环处理的结构。串口接收全部在 USART1_IRQHandler 里完成，'
         '中断只负责把收到的字节塞进环形缓冲，不做任何耗时操作；主循环不断把缓冲里的字节取出来喂给协议解析器，'
         '同时按固定周期完成按键扫描（10ms）、温度采集（2s）、转向灯闪烁与呼吸灯占空比调整。'
         '各任务的节奏互不干扰，长数据帧也不会把其他功能堵住。')

loop_lines = ['while (1) {',
              '    while (Usart_ReadByte(&rxByte) != 0) { ParseByte(rxByte); } // 串口协议解析',
              '    if ((uint32_t)(now - s_lastKeyMs) >= 10u) { HandleKey(Key_Scan()); } // 按键 10ms 扫描',
              '    if ((uint32_t)(now - s_lastSampleMs) >= 2000u) { DoSample(); } // 温度 2s 采集并上报',
              '    TurnSignalService(); // 转向灯 500ms 闪烁',
              '    Breath_Service(); // 呼吸灯每 20ms 调一次占空比',
              '}']
cur = paras[116]
set_text(cur, loop_lines[0])
for line in loop_lines[1:]:
    new = clone(paras[116], line)
    cur.addnext(new)
    cur = new
log.append('3.1 主循环代码块')

set_text(paras[123],
         '为方便调试，固件额外支持 ASCII 快捷命令（仅在空闲态识别，不影响协议帧）：'
         '字母 L/R/B/D 后跟数字 1/0 直接开/关 左转向灯/右转向灯/蜂鸣器/LED 灯条，'
         '省略数字则翻转一次（如 B1 开蜂鸣器、B0 关、单独 B 翻转）；'
         'T 加文本立即屏显并保存，回车或换行结束；'
         'S/C/P 分别为保存 Flash、清除 Flash、重新读回恢复；A 立即采集一次温度并上报。')

paras[123].addnext(clone(paras[123],
    '温度数据每 2 秒自动上报一次，格式固定为三行，在串口助手里直接输入 A 也可以立刻触发一次上报：'
    'Current ADC_Value is 2018 / Current Voltage is 1.626 / Current Temperature is 30.52。'
    '其中 ADC 值为 0~4095 的原始值，电压单位为 V（3 位小数），温度单位为 ℃（2 位小数）；'
    '当读数超出传感器量程（-40~125℃）时，温度一行打印 --，表示本次读数不可信。'))
log.append('3.1.2 快捷命令 + 温度上报格式')

set_text(paras[126], 'STATUS LEFT_TURN=1 RIGHT_TURN=0 BEEP=0 LED=1 BREATH=0')
for tc in tbls[6].iter(q('tc')):
    if cell_text(tc).startswith('55 FF 06 07 HELLO'):
        set_cell(tc, '55 FF 06 07 HELLO 屏显到文本页并保存')
log.append('3.1.3 状态上报 / 0x07 说明')

set_text(paras[128],
         '本模块包含板载 LED、RGB 灯条、有源蜂鸣器和 OLED 显示屏四类外设，'
         '向上提供开关、翻转、显示等接口，应用层不接触任何 GPIO 或 I2C 寄存器；'
         '左转向灯的呼吸效果由 3.8 节的软件 PWM 模块提供。')
log.append('3.2 模块引言')

# ---------- OLED：地址自检 + 排版表 ----------
for tc in tbls[19].iter(q('tc')):
    if cell_text(tc).startswith('7 位地址 0x3C'):
        set_cell(tc, '上电自动识别：先试 0x78，再试 0x7A，哪个有应答就用哪个（见 OLED_Probe）')

t = clone(IFACE_T)
for r, (k, v) in zip(t.findall(q('tr')),
                     (('函数原型', 'uint8_t OLED_Probe(void)'),
                      ('描述', '探测屏是否存在并自动选择从机地址：先试 0x78、再试 0x7A，命中后所有读写都用该地址；只发一个地址字节，不修改显存，对屏无副作用'),
                      ('参数', 'void'),
                      ('返回值', '1 = 0x78 有应答；2 = 0x7A 有应答；0 = 两个地址都没有应答'))):
    cs = r.findall(q('tc'))
    set_cell(cs[0], k)
    set_cell(cs[1], v)
tbls[27].addnext(t)
log.append('3.2.3 OLED_Probe 接口表')

set_text(paras[140], '屏分温度数据页与文本页两个显示页，每页 4 行、每行 16 个字符：')
t28 = tbls[28]
rows = t28.findall(q('tr'))
proto = rows[-1]
for r in rows[1:]:
    t28.remove(r)
for c0, c1, c2 in (
    ('温度页 第 0 行', 'ADCvalue: 2018', 'ADC 原始值，范围 0~4095，右对齐显示'),
    ('温度页 第 1 行', 'Voltage :1.626', '换算后的模拟量，单位 V，3 位小数'),
    ('温度页 第 2 行', 'Temp    :30.52', '温度值，单位 ℃，2 位小数；超出量程显示 --.--'),
    ('温度页 第 3 行', 'L0 R0 B0 D0 BRTH', '设备状态与模式提示：BRTH 呼吸灯、TEXT 文本页、RST / NEW 开机来源'),
    ('文本页 第 0、1 行', '串口下发的文本', '32 个字符分两行显示'),
    ('文本页 第 2 行', '提示信息', 'BOOTING...、CTRL OK、BREATH ON、TEXT SAVED、FLASH CLEARED 等'),
    ('文本页 第 3 行', '与温度页第 3 行相同', '两页共用设备状态栏'),
):
    row = clone(proto)
    cs = row.findall(q('tc'))
    set_cell(cs[0], c0)
    set_cell(cs[1], c1)
    set_cell(cs[2], c2)
    t28.append(row)
log.append('3.2.3 屏显排版表重写')

# ============================ 第二部分：新增 3.6 / 3.7 / 3.8 ============================


def add_para(template, text):
    global LAST
    p = clone(template, text)
    LAST.addnext(p)
    LAST = p
    return p


def add_iface(proto, desc, param, ret):
    global LAST
    t = clone(IFACE_T)
    for r, (k, v) in zip(t.findall(q('tr')),
                         (('函数原型', proto), ('描述', desc), ('参数', param), ('返回值', ret))):
        cs = r.findall(q('tc'))
        set_cell(cs[0], k)
        set_cell(cs[1], v)
    LAST.addnext(t)
    LAST = t
    return t


def add_info3(header, rows_data):
    """header: 三列表头；rows_data: [(c0, c1, c2), ...]"""
    global LAST
    t = clone(INFO3_T)
    trs = t.findall(q('tr'))
    proto = copy.deepcopy(trs[-1])
    for r in trs:
        t.remove(r)
    for cells in [header] + list(rows_data):
        row = copy.deepcopy(proto)
        cs = row.findall(q('tc'))
        set_cell(cs[0], cells[0])
        set_cell(cs[1], cells[1])
        set_cell(cs[2], cells[2])
        t.append(row)
    LAST.addnext(t)
    LAST = t
    return t


def add_h3(text):
    return add_para(H3_T, text)


def add_h4(text):
    return add_para(H4_T, text)


def add_body(text):
    return add_para(BODY_T, text)


# ---------------- 3.6 ADC 模块 ----------------
add_h3('3.6 ADC 模块及接口说明')
add_body('本模块负责采集芯片内部温度传感器，输出 ADC 原始值、换算后的模拟量与温度值。'
         '温度传感器做在芯片内部，接在 ADC1 的通道 16 上，不需要任何外部器件，'
         '因此本工程没有新增任何硬件连接。')

add_body('内部温度传感器的关键设置如下：')
add_info3(('项目', '取值', '说明'), [
    ('转换通道', 'ADC1 的通道 16（ADC_Channel_16）',
     '通道 16 是内部温度传感器；内部通道只有 ADC1 能选，ADC2 / ADC3 选不到'),
    ('使能位', 'ADC_CR2 的 TSVREFE 位',
     '由 ADC_TempSensorVrefintCmd(ENABLE) 打开；不打开这个位，通道 16 读回来恒为 0'),
    ('采样时间', '239.5 个 ADC 周期',
     '数据手册要求内部温度传感器采样时间不小于 17.1us，ADCCLK 12MHz 下约 20us'),
    ('ADC 时钟', 'PCLK2 六分频 = 12MHz', '不超过 ADC 允许的最高 14MHz'),
    ('参考电压', '用通道 17 的 Vrefint 反推 VDDA',
     '板上 3V3 存在偏差，先用内部 1.20V 基准算出真实 VDDA 再换算，结果更准'),
    ('软件平均', '连续采样 8 次取平均', '内部通道本体噪声比外部通道大，平均后读数更稳'),
    ('采集周期', '2000ms', '由主循环基于 SysTick 时基判断，不使用阻塞延时'),
])

add_h4('3.6.1 ADC 采集接口')
add_iface('void Adc_Init(void)',
          '使能 ADC1 时钟并把 ADCCLK 设为 12MHz，配置独立模式、单次转换、右对齐，'
          '打开 TSVREFE 使能内部通道，最后做复位校准与校准',
          'void', 'void')
add_iface('uint16_t Adc_ReadChannelAvg(uint8_t channel, uint8_t times)',
          '软件触发读指定通道 times 次，返回平均值；读内部温度传感器时 channel 传 ADC_Channel_16',
          'channel：通道号 0~17；times：平均次数', '平均后的 ADC 原始值（0~4095）')
add_iface('uint16_t Adc_GetVddaMv(void)',
          '读通道 17 的内部 1.20V 基准，反推实际 VDDA；读数明显不合理（超出 2.8~3.6V）时退回 3300mV',
          'void', 'VDDA，单位 mV')
add_iface('uint32_t Adc_RawToVoltageMv(uint16_t raw, uint16_t vddaMv)',
          '把 ADC 原始值换算成电压：Vsense = raw x VDDA / 4096',
          'raw：ADC 原始值；vddaMv：参考电压，单位 mV', '换算后的电压，单位 mV')
add_iface('int32_t Adc_RawToTempX100(uint16_t raw, uint16_t vddaMv)',
          '按任务书公式把读数换算成温度：温度 = (V25 - Vsense) / Avg_Slope + 25；'
          '全程整数运算，不引入浮点库',
          'raw：ADC 原始值；vddaMv：参考电压，单位 mV', '温度 x100（3052 表示 30.52℃）')
add_iface('void Adc_SampleTemp(AdcTempSample_t *sample)',
          '一次完整采样：取 VDDA、读通道 16、换算电压与温度，并判断结果是否在传感器量程内',
          'sample：结果结构体指针', 'void（结果写入 sample）')

add_h4('3.6.2 温度换算与量程检查')
add_body('换算公式（任务书给定）：温度(℃) = {(V25 - Vsense) / Avg_Slope} + 25，'
         '其中 V25 典型值 1.43V、Avg_Slope 典型值 4.3mV/℃。温度传感器是负温度系数，'
         '温度越高输出电压越低，所以 25℃ 时 Vsense 恰好是 1.43V。')
add_body('为避免引入浮点运算，固件把结果放大 100 倍后用整数计算：'
         '温度 x100 = 2500 + (1430 - Vsense_mV) x 1000 / 43。')
add_info3(('项目', '取值', '说明'), [
    ('V25', '1430 mV', '25℃ 时传感器输出的典型电压，即公式里的 V25'),
    ('Avg_Slope', '4.3 mV/℃', '温度系数，代码里用 43 表示 4.3mV/℃ 的十倍整数化'),
    ('Vsense', 'AD 值 x VDDA / 4096', '12 位 ADC，满量程 4096'),
    ('有效量程', '-40 ~ 125 ℃', '数据手册给出的传感器量程，超出即判为读数不可信'),
    ('超量程处理', '屏上显示 --.--，串口打印 --',
     '例如 TSVREFE 没打开时通道读回 0，公式会算出 357℃ 这类明显错误的值，直接屏蔽掉'),
    ('结果结构体', 'AdcTempSample_t',
     '成员：rawValue（原始值）、vddaMv（本次参考电压）、voltageMv（电压 mV）、tempX100（温度 x100）、valid（是否可信）'),
])

# ---------------- 3.7 按键模块 ----------------
add_h3('3.7 按键模块及接口说明')
add_body('板上三个功能按键都是一端接地、一端接 IO，IO 平时被 10K 电阻上拉到 3V3，按下为低电平。'
         '驱动把引脚配置为上拉输入，主循环每 10ms 调用一次扫描函数，'
         '内部对每个按键做 20ms 消抖，确认按下后立即返回一次单击事件。')

add_body('按键功能分配如下：')
add_info3(('按键', '引脚', '功能'), [
    ('KEY1', 'PG3', '切换 OLED 显示页（温度数据页 / 文本页）'),
    ('KEY2', 'PG4', '左转向灯（红色 LED1 / PG14）呼吸灯 开 / 关'),
    ('KEY3', 'PG5', '立即采集一次温度并上报，不用等 2 秒周期'),
])

add_h4('3.7.1 按键驱动接口')
add_iface('void Key_Init(void)',
          '把 PG3 / PG4 / PG5 配置为上拉输入，并初始化三个按键的消抖状态',
          'void', 'void')
add_iface('KeyEvent Key_Scan(void)',
          '扫描三个按键并返回本次产生的按键事件；内部做 20ms 消抖，按下沿触发一次事件；'
          '建议每 10ms 调用一次',
          'void',
          'KEY_EVT_NONE / KEY_EVT_KEY1_CLICK / KEY_EVT_KEY2_CLICK / KEY_EVT_KEY3_CLICK')

add_body('按键事件枚举定义如下：')
add_para(CODE_T, 'typedef enum { KEY_EVT_NONE = 0, KEY_EVT_KEY1_CLICK, KEY_EVT_KEY2_CLICK, KEY_EVT_KEY3_CLICK } KeyEvent;')
add_body('一次按下只上报一次事件，不放着不管也不会重复触发。呼吸模式下再按一次 KEY2 即退出呼吸；'
         '若此时用串口或快捷命令手动控制左转向灯，固件会先自动退出呼吸模式再执行命令，'
         '不会出现两处同时写同一个引脚的情况。')

# ---------------- 3.8 软件 PWM（呼吸灯） ----------------
add_h3('3.8 软件 PWM（呼吸灯）模块及接口说明')
add_body('本模块在左转向灯（红色 LED1，PG14）上产生呼吸效果。'
         '需要注意的是，PG14 在 STM32F103 上的复用功能是 FSMC_A25，没有任何定时器通道，'
         '无法像常规做法那样用 TIM_OCxInit 输出硬件 PWM。'
         '因此这里改用 TIM2 定时中断做时间基准，在中断里自己计数、自己翻转引脚，等效出一个 PWM 波形，'
         '也就是软件 PWM。')

add_body('参数选择如下：')
add_info3(('项目', '取值', '说明'), [
    ('定时器', 'TIM2', '挂在 APB1 上，APB1 分频系数不为 1 时定时器时钟为 72MHz'),
    ('中断频率', '20 kHz', '重装值 = 72 000 000 / 20 000 - 1 = 3599'),
    ('亮度级数', '100 级', '中断里 0~99 循环计数，与占空比比较后决定引脚电平'),
    ('PWM 频率', '200 Hz', '20kHz / 100 级；高于 100Hz，肉眼看不到闪烁'),
    ('调光节奏', '每 20ms 调 2 级', '单程 1s，一亮一暗一个来回约 2s，呼吸感自然'),
    ('中断开销', '约占 3% CPU', '只在引脚电平真的变化时才写 GPIO；退出呼吸模式立即关闭定时器'),
])

add_h4('3.8.1 呼吸灯接口')
add_iface('void Breath_Init(void)',
          '配置 TIM2 时基与更新中断，配置 NVIC；初始化后定时器处于关闭状态，不会产生中断',
          'void', 'void')
add_iface('void Breath_Start(void)',
          '从最暗开始呼吸：亮度等级清零、启动 TIM2 更新中断',
          'void', 'void')
add_iface('void Breath_Stop(void)',
          '停止呼吸：关闭 TIM2 更新中断、熄灭左转向灯，把引脚控制权交回应用层',
          'void', 'void')
add_iface('uint8_t Breath_IsActive(void)',
          '查询当前是否处于呼吸模式；转向灯闪烁服务据此跳过 LED1，避免两处抢同一个引脚',
          'void', '1 = 正在呼吸；0 = 未呼吸')
add_iface('void Breath_Service(void)',
          '主循环调用：每 20ms 按"渐亮到最亮再渐暗到最暗"的方向调整占空比',
          'void', 'void')

add_body('呼吸模式下左转向灯由本模块独占，转向灯闪烁服务会自动跳过 LED1；'
         '通过串口 0x06 功能字或快捷命令手动控制左转向灯时，固件会先退出呼吸模式，'
         '保证任意时刻只有一个模块在驱动该引脚。')

# ============================ 落盘 ============================
out = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
zout = zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED)
for item in zin.infolist():
    data = zin.read(item.filename)
    if item.filename == 'word/document.xml':
        data = out
    zout.writestr(item, data)
zout.close()
zin.close()

print('== 改动清单 ==')
for x in log:
    print('   -', x)
print('== 新增章节 ==')
for x in ('3.6 ADC 模块及接口说明（6 张接口表 + 2 张说明表）',
          '3.7 按键模块及接口说明（2 张接口表 + 1 张功能分配表）',
          '3.8 软件 PWM（呼吸灯）模块及接口说明（5 张接口表 + 1 张参数表）'):
    print('   -', x)
print('SAVED ->', DST)
