# -*- coding: utf-8 -*-
"""
按「方法 B」在既有成品文档上增量生成本次智能门锁工程的接口文档。

思路：
  1) cp 一份上一章成品（红外避障）当骨架，样式 / 目录 / 缩略语表 / 修订记录表全部沿用；
  2) 第 1 章（简介）在模板里本来就在第一个分节内，直接原地改文字；
  3) 第 2、3 章整段重建：删掉分节符之后的全部 body 子元素，再用
     deepcopy 出来的 H3 / H4 / 正文 / 接口表原型逐个克隆追加。
      —— 克隆再改文字，样式与手打编号原样保留，绕开 markdown 转义与自动编号三坑。
"""
import copy
import os
import shutil
import sys

sys.stdout.reconfigure(encoding='utf-8')

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from lxml import etree

SRC = r'D:\STM32_Project\docs\红外避障传感器采集_接口文档.docx'
DST = r'D:\STM32_Project\docs\智能门锁_接口文档.docx'
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'


def q(tag):
    return qn('w:' + tag)


def sanitize(el):
    """克隆出来的元素不能带重复书签，否则 Word 会报文档损坏。"""
    for tag in ('w:bookmarkStart', 'w:bookmarkEnd', 'w:commentRangeStart',
                'w:commentRangeEnd', 'w:proofErr'):
        for x in el.findall('.//' + qn(tag)):
            x.getparent().remove(x)
    return el


def set_text(p_el, text):
    """段落里只留第一个 run，把文字换掉；没有 run 就造一个。"""
    runs = p_el.findall(q('r'))
    if not runs:
        r = OxmlElement('w:r')
        t = OxmlElement('w:t')
        t.set(XML_SPACE, 'preserve')
        t.text = text
        r.append(t)
        p_el.append(r)
        return
    keep = runs[0]
    for r in runs[1:]:
        p_el.remove(r)
    for tag in ('tab', 'br', 'drawing', 'fldChar', 'instrText'):
        for e in keep.findall(q(tag)):
            keep.remove(e)
    ts = keep.findall(q('t'))
    if ts:
        ts[0].text = text
        ts[0].set(XML_SPACE, 'preserve')
        for t in ts[1:]:
            keep.remove(t)
    else:
        t = OxmlElement('w:t')
        t.set(XML_SPACE, 'preserve')
        t.text = text
        keep.append(t)


def set_cell(tc, text):
    ps = tc.findall(q('p'))
    for p in ps[1:]:
        tc.remove(p)
    set_text(ps[0], text)


def resize_rows(tbl, nrows):
    trs = tbl.findall(q('tr'))
    while len(trs) > nrows:
        tbl.remove(trs[-1])
        trs = tbl.findall(q('tr'))
    while len(trs) < nrows:
        tbl.append(copy.deepcopy(trs[-1]))
        trs = tbl.findall(q('tr'))
    return tbl.findall(q('tr'))


def no_split_rows(tbl):
    """表格行禁止跨页拆分。不加的话一行文字会被切成两半，
    下一页开头只剩「码，高字节在前」这种半截内容，看不出属于哪个函数。"""
    for tr in tbl.findall(q('tr')):
        trPr = tr.find(q('trPr'))
        if trPr is None:
            trPr = OxmlElement('w:trPr')
            tr.insert(0, trPr)
        if trPr.find(q('cantSplit')) is None:
            trPr.insert(0, OxmlElement('w:cantSplit'))


def set_col_widths(tbl, ratios):
    """按比例重设列宽。不设的话 4 列表格会沿用原型里那套等分宽度，
    「主要职责」这种长文字列被挤成一条竖排，很难看。"""
    grid = tbl.find(q('tblGrid'))
    cols = grid.findall(q('gridCol'))
    total = sum(int(c.get(q('w')) or 0) for c in cols)
    if total <= 0:
        total = 8306
    widths = [int(total * r) for r in ratios]
    widths[-1] = total - sum(widths[:-1])
    for c, w in zip(cols, widths):
        c.set(q('w'), str(w))
    for tr in tbl.findall(q('tr')):
        for tc, w in zip(tr.findall(q('tc')), widths):
            tcPr = tc.find(q('tcPr'))
            if tcPr is None:
                tcPr = OxmlElement('w:tcPr')
                tc.insert(0, tcPr)
            tcW = tcPr.find(q('tcW'))
            if tcW is None:
                tcW = OxmlElement('w:tcW')
                tcPr.insert(0, tcW)
            tcW.set(q('w'), str(w))
            tcW.set(q('type'), 'dxa')
    tblPr = tbl.find(q('tblPr'))
    if tblPr is not None and tblPr.find(q('tblLayout')) is None:
        lay = OxmlElement('w:tblLayout')
        lay.set(q('type'), 'fixed')
        look = tblPr.find(q('tblLook'))
        if look is not None:
            look.addprevious(lay)
        else:
            tblPr.append(lay)


def fill_table(tbl, data, ratios=None):
    """data 是二维列表，第一行当表头（不改底纹，底纹在原型里已有）。"""
    trs = resize_rows(tbl, len(data))
    ncol = len(tbl.findall(q('tr'))[0].findall(q('tc')))
    for i, row in enumerate(data):
        tcs = trs[i].findall(q('tc'))
        for j in range(ncol):
            set_cell(tcs[j], row[j] if j < len(row) else '')
    if ratios is None:
        ratios = RATIOS.get(tuple(data[0]))
    if ratios:
        set_col_widths(tbl, ratios)
    no_split_rows(tbl)
    return tbl


# 按表头签名给每张内容表配一套列宽比例（不配的沿用原型宽度）
RATIOS = {
    ('组成', '实现', '说明'): [0.16, 0.30, 0.54],
    ('层次', '目录', '职责'): [0.14, 0.24, 0.62],
    ('模块', '源文件', '主要职责', '使用引脚'): [0.17, 0.22, 0.37, 0.24],
    ('状态', '进入条件', '主要动作'): [0.22, 0.30, 0.48],
    ('功能', '引脚', '配置', '说明'): [0.19, 0.24, 0.24, 0.33],
    ('页面元素', '纵坐标', '占用高度'): [0.30, 0.22, 0.48],
    ('键位', '矩阵行列', '语义'): [0.18, 0.28, 0.54],
    ('寄存器', '取值', '说明'): [0.16, 0.32, 0.52],
    ('项目', '取值', '说明'): [0.26, 0.16, 0.58],
    ('字段', '字节数', '取值', '说明'): [0.15, 0.12, 0.30, 0.43],
    ('命令字', '含义', '参数'): [0.13, 0.40, 0.47],
    ('寄存器', '地址', '用途'): [0.28, 0.14, 0.58],
    ('偏移', '字节数', '内容', '说明'): [0.09, 0.10, 0.36, 0.45],
    ('场景', '处理方式', '原因'): [0.26, 0.30, 0.44],
    ('按键', '作用', '说明'): [0.16, 0.18, 0.66],
    ('步骤', '调用接口', '作用'): [0.10, 0.26, 0.64],
}


def make_iface_table(proto, funcs):
    """接口表：一个函数四行（函数原型 / 描述 / 参数 / 返回值）。"""
    tbl = copy.deepcopy(proto)
    labels = ('函数原型', '描述', '参数', '返回值')
    trs = tbl.findall(q('tr'))
    pattern = [copy.deepcopy(x) for x in trs[:4]]
    for x in trs:
        tbl.remove(x)
    for fn, desc, param, ret in funcs:
        for i, txt in enumerate((fn, desc, param, ret)):
            row = copy.deepcopy(pattern[i])
            tbl.append(row)
            tcs = row.findall(q('tc'))
            set_cell(tcs[0], labels[i])
            set_cell(tcs[1], txt)
    # 右列改成左对齐：原型段落继承的是两端对齐，长函数名在空格处换行时
    # 会被拉开一大段空白（例如 void UI_Lock_UpdateClock(const 那行）。
    for row in tbl.findall(q('tr')):
        for tc in row.findall(q('tc')):
            for p in tc.findall(q('p')):
                Paragraph(p, None).alignment = WD_ALIGN_PARAGRAPH.LEFT
    no_split_rows(tbl)
    return tbl


# ---------------------------------------------------------------- 打开骨架
if os.path.exists(DST):
    os.remove(DST)
shutil.copy2(SRC, DST)

d = docx.Document(DST)
body = d.element.body
children = list(body)

# 找第一个分节符（模板里它落在第 1 章之后）
sect_idx = None
for i, ch in enumerate(children):
    pPr = ch.find(q('pPr'))
    if pPr is not None and pPr.find(q('sectPr')) is not None:
        sect_idx = i
        break
assert sect_idx is not None, '没找到分节符'
tail_sect = children[-1]
assert etree.QName(tail_sect).localname == 'sectPr', '文末不是 sectPr'

# 第 1 章各段落在 body 里的位置（相对分节符倒推是稳定的：89/88/87...）
# 用文本定位更稳，不写死下标
def find_body_p(text, start=0, end=None):
    end = len(children) if end is None else end
    for i in range(start, end):
        ch = children[i]
        if etree.QName(ch).localname != 'p':
            continue
        t = ''.join(x.text or '' for x in ch.iter(q('t'))).strip()
        if t == text:
            return i
    return None


i_h1 = find_body_p('1 简介', 60)
i_11 = find_body_p('1.1 前言', i_h1)
i_12 = find_body_p('1.2 范围', i_h1)
i_13 = find_body_p('1.3 背景', i_h1)
i_14 = find_body_p('1.4 缩略语', i_h1)
i_toc = find_body_p('目录', 0, i_h1)
print('body 定位: 目录=%s H1=%s 1.1=%s 1.4=%s sect=%s' % (i_toc, i_h1, i_11, i_14, sect_idx))
assert None not in (i_toc, i_h1, i_11, i_12, i_13, i_14)

# ---------------------------------------------------------------- 取原型
PROTO_H3 = sanitize(copy.deepcopy(children[i_11]))
PROTO_BODY = sanitize(copy.deepcopy(children[i_11 + 1]))
PROTO_H4 = None
for ch in children[i_h1:sect_idx]:
    if etree.QName(ch).localname != 'p':
        continue
    for st in ch.iter(q('pStyle')):
        if st.get(q('val')) in ('4', 'Heading4', 'heading 4'):
            PROTO_H4 = sanitize(copy.deepcopy(ch))
            break
    if PROTO_H4 is not None:
        break
if PROTO_H4 is None:
    # 后面章节里找
    for ch in children[sect_idx:]:
        if etree.QName(ch).localname != 'p':
            continue
        for st in ch.iter(q('pStyle')):
            if st.get(q('val')) in ('4', 'Heading4', 'heading 4'):
                PROTO_H4 = sanitize(copy.deepcopy(ch))
                break
        if PROTO_H4 is not None:
            break
assert PROTO_H4 is not None, '没找到 Heading 4 原型'

# 目录条目原型（按缩进分三级）
# ★ 必须从「目录」这一段的下一段开始找：否则 '目录' 自己（居中、字号大）
#   会被当成一级条目原型，生成出来的目录一级条目全都居中。
PROTO_TOC = {}
for ch in children[i_toc + 1:i_h1]:
    if etree.QName(ch).localname != 'p':
        continue
    txt = ''.join(x.text or '' for x in ch.iter(q('t'))).strip()
    if not txt or txt == '目录':
        continue
    pPr = ch.find(q('pPr'))
    ind = pPr.find(q('ind')) if pPr is not None else None
    left = ind.get(q('left')) if ind is not None else None
    left = '0' if left is None else str(left)
    if left not in PROTO_TOC:
        PROTO_TOC[left] = sanitize(copy.deepcopy(ch))
print('目录缩进原型:', sorted(PROTO_TOC.keys(), key=lambda s: int(s)))

# 表格原型
def find_table(rows, cols, start_tbl=0):
    n = 0
    for t in d.tables:
        if len(t.rows) == rows and len(t.columns) == cols:
            return copy.deepcopy(t._tbl)
        n += 1
    return None


PROTO_IF = find_table(32, 2)
PROTO_T3 = find_table(11, 3)
PROTO_T4 = find_table(14, 4)
PROTO_ABBR = copy.deepcopy(d.tables[1]._tbl)
PROTO_REV = copy.deepcopy(d.tables[0]._tbl)
assert all(x is not None for x in (PROTO_IF, PROTO_T3, PROTO_T4, PROTO_ABBR, PROTO_REV))

# ---------------------------------------------------------------- 封面标题
set_text(children[0], '智能门锁实训方案文档（接口）')

# ---------------------------------------------------------------- 修订记录
REV = [
    ['日期', '版本', '修订说明', '修订人'],
    ['2026.10.20', 'V1.0', '首次发布：OLED 锁屏与实时时钟、16 键矩阵键盘、密码开锁、继电器驱动与自动上锁', '陈相林'],
    ['2026.10.21', 'V2.0', '新增 AS608 指纹模块（USART2 协议帧、校验、1:N 验证与录入删除流程）、BKP 密码管理与六项设置菜单', '陈相林'],
    ['2026.10.22', 'V3.0', '新增 RC522 读卡模块（软件 SPI、寻卡/防冲突/选卡）与片内 Flash 卡片库（魔字 + CRC16 校验）', '陈相林'],
    ['2026.10.26', 'V4.0', '新增蓝牙串口开锁（双策略断帧 + 防爆破）、刷卡匹配显示卡号、自动上锁回锁屏；任务书七条需求全部联调通过', '陈相林'],
]
fill_table(d.tables[0]._tbl, REV)

# ---------------------------------------------------------------- 第 1 章原地改写
set_text(children[i_11], '1.1 前言')
set_text(children[i_11 + 1],
         '本文档用于说明智能门锁实训工程的模块划分、对外接口与使用方法，作为开发、调试与验收的统一依据。'
         '工程按任务书七条需求逐层搭建：先做出能看清时间的锁屏，再把 4x4 矩阵键盘接成密码输入，'
         '用继电器模拟门锁开合；随后接入 AS608 指纹与 RC522 读卡两种身份认证方式，'
         '最后补上蓝牙串口开锁。四种开锁方式共用同一套执行机构、同一套界面规则和同一套自动上锁逻辑，'
         '任何一路通过都走同一条开锁与延时上锁路径，行为完全一致。')

set_text(children[i_12], '1.2 范围')
set_text(children[i_12 + 1],
         '本文档适用于基于 STM32F103C8 与 STM32F10x 标准外设库 V3.6 的智能门锁实训工程，'
         '覆盖 OLED 显示与中文排版、SysTick 时基、RTC 实时时钟、4x4 矩阵键盘扫描与消抖、'
         '继电器与蜂鸣器驱动、密码在备份域寄存器中的存取、AS608 指纹模块的串口协议与业务流程、'
         'RC522 读卡模块的软件 SPI 时序与寻卡流程、卡片库存片内 Flash、'
         '蓝牙串口接收与断帧策略、六项设置菜单交互以及上电初始化顺序等内容。')

set_text(children[i_13], '1.3 背景')
set_text(children[i_13 + 1],
         '智能门锁是把「身份认证」与「执行机构」连起来的最小完整系统：认证方式可以有好几种，'
         '但最后动作只有「开锁」和「上锁」两个。本工程故意把四种认证方式并列，'
         '目的不是堆功能，而是练三件事——一是多种输入通道（矩阵键盘、串口、两个独立的读模块）'
         '如何在同一个主循环里互不阻塞地轮询；二是掉电要保持的数据（密码、卡片库）'
         '该放在什么地方，为什么密码放备份域寄存器、卡片库放片内 Flash；'
         '三是身份认证的结果如何收口到统一的开锁流程，让四种方式的行为看起来完全一样。')

set_text(children[i_14], '1.4 缩略语')

ABBR = [
    ['缩略语', '英文全名', '中文解释'],
    ['USART', 'Universal Synchronous Asynchronous Receiver Transmitter', '通用同步异步收发器，即常说的串口；本工程用到 USART1（蓝牙）与 USART2（指纹）'],
    ['UART', 'Universal Asynchronous Receiver Transmitter', '异步串行收发器，本工程按 8 位数据、无校验、1 位停止位使用'],
    ['SPL', 'Standard Peripheral Library', 'ST 官方标准外设库，本工程使用 V3.6 版本'],
    ['OLED', 'Organic Light-Emitting Diode', '有机发光二极管显示屏，本工程用 0.96 寸 128x64'],
    ['SSD1306', '—', 'OLED 显示驱动控制器芯片，通过 I2C 接收显存数据'],
    ['I2C', 'Inter-Integrated Circuit', '两线式串行总线；本工程没有用硬件 I2C，而是用 GPIO 软件模拟'],
    ['SPI', 'Serial Peripheral Interface', '串行外设接口；RC522 挂在这条总线上，同样用 GPIO 软件模拟'],
    ['RC522', '—', '13.56MHz 非接触读卡芯片；本工程用的是国产兼容片，版本号 0xB2'],
    ['AS608', '—', '光学指纹识别模块，内置指纹算法与指纹库，通过串口下命令'],
    ['BKP', 'Backup Registers', 'STM32 备份域寄存器，靠 VBAT 维持，本工程用来存门锁密码'],
    ['RTC', 'Real-Time Clock', '实时时钟，锁屏显示的年月日时分秒由它提供'],
    ['GBK', 'Chinese Internal Code Specification', '汉字编码，一个汉字两个字节；中文字库按它索引'],
    ['UID', 'Unique Identifier', '卡片出厂固化的唯一序列号，4 字节，本工程用它区分卡片'],
    ['Mifare', '—', '恩智浦的 13.56MHz 非接触卡协议族，本工程按 Mifare One 的寻卡流程实现'],
    ['Flash', 'Flash Memory', '闪存，本文指 STM32 片内 Flash，卡片库存放在这里'],
]
fill_table(d.tables[1]._tbl, ABBR)

# ---------------------------------------------------------------- 删掉第 2 章以后
for ch in children[sect_idx + 1:]:
    if ch is tail_sect:
        continue
    body.remove(ch)

# ---------------------------------------------------------------- 重建目录
h1_el = children[i_h1]
# i_toc+1 与 i_toc+2 是「目录」标题下面原有的两个空行（排版留白），保留；
# 从这里之后到第 1 章标题之间的都是旧目录条目，全部换掉。
for ch in children[i_toc + 3:i_h1]:
    body.remove(ch)


def toc_el(level, text):
    keys = sorted(PROTO_TOC.keys(), key=lambda s: int(s))
    key = keys[level] if level < len(keys) else keys[-1]
    el = sanitize(copy.deepcopy(PROTO_TOC[key]))
    set_text(el, text)
    return el


# ---------------------------------------------------------------- 正文数据
IF_SYSTICK = [
    ('void SysTick_Init(void)',
     '把 SysTick 配置成 1ms 中断，作为全工程唯一的时基；中断里只做一件事，给一个 32 位计数器加一',
     'void', 'void'),
    ('uint32_t Get_SysRunTime(void)',
     '返回上电以来经过的毫秒数。全工程的超时判断都拿它做差，不用阻塞延时去数循环',
     'void', '毫秒计数，32 位，约 49.7 天回绕一次；两数做差时回绕天然正确'),
    ('void DelayMs(uint16_t ms)',
     '阻塞延时指定毫秒数，内部按运行时间戳计算，中断打断也不会延长实际延时',
     'ms：延时长度，单位毫秒', 'void'),
]

IF_OLED = [
    ('void OLED_Init(void)',
     '把 PB12（SCL）与 PB13（SDA）配成开漏输出，下发 SSD1306 上电配置序列，清空显存后刷新一次',
     'void', 'void'),
    ('uint8_t OLED_Probe(void)',
     '发一次 SSD1306 状态读命令，判断屏幕在不在线；上电自检与换板自检都调它',
     'void', '1 = 屏幕应答，0 = 无应答（未焊接或接线异常）'),
    ('void OLED_Clear(void)',
     '把 8 页显存全部填 0；只改内存，必须再调 OLED_Refresh 才会上屏',
     'void', 'void'),
    ('void OLED_Refresh(void)',
     '把整屏显存通过 I2C 一次性刷到屏幕，一帧约 25ms；画面切换时调用',
     'void', 'void'),
    ('void OLED_ClearBlock(uint8_t x, uint8_t y, uint8_t w, uint8_t h)',
     '按像素坐标清一块矩形区域，只清需要的部分，比整屏刷快得多',
     'x：起始列 0~127；y：起始行 0~63；w：宽度；h：高度', 'void'),
    ('void OLED_DrawCharAt(uint8_t x, uint8_t y, char ch)',
     '在任意像素坐标画一个 8x8 的 ASCII 字符',
     'x：列坐标；y：行坐标；ch：待画字符', 'void'),
    ('void OLED_DrawStringAt(uint8_t x, uint8_t y, const char *str)',
     '从给定坐标起连续画一串 ASCII，超出右边界自动截断，不会绕回下一行',
     'x：列坐标；y：行坐标；str：以 0 结尾的字符串', 'void'),
    ('void OLED_DrawCharTallAt(uint8_t x, uint8_t y, char ch)',
     '画一个 8x16 的高字：把 8x8 字模逐行垂直放大两倍，用于数字与字母',
     'x：列坐标；y：行坐标；ch：待画字符', 'void'),
    ('uint8_t OLED_DrawTextAt(uint8_t x, uint8_t y, const char *txt)',
     '按字节流自动混排：ASCII 走 8x16 高字，成对的中文走 16x16 字库，依次往右排',
     'x：列坐标；y：行坐标；txt：GBK 编码字符串', '画完后下一个字符的 x 坐标'),
    ('uint8_t OLED_DrawTextCenter(uint8_t y, const char *txt)',
     '先用 OLED_TextWidth 算宽度，再反推起始 x，把一行文本水平居中',
     'y：行坐标；txt：GBK 编码字符串', '画完后下一个字符的 x 坐标'),
    ('uint8_t OLED_TextWidth(const char *txt)',
     '计算一行混排文本占多少像素：ASCII 按 8 像素、汉字按 16 像素累加',
     'txt：GBK 编码字符串', '像素宽度'),
    ('void OLED_DrawCNCharAt(uint8_t x, uint8_t y, uint16_t gbk)',
     '从 16x16 字库取字模并在指定坐标画出；字库未收录时画一个空心方框占位',
     'x：列坐标；y：行坐标；gbk：GBK 双字节编码，高字节在前', 'void'),
    ('void OLED_ShowCNStringCenter(uint8_t page, const char *gbkStr)',
     '把一串中文按页居中显示，内部逐个汉字调 OLED_DrawTextCenter 排版',
     'page：页号 0~7；gbkStr：GBK 编码字符串', 'void'),
    ('void OLED_ShowCharBig(uint8_t col, uint8_t page, char ch)',
     '画一个 16x16 放大的 ASCII 字符，占两列、两页；锁屏大号时间用它',
     'col：列单位（每单位 16 像素）；page：起始页；ch：待画字符', 'void'),
    ('void OLED_ShowStringBig(uint8_t col, uint8_t page, const char *str)',
     '连续画放大 ASCII，每字符占两个列单位，超右边界截断',
     'col：起始列单位；page：起始页；str：字符串', 'void'),
    ('void OLED_ShowTime(uint8_t page, uint8_t hour, uint8_t minute, uint8_t second)',
     '按 HH:MM:SS 画一行放大时间，秒位冒号按奇偶闪烁，锁屏每秒调一次',
     'page：起始页；hour/minute/second：时分秒', 'void'),
    ('void OLED_ShowCharInv(uint8_t col, uint8_t row, char ch)',
     '反白画一个字符（前景背景互换），菜单选中项用它标出来',
     'col：列号；row：页号；ch：待画字符', 'void'),
    ('void OLED_BarRow(uint8_t row, uint8_t cells, uint8_t lit)',
     '在指定页画一条按格数点亮的进度条，菜单滚动条用它表示当前位置',
     'row：页号；cells：总格数；lit：点亮格数', 'void'),
]

IF_FONT = [
    ('const CnGlyph16_t *CnFont16_Lookup(uint16_t gbk)',
     '按 GBK 编码在字库里线性查找 16x16 字模；收录 80 个汉字，覆盖全部界面文案',
     'gbk：GBK 双字节编码，高字节在前', '命中返回字模指针；未收录返回 0（调用方据此画空心方框）'),
]

IF_KEY = [
    ('void KeyMx_Init(void)',
     '4 行配推挽输出、4 列配上拉输入；同时调 GPIO_Remap_SWJ_JTAGDisable 只留 SWD，'
     'PB3/PB4/PB5 才空得出来给键盘用',
     'void', 'void'),
    ('void KeyMx_CrossScan(KeyMx_Raw_t *out)',
     '逐行拉低、读四列，做一次完整交叉扫描，把原始行列电平写进 out',
     'out：用于返回本次原始扫描结果', 'void'),
    ('uint16_t KeyMx_ScanMask(void)',
     '扫一遍并做 20ms 消抖，返回当前稳定按下的键位掩码',
     'void', '16 位掩码，每 bit 对应一个键位；0 表示没有键按下'),
    ('uint16_t KeyMx_PressedMask(const KeyMx_Raw_t *raw)',
     '取「上一拍没按、这一拍按下」的边沿，避免长按被重复当成多次单击',
     'raw：本次原始扫描结果', '新按下的键位掩码'),
    ('uint8_t KeyMx_MaskToKey(uint16_t mask)',
     '把按键掩码翻译成键号；多键同按时只取第一个，取到就返回',
     'mask：按键掩码', '键号 0~15；0xFF 表示无键'),
    ('uint8_t KeyMx_Poll(void)',
     '一拍按键处理的总入口：扫描 + 消抖 + 边沿判断，主循环每 10ms 调一次',
     'void', '键号 0~15；KEY_NONE 表示这一拍没有新按键'),
    ('uint8_t KeyMx_KeyRow(uint8_t key)',
     '查某个键位在矩阵里的行号；原理图行序与实际键位是反的，这里统一换算',
     'key：键号 0~15', '行号 0~3'),
    ('uint8_t KeyMx_KeyCol(uint8_t key)',
     '查某个键位在矩阵里的列号',
     'key：键号 0~15', '列号 0~3'),
]

IF_LOCKIO = [
    ('void LockIo_Init(void)',
     'PB9 配推挽输出并先置低（确保上电不吸合）；PB8 配上拉输入，把蜂鸣器引脚置于高阻，避免上电误鸣',
     'void', 'void'),
    ('void LockIo_Relay(uint8_t on)',
     '驱动继电器：非 0 吸合（模拟开锁，同时板上 LED 点亮），0 释放（上锁）',
     'on：1 = 吸合开锁，0 = 释放上锁', 'void'),
    ('uint8_t LockIo_RelayState(void)',
     '读回软件记录的继电器状态，用于自动上锁的判断',
     'void', '1 = 正在吸合，0 = 已释放'),
    ('void LockIo_Beep(uint16_t ms)',
     '让蜂鸣器鸣叫指定时长，到点由 LockIo_Tick 自动关掉，不阻塞调用方',
     'ms：鸣叫时长，单位毫秒', 'void'),
    ('void LockIo_BeepOff(void)',
     '立即停鸣并清掉定时',
     'void', 'void'),
    ('void LockIo_Tick(void)',
     '放在主循环里每 10ms 调一次，负责把到点的蜂鸣器关掉',
     'void', 'void'),
]

IF_RTC = [
    ('uint8_t RTC_Init(void)',
     '打开 PWR 与 BKP 时钟，启动 LSE，配置 RTC 时钟源与预分频，再读备份域判断要不要重新写时间',
     'void', '1 = 本次上电重新初始化过（时间可能是复位值），0 = 从备份域恢复，时间连续'),
    ('uint8_t RTC_GetClockSource(void)',
     '查询 RTC 实际使用的时钟源，LSE 起不来时会自动降级',
     'void', '0 = LSE，1 = LSI，2 = HSE/128'),
    ('uint8_t RTC_IsRestored(void)',
     '查询本次上电是否从备份域恢复了时间',
     'void', '1 = 恢复，0 = 重新配置'),
    ('void RTC_SetDateTime(const RTC_DateTime_t *dt)',
     '把结构体里的年月日时分秒换算成秒数写进 RTC 计数器，同时更新影子寄存器',
     'dt：待写入的日期时间', 'void'),
    ('void RTC_GetDateTime(RTC_DateTime_t *dt)',
     '读 RTC 计数器并换算成结构体，锁屏每秒调一次',
     'dt：用于返回当前日期时间', 'void'),
    ('uint32_t RTC_DateTimeToCounter(const RTC_DateTime_t *dt)',
     '把日期时间换算成 2000 年 1 月 1 日 0 点起的秒数',
     'dt：待换算的日期时间', '秒数'),
    ('void RTC_CounterToDateTime(uint32_t counter, RTC_DateTime_t *dt)',
     '把秒数反算回年月日时分秒，内部处理闰年与大小月',
     'counter：秒数；dt：用于返回日期时间', 'void'),
]

IF_PWD = [
    ('void Pwd_Init(void)',
     '从 BKP 读密码记录，魔字与长度都合法才采用；否则写入出厂默认密码 123456。必须在 RTC_Init 之后调用',
     'void', 'void'),
    ('uint8_t Pwd_Get(uint8_t *out)',
     '取当前密码，按位写入 out（每个元素是一位数字，不是 ASCII）',
     'out：输出缓冲，至少 6 字节', '密码位数 4~6'),
    ('uint8_t Pwd_Length(void)',
     '取当前密码位数',
     'void', '4~6'),
    ('uint8_t Pwd_Set(const uint8_t *in, uint8_t len)',
     '写入新密码，同时更新魔字、长度与两处打包寄存器，立即生效',
     'in：数字数组，每个元素取值 0~9；len：位数 4~6', '1 = 保存成功，0 = 参数非法'),
    ('uint8_t Pwd_Verify(const uint8_t *in, uint8_t len)',
     '逐位比对，长度也要对上才算通过；密码界面的数字键与蓝牙收到的密码都走它',
     'in：数字数组；len：位数', '1 = 密码正确，0 = 不正确'),
]

IF_AS608 = [
    ('void As608_Init(uint32_t baud)',
     '初始化 USART2 并把模块下电，再用 ReadSysPara 探一次在线；探不到只记录状态，不影响其它功能',
     'baud：波特率，工程默认 57600', 'void'),
    ('void As608_SetBaud(uint32_t baud)',
     '重设串口波特率，用于逐个波特率探测模块实际工作在哪个档位',
     'baud：目标波特率', 'void'),
    ('uint8_t As608_Exec(uint8_t cmd, const uint8_t *param, uint8_t n, uint16_t timeoutMs)',
     '组包并发送一条命令，等应答包收全后校验包头、长度与校验和，把内容缓存起来',
     'cmd：命令字；param：参数区，可为 0；n：参数字节数；timeoutMs：应答超时',
     '0 = 成功（应答已进缓存）；非 0 为模块返回的错误码或本地超时码'),
    ('void As608_Run(void)',
     '推进收包状态机，非阻塞地收集应答字节；主循环每 10ms 调一次',
     'void', 'void'),
    ('uint8_t As608_Busy(void)',
     '查询上一条命令是否还在等应答',
     'void', '1 = 忙，0 = 空闲'),
    ('uint8_t As608_Err(void)',
     '取上一条命令的结果码',
     'void', '0 = 成功，其余为 AS608 错误码或本地超时码'),
    ('uint8_t As608_LastCmd(void)',
     '取上一条执行的命令字',
     'void', '命令字'),
    ('uint8_t As608_Resp8(uint8_t idx)',
     '读应答包里第 idx 个字节',
     'idx：从 0 开始的偏移', '该字节内容'),
    ('uint16_t As608_Resp16(uint8_t idx)',
     '读应答包里第 idx 起的两字节，按高字节在前拼成 16 位数',
     'idx：偏移', '16 位数值'),
    ('uint8_t As608_RespLen(void)',
     '取应答包有效字节数',
     'void', '字节数'),
    ('const char *As608_ErrText(uint8_t err)',
     '把错误码翻译成可读文本，串口打印排障时用',
     'err：错误码', '常量字符串指针'),
]

IF_APPFP = [
    ('void Fp_Init(void)',
     '初始化 AS608 与触摸脚 PA0，探在线并读一次指纹库容量',
     'void', 'void'),
    ('void Fp_Poll(void)',
     '指纹状态机总入口，主循环每 10ms 调一次；推进探测、验证、录入、删除、清空各流程',
     'void', 'void'),
    ('uint8_t Fp_Online(void)',
     '查询模块是否在线',
     'void', '1 = 在线，0 = 无应答'),
    ('FpState_t Fp_State(void)',
     '取当前流程状态',
     'void', 'FpState_t 枚举值'),
    ('FpResult_t Fp_Result(void)',
     '取一次流程结果并自动清掉（一次性）',
     'void', 'FpResult_t 枚举值，取完复位为无结果'),
    ('void Fp_Clear(void)',
     '清掉结果与匹配信息',
     'void', 'void'),
    ('void Fp_VerifyStart(void)',
     '启动 1:N 指纹验证；锁屏检测到手指后调用',
     'void', 'void'),
    ('void Fp_EnrollStart(void)',
     '启动录入一枚新指纹（两次按压），自动在库里找第一个空编号',
     'void', 'void'),
    ('void Fp_DeleteStart(void)',
     '读指纹索引表；读完后状态置为列表就绪，供菜单显示已有指纹',
     'void', 'void'),
    ('void Fp_DeleteNow(uint8_t id)',
     '删除指定编号的指纹模板',
     'id：指纹库编号 0~255', 'void'),
    ('void Fp_EmptyStart(void)',
     '清空整个指纹库',
     'void', 'void'),
    ('void Fp_Cancel(void)',
     '中止当前流程并停在空闲态；自动上锁与回锁屏时调用',
     'void', 'void'),
    ('uint8_t Fp_MatchId(void)',
     '取验证通过或录入成功对应的指纹编号',
     'void', '指纹编号 0~255'),
    ('uint16_t Fp_MatchScore(void)',
     '取搜索比对得分',
     'void', '得分 0~255，越大越像'),
    ('uint16_t Fp_Capacity(void)',
     '取指纹库容量',
     'void', '可存指纹数，AS608 出厂为 300'),
    ('uint8_t Fp_IdCount(void)',
     '取指纹库里已录入的模板数',
     'void', '已录入个数'),
    ('uint8_t Fp_IdAt(uint8_t idx)',
     '取已录入的第 idx 个指纹编号',
     'idx：序号 0 ~ Fp_IdCount()-1', '指纹编号'),
    ('uint8_t Fp_TouchActive(void)',
     '读触摸脚 PA0，判断手指在不在感应区',
     'void', '1 = 有手指，0 = 无'),
]

IF_RC522 = [
    ('uint8_t Rc522_Init(void)',
     '配置软件 SPI 引脚与复位脚，硬复位后写配置寄存器，再读版本号判断芯片在不在',
     'void', 'RC522_RET_OK 或 RC522_RET_OFFLINE'),
    ('uint8_t Rc522_Probe(void)',
     '读一次 VersionReg 判断芯片是否在位；只有读到 0x00 或 0xFF 才算离线',
     'void', 'RC522_RET_OK / RC522_RET_OFFLINE'),
    ('uint8_t Rc522_Version(void)',
     '取最近一次读到的芯片版本号',
     'void', '版本字节；本板国产兼容片实测为 0xB2'),
    ('void Rc522_Antenna(uint8_t on)',
     '打开或关闭天线；关掉后模块功耗降到微安级',
     'on：1 = 打开，0 = 关闭', 'void'),
    ('uint8_t Rc522_ReadCard(uint8_t uid[4])',
     '完整走一次寻卡 → 防冲突 → 选卡，取回 4 字节 UID；任何一步失败都返回对应错误码',
     'uid：输出缓冲，4 字节', 'RC522_RET_OK / NOCARD / OFFLINE / ERR_FRAME'),
    ('void Rc522_Halt(void)',
     '让卡片进入休眠；读完卡必须调，否则同一张卡会每 180ms 反复触发开锁',
     'void', 'void'),
    ('void Rc522_SoftReset(void)',
     '软复位芯片寄存器，寻卡连续异常时用来恢复',
     'void', 'void'),
    ('uint8_t Rc522_ReadReg(uint8_t reg)',
     '读一个寄存器：地址字节为 (reg<<1)&0x7E 再或上 0x80',
     'reg：寄存器地址 0~0x3F', '寄存器值'),
    ('void Rc522_WriteReg(uint8_t reg, uint8_t val)',
     '写一个寄存器：地址字节为 (reg<<1)&0x7E',
     'reg：寄存器地址；val：写入值', 'void'),
]

IF_CSTORE = [
    ('void Card_StoreInit(void)',
     '读片内 Flash 数据页，校验魔字与 CRC16，把卡片表载入内存镜像；校验失败按空库处理',
     'void', 'void'),
    ('uint8_t Card_Count(void)',
     '取当前已存卡片数',
     'void', '0~8'),
    ('uint8_t Card_GetUid(uint8_t idx, uint8_t *uid)',
     '取第 idx 张卡的 UID',
     'idx：序号 0 ~ Card_Count()-1；uid：输出 4 字节', '1 = 有效，0 = 该位置为空'),
    ('uint8_t Card_Find(const uint8_t *uid)',
     '在库里顺序查找指定 UID',
     'uid：待查找的 4 字节 UID', '命中返回序号 0~7；未找到返回 CARD_NOT_FOUND(0xFF)'),
    ('uint8_t Card_Add(const uint8_t *uid, uint8_t *id)',
     '追加一张卡并立刻落盘（只在真正添加时擦写 Flash，寻卡不碰）',
     'uid：4 字节 UID；id：输出该卡在库里的序号', '1 = 添加成功，0 = 库满或写失败'),
    ('uint8_t Card_Del(uint8_t idx)',
     '删除指定序号的卡，把后面的前移，然后落盘',
     'idx：序号', '1 = 删除成功，0 = 序号非法'),
    ('uint8_t Card_ClearAll(void)',
     '清空整库并落盘',
     'void', '1 = 成功，0 = 写失败'),
]

IF_APPCARD = [
    ('uint8_t Card_Init(void)',
     '初始化 RC522 与卡片库，并探一次在线',
     'void', 'RC522_RET_OK 或 RC522_RET_OFFLINE'),
    ('uint8_t Card_Online(void)',
     '查询读卡模块是否在线',
     'void', '1 = 在线，0 = 无应答'),
    ('uint8_t Card_Version(void)',
     '取最近一次读到的芯片版本号',
     'void', '版本字节，本板实测 0xB2'),
    ('void Card_Poll(void)',
     '锁屏寻卡入口，内部按 180ms 节流；读到卡后比对卡片库并把结果置位',
     'void', 'void'),
    ('CardResult_t Card_Result(void)',
     '取一次刷卡结果并自动清掉（一次性）',
     'void', 'CARD_RES_NONE / UNLOCK / DENIED'),
    ('void Card_ClearResult(void)',
     '清掉刷卡结果',
     'void', 'void'),
    ('void Card_LastUid(uint8_t *out)',
     '取最近一次读到的卡号；界面要显示「卡号 XXXX」时调用',
     'out：输出 4 字节 UID', 'void'),
    ('void Card_EnrollStart(void)',
     '启动录入，进入「请放卡」等待状态',
     'void', 'void'),
    ('void Card_EnrollPoll(void)',
     '录入流程推进，主循环每 10ms 调一次',
     'void', 'void'),
    ('CardEnroll_t Card_EnrollResult(void)',
     '取一次录入结果并自动清掉（一次性）',
     'void', 'CARD_EN_OK / EXIST / FULL / OFFLINE / TIMEOUT / CANCEL'),
    ('uint8_t Card_EnrollNo(void)',
     '取录入成功后该卡在库里的序号',
     'void', '序号 0~7'),
    ('void Card_EnrollCancel(void)',
     '中止录入；自动上锁与回锁屏时调用',
     'void', 'void'),
]

IF_USART = [
    ('void Usart_Init(uint32_t baud)',
     'PA9 配复用推挽、PA10 配浮空输入，设置波特率，打开接收中断并配置 NVIC 优先级',
     'baud：波特率，工程默认 115200', 'void'),
    ('void Usart_SendByte(uint8_t byte)',
     '阻塞发一个字节，等发送数据寄存器空才返回',
     'byte：待发送字节', 'void'),
    ('void Usart_SendString(const char *str)',
     '阻塞发一串以 0 结尾的字符串；蓝牙回 OK / ERR / LOCKED 时用',
     'str：字符串指针', 'void'),
    ('uint8_t Usart_ReadByte(uint8_t *pByte)',
     '从环形缓冲取一个字节，缓冲空则立即返回、不等待',
     'pByte：用于返回取到的字节', '1 = 取到，0 = 缓冲空'),
    ('void Usart_Flush(void)',
     '丢掉环形缓冲里所有还没读的字节；回锁屏时清掉残留数据，避免旧数据被当成刚收到的密码',
     'void', 'void'),
]

IF_BT = [
    ('void Bt_Init(void)',
     '初始化 USART1，清空帧缓冲、失败计数与锁定状态',
     'void', 'void'),
    ('void Bt_Reset(void)',
     '回锁屏时调用：丢掉半截帧、丢掉旧结果、清空串口缓冲',
     'void', 'void'),
    ('void Bt_Poll(void)',
     '断帧与密码校验的总入口，主循环每 10ms 调一次',
     'void', 'void'),
    ('BtResult_t Bt_Result(void)',
     '取一次开锁结果并自动清掉（一次性）',
     'void', 'BT_RES_NONE / OK / BAD / LOCKED'),
    ('void Bt_ClearResult(void)',
     '清掉结果',
     'void', 'void'),
    ('uint8_t Bt_LockLeftSec(void)',
     '取防爆破锁定的剩余秒数',
     'void', '剩余秒数；0 表示当前没有锁定'),
]

IF_UILOCK = [
    ('void UI_Lock_Draw(const RTC_DateTime_t *dt)',
     '画整张锁屏：顶部标题、大号时间、年月日与底部操作提示',
     'dt：当前日期时间', 'void'),
    ('void UI_Lock_UpdateClock(const RTC_DateTime_t *dt)',
     '只重画时间与日期区域，秒变化时调用，避免整屏刷新造成闪烁',
     'dt：当前日期时间', 'void'),
    ('void UI_Lock_StatusLine(const char *ascii)',
     '在锁屏底部写一行 ASCII 状态；指纹或读卡模块离线时用来提示',
     'ascii：提示文本', 'void'),
    ('void UI_Pwd_Draw(const uint8_t *digits, uint8_t len)',
     '画密码输入页：标题、6 个圆点占位与底部按键提示',
     'digits：已输入的数字数组；len：已输入位数', 'void'),
    ('void UI_Pwd_UpdateEcho(uint8_t len)',
     '只更新圆点那一行，每按一个数字调一次',
     'len：当前位数', 'void'),
    ('void UI_Pwd_ShowUnlocked(void)',
     '画「已解锁」页，锁图标切换成打开状态',
     'void', 'void'),
    ('void UI_Pwd_ShowWrong(void)',
     '画「密码错误」页并清掉已输入内容',
     'void', 'void'),
    ('void UI_Pwd_ShowTip(const char *ascii)',
     '在密码页底部显示一行 ASCII 提示，例如防爆破的剩余锁定秒数',
     'ascii：提示文本', 'void'),
]

IF_UIFP = [
    ('void UI_Fp_DrawResult(const char *title, const char *line, uint8_t ok)',
     '画指纹结果页：标题 + 一行说明 + 与正文同高的 OK / FAIL 结论',
     'title：标题；line：说明文字；ok：1 = 成功，0 = 失败', 'void'),
    ('void UI_Fp_DrawDelList(uint8_t total, uint8_t selIdx, uint8_t selId)',
     '画指纹删除列表页，一屏三项，选中项反白',
     'total：总数；selIdx：选中序号；selId：选中项对应的指纹编号', 'void'),
    ('void UI_Fp_Num2(uint8_t v, char *out)',
     '把 0~99 的编号格式化成两位十进制字符串，不足两位补 0',
     'v：待格式化数值；out：输出缓冲，至少 3 字节', 'void'),
    ('void UI_Card_DrawPage(const char *title, const char *line1, const char *line2, uint8_t hintMode)',
     '画卡片通用页：标题 + 两行正文 + 底部提示；任一行传 0 表示不画',
     'title / line1 / line2：标题与两行正文；hintMode：底部提示组合', 'void'),
    ('void UI_Result_Draw(const char *title, const char *line, uint8_t ok)',
     '画通用结果页；刷卡被拒与蓝牙密码错误共用它，保证几种失败画面完全一致',
     'title：标题；line：说明文字；ok：1 = 成功，0 = 失败', 'void'),
    ('void UI_Card_DrawList(uint8_t total, uint8_t selIdx, const uint8_t *uid)',
     '画卡片删除列表页，一行显示「序号 + 卡号」',
     'total：总数；selIdx：选中序号；uid：选中卡 UID，传 0 时只画编号', 'void'),
    ('void UI_Card_UidHex(const uint8_t *uid, char *out)',
     '把 4 字节 UID 写成 8 位大写十六进制字符',
     'uid：4 字节 UID；out：输出缓冲，至少 9 字节', 'void'),
]

IF_MENU = [
    ('void Menu_Enter(void)',
     '进入设置菜单，把选中项复位到第 1 项；每次进入都重建菜单状态',
     'void', 'void'),
    ('MenuResult_t Menu_Tick(uint8_t key)',
     '处理一个按键事件，推动菜单浏览、指纹录入删除、改密码、改时间、卡片录入删除各子流程',
     'key：键号；KEY_NONE 表示这一拍没有按键', 'MENU_STAY 留在菜单；MENU_EXIT 退出，由调用方负责上锁并回锁屏'),
]

IF_APP = [
    ('void App_Run(void)',
     '工程唯一对外入口：按固定顺序初始化全部模块，画出锁屏后进入 10ms 主循环，永不返回',
     'void', '不返回'),
]

IF_TEST = [
    ('void UiTest_Run(void)',
     '依次绘制全部 37 张界面并每张停住，配合 SWD 读显存逐个核对版面与文案',
     'void', 'void'),
    ('void KeyTest_Run(void)',
     '按键测试：每按一个键就在屏上显示键号以及它所在的行号与列号',
     'void', 'void'),
]

# 三列表 / 四列表数据
T_ARCH = [
    ['状态', '进入条件', '主要动作'],
    ['APP_ST_LOCK', '上电、任何流程结束后回到锁屏', '刷日期时间；轮询蓝牙与读卡；检测按键与指纹触摸脚'],
    ['APP_ST_PWD', '锁屏下按 Bck 键', '接收数字键输入，凑够密码位数后自动校验'],
    ['APP_ST_FP', '锁屏检测到手指（PA0 高电平）', '启动 1:N 指纹验证，等待模块返回结果'],
    ['APP_ST_CARD_SHOW', '刷卡 UID 命中卡片库', '先显示「卡号 A1B2C3D4」0.7 秒，再开锁'],
    ['APP_ST_UNLOCKED', '密码、指纹、卡片、蓝牙任一路通过', '继电器吸合 15 秒，显示「已解锁」，1 秒后进设置菜单'],
    ['APP_ST_DENIED', '密码错、卡未授权、指纹不符、蓝牙密码错', '显示失败页，1.5 秒后回锁屏'],
    ['APP_ST_MENU', '开锁流程走完自动进入', '六项设置菜单；按 Bck 或空闲超时退出，退出即上锁回锁屏'],
]

T_PIN = [
    ['功能', '引脚', '配置', '说明'],
    ['OLED SCL', 'PB12', '开漏输出', '软件 I2C 时钟线'],
    ['OLED SDA', 'PB13', '开漏输出', '软件 I2C 数据线'],
    ['矩阵键盘 行 0~3', 'PB0、PB1、PA11、PB3', '推挽输出', '逐行拉低扫描；PB3 需关闭 JTAG 才可用'],
    ['矩阵键盘 列 0~3', 'PB4、PB5、PB6、PB10', '上拉输入', '读列电平判断哪个键按下'],
    ['继电器', 'PB9', '推挽输出', '高电平吸合，模拟开锁'],
    ['蜂鸣器', 'PB8', '上拉输入（当前禁用）', '当前版本关闭，避免上电误鸣'],
    ['指纹 串口', 'PA2 = TX、PA3 = RX', '复用推挽 / 浮空输入', 'USART2，57600-8-N-1'],
    ['指纹 触摸', 'PA0', '上拉输入', '手指放上输出高电平，锁屏据此启动验证'],
    ['RC522 片选', 'PA7', '推挽输出', 'CS，低电平有效'],
    ['RC522 时钟', 'PA6', '推挽输出', '软件 SPI 的 SCK'],
    ['RC522 数据出', 'PA5', '推挽输出', 'MOSI，主机到从机'],
    ['RC522 数据入', 'PA4', '上拉输入', 'MISO，从机到主机'],
    ['RC522 复位', 'PA1', '推挽输出', 'RST，高电平复位'],
    ['蓝牙 串口', 'PA9 = TX、PA10 = RX', '复用推挽 / 浮空输入', 'USART1，115200-8-N-1'],
]

T_MOD = [
    ['模块', '源文件', '主要职责', '使用引脚'],
    ['系统时基模块', 'systick_drv.c / .h', '1ms 节拍、毫秒延时、运行时间统计', '无'],
    ['显示模块', 'oled_drv.c / .h', 'SSD1306 初始化、显存管理、ASCII 与中文显示、居中排版', 'PB12、PB13'],
    ['字库', 'font8x8.c / .h、cn_font16.c / .h', '8x8 ASCII 点阵与 16x16 中文点阵（收录 80 个汉字）', '无'],
    ['中文消息', 'cn_text.h', '界面全部中文文案（GBK 转义常量，共 60 条）', '无'],
    ['按键模块', 'key_matrix.c / .h', '4x4 矩阵键盘行列扫描、20ms 消抖、单击边沿与键位映射', 'PB0、PB1、PA11、PB3~PB6、PB10'],
    ['门锁执行模块', 'lock_io.c / .h', '继电器开关与状态查询、蜂鸣器定时鸣叫', 'PB9、PB8'],
    ['时钟模块', 'rtc_drv.c / .h', 'RTC 初始化与掉电恢复、日期与计数器双向换算', '无（外接 32.768kHz 晶振）'],
    ['密码管理模块', 'pwd_store.c / .h', '密码读写与校验，存备份域寄存器 BKP_DR3~DR5', '无'],
    ['指纹驱动', 'as608.c / .h', 'AS608 协议帧组包、应答校验、命令执行与结果缓存', 'PA2、PA3'],
    ['指纹业务', 'app_fp.c / .h', '在线探测、1:N 验证、录入、删除、清空、列表读取状态机', 'PA0（触摸检测）'],
    ['读卡驱动', 'rc522.c / .h', '软件 SPI 读写寄存器、寻卡、防冲突、选卡、休眠', 'PA1、PA4~PA7'],
    ['卡片库', 'card_store.c / .h', '8 张卡片存在片内 Flash 0x08010000 页，带魔字与 CRC16', '无'],
    ['读卡业务', 'app_card.c / .h', '锁屏寻卡节流、比对卡片库、录入与删除流程', '无'],
    ['蓝牙模块', 'usart_drv.c / .h、bt_lock.c / .h', 'USART1 环形缓冲接收、双策略断帧、密码校验与防爆破', 'PA9、PA10'],
    ['指纹串口', 'usart2_drv.c / .h', 'USART2 收发与发送完成判断，专供 AS608 使用', 'PA2、PA3'],
    ['界面模块', 'ui_lock / ui_pwd / ui_fp / ui_card.c / .h', '锁屏、密码、指纹、卡片四套界面与通用结果页', '无'],
    ['设置菜单模块', 'app_menu.c / .h', '六项菜单的选中滚动、按键分发与空闲退出', '无'],
    ['应用主控模块', 'app_lock.c / .h', '上电初始化、锁屏状态机、开锁与自动上锁、模块调度', '无'],
    ['自检模块', 'ui_test.c / .h、key_test.c / .h', '逐一绘制全部界面并停住，供 SWD 抓屏核对版面', '无'],
]

T_LAYOUT = [
    ['页面元素', '纵坐标', '占用高度'],
    ['标题行', 'y = 0', '16 像素（0~15）'],
    ['第一行正文', 'y = 21', '16 像素（21~36）'],
    ['第二行正文', 'y = 39', '16 像素（39~54）'],
    ['底部提示', 'y = 56', '8 像素（56~63），只能是 ASCII'],
    ['删除列表 总数行', 'y = 18', '16 像素（18~33）'],
    ['删除列表 选中行', 'y = 36', '16 像素（36~52）'],
]

T_KEYMAP = [
    ['键位', '矩阵行列', '语义'],
    ['S1 ~ S4', '行 3，列 0 ~ 3', '数字 1、2、3，Bck（返回）'],
    ['S5 ~ S8', '行 2，列 0 ~ 3', '数字 4、5、6，Del（删除）'],
    ['S9 ~ S12', '行 1，列 0 ~ 3', '数字 7、8、9，Dis（上翻）'],
    ['S13 ~ S16', '行 0，列 0 ~ 3', 'Clr（清零）、0、Chg（下翻）、Ok（确定）'],
    ['说明', '行号与原理图丝印相反', '矩阵行序按实物接线反着排，代码里已统一换算，改线只改 KeyMx_KeyRow'],
]

T_BKP = [
    ['寄存器', '取值', '说明'],
    ['BKP_DR3', '0x5A00 或 密码位数', '高字节是魔字 0x5A，低字节是密码位数 4~6'],
    ['BKP_DR4', 'd0 | d1<<4 | d2<<8 | d3<<12', '第 1~4 位数字，每位占 4 bit'],
    ['BKP_DR5', 'd4 | d5<<4', '第 5~6 位数字'],
    ['失效条件', 'VBAT 断电', '电池没电后自动回到出厂密码 123456，实训场景下反而方便复位'],
]

T_FPUART = [
    ['项目', '取值', '说明'],
    ['波特率', '57600', '工程默认；若模块被改过档位，上电会依次试 115200 / 9600 / 38400 / 19200'],
    ['数据位', '8', '—'],
    ['停止位', '1', '—'],
    ['校验', '无', '—'],
    ['流控', '无', '—'],
    ['触摸脚', 'PA0', '手指放上输出高电平，用来在锁屏唤醒验证'],
]

T_FPFRAME = [
    ['字段', '字节数', '取值', '说明'],
    ['包头', '2', 'EF 01', '固定'],
    ['芯片地址', '4', 'FF FF FF FF', '模块出厂地址，一般不改'],
    ['包标识', '1', '01 命令 / 02 数据 / 07 应答', '区分命令包与应答包'],
    ['包长度', '2', 'N（高字节在前）', '包标识 + 包长度 + 包内容 的总字节数'],
    ['包内容', 'N', '命令字 + 参数', '常用命令字见下表'],
    ['校验和', '2', 'Sum（高字节在前）', '从包标识起逐字节累加，取低 16 位'],
]

T_FPCMD = [
    ['命令字', '含义', '参数'],
    ['0x01', 'GenImg：采集指纹图像', '无'],
    ['0x02', 'Img2Tz：生成特征并存入缓冲区', '缓冲号 1~2'],
    ['0x04', 'RegModel：把两个缓冲区合并成模板', '无'],
    ['0x05', 'Store：把模板存进指纹库', '缓冲号 + 编号'],
    ['0x06', 'LoadChar：从指纹库载入模板', '缓冲号 + 编号'],
    ['0x08', 'Match：比对两个缓冲区', '无'],
    ['0x09', 'Search：在库里做 1:N 搜索', '缓冲号 + 起始编号 + 总数'],
    ['0x0C', 'DeletChar：删除指定编号的模板', '编号 + 数量'],
    ['0x0D', 'Empty：清空整个指纹库', '无'],
    ['0x0E', 'ReadSysPara：读系统参数（含容量）', '无'],
    ['0x1F', 'ReadIndexTable：读指纹索引表', '页码；返回 32 字节位图，LSB 在前'],
]

T_RCREG = [
    ['寄存器', '地址', '用途'],
    ['CommandReg', '0x01', '软复位与收发控制'],
    ['ComIrqReg', '0x04', '中断标志；寻卡等 RxIRq，防冲突等 RxIRq 或 TimerIRq'],
    ['ErrorReg', '0x06', '错误标志；校验错与冲突错都看它'],
    ['FIFODataReg', '0x09', '收发数据先进 FIFO，再从这里读出'],
    ['FIFOLevelReg', '0x0A', 'FIFO 里现有字节数'],
    ['ControlReg', '0x0C', '定时器启动位'],
    ['BitFramingReg', '0x0D', '收发位数设置；寻卡写 0x07，防冲突写 0x00'],
    ['CollReg', '0x0E', '防冲突结果'],
    ['ModeReg', '0x11', 'CRC 预设值'],
    ['TxControlReg', '0x14', '天线开关，bit0 与 bit1 都要置 1'],
    ['TModeReg', '0x2A', '内部定时器预设'],
    ['TPrescalerReg', '0x2D', '定时器分频'],
    ['TReloadRegL / H', '0x2B / 0x2C', '定时器重装值'],
    ['VersionReg', '0x37', '版本号；判在线只排除 0x00 与 0xFF'],
]

T_CARDLAYOUT = [
    ['偏移', '字节数', '内容', '说明'],
    ['0', '4', '43 41 52 44（“CARD”）', '魔字；判断这一页有没有有效数据'],
    ['4', '1', '0 ~ 8', '已存卡片数'],
    ['5', '40', '8 × （UID[4] + 有效位）', '每张卡占 5 字节：4 字节 UID + 1 字节有效位'],
    ['45', '2', 'CRC16', '前面 45 字节的校验和'],
    ['47', '977', '0xFF 填充', '整页 1KB，其余留空；擦除后本来就是 0xFF'],
]

T_BTUART = [
    ['项目', '取值', '说明'],
    ['波特率', '115200', 'JDY-06 与 JDY-10 两份手册都写明出厂默认 115200，不用先发 AT 改'],
    ['数据位 / 停止位 / 校验', '8-N-1', '—'],
    ['服务 UUID', 'FFE0', '蓝牙调试助手连上后能看到的服务'],
    ['透传特征', 'FFE1', '手机往这里写密码，模块原样转到串口'],
    ['配置特征', 'FFE2', '模块 AT 配置用；手机端也能看到，但本工程不用'],
]

T_BTRULE = [
    ['场景', '处理方式', '原因'],
    ['帧尾带回车或换行', '立刻结算这一帧', '串口助手的「发送新行」模式，最干脆'],
    ['帧尾什么都没带', '静默 120ms 后结算', 'nRF Connect 手动写特征值不会自己加换行，只认换行就永远收不到'],
    ['帧里含非数字字符', '整帧丢弃，不计入失败次数', '模块的 AT 回显、串口工具乱发的内容不能把门锁死'],
    ['帧长超过密码最大位数', '判为错误密码', '密码最长 6 位，多余的字节说明不是密码'],
    ['连续 5 次密码错', '锁定 30 秒，期间一律回 LOCKED', '防止拿手机逐个试密码'],
    ['从菜单回到锁屏', '调 Bt_Reset 清掉残帧与串口缓冲', '菜单期间收到的旧数据不能被当成刚输入的密码'],
]

T_MENUKEY = [
    ['按键', '作用', '说明'],
    ['Dis', '上翻', '选中项上移，滚到顶回到底'],
    ['Chg', '下翻', '选中项下移，滚到底回到顶'],
    ['Ok', '确定', '进入选中项对应的子流程'],
    ['Bck', '返回', '退回上一级；在菜单根则退出菜单、上锁并回锁屏'],
    ['空闲超时', '自动退出', '与自动上锁一致：退出即上锁、屏幕回锁屏'],
]

T_INIT = [
    ['步骤', '调用接口', '作用'],
    ['1', 'SysTick_Init', '建立 1ms 时基；后面所有超时与延时都依赖它'],
    ['2', 'OLED_Init', '屏幕最先起来，后面每一步都能把状态显示出来'],
    ['3', 'RTC_Init', '打开备份域时钟；Pwd_Init 依赖它才能读写 BKP'],
    ['4', 'Pwd_Init', '读回密码，记录无效则写入出厂密码 123456'],
    ['5', 'LockIo_Init', '继电器先置低，确保上电不会误吸合'],
    ['6', 'KeyMx_Init', '键盘扫描就绪'],
    ['7', 'Fp_Init', '探指纹模块；探不到只降级该路，不影响密码与刷卡'],
    ['8', 'Card_Init', '探读卡模块；同样只降级，不阻塞其它功能'],
    ['9', 'Bt_Init', '打开 USART1 接收，进入蓝牙待命'],
    ['10', 'UI_Lock_Draw', '画出锁屏，随后进入 10ms 主循环'],
]

# ---------------------------------------------------------------- 章节内容
BLOCKS = [
    ('h1', '2 场景和流程'),
    ('h3', '2.1 系统组成'),
    ('p', '本工程是一套完整的智能门锁控制器，由主控板、人机界面、三种身份认证通道和一套执行机构组成，'
          '不需要上位机参与即可独立完成认证与开关锁。各部分的分工如下表。'),
    ('t3', [
        ['组成', '实现', '说明'],
        ['主控', 'YB-DSF01-V1.0 开发板（STM32F103C8）', '标称 64KB Flash，实测 128KB；20KB RAM，主频 72MHz'],
        ['人机界面', '0.96 寸 OLED（SSD1306，128x64）', '软件 I2C：SCL = PB12、SDA = PB13；显示锁屏、密码、菜单与各类提示'],
        ['密码输入', '4x4 矩阵键盘', '8 根线：PB0、PB1、PA11、PB3、PB4、PB5、PB6、PB10；逐行扫描读数'],
        ['执行机构', '板载继电器', 'PB9 高电平吸合，用通断模拟门锁开合'],
        ['声光提示', '板载有源蜂鸣器', 'PB8；当前版本默认关闭，避免上电误鸣'],
        ['指纹识别', 'AS608 光学指纹模块（U5 座）', 'USART2：PA2 = TX、PA3 = RX，57600-8-N-1；触摸检测接 PA0'],
        ['卡片识别', 'RC522 读卡模块', '软件 SPI：CS = PA7、SCK = PA6、MOSI = PA5、MISO = PA4、RST = PA1'],
        ['无线开锁', 'JDY-06 / JDY-10 蓝牙串口模块', 'USART1：PA9 = TX、PA10 = RX，115200-8-N-1'],
        ['时钟', '片内 RTC + 32.768kHz 晶振 + 纽扣电池', '锁屏显示年月日时分秒；主电源断掉后由 VBAT 维持走时'],
    ]),
    ('h3', '2.2 分层设计'),
    ('p', '应用层不直接操作任何寄存器，全部通过驱动层接口完成；驱动层只负责把外设细节封装成函数，'
          '不关心业务；应用层之间通过显式的状态与结果查询接口通信，不用全局变量互相读。'),
    ('t3', [
        ['层次', '目录', '职责'],
        ['应用层', 'App_User', '锁屏状态机、开锁与自动上锁、密码校验、指纹与读卡业务流程、设置菜单、界面绘制'],
        ['驱动层', 'Drv_Common', '把外设细节封装成函数接口，向上屏蔽寄存器操作；本工程共 10 个驱动与 2 份字库'],
        ['库层', 'STM32_Library、Arm_Kernel', 'STM32F10x 标准外设库 V3.6 与 CMSIS 内核文件'],
        ['启动层', 'Startup', '中断向量表、复位入口、栈顶定义'],
    ]),
    ('h3', '2.3 模块设计'),
    ('p', '工程共 19 个模块。下表按「驱动在前、业务在后」的顺序列出，最后一个自检模块只在验证阶段使用。'),
    ('t4', T_MOD),

    ('h1', '3 模块(组件)及接口说明'),
    ('h3', '3.1 系统架构与调用关系'),
    ('p', '主循环只有一个，所有模块都是「被轮询」而不是「互相回调」：每 10ms 依次调用按键、门锁、'
          '指纹、读卡、蓝牙各一次 Poll 接口，谁有结果就通过各自的 Result 接口取出来。'
          '这样任何一路模块卡住都不会影响其它路，也不会出现中断里做业务的情况。'
          '唯一的例外是串口接收：USART1 与 USART2 都在中断里把字节塞进环形缓冲，'
          '解析留给主循环，中断服务函数只做搬运。'),
    ('h4', '3.1.1 锁屏状态机'),
    ('p', '四种开锁方式最终都收口到同一条路径：验证通过 → 继电器吸合 → 显示「已解锁」→ 进入设置菜单 → 15 秒后自动上锁并回锁屏。'
          '失败则一律走失败页，1.5 秒后回锁屏。状态定义与迁移条件如下表。'),
    ('t3', T_ARCH),
    ('h4', '3.1.2 硬件资源与引脚分配'),
    ('p', '下表是本工程占用的全部引脚。需要注意两点：一是 PB3、PB4、PB5 出厂默认被 JTAG 占用，'
          '必须在初始化时调用 GPIO_Remap_SWJ_JTAGDisable 关闭 JTAG 只保留 SWD，键盘才能正常工作；'
          '二是 PA10 既是 USART1 的接收脚，板上也可能接了 USB 转串口芯片，'
          '若同时焊接需要确认两者不会互相顶电平。'),
    ('t4', T_PIN),
    ('h4', '3.1.3 编译与资源占用'),
    ('p', '工程使用 Keil MDK 5.39 与标准外设库 V3.6 编译，结果为 0 Error、0 Warning。'
          '代码段 24936 字节、只读数据 4120 字节、已初始化数据 248 字节、未初始化数据 3120 字节，'
          'Flash 占用约 22.2%、RAM 占用约 16.4%，都留有充足余量。'
          '下载时用整片擦除 + 烧录 + 读回逐字节比对三步走：只擦「要改的扇区」会把旧工程的残留代码留在板上，'
          '拼出来的固件半新半旧，现象是按键回的是上一版文案，非常容易误判成逻辑错误。'),

    ('h3', '3.2 系统时基模块及接口说明'),
    ('p', '全工程的超时、节流、延时都建立在同一个 1ms 计数器上，不另设定时器。'
          '所有需要「等一段时间」的地方都写成「记住起始时间戳，每次进来做差比较」，'
          '而不是死等循环，这样主循环永远不会被某一路拖住。'),
    ('h4', '3.2.1 SysTick 接口'),
    ('if', IF_SYSTICK),

    ('h3', '3.3 显示模块及接口说明'),
    ('p', '屏幕是只写设备，写进去就读不回来，所以驱动层自己维护一块 1KB 的显存镜像（8 页 × 128 列），'
          '所有绘图函数改的都是内存，只有调 OLED_Refresh 才整屏刷到屏上。'
          '局部更新优先用 OLED_ClearBlock 清一块再重画，比整屏刷快一个数量级，也不闪。'
          '中文字库是 16x16 点阵，按 GBK 编码线性查找；ASCII 用 8x8 点阵，需要大号时逐行垂直放大两倍成 8x16。'),
    ('h4', '3.3.1 OLED 驱动接口'),
    ('if', IF_OLED),
    ('h4', '3.3.2 16x16 中文字库'),
    ('p', '字库由脚本从界面文案里自动扫出用到的汉字生成，共 80 字，覆盖全部提示。'
          '新增文案时先跑一次字模生成脚本，否则屏上会画成空心方框。'),
    ('if', IF_FONT),
    ('h4', '3.3.3 版面参数约定'),
    ('p', '所有界面共用同一套纵向版面参数，页面之间来回切换时标题和正文不会上下跳。'
          '新增页面时先按这张表算出「y + 文本高度」，绝不能压到下一行——这一点在开发中踩过两次坑。'),
    ('t3', T_LAYOUT),

    ('h3', '3.4 按键模块及接口说明'),
    ('p', '4x4 矩阵键盘用 8 根 GPIO 逐行扫描：先把行 0 拉低、读四列，再换行 1，四行扫完得到一个 16 位掩码。'
          '每 20ms 采一次，连续两次一致才认为稳定，避免机械抖动被当成多次按下。'
          '按键语义由应用层决定，驱动层只负责给出「哪个键号被按下」。'),
    ('h4', '3.4.1 矩阵键盘驱动接口'),
    ('if', IF_KEY),
    ('h4', '3.4.2 键位映射'),
    ('p', '矩阵的行号与原理图丝印是相反的，实物上第一排实际接在行 3。下表是实测结果，'
          '换板或改线时只需要改 KeyMx_KeyRow 的换算表。'),
    ('t3', T_KEYMAP),

    ('h3', '3.5 门锁执行模块及接口说明'),
    ('p', '继电器与蜂鸣器共用同一套「设定时长、由 Tick 关掉」的机制，调用方给一个毫秒数就能走开，'
          '不需要自己开定时器。继电器状态由软件镜像记录，自动上锁靠查询这个镜像判断要不要动作。'),
    ('h4', '3.5.1 继电器与蜂鸣器接口'),
    ('if', IF_LOCKIO),

    ('h3', '3.6 时钟模块及接口说明'),
    ('p', 'RTC 用外部 32.768kHz 晶振配合备份域电池走时，主电源断掉时间也继续走。'
          '上电时先读备份域的标记位：标记有效说明时间还在，直接沿用；标记无效说明电池掉过，'
          '按编译时的默认时间重新配置。日期与秒数之间可以双向换算，设置菜单改时间时走的就是这条路径。'),
    ('h4', '3.6.1 RTC 接口'),
    ('if', IF_RTC),
    ('h4', '3.6.2 掉电恢复策略'),
    ('p', '备份域里放一个魔字标记，与密码区的魔字互不干扰。上电时如果读到标记但月份、日期越界，'
          '同样按无效处理并重新配置——这样即使晶振起振失败导致计数器乱跳，屏上也不会显示出一个荒唐的日期。'),

    ('h3', '3.7 密码管理模块及接口说明'),
    ('p', '密码只有 6 位数字，没必要占一整页 Flash。选择存备份域寄存器出于三点考虑：'
          '一是 BKP 写一次就生效，没有擦页延迟；二是 Flash 擦写寿命标称 1 万次，'
          '演示时反复改密码有风险；三是电池没电后密码自动回到出厂的 123456，思政楼里忘记密码也不至于锁死。'),
    ('h4', '3.7.1 备份寄存器布局'),
    ('t3', T_BKP),
    ('h4', '3.7.2 密码存取接口'),
    ('if', IF_PWD),

    ('h3', '3.8 指纹模块及接口说明'),
    ('p', 'AS608 是一颗带算法的光学指纹模块，图像采集、特征提取、模板比对都在模块内部完成，'
          '主控只负责发命令、收结果。这样主控不需要做任何图像处理，代价是必须严格遵守它的串口协议帧格式，'
          '任何一处长度或校验算错，模块都会默不作声。'),
    ('h4', '3.8.1 硬件连接与串口参数'),
    ('t3', T_FPUART),
    ('h4', '3.8.2 协议帧格式'),
    ('p', '命令包与应答包的格式完全一致，区别只在包标识：命令用 0x01，数据用 0x02，应答用 0x07。'
          '校验和从包标识开始逐字节累加，不含包头与芯片地址。'),
    ('t4', T_FPFRAME),
    ('p', '指纹验证、录入、删除都是这几个基本命令的组合：录入是 GenImg → Img2Tz(1) → GenImg → Img2Tz(2) → RegModel → Store；'
          '验证是 GenImg → Img2Tz(1) → Search；删除是 DeletChar，清空是 Empty。'
          '读索引表返回 32 字节位图，最低位在前，编号公式为「索引 × 8 + 位号」。'),
    ('t3', T_FPCMD),
    ('h4', '3.8.3 AS608 驱动接口'),
    ('if', IF_AS608),
    ('h4', '3.8.4 指纹业务流程接口'),
    ('p', '业务层把上面这些命令组合成四个对外流程：锁屏验证、录入、删除、清空，'
          '每个流程都是一个小状态机，由 Fp_Poll 每 10ms 推进一步，不会阻塞主循环。'),
    ('if', IF_APPFP),

    ('h3', '3.9 读卡模块及接口说明'),
    ('p', 'RC522 走 SPI，但本工程用的是 GPIO 软件模拟：位操作的时序完全由代码控制，'
          '换引脚只改宏定义，不受硬件 SPI 的引脚复用限制。'
          '地址字节的算法是把寄存器地址左移一位再与 0x7E 相与，读操作再或上 0x80。'),
    ('h4', '3.9.1 软件 SPI 与寄存器'),
    ('p', 'SPI 模式 0（空闲低、上升沿采样），每字节之间插几个空操作保证片选建立时间。'
          '寻卡、防冲突、选卡三步的超时都用毫秒计算——参考代码里按循环次数计超时，'
          '在 72MHz 下等于没有超时，模块没插时会把主循环拖死。'),
    ('t3', T_RCREG),
    ('h4', '3.9.2 RC522 驱动接口'),
    ('p', '在线判断有一个容易踩的坑：手册说版本号应该是 0x91 或 0x92，但本板用的是国产兼容片，'
          '读回来是 0xB2。所以判据写成「只有 0x00 与 0xFF 算离线」，其余任何值都认为芯片在位，'
          '照抄参考代码的版本号白名单会把好芯片判成没插。'),
    ('if', IF_RC522),
    ('h4', '3.9.3 卡片库存储布局'),
    ('p', '8 张卡片需要 40 字节，备份域寄存器放不下，改用片内 Flash 的最后一页 0x08010000。'
          '这一页在工程的下载范围之外（IROM 只配置到 0x0800FFFF），链接器永远不会把代码放到这里，'
          '所以整页都可以放心拿来存数据。写入前先算 CRC16，读回时校验不一致就整页当空处理。'),
    ('t4', T_CARDLAYOUT),
    ('h4', '3.9.4 卡片库接口'),
    ('if', IF_CSTORE),
    ('h4', '3.9.5 读卡业务流程接口'),
    ('p', '锁屏寻卡按 180ms 节流，避免天线一直全功率工作带来的发热与干扰；'
          '读到卡后必须让卡片休眠，否则同一张卡会一直在天线区被反复选中，'
          '表现为「放一次卡连续开锁好几次」。匹配成功先显示 0.7 秒卡号再开锁，是任务书的明确要求。'),
    ('if', IF_APPCARD),

    ('h3', '3.10 蓝牙开锁模块及接口说明'),
    ('p', '蓝牙模块本质就是一个透传串口：手机连上后往特征值里写什么，模块就往串口吐什么，'
          '主控收到的是一串裸字节，没有帧头帧尾也没有长度。所以「怎么判断一帧收完了」'
          '是这一块最关键的设计，比密码校验本身更麻烦。'),
    ('h4', '3.10.1 硬件连接与串口参数'),
    ('t3', T_BTUART),
    ('h4', '3.10.2 断帧策略与安全策略'),
    ('p', '断帧采用双保险：见到回车或换行立刻结算；什么终止符都没有时，靠 120ms 静默结算。'
          '只用其中一种都不行——只认换行，用 nRF Connect 手动写特征值就永远收不到完整帧；'
          '只靠静默，连发两串会粘成一串。'),
    ('t3', T_BTRULE),
    ('h4', '3.10.3 串口驱动接口'),
    ('if', IF_USART),
    ('h4', '3.10.4 蓝牙开锁接口'),
    ('if', IF_BT),

    ('h3', '3.11 界面模块及接口说明'),
    ('p', '界面按「一个人看一次」来设计：每张页面只放三行，标题、正文、底部提示，'
          '不做滚动也不做多级跳转。四种开锁方式的失败页特意做成同一个函数画的，'
          '保证不管是密码错、卡未授权还是指纹不符，看到的画面结构完全一致。'),
    ('h4', '3.11.1 锁屏与密码界面接口'),
    ('if', IF_UILOCK),
    ('h4', '3.11.2 指纹与卡片界面接口'),
    ('if', IF_UIFP),
    ('h4', '3.11.3 结果页的字号约定'),
    ('p', '结果页的 OK / FAIL 结论必须与正文一样用 16 像素高的字。最初用的是 8x8 小字，'
          '贴在大字下面看起来像压在上一行上，实测截图里非常明显，后来统一改成 16 像素。'),

    ('h3', '3.12 设置菜单模块及接口说明'),
    ('p', '菜单共 6 项：录入指纹、删除指纹、修改密码、修改时间、录入卡片、删除卡片。'
          '一屏显示 3 项，选中项用反白加滚动条标出，滚动窗口跟随选中项移动。'
          '任务书没有规定按键语义，本工程定的一套是「Dis 上翻、Chg 下翻、Ok 确定、Bck 返回」，并在屏底标出来。'),
    ('h4', '3.12.1 按键语义与退出规则'),
    ('t3', T_MENUKEY),
    ('h4', '3.12.2 菜单接口'),
    ('if', IF_MENU),

    ('h3', '3.13 应用主控模块及接口说明'),
    ('p', '应用层把「初始化顺序」和「状态机」两件事写在同一个文件里。初始化顺序不能随便调换：'
          '密码要等 RTC 打开备份域时钟后才能读，继电器要在其它模块之前先置低，'
          '否则上电瞬间会听到继电器啪一下。'),
    ('h4', '3.13.1 上电初始化顺序'),
    ('t3', T_INIT),
    ('h4', '3.13.2 应用层接口'),
    ('if', IF_APP),
    ('h4', '3.13.3 自动上锁与回锁屏'),
    ('p', '任务书第 7 条要求「过一段时间（10~20 秒）门锁自动上锁，屏幕回到锁屏状态」。'
          '这里容易只做到一半：把继电器断了、屏幕却还停在菜单里，要等菜单自己空闲超时才回去。'
          '正确做法是到点后先中止菜单里可能挂着的指纹与刷卡子流程，再直接跳回锁屏，'
          '本工程的开锁保持时间取 15 秒。'),

    ('h3', '3.14 自检工具模块及接口说明'),
    ('p', '两个自检模块不进正常业务流程，只在验证阶段编译进去使用：屏幕是只写设备，'
          '肉眼隔着照片看不清像素级对齐，所以让固件把所有界面逐张画出来并停住，'
          '再用调试器直接把显存读出来渲染成图片核对，比拍照放大看可靠得多。'),
    ('h4', '3.14.1 自检接口'),
    ('if', IF_TEST),
]

# ---------------------------------------------------------------- 目录条目
toc_items = []
for kind, *rest in BLOCKS:
    if kind == 'h1':
        toc_items.append((0, rest[0]))
    elif kind == 'h3':
        toc_items.append((1, rest[0]))
    elif kind == 'h4':
        toc_items.append((2, rest[0]))

# 第 1 章是原地改写的，不在 BLOCKS 里，目录条目要手工补在最前面
toc_items.insert(0, (1, '1.4 缩略语'))
toc_items.insert(0, (1, '1.3 背景'))
toc_items.insert(0, (1, '1.2 范围'))
toc_items.insert(0, (1, '1.1 前言'))
toc_items.insert(0, (0, '1 简介'))

first_toc_el = None
for level, text in toc_items:
    el = toc_el(level, text)
    if first_toc_el is None:
        first_toc_el = el
    h1_el.addprevious(el)

# 目录条目整体从第 2 页开始（「目录」二字留在封面页底部）——与历史交付件版式一致。
# 不加这一句时条目会顺着封面页底部往上爬，第一条单独留在第 1 页，很难看。
pPr = first_toc_el.find(q('pPr'))
if pPr is None:
    pPr = OxmlElement('w:pPr')
    first_toc_el.insert(0, pPr)
if pPr.find(q('pageBreakBefore')) is None:
    pb = OxmlElement('w:pageBreakBefore')
    style = pPr.find(q('pStyle'))
    if style is not None:
        style.addnext(pb)
    else:
        pPr.insert(0, pb)

# ---------------------------------------------------------------- 追加正文
for block in BLOCKS:
    kind = block[0]
    if kind == 'h1':
        el = sanitize(copy.deepcopy(PROTO_H3))
        # H1 用正文里已有的 Heading 1 元素做原型更合适
        el = sanitize(copy.deepcopy(children[i_h1]))
        set_text(el, block[1])
    elif kind == 'h3':
        el = sanitize(copy.deepcopy(PROTO_H3))
        set_text(el, block[1])
    elif kind == 'h4':
        el = sanitize(copy.deepcopy(PROTO_H4))
        set_text(el, block[1])
    elif kind == 'p':
        el = sanitize(copy.deepcopy(PROTO_BODY))
        set_text(el, block[1])
    elif kind == 'if':
        el = make_iface_table(PROTO_IF, block[1])
    elif kind in ('t3', 't4'):
        proto = PROTO_T3 if kind == 't3' else PROTO_T4
        ratios = block[2] if len(block) > 2 else None
        el = fill_table(copy.deepcopy(proto), block[1], ratios)
    else:
        raise ValueError(kind)
    tail_sect.addprevious(el)

d.save(DST)
print('已保存:', DST)
print('尺寸: %.1f KB' % (os.path.getsize(DST) / 1024.0))
