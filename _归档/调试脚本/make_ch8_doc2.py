# -*- coding: utf-8 -*-
"""chapter8 接口文档 v2 —— 在 09:56 版基础上做增量更新。

源：D:/STM32_Project/docs/ADC内部温度采集_接口文档.docx
目标：D:/STM32_Project/docs/ADC内部温度采集_接口文档_v2.docx

v2 相对 v1 的改动（09:56 之后新增/修正的全部内容）：
  修正：左转向灯的真实硬件是左 RGB 灯珠（PG0/PG1/PG2），不是 LED1/PG14
  修正：VDDA 有效窗口由 2.8~3.6V 放宽到 1800~4600mV
  修正：采样算法补「丢弃首次转换 + 去极值平均」
  修正：存储结构体 reserved -> calOffsetX100，校验长度 sizeof-2
  修正：OLED 排版改为 16px 大字 + 中文提示，小数点加粗
  新增：3.2.5 16x16 中文字库 / 3.4.3 数据页保护 / 3.6.3 温度单点标定
        3.9 转向灯模块（右灯彩虹）/ 3.10 中文消息与串口中文
做法：全部「克隆现有段落/表格再改文字」，样式与手打编号原样保留。
"""
import copy
import zipfile
from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
XML = 'http://www.w3.org/XML/1998/namespace'
q = lambda t: '{%s}%s' % (W, t)

SRC = r'D:/STM32_Project/docs/ADC内部温度采集_接口文档.docx'
DST = r'D:/STM32_Project/docs/ADC内部温度采集_接口文档_v2.docx'

zin = zipfile.ZipFile(SRC)
root = etree.fromstring(zin.read('word/document.xml'))
body = root.find(q('body'))
B = list(body)
# 本文档由模板克隆而来，body 末尾没有独立 sectPr（sectPr 嵌在中间某段的 pPr 里），
# 因此统一用「body 最后一个元素」作为文末锚点，新增章节依次 addnext 追加在文末。
sectPr = body.find(q('sectPr'))
if sectPr is None:
    sectPr = list(body)[-1]
log = []


def set_text(elem, text):
    ts = list(elem.iter(q('t')))
    if not ts:
        raise RuntimeError('no w:t')
    ts[0].text = text
    ts[0].set('{%s}space' % XML, 'preserve')
    for t in ts[1:]:
        t.text = ''
    return elem


set_cell = set_text


def clone(elem, text=None):
    new = copy.deepcopy(elem)
    if text is not None:
        set_text(new, text)
    return new


def _donor_run(elem):
    """在元素范围内找一个带 w:t 的 run，用于给空单元格补一个可写的 run。"""
    for tc in elem.iter(q('tc')):
        for r in tc.iter(q('r')):
            if list(r.iter(q('t'))):
                return r
    return None


def set_cells(elem, values):
    """按顺序写一行的各个单元格；空单元格没有 w:t，先从同行的 run 借一个再写。"""
    cs = elem.findall(q('tc'))
    dr = _donor_run(elem)
    for c, v in zip(cs, values):
        if not list(c.iter(q('t'))):
            p = c.find(q('p'))
            if p is None or dr is None:
                continue
            nr = copy.deepcopy(dr)
            for t in nr.iter(q('t')):
                t.text = ''
            ppr = p.find(q('pPr'))
            if ppr is not None:
                ppr.addnext(nr)
            else:
                p.insert(0, nr)
        set_cell(c, v)
    return elem


def clone_row(tbl, values):
    row = clone(tbl.findall(q('tr'))[-1])
    set_cells(row, values)
    tbl.append(row)
    return row


def fill_row(tbl, idx, values):
    """把表格第 idx 行替换成由首个数据行克隆来的新行（避免空行没有 w:t）"""
    rows = tbl.findall(q('tr'))
    new = clone(rows[1])
    set_cells(new, values)
    tbl.replace(rows[idx], new)
    return new


def cell_text(tc):
    return ' '.join(''.join(t.text or '' for t in tc.iter(q('t'))).split())


# ---------------- 模板引用（插入前先取好，避免索引漂移） ----------------
H3_T = B[225]        # "3.6 ADC 模块及接口说明"
H4_T = B[229]        # "3.6.1 ADC 采集接口"
BODY_T = B[226]      # 普通正文段
CODE_T = B[207]      # 代码样式段 "typedef struct"
IFACE_T = B[259]     # 4x2 接口表
INFO_T = B[228]      # 3 列表格（带表头）
A_8X8 = B[184]       # 3.2.5 插入锚点（8x8 字库末尾）
A_STORE = B[218]     # 3.4.3 插入锚点
A_ADC = B[239]       # 3.6.3 插入锚点

# ============================================================
# 第一部分：修正既有内容
# ============================================================

# ---- 修订记录：填 V1.1 ----
fill_row(B[36], 2, ['2026.09.16', 'V1.1',
                    '补充：温度单点标定、OLED 大字与中文显示、串口中文提示、'
                    '左转向灯呼吸、右转向灯彩虹闪烁、下载数据页保护', ''])
log.append('封面修订记录 +V1.1')

# ---- 1.1 前言 ----
set_text(B[94],
         '本文档用于说明 ADC 内部温度采集工程的模块划分、对外接口与使用方法，'
         '作为开发、调试与验收的统一依据。本工程在串口数据控制测试工程的基础上，'
         '新增了芯片内部温度采集、温度单点标定、左转向灯呼吸效果、右转向灯彩虹闪烁、'
         'OLED 大字与中文显示、串口中文提示六部分功能。')
log.append('1.1 前言')

# ---- 1.2 范围 ----
set_text(B[96],
         '本文档适用于基于 STM32F103ZET6 与 STM32F10x 标准外设库 V3.6 的 ADC 内部温度采集工程，'
         '覆盖串口协议控制板载外设、串口文本屏显与内部 Flash 掉电保存三项既有功能，'
         '以及本次新增的要求：每 2 秒采集一次芯片内部温度传感器并支持单点标定、'
         '按下 KEY2 让左转向灯呈现呼吸灯效果、打开右转向灯时车灯呈现彩虹轮转闪烁、'
         '每次采样完成后把 ADC 原始值、换算后的模拟量与温度值同时显示到 OLED 并通过串口发送到 PC。')
log.append('1.2 范围')

# ---- 1.3 背景 ----
set_text(B[98],
         '本工程为嵌入式培训课程 ADC 章节的实践任务，在串口章节工程的基础上扩展而来。'
         '温度传感器做在芯片内部，接在 ADC1 的通道 16 上，打开 TSVREFE 使能位后即可直接转换；'
         '温度按任务书给定公式 {(V25 - Vsense) / Avg_Slope} + 25 换算，其中 V25 = 1.43V、'
         'Avg_Slope = 4.3mV/℃。板上左右各有一颗四脚 RGB 灯珠构成车灯，'
         '左灯珠接在 PG0、PG1、PG2 上，右灯珠接在 PE2、PE3、PE4 上，三路均为高电平点亮；'
         '左转向灯的呼吸效果用 TIM2 定时中断产生软件 PWM 实现，'
         '右转向灯在闪烁的同时按六种颜色依次轮转，形成彩虹效果。')
log.append('1.3 背景')

# ---- 1.4 缩略语 +1 行 ----
clone_row(B[100], ['GBK', 'Chinese Internal Code Specification',
                   '汉字编码，一个汉字两个字节；本工程的中文字库索引与串口中文都按它编码'])
log.append('1.4 缩略语 +GBK')

# ---- 2.1 系统组成 +2 行 ----
clone_row(B[105], ['中文显示', '16x16 点阵字库 + 串口 GBK 编码',
                   '界面提示与串口提示都用中文显示，方便现场演示与验收'])
clone_row(B[105], ['转向灯', '左、右两颗 RGB 灯珠',
                   '左转向灯呼吸、右转向灯彩虹闪烁，同时点亮旁边的板载小灯'])
log.append('2.1 系统组成 +中文显示/转向灯')

# ---- 2.2 分层设计：驱动数量 ----
for tc in B[107].iter(q('tc')):
    if cell_text(tc).startswith('把外设细节封装成函数接口'):
        set_cell(tc, '把外设细节封装成函数接口，向上屏蔽寄存器操作；本工程共 11 个驱动与 2 份字库：'
                     'LED/RGB、蜂鸣器、OLED、串口、内部 Flash、SysTick、ADC、按键、软件 PWM、'
                     'RGB 转向灯珠、中文消息，以及 8x8 与 16x16 两份字库数据')
log.append('2.2 分层设计')

# ---- 2.3 模块设计：改 3 行 ----
for tr in B[110].findall(q('tr')):
    c0 = tr.findall(q('tc'))[0]
    name = cell_text(c0)
    if name == 'LED 与 RGB 模块':
        set_cells(tr, ['LED 与 RGB 模块', 'led_drv.c / .h',
                       'LED1、LED2 与左右两颗 RGB 转向灯珠的开关、翻转与颜色设置',
                       'PG14、PG15、PG0、PG1、PG2、PE2、PE3、PE4'])
    elif name == '字库':
        set_cells(tr, ['字库', 'font8x8.c / .h、cn_font16.c / .h',
                       '8x8 点阵 ASCII 字模与 16x16 点阵中文字模（收录 60 个汉字）', '无'])
    elif name == '呼吸灯模块':
        set_cells(tr, ['呼吸灯模块', 'pwm_drv.c / .h',
                       'TIM2 定时中断产生软件 PWM，在左转向灯珠上输出呼吸效果',
                       'PG0、PG1、PG2（左 RGB 灯珠）'])
clone_row(B[110], ['中文消息', 'cn_msg.h',
                   '界面提示与串口提示的全部中文文本（GBK 转义常量，共 25 条）', '无'])
log.append('2.3 模块设计：改 LED/字库/呼吸灯，+中文消息')

# ---- 3.1 初始化序列 +1 行 ----
new = clone(B[115], 'RGB2_Init(); // 右转向灯珠（PE2 / PE3 / PE4）')
B[115].addnext(new)
log.append('3.1 初始化序列 +RGB2_Init')

# ---- 3.1 主循环说明 ----
set_text(B[123],
         '主循环采用中断收加主循环处理的结构。串口接收全部在 USART1_IRQHandler 里完成，'
         '中断只负责把收到的字节塞进环形缓冲，不做任何耗时操作；主循环不断把缓冲里的字节取出来喂给协议解析器，'
         '同时按固定周期完成按键扫描（10ms）、温度采集（2s）、转向灯闪烁（含右灯彩虹换色）'
         '与呼吸灯占空比调整。各任务的节奏互不干扰，长数据帧也不会把其他功能堵住。')

# ---- 3.1.2 快捷命令 ----
set_text(B[141],
         '为方便调试，固件额外支持 ASCII 快捷命令（仅在空闲态识别，不影响协议帧）：'
         '字母 L/R/B/D 后跟数字 1/0 直接开/关 左转向灯/右转向灯/蜂鸣器/LED 灯条，'
         '省略数字则翻转一次（如 B1 开蜂鸣器、B0 关、单独 B 翻转）；'
         'T 加文本立即屏显并保存，回车或换行结束；'
         'S/C/P 分别为保存 Flash、清除 Flash、重新读回恢复；A 立即采集一次温度并上报；'
         'K 后跟温度值（如 K29）把当前室温写入 Flash 作为单点标定偏移，只发 K 则按 25℃ 标定；'
         'Z 清除标定偏移，回到手册公式的原始值。')
log.append('3.1.2 快捷命令（补 K / Z）')

# ---- 3.1.2 温度上报格式 ----
set_text(B[142],
         '温度数据每 2 秒自动上报一次，在串口助手里直接输入 A 也可以立刻触发一次上报。'
         '前几行沿用既有格式：Current ADC_Value is 1449 / Current Voltage is 1.159 / '
         'Current Temperature is 35.93 / Current VDDA is 3276 mV (Vrefint raw 1500)，'
         '其后追加一行中文小结：小结 : 温度 35.9 C  电压 1.159 V  原始值 1449  芯片结温 (已标定/未标定)。'
         'ADC 值为 0~4095 的原始值，电压单位为 V（3 位小数），温度单位为 ℃（2 位小数）；'
         '当读数超出传感器量程（-40~125℃）时，温度一行打印 --，表示本次读数不可信；'
         'VDDA 由通道 17 的内部基准反推，超过 3700mV 时额外打印一行供电告警。'
         '中文行按 GBK 编码发送，串口助手的接收编码需要设为 GBK 或 ANSI。')
log.append('3.1.2 温度上报格式（补 VDDA 行与中文小结）')

# ---- 3.2 模块引言 ----
set_text(B[147],
         '本模块包含板载 LED、左右两颗 RGB 转向灯珠、有源蜂鸣器和 OLED 显示屏四类外设，'
         '向上提供开关、翻转、颜色设置与显示等接口，应用层不接触任何 GPIO 或 I2C 寄存器；'
         '左转向灯的呼吸效果由 3.8 节的软件 PWM 模块提供，'
         '右转向灯的彩虹效果由 3.9 节的转向灯模块提供。')
log.append('3.2 模块引言')

# ---- 3.2.1 引言 ----
set_text(B[149],
         'LED1（PG14）与 LED2（PG15）是板载小指示灯；板上左右各有一颗四脚 RGB 灯珠构成车灯，'
         '左灯珠接在 PG0、PG1、PG2 上（RGB_Init / RGB_Set），'
         '右灯珠接在 PE2、PE3、PE4 上（RGB2_Init / RGB2_Set），三路都是高电平点亮。'
         '板上另有一个三针 RGB 灯条座（J6），其信号与左灯珠共用同一组引脚。')
log.append('3.2.1 引言（左灯珠/右灯珠/灯条座）')

# ---- 3.2.1 补 RGB2 接口表 2 张 ----
t = clone(IFACE_T)
for r, (k, v) in zip(t.findall(q('tr')),
                     (('函数原型', 'void RGB2_Init(void)'),
                      ('描述', '把右转向灯珠的 PE2 / PE3 / PE4 配置为推挽输出并熄灭；'
                               '上电时先置为灭，避免上电瞬间误亮'),
                      ('参数', 'void'),
                      ('返回值', 'void'))):
    set_cells(r, [k, v])
B[155].addnext(t)
last_rgb2 = t

t = clone(IFACE_T)
for r, (k, v) in zip(t.findall(q('tr')),
                     (('函数原型', 'void RGB2_Set(RGB_TypeDef color)'),
                      ('描述', '设置右转向灯珠的颜色；颜色枚举与 RGB_Set 完全相同，'
                               '由转向灯服务在每次闪烁时轮换一种颜色'),
                      ('参数', 'color：RGB_NONE / RGB_R / RGB_G / RGB_B / '
                               'RGB_YELLOW / RGB_CYAN / RGB_MAGENTA / RGB_ALL'),
                      ('返回值', 'void'))):
    set_cells(r, [k, v])
last_rgb2.addnext(t)
log.append('3.2.1 +RGB2_Init / RGB2_Set 两张接口表')

# ---- 3.2.1 枚举文本（补 CYAN / MAGENTA） ----
set_text(B[158],
         'typedef enum { RGB_NONE = 0, RGB_R, RGB_G, RGB_B, RGB_YELLOW, '
         'RGB_CYAN, RGB_MAGENTA, RGB_ALL } RGB_TypeDef;')
log.append('3.2.1 枚举补 CYAN/MAGENTA')

# ---- 3.2.3 屏显排版 ----
set_text(B[179],
         '屏分温度数据页与文本页两个显示页。温度页上半屏用 16x16 大字显示温度，'
         '下半屏用 8x8 小字显示采样值与设备状态；文本页保留两行 32 字符的文本，'
         '下半屏用 16x16 大字显示中文提示：')
t28 = B[180]
rows = t28.findall(q('tr'))
proto = rows[-1]
for r in rows[1:]:
    t28.remove(r)
for c0, c1, c2 in (
    ('温度页 上半屏', '温度 35.9C',
     '16x16 大字：两个汉字「温度」占 2 个字宽，数值与单位占 5 个字宽，一行共 8 个大字'),
    ('温度页 第 3 行', 'ADC 1449  1.159 V',
     'ADC 原始值与换算电压左右分栏、定宽右对齐，数值变化时整体不抖动'),
    ('温度页 第 4 行', 'L0 R0 B0 D0 CAL',
     '设备状态与模式提示：L/R 左右转向灯、B 蜂鸣器、D 灯条；尾部 CAL 表示已标定、'
     'BRTH 表示正在呼吸、RST / NEW 标识开机来源'),
    ('文本页 第 1、2 行', '串口下发的文本',
     '32 个字符分两行显示，每行 16 个 8x8 字符'),
    ('文本页 下半屏', '中文提示',
     '16x16 汉字居中显示，例如「温度已标定」「呼吸灯已开」「串口已保存」'),
    ('说明', '小数点加粗',
     '大字模式下句点按 6x6 实心方块绘制（写入显存 0xFC），避免"35.9C"的小数点在'
     '0.86 寸小屏上被忽略；8x8 小字模式保持不变'),
):
    row = clone(proto)
    set_cells(row, [c0, c1, c2])
    t28.append(row)
log.append('3.2.3 屏显排版表重写（16px 大字 + 中文）')

# ---- 3.4 存储引言：补数据页被擦的背景 ----
set_text(B[197],
         '文本字段是定长字段而不是 C 字符串，固定占 32 字节，不足部分用空格补齐，'
         '有效字符个数由 textLen 给出。这样存储和显示都不必关心结尾有没有结束符。'
         '数据页位于主存储区最后一页，Keil 的下载范围如果覆盖到这一页，'
         '每次下载都会把它擦掉，因此本工程对下载范围做了限制，详见 3.4.3 节。')
log.append('3.4 存储引言（提下载范围）')

# ---- 3.4.1 宏表 +1 行 ----
clone_row(B[204], ['ADC_CAL_OFFSET_X100_LIMIT', '12000',
                   '温度单点标定偏移的上下限（±120℃），超出即被夹紧，防止误输入把读数带飞'])
log.append('3.4.1 宏表 +标定限幅')

# ---- 3.4.2 结构体代码块 ----
set_text(B[213], '    int16_t  calOffsetX100;   /* 温度单点标定偏移（×100℃，0 = 未标定）*/')
set_text(B[214], '    uint16_t checksum;')
log.append('3.4.2 结构体 reserved -> calOffsetX100')

# ---- 3.4.2 字段表 ----
for tr in B[217].findall(q('tr')):
    if cell_text(tr.findall(q('tc'))[0]) == 'reserved':
        set_cells(tr, ['calOffsetX100', 'int16_t',
                       'ADC 温度单点标定偏移（×100℃），0 表示未标定；'
                       '复用原来的占位字段，结构体总长度仍是 48 字节'])
log.append('3.4.2 字段表 reserved 行')

set_text(B[218],
         '字段按 4 字节对齐排列，结构体不会有隐式填充，总长度 48 字节；'
         '校验范围是结构体长度减去末尾 2 字节，即除 checksum 自身以外的全部字段，'
         '标定偏移也被纳入累加和，任何一处被改动都会被校验发现。')
log.append('3.4.2 校验范围 -2 字节')

# ---- 3.6 传感器关键设置表：改 2 行 + 加 2 行 ----
for tr in B[228].findall(q('tr')):
    key = cell_text(tr.findall(q('tc'))[0])
    if key == '参考电压':
        set_cells(tr, ['参考电压', '用通道 17 的 Vrefint 反推 VDDA',
                       '板上 3V3 存在偏差，先用内部 1.20V 基准算出真实 VDDA 再换算；'
                       '反推结果落在 1800~4600mV 窗内才采用，明显不合理时退回 3300mV'])
    elif key == '软件平均':
        set_cells(tr, ['采样算法', '丢弃首次转换 + 去极值平均',
                       '切换通道后第一次转换的采样保持电容尚未建立，读数偏低，必须丢弃；'
                       '其余 8 次去掉一个最大值和一个最小值再取平均，压制内部通道的噪声'])
clone_row(B[228], ['采集周期', '2000ms', '由主循环基于 SysTick 时基判断，不使用阻塞延时'])
clone_row(B[228], ['单点标定', '存入 Flash 的 calOffsetX100',
                   '芯片内部传感器没有出厂校准值，用室温做一次单点标定把读数平移到环境温度附近，'
                   '详见 3.6.3 节'])
log.append('3.6 关键设置表：改参考电压/采样算法，+采集周期/单点标定')

# ---- 3.6.1 接口表描述修正 ----
for r in B[231].findall(q('tr')):
    if cell_text(r.findall(q('tc'))[0]) == '描述':
        set_cells(r, ['描述', '软件触发读指定通道 times 次，丢弃首次转换、去掉一个最大值与'
                             '一个最小值后返回平均值；读内部温度传感器时 channel 传 ADC_Channel_16'])
for r in B[232].findall(q('tr')):
    if cell_text(r.findall(q('tc'))[0]) == '描述':
        set_cells(r, ['描述', '读通道 17 的内部 1.20V 基准，反推实际 VDDA；'
                             '读数超出 1800~4600mV 时退回 3300mV，并用结构体里的 vrefRaw 字段留作诊断'])
log.append('3.6.1 Adc_ReadChannelAvg / Adc_GetVddaMv 描述修正')

# ---- 3.6.2 说明表 +2 行 ----
clone_row(B[239], ['结果结构体', 'AdcTempSample_t',
                   '成员：rawValue（原始值）、vrefRaw（Vrefint 原始值，诊断用）、'
                   'vddaMv（本次参考电压）、voltageMv（电压 mV）、tempX100（温度 x100）、valid（是否可信）'])
clone_row(B[239], ['标定叠加时机', '先判量程、后加偏移',
                   '先用未标定的温度判断是否在 -40~125℃ 内，再叠加标定偏移，'
                   '避免标定值把有效采样误判成超量程'])
log.append('3.6.2 说明表 +结果结构体/标定时机')

# ---- 3.7 按键功能表：KEY2 行修正 ----
for tr in B[243].findall(q('tr')):
    if cell_text(tr.findall(q('tc'))[0]) == 'KEY2':
        set_cells(tr, ['KEY2', 'PG4', '左转向灯（左上角 RGB 灯珠 PG0 / PG1 / PG2）呼吸灯 开 / 关'])
log.append('3.7 按键表 KEY2 行修正为 RGB 灯珠')

set_text(B[249],
         '一次按下只上报一次事件，不放着不管也不会重复触发。呼吸模式下再按一次 KEY2 即退出呼吸；'
         '若此时用串口或快捷命令手动控制左转向灯，固件会先自动退出呼吸模式再执行命令，'
         '不会出现两处同时写同一组引脚的情况。')
log.append('3.7 按键说明（改为同一组引脚）')

# ---- 3.8 呼吸灯引言重写 ----
set_text(B[251],
         '本模块在左转向灯上产生呼吸效果。左转向灯是板上左上角那颗四脚 RGB 灯珠（L1），'
         '三色分别接在 PG0、PG1、PG2 上，共阴接法、高电平点亮。'
         '选择软件 PWM 而不是硬件 PWM 的原因有两个：一是这组引脚在 F103 上没有连到任何定时器通道，'
         '无法用 TIM_OCxInit 输出硬件 PWM；二是只有这一组引脚需要呼吸，'
         '用一个定时中断同时驱动三路，比额外占用三个定时器通道更省资源。'
         '做法是 TIM2 定时中断做时间基准，在中断里自己计数、自己写 GPIO 的 BSRR 寄存器，'
         '等效出一个 PWM 波形，也就是软件 PWM。')
log.append('3.8 呼吸灯引言重写（RGB 灯珠）')

# ---- 3.8 参数表 +1 行 & 改 1 行 ----
for tr in B[253].findall(q('tr')):
    key = cell_text(tr.findall(q('tc'))[0])
    if key == '中断开销':
        set_cells(tr, ['中断开销', '约占 3% CPU',
                       '只在电平真的变化时才写 GPIO；退出呼吸模式立即关闭定时器'])
clone_row(B[253], ['驱动对象', 'PG0、PG1、PG2（左 RGB 灯珠）',
                   '中断里用 BSRR 同时驱动三路，红、绿、蓝以相同占空比输出，'
                   '视觉上呈现由暗到亮的单色呼吸'])
log.append('3.8 参数表 +驱动对象')

# ---- 3.8.1 补 2 张诊断接口表 ----
t = clone(IFACE_T)
for r, (k, v) in zip(t.findall(q('tr')),
                     (('函数原型', 'uint8_t Breath_GetDuty(void)'),
                      ('描述', '诊断接口：返回当前呼吸亮度等级，配合串口日志判断调光逻辑是否在运行'),
                      ('参数', 'void'),
                      ('返回值', '当前占空比，0~100' ))):
    set_cells(r, [k, v])
B[259].addnext(t)
last_breath = t

t = clone(IFACE_T)
for r, (k, v) in zip(t.findall(q('tr')),
                     (('函数原型', 'uint8_t Breath_GetPwmCnt(void)'),
                      ('描述', '诊断接口：返回 PWM 周期内的计数值；它与占空比都在变化，'
                               '说明定时中断与调光逻辑都正常'),
                      ('参数', 'void'),
                      ('返回值', '0~99 的周期计数值'))):
    set_cells(r, [k, v])
last_breath.addnext(t)

set_text(B[260],
         '呼吸模式下左转向灯由本模块独占，转向灯闪烁服务会自动跳过左灯珠；'
         '通过串口 0x06 功能字或快捷命令手动控制左转向灯时，固件会先退出呼吸模式，'
         '保证任意时刻只有一个模块在驱动同一组引脚。')
log.append('3.8.1 +Breath_GetDuty / Breath_GetPwmCnt 两张表')

# ---- 3.8 正文措辞：LED1 是「灯条」不是转向灯，呼吸模块独占的是左 RGB 灯珠 ----
for e in B:
    if e.tag == q('tbl') and 'Breath_IsActive' in ''.join(x.text or '' for x in e.iter(q('t'))):
        for r in e.findall(q('tr')):
            cells = r.findall(q('tc'))
            if cells and '描述' in cell_text(cells[0]):
                set_cell(cells[1], '查询当前是否处于呼吸模式；转向灯闪烁服务据此跳过左转向灯，'
                                   '避免两个模块同时驱动同一组引脚')
        break
log.append('3.8 措辞修正（跳过左转向灯）')

# ---- 3.1.2 控制单元表：补齐转向灯实际驱动的引脚（V2 板左右灯珠各带一颗板载小灯） ----
for e in B:
    if e.tag != q('tbl'):
        continue
    txt = ''.join(x.text or '' for x in e.iter(q('t')))
    if ('左转向灯（LED1）' in txt) and ('0x03' in txt):
        for r in e.findall(q('tr')):
            cs = r.findall(q('tc'))
            if len(cs) < 3:
                continue
            a, b = cell_text(cs[0]), cell_text(cs[1])
            if b.startswith('左转向灯'):
                set_cells(r, [a, '左转向灯（LED1 + 左灯珠）', 'PG14、PG0、PG1、PG2'])
            elif b.startswith('右转向灯'):
                set_cells(r, [a, '右转向灯（LED2 + 右灯珠）', 'PG15、PE2、PE3、PE4'])
            elif b.startswith('LED 灯'):
                set_cells(r, [a, 'LED 灯（RGB 灯条）', 'PG0、PG1、PG2'])
        break
log.append('3.1.2 控制单元表补齐转向灯引脚')


# ============================================================
# 第二部分：插入新增章节
# ============================================================

def add_iface(anchor, proto, desc, param, ret):
    t = clone(IFACE_T)
    for r, (k, v) in zip(t.findall(q('tr')),
                         (('函数原型', proto), ('描述', desc), ('参数', param), ('返回值', ret))):
        set_cells(r, [k, v])
    anchor.addnext(t)
    return t


def add_info3(anchor, header, rows_data):
    t = clone(INFO_T)
    trs = t.findall(q('tr'))
    proto = copy.deepcopy(trs[-1])
    for r in trs:
        t.remove(r)
    for cells in [header] + list(rows_data):
        row = copy.deepcopy(proto)
        set_cells(row, list(cells))
        t.append(row)
    anchor.addnext(t)
    return t


def chain(anchor, items):
    """items: [('h3'|'h4'|'body'|'code', text), ...]，返回最后一个元素。
    anchor 为文末锚点时追加到 body 最末尾（保留原文档末段的位置）。"""
    cur = anchor
    for kind, text in items:
        tpl = {'h3': H3_T, 'h4': H4_T, 'body': BODY_T, 'code': CODE_T}[kind]
        new = clone(tpl, text)
        if cur is sectPr:
            body.append(new)
        else:
            cur.addnext(new)
        cur = new
    return cur


# ---------------- 3.2.3 补 16x16 放大字显示接口 ----------------
def ttext(e):
    return ''.join(x.text or '' for x in e.iter(q('t')))


def find_B(pred):
    for e in B:
        if pred(e):
            return e
    raise RuntimeError('anchor not found')


A_OLEDPROBE = find_B(lambda e: e.tag == q('tbl') and 'OLED_Probe' in ttext(e))
cur = chain(A_OLEDPROBE, [
    ('body', '屏最上面一行文字用放大字显示。放大字不做新的字模，而是把 8x8 字模按'
             '「每行像素复制一遍、每列像素复制一遍」放大 2 倍，得到 16x16 的点阵，'
             '纵向跨相邻两页，字号立刻翻倍，在 0.86 寸小屏上一眼就能看清。'
             '一行最多放 8 个放大字。'),
    ('body', '放大字的小数点单独处理：8x8 字模里句点只有 2x2 个像素，放大后也只有 4x4，'
             '在屏上很不显眼，因此绕过字模，直接画一个 6x6 的实心方块，贴着底线、'
             '在 16 像素宽的格子里水平居中。放大字相关的接口如下：'),
])
cur = add_iface(cur, 'void OLED_ShowCharBig(uint8_t col, uint8_t page, char ch)',
                '在指定位置显示一个 16x16 放大字符，占用 col 起的两个列单位与 page 起的两个页；'
                '字符为句点时画 6x6 实心方块；列号或页号越界直接返回，可显示范围外的字符按问号处理',
                'col：列号（单位 16 像素，取值 0 到 7）；page：起始页（取值 0 到 2，'
                '放大字占两页所以要留出下一页）；ch：待显示字符',
                'void')
cur = add_iface(cur, 'void OLED_ShowStringBig(uint8_t col, uint8_t page, const char *str)',
                '从指定位置起连续显示一个放大字符串，每个字符占两个列单位，超出右边界自动截断',
                'col：起始列（单位 16 像素，取值 0 到 7）；page：起始页（取值 0 到 2）；'
                'str：以 0 结尾的字符串',
                'void')
log.append('3.2.3 +放大字接口 2 张表')

# ---------------- 3.2.5 16x16 中文字库与中文显示 ----------------
cur = chain(A_8X8, [
    ('h4', '3.2.5 16x16 中文字库与中文显示'),
    ('body', '屏上除了 8x8 的 ASCII 字符，还支持 16x16 的汉字显示。字库是独立的数据文件 '
             'cn_font16.c / .h，收录本工程界面与提示用到的 60 个汉字，每个汉字 32 字节字模'
             '（16 行乘 2 字节），1 表示点亮。字模用宋体 16 像素无抗锯齿渲染后取模，'
             '按 GBK 双字节编码线性查表，查找失败时画一个空心方框，方便一眼看出缺字。'),
    ('body', '字库相关的数据结构与接口如下：'),
])
t = add_info3(cur, ('名称', '类型', '说明'), [
    ('g_cnFont16', 'CnGlyph16_t 数组', '全部汉字字模，每项含 GBK 编码与 32 字节点阵'),
    ('g_cnFont16Count', 'uint16_t', '字库收录的汉字个数'),
    ('CnGlyph16_t', '结构体', '成员：gbk（GBK 双字节编码，高字节在前）、data[32]（16 行乘 2 字节点阵）'),
    ('OLED_BIG_COL_MAX', '8', '16x16 大字的列单位：一行最多 8 个（128 除以 16），汉字与放大字母共用'),
])
cur = chain(t, [('body', '汉字显示接口如下：')])
cur = add_iface(cur, 'const CnGlyph16_t *CnFont16_Lookup(uint16_t gbk)',
                '按 GBK 编码在字库里查找字模，采用线性查找；找不到返回空指针，调用方据此画空心方框',
                'gbk：GBK 双字节编码（高字节在前）', '命中返回字模指针；未收录返回 0')
cur = add_iface(cur, 'void OLED_ShowCNChar(uint8_t col, uint8_t page, uint16_t gbk)',
                '在指定位置显示一个 16x16 汉字，占用 col 起的两个列单位、page 起的两个页；'
                '写入显存时要做行列转置（字库是行优先、显存是列优先）',
                'col：列号（单位 16 像素，0~7）；page：起始页（0~2）；gbk：GBK 编码', 'void')
cur = add_iface(cur, 'void OLED_ShowCNString(uint8_t col, uint8_t page, const char *gbkStr)',
                '连续显示一串汉字，字符串每个汉字占 2 字节，每显示一个自动右移两个字列单位',
                'col：起始列（单位 16 像素）；page：起始页；gbkStr：GBK 编码字符串', 'void')
log.append('新增 3.2.5 16x16 中文字库与中文显示')

# ---------------- 3.4.3 数据页保护 ----------------
cur = chain(A_STORE, [
    ('h4', '3.4.3 数据页保护（下载范围限制）'),
    ('body', '数据页位于内部 Flash 的最后一页 0x0807F800。Keil 工程默认的下载范围覆盖整个主存储区，'
             '每次按 F8 下载都会顺手把这一页擦掉，表现出来的现象是"标定值和保存的状态每次下载后就没了"。'),
    ('body', '处理办法是把下载范围限制到数据页之前，即把工程 Flash Download 设置里的容量由 512K 改为 508K'
             '（命令行参数 -FL07F800），最后一页留给数据页。这样正常下载不再影响掉电保存的内容。'),
])
t = add_info3(cur, ('情况', '结果', '说明'), [
    ('Keil 按 F8 下载（下载范围已限制到数据页之前）', '数据页保留',
     '标定值、文本与设备状态都不用重做，开机横幅会显示已标定'),
    ('手动勾选 Erase Full Chip，或用其他工具整片擦除', '数据页被擦掉',
     '重新发一次 K 加室温值即可恢复标定，文本与状态需要重新保存'),
    ('串口发 C 命令清除 Flash', '数据页被擦掉',
     '效果同上，属于主动清除，需要重新保存与标定'),
])
log.append('新增 3.4.3 数据页保护')

# ---------------- 3.6.3 温度单点标定 ----------------
cur = chain(A_ADC, [
    ('h4', '3.6.3 温度单点标定'),
    ('body', '芯片内部的温度传感器没有逐片的出厂校准值，手册给出的 V25 = 1.43V 与 '
             'Avg_Slope = 4.3mV/℃ 只是典型值；再加上芯片自身在运行时发热，'
             '按手册公式直接算出来的读数会比环境温度高出几度。'
             '本工程提供单点标定：以室温为基准算出一个加性偏移量，把整体读数平移到室温附近。'
             '标定只做平移、不改斜率，因此温升趋势与相对变化依然准确。'),
    ('body', '标定值保存在内部 Flash 数据页里，掉电不丢；开机横幅会直接打印当前是否已标定。'
             '标定相关的取值如下：'),
])
t = add_info3(cur, ('项目', '取值', '说明'), [
    ('标定命令', '串口发 K 加温度值再回车', '例如室温 29℃ 发 K29；只发 K 则按 25℃ 标定'),
    ('清除命令', '串口发 Z 再回车', '偏移清零，回到手册公式的原始值'),
    ('偏移存储', 'StoreRecord_t 的 calOffsetX100 字段',
     '单位 0.01℃，0 表示未标定；复用原占位字段，结构体大小与 Flash 布局都不变'),
    ('偏移限幅', '±120℃（对应 12000）', '防止误输入把读数带飞，超出范围即被夹紧'),
    ('生效时机', '在 Adc_SampleTemp 内部叠加',
     '先用未标定的温度判断量程，再叠加偏移，避免标定值把有效采样误判成超量程'),
])
cur = chain(t, [('body', '标定接口如下：')])
cur = add_iface(cur, 'void Adc_SetCalOffsetX100(int32_t offsetX100)',
                '设置标定偏移，内部夹紧到 ±120℃；只修改内存中的偏移量，不直接写 Flash，'
                '需要保存时由应用层调用 Store_Save',
                'offsetX100：偏移量，单位 0.01℃', 'void')
cur = add_iface(cur, 'int32_t Adc_GetCalOffsetX100(void)',
                '读取当前标定偏移，用于开机提示与状态显示',
                'void', '偏移量，单位 0.01℃；0 表示未标定')
log.append('新增 3.6.3 温度单点标定')

# ---------------- 3.9 转向灯模块 ----------------
cur = chain(sectPr, [
    ('h3', '3.9 转向灯模块及接口说明'),
    ('body', '板上左右各有一颗四脚 RGB 灯珠构成车灯，两盏灯的颜色由各自的驱动接口设置。'
             '左转向灯打开时做呼吸效果，由 3.8 节的软件 PWM 模块驱动；'
             '右转向灯打开时做彩虹闪烁，每闪一次换一种颜色，按 红、黄、绿、青、蓝、紫 六色轮转。'
             '两盏灯在亮灭的同时会一起驱动旁边的板载小灯（LED1 / LED2），'
             '车灯负责远处可见、小灯负责近处观察。'),
    ('body', '转向灯的闪烁由主循环里的 TurnSignalService 统一调度，左右灯共用同一个半周期，'
             '因此同时打开时两盏灯同步闪烁。左转向灯处于呼吸模式时该服务会跳过左灯珠，'
             '避免两个模块同时写同一组引脚。转向灯相关取值如下：'),
])
t = add_info3(cur, ('项目', '取值', '说明'), [
    ('闪烁周期', '半周期 500ms', '由 SysTick 时基计算，不使用阻塞延时，闪烁节奏不受其他任务影响'),
    ('左转向灯', 'PG0、PG1、PG2（左上角 RGB 灯珠）', '打开时呼吸；呼吸期间由软件 PWM 模块独占这三路'),
    ('右转向灯', 'PE2、PE3、PE4（右上角 RGB 灯珠）', '打开时彩虹闪烁，同时点亮 LED2（PG15）'),
    ('彩虹色序', '红、黄、绿、青、蓝、紫', '六个颜色循环轮转，每亮一次换下一色'),
    ('同步小灯', 'LED1（PG14）、LED2（PG15）', '与对应灯珠一起亮灭，方便近距离观察状态'),
])
cur = chain(t, [('body', '右转向灯珠的驱动接口如下：')])
cur = add_iface(cur, 'void RGB2_Init(void)',
                '把右转向灯珠的 PE2 / PE3 / PE4 配置为推挽输出并置为熄灭；上电初始化时先灭灯，'
                '避免上电瞬间误亮',
                'void', 'void')
cur = add_iface(cur, 'void RGB2_Set(RGB_TypeDef color)',
                '设置右转向灯珠的颜色，颜色枚举与左灯珠的 RGB_Set 完全相同；'
                '转向灯服务在每次闪烁时传入彩虹色序中的下一个颜色',
                'color：RGB_NONE / RGB_R / RGB_G / RGB_B / RGB_YELLOW / RGB_CYAN / RGB_MAGENTA / RGB_ALL',
                'void')
log.append('新增 3.9 转向灯模块（右灯彩虹 + 2 张接口表）')

# ---------------- 3.10 中文消息与串口中文输出 ----------------
cur = chain(sectPr, [
    ('h3', '3.10 中文消息与串口中文输出'),
    ('body', '工程里的界面提示与串口提示都用中文。中文文本集中放在 App_User/cn_msg.h 中，'
             '以 GBK 转义的 C 字面量形式定义，源文件中不出现中文字节，'
             '避免不同编辑器或编译器对源码编码的解释不一致而导致乱码。'),
    ('body', 'OLED 上的中文用 16x16 字库点阵显示，走 3.2.5 节的显示接口；'
             '串口上的中文按 GBK 编码逐字节发出，一个汉字 2 字节。'
             '需要注意的是，串口助手默认的接收编码是 UTF-8，看到中文会变成乱码，'
             '必须把接收编码设为 GBK 或 ANSI 才能正常显示。'),
    ('body', '中文相关的约定如下：'),
])
t = add_info3(cur, ('类别', '取值', '说明'), [
    ('宏定义', 'CN_BOOTING、CN_CAL_OK、CN_BREATH_ON 等',
     '界面与串口的全部中文提示，共 25 条，集中在 cn_msg.h 中管理'),
    ('屏显字库', 'g_cnFont16（60 个汉字）', 'OLED 上显示的汉字取自这份 16x16 点阵字库'),
    ('串口编码', 'GBK', '每个汉字 2 字节；串口助手的接收编码需设为 GBK 或 ANSI'),
    ('屏显编码', 'GBK', '字库按 GBK 双字节编码索引，串口下发的文本按 ASCII 直接显示'),
    ('保持英文的部分', 'Current ADC_Value / Voltage / Temperature / VDDA',
     '任务书要求的上报格式保持英文，中文只出现在其后追加的小结行，不影响验收'),
])
log.append('新增 3.10 中文消息与串口中文输出')

# ============================================================
# 落盘
# ============================================================
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
print('SAVED ->', DST)
