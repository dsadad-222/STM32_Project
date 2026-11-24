# -*- coding: utf-8 -*-
"""
chapter9 接口文档生成：在 0916 成品文档基础上增量更新
    ADC 内部温度采集  ->  片内片外 FLASH 读写

思路（沿用 skill 的方法 B）：不碰模板、不重新排版，
直接克隆上一章成品里的段落/表格元素再改文字，
样式、手打编号、表格式样全部原样继承。
"""
import os
import re
import sys
import copy
import zipfile

from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
XSPACE = '{http://www.w3.org/XML/1998/namespace}space'


def q(t):
    return '{%s}%s' % (W, t)


BASE = ('C:/Users/y7000/Desktop/嵌入式/0916_ADC内部温度采集/'
        '202417010304智能3班陈相林实现ADC内部温度采集/ADC内部温度采集_接口文档.docx')
OUT = 'D:/STM32_Project/docs/片内片外FLASH读写_接口文档.docx'


# ---------------------------------------------------------------- 读写 docx

def load_parts(path):
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist()}


def save_parts(parts, path):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    if os.path.exists(path):
        os.remove(path)
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, data in parts.items():
            z.writestr(n, data)


# ---------------------------------------------------------------- 文本操作

def ptext(p):
    return ''.join(t.text or '' for t in p.iter(q('t')))


def pstyle(p):
    st = p.find(q('pPr') + '/' + q('pStyle'))
    return st.get(q('val')) if st is not None else ''


def set_ptext(p, s):
    # 只允许对段落调用：表格的 ptext 是所有单元格拼起来的，
    # 一旦误传表格进来，set_ptext 会把整张表压成第一个单元格（已踩过）。
    if etree.QName(p).localname != 'p':
        raise RuntimeError('set_ptext 只接受段落，收到的是 <%s>' % etree.QName(p).localname)
    ts = list(p.iter(q('t')))
    if not ts:
        raise RuntimeError('段落里没有 w:t，无法写入：%r' % ptext(p))
    ts[0].text = s
    ts[0].set(XSPACE, 'preserve')
    for t in ts[1:]:
        t.text = ''


def replace_in_p(p, old, new):
    if etree.QName(p).localname != 'p':
        raise RuntimeError('replace_in_p 只接受段落，收到的是 <%s>' % etree.QName(p).localname)
    cur = ptext(p)
    if old not in cur:
        raise RuntimeError('段落里找不到 %r：%r' % (old, cur[:60]))
    set_ptext(p, cur.replace(old, new))


def replace_in_cell(tbl, old, new):
    """在表格里找含 old 的单元格，就地替换文字。"""
    hit = 0
    for tc in tbl.iter(q('tc')):
        cur = cell_text(tc)
        if old in cur:
            set_cell(tc, cur.replace(old, new))
            hit += 1
    if hit == 0:
        raise RuntimeError('表格里找不到 %r' % old)
    return hit


def cell_text(tc):
    return ''.join(t.text or '' for t in tc.iter(q('t')))


def set_cell(tc, s):
    ts = list(tc.iter(q('t')))
    if not ts:
        raise RuntimeError('单元格里没有 w:t，无法写入：%r' % cell_text(tc))
    ts[0].text = s
    ts[0].set(XSPACE, 'preserve')
    for t in ts[1:]:
        t.text = ''


def set_row(tr, vals):
    tcs = tr.findall(q('tc'))
    if len(tcs) != len(vals):
        raise RuntimeError('该行有 %d 个单元格，却给了 %d 个值' % (len(tcs), len(vals)))
    for tc, v in zip(tcs, vals):
        set_cell(tc, v)


def rows_of(tbl):
    return tbl.findall(q('tr'))


def strip_junk(el):
    """克隆出来的元素里，书签与校对标记要清掉，免得重复 ID 把文档搞坏。"""
    for tag in ('bookmarkStart', 'bookmarkEnd', 'proofErr', 'lastRenderedPageBreak'):
        for node in el.iter(q(tag)):
            node.getparent().remove(node)
    return el


def clone_row_after(ref_tr, vals):
    new = strip_junk(copy.deepcopy(ref_tr))
    ref_tr.addnext(new)
    set_row(new, vals)
    return new


def make_table_like(src_tbl, data, cycle=None):
    """克隆 src_tbl 的结构，按 data 重建行。cycle=4 表示行样式按 4 行循环复用。"""
    src_rows = rows_of(src_tbl)
    new = copy.deepcopy(src_tbl)
    for tr in rows_of(new):
        new.remove(tr)
    for i, vals in enumerate(data):
        if cycle:
            tmpl = src_rows[i % cycle]
        elif i < len(src_rows):
            tmpl = src_rows[i]
        else:
            tmpl = src_rows[-1]
        tr = strip_junk(copy.deepcopy(tmpl))
        new.append(tr)
        set_row(tr, vals)
    return new


class Cursor(object):
    """从某个锚点元素开始，按顺序往下插内容。"""

    def __init__(self, anchor):
        self.prev = anchor

    def add(self, el):
        self.prev.addnext(el)
        self.prev = el
        return el

    def para(self, tmpl, text):
        return self.add(mk_para(tmpl, text))

    def table(self, src_tbl, data, cycle=None):
        return self.add(make_table_like(src_tbl, data, cycle=cycle))


def mk_para(tmpl, text):
    p = strip_junk(copy.deepcopy(tmpl))
    set_ptext(p, text)
    return p


def mk_toc_line(tmpl_p, text, level, half_pt=21):
    """按模板的空段落造一行静态目录：缩进按层级，字号 10.5 磅。"""
    p = strip_junk(copy.deepcopy(tmpl_p))
    for r in p.findall(q('r')):
        p.remove(r)

    r = etree.SubElement(p, q('r'))
    rPr = etree.SubElement(r, q('rPr'))
    etree.SubElement(rPr, q('rFonts')).set(q('hint'), 'eastAsia')
    etree.SubElement(rPr, q('sz')).set(q('val'), str(half_pt))
    etree.SubElement(rPr, q('szCs')).set(q('val'), str(half_pt))
    t = etree.SubElement(r, q('t'))
    t.text = text
    t.set(XSPACE, 'preserve')

    pPr = p.find(q('pPr'))
    if pPr is None:
        pPr = etree.Element(q('pPr'))
        p.insert(0, pPr)
    # 段落标记的字号也一起改小
    mark_rPr = pPr.find(q('rPr'))
    if mark_rPr is not None:
        for tag in ('sz', 'szCs'):
            node = mark_rPr.find(q(tag))
            if node is not None:
                node.set(q('val'), str(half_pt))
    # w:ind 必须排在 w:rPr 之前（OOXML 元素顺序）
    old_ind = pPr.find(q('ind'))
    if old_ind is not None:
        pPr.remove(old_ind)
    ind = etree.Element(q('ind'))
    ind.set(q('left'), str(level * 210))
    if mark_rPr is not None:
        mark_rPr.addprevious(ind)
    else:
        pPr.append(ind)
    return p


def fix_footer(parts):
    """修模板自带的页脚缺陷。

    模板把页码放在一个浮动文本框里（wps:txbx + VML 回退），Word 导出 PDF 时
    两位数的页码只显示第一位：第 10~19 页显示 1、第 20 页以后显示 2。
    0916 那份交付件也是同样毛病。改成最普通的居中段落 + PAGE 域，稳定可靠。
    """
    name = 'word/footer1.xml'
    if name not in parts:
        return False
    root = etree.fromstring(parts[name])
    if root.findall(q('p')) == []:
        return False
    for p in root.findall(q('p')):
        root.remove(p)

    p = etree.SubElement(root, q('p'))
    pPr = etree.SubElement(p, q('pPr'))
    etree.SubElement(pPr, q('pStyle')).set(q('val'), 'a5')
    etree.SubElement(pPr, q('jc')).set(q('val'), 'center')

    r = etree.SubElement(p, q('r'))
    etree.SubElement(r, q('fldChar')).set(q('fldCharType'), 'begin')
    r = etree.SubElement(p, q('r'))
    it = etree.SubElement(r, q('instrText'))
    it.set(XSPACE, 'preserve')
    it.text = ' PAGE  \\* MERGEFORMAT '
    r = etree.SubElement(p, q('r'))
    etree.SubElement(r, q('fldChar')).set(q('fldCharType'), 'separate')
    r = etree.SubElement(p, q('r'))
    etree.SubElement(r, q('t')).text = '1'
    r = etree.SubElement(p, q('r'))
    etree.SubElement(r, q('fldChar')).set(q('fldCharType'), 'end')

    parts[name] = etree.tostring(root, xml_declaration=True,
                                 encoding='UTF-8', standalone=True)
    return True


# ---------------------------------------------------------------- 主流程

def main():
    parts = load_parts(BASE)
    root = etree.fromstring(parts['word/document.xml'])
    body = root.find(q('body'))

    # 先按索引把所有锚点抓成引用（后面会插元素，索引会漂）
    E = list(body)
    n0 = len(E)

    # ---- 模板 ----
    TMPL_H3 = E[41]      # 3.1 模块调用说明        style 3
    TMPL_H4 = E[61]      # 3.1.1 协议帧格式        style 4
    TMPL_BODY = E[23]    # 1.1 前言正文            style ''
    TMPL_CODE = E[43]    # LED_Init(); // ...      代码行
    TBL_T2 = E[165]      # 按键驱动接口表（2 列，4 行一循环）
    TBL_T3 = E[172]      # 呼吸灯参数表（3 列）
    TBL_T4 = E[62]       # 协议帧格式表（4 列）

    if not ptext(E[0]).endswith('方案文档（接口）'):
        raise RuntimeError('封面标题对不上：%r' % ptext(E[0]))
    if pstyle(TMPL_H3) != '3' or pstyle(TMPL_H4) != '4':
        raise RuntimeError('标题模板样式不对：%r / %r' % (pstyle(TMPL_H3), pstyle(TMPL_H4)))
    if len(rows_of(TBL_T2)[0].findall(q('tc'))) != 2:
        raise RuntimeError('T2 模板不是 2 列')
    if len(rows_of(TBL_T3)[0].findall(q('tc'))) != 3:
        raise RuntimeError('T3 模板不是 3 列')
    if len(rows_of(TBL_T4)[0].findall(q('tc'))) != 4:
        raise RuntimeError('T4 模板不是 4 列')

    print('锚点抓取完成，body 子元素 %d 个' % n0)

    # ============================================================ 1. 封面
    set_ptext(E[0], '片内片外 FLASH 读写方案文档（接口）')

    # ============================================================ 2. 修订记录
    rev_tbl = E[16]
    rev_rows = rows_of(rev_tbl)
    clone_row_after(rev_rows[1], [
        '2026.09.17', 'V2.0',
        '新增片内 Flash 数据页读写与片外 W25Q64 驱动；按 0x07 功能字不定长协议存储数据；'
        'OLED 改为固定四行版式，串口只上报温度',
        '陈相林',
    ])

    # ============================================================ 3. 1.1 前言
    set_ptext(E[23],
              '本文档用于说明片内片外 FLASH 读写工程的模块划分、对外接口与使用方法，'
              '作为开发、调试与验收的统一依据。本工程在 ADC 内部温度采集工程的基础上扩展而来，'
              '按任务书要求取消了屏上与串口上报的 ADC 原始值、换算电压，只保留温度；'
              '新增片内 Flash 数据页的读写与片外 SPI Flash（W25Q64）的读写驱动，'
              '并按 0x07 功能字的不定长协议帧，把上位机下发的数据分别写入这两片 Flash。')

    # ============================================================ 4. 1.2 范围
    set_ptext(E[25],
              '本文档适用于基于 STM32F103ZET6 与 STM32F10x 标准外设库 V3.6 的片内片外 FLASH 读写工程，'
              '覆盖串口协议控制板载外设、串口不定长数据帧接收、片内 Flash 数据页擦写与校验、'
              '片外 W25Q64 的 SPI2 读写驱动、OLED 显示、按键交互与温度上报等模块的接口说明。')

    # ============================================================ 5. 1.3 背景
    set_ptext(E[27],
              '本工程为嵌入式培训课程 FLASH 章节的实践任务，在 ADC 内部温度采集工程的基础上扩展而来。'
              '片内 Flash 与片外 SPI Flash 都是掉电不丢失的存储器，但操作方式差别很大：'
              '片内 Flash 地址直接映射在 0x08000000 之后，用指针就能读，按页擦除、按半字编程；'
              '片外 W25Q64 挂在 SPI2 上，只能通过命令字访问，写之前必须先发写使能，'
              '擦除的最小单位是 4KB 扇区。本任务把这两种存储器都用起来，并用同一套协议帧驱动，'
              '因此还需要解决串口不定长数据的接收问题。')

    # ============================================================ 6. 1.4 缩略语
    syn_rows = rows_of(E[29])
    flash_row = None
    for tr in syn_rows:
        if cell_text(tr.findall(q('tc'))[0]) == 'Flash':
            flash_row = tr
            break
    if flash_row is None:
        raise RuntimeError('缩略语表里没找到 Flash 行')
    for vals in [
        ['SPI', 'Serial Peripheral Interface', '串行外设接口，片外 Flash 挂在这条总线上'],
        ['W25Q64', '—', '华邦 8MB 片外 SPI Flash（板上位号 U9），JEDEC ID 为 0xEF4017'],
        ['JEDEC ID', '—', 'Flash 的厂商、类型、容量三字节标识，用于判断芯片是否在线'],
    ]:
        flash_row = clone_row_after(flash_row, vals)

    # ============================================================ 7. 2.1 系统组成
    comp_rows = rows_of(E[34])
    for tr in comp_rows:
        tcs = tr.findall(q('tc'))
        name = cell_text(tcs[0])
        if name == '下位机':
            set_cell(tcs[2], '解析协议帧，控制外设、刷新 OLED、读写片内 Flash 与片外 W25Q64')
        elif name == '按键输入':
            set_cell(tcs[2], 'KEY2 触发左转向灯呼吸灯，KEY1 读取片内 Flash 数据，KEY3 读取片外 Flash 数据')
    # 在「执行与显示」之后插入片外存储一行
    anchor = None
    for tr in comp_rows:
        if cell_text(tr.findall(q('tc'))[0]) == '执行与显示':
            anchor = tr
    if anchor is None:
        raise RuntimeError('系统组成表里没找到「执行与显示」行')
    clone_row_after(anchor, [
        '片外存储',
        'W25Q64 SPI Flash（8MB，板上 U9）',
        '挂 SPI2：CS = PB12、SCK = PB13、MISO = PB14、MOSI = PB15，'
        '开机读 JEDEC ID 自检芯片是否在线',
    ])

    # ============================================================ 8. 2.2 分层设计
    for tr in rows_of(E[36]):
        tcs = tr.findall(q('tc'))
        if cell_text(tcs[0]) == '驱动层':
            set_cell(tcs[2],
                     '把外设细节封装成函数接口，向上屏蔽寄存器操作；本工程共 12 个驱动与 2 份字库：'
                     'LED/RGB、蜂鸣器、OLED、串口、内部 Flash、片外 W25Q64、SysTick、ADC、按键、'
                     '软件 PWM、RGB 转向灯珠、中文消息，以及 8x8 与 16x16 两份字库数据')

    # ============================================================ 9. 2.3 模块设计
    mod_anchor = None
    for tr in rows_of(E[39]):
        tcs = tr.findall(q('tc'))
        if cell_text(tcs[0]) == '数据存储模块':
            set_cell(tcs[2], '内部 Flash 两页的擦写、记录校验与回读：最后一页存设备状态，'
                             '倒数第二页存本任务的上位机数据记录')
            mod_anchor = tr
    if mod_anchor is None:
        raise RuntimeError('模块设计表里没找到「数据存储模块」行')
    clone_row_after(mod_anchor, [
        '片外 Flash 模块',
        'w25q64_drv.c / .h',
        '片外 W25Q64 的 SPI2 初始化、JEDEC ID 自检、扇区擦除、页编程与整条记录写入',
        'PB12、PB13、PB14、PB15',
    ])

    # ============================================================ 10. 初始化代码
    E[52].addnext(strip_junk(mk_para(TMPL_CODE,
                                      's_extOk = W25Q64_Init(); // 片外 W25Q64：读 JEDEC ID 判断芯片在不在')))

    # ============================================================ 11. 3.1.1 帧格式表
    fmt_rows = rows_of(E[62])
    for tr in fmt_rows:
        tcs = tr.findall(q('tc'))
        name = cell_text(tcs[0])
        if name == '数据域长度':
            set_cell(tcs[3], '功能字＋控制单元＋数据的总字节数，即 N = 2 + 数据字节数')
        elif name == '数据':
            set_cell(tcs[2], '见 3.1.2')
            set_cell(tcs[3], '控制单元＋数据、控制单元＋开关状态或 ASCII 文本')

    # ============================================================ 12. 3.1.2 功能字表
    new_func = make_table_like(E[65], [
        ['功能字', '含义', '数据域', '示例帧'],
        ['0x06', '控制设备', '2 字节：控制单元＋开关状态',
         '55 FF 03 06 02 01 AC 蜂鸣器开（02 00 关）；1 字节旧格式为翻转'],
        ['0x07', '数据存储（本任务）', '1 字节控制单元＋1~20 字节数据',
         '55 FF 07 07 01 01 02 03 04 05 AA 存片内 Flash；控制单元改 02 存片外 Flash'],
        ['0x08', '存储操作', '1 字节操作码', '55 FF 02 08 02 A2 从 Flash 重新读回'],
        ['0x09', '下发文本', 'ASCII 文本，最多 32 字符',
         '55 FF 06 09 HELLO E7 屏显提示并保存（原为 0x07，为数据存储让位）'],
    ])
    E[65].getparent().replace(E[65], new_func)

    # ============================================================ 13. 3.1.3 状态上报补充
    cur = Cursor(E[75])
    cur.para(TMPL_BODY, '数据存储命令执行完成后会单独回一行结果，方便在串口助手里直接核对，例如：')
    cur.para(TMPL_CODE, 'STORE: internal flash saved -> 01 02 03 04 05')
    cur.para(TMPL_CODE, 'STORE: external flash saved -> 01 02 03 04 05')
    cur.para(TMPL_CODE, 'ERROR: data length must be 1~20')
    cur.para(TMPL_CODE, 'STORE: W25Q64 not found')

    # ============================================================ 14. 温度上报说明
    set_ptext(E[72],
              '温度数据每 2 秒自动上报一次，在串口助手里直接输入 A 也可以立刻触发一次上报。'
              '按任务书要求，本任务的串口只上报温度一行：Current Temperature is 35.93，'
              'ADC 原始值与换算电压不再上报。屏上也同步只保留温度，'
              '屏显示的内容与串口上报的内容各自独立 —— 屏上另有片内与片外 Flash 数据两行，'
              '串口则在存储命令执行后额外回一行存储结果。温度单位为 ℃（2 位小数）；'
              '当读数超出传感器量程（-40~125℃）时打印 --，表示本次读数不可信。')

    # ============================================================ 15. OLED 版式说明
    set_ptext(E[96],
              '屏不再分页，按任务书要求固定为四行：第 1 行显示片内 Flash 读出的数据，'
              '第 2 行显示温度，第 3 行显示片外 Flash 读出的数据，第 4 行显示状态提示。'
              'ADC 原始值与换算电压已按任务书要求取消显示：')

    new_line_tbl = make_table_like(E[97], [
        ['行号', '内容', '说明'],
        ['第 1 行', 'IN:0102030405',
         '片内 Flash 数据页读出的数据，十六进制显示；无有效记录时显示 IN:--'],
        ['第 2 行', 'TEMP 36.9 C',
         '芯片温度，保留 1 位小数（已标定时为标定后的值）；读数无效时显示 TEMP --.- C'],
        ['第 3 行', 'EX:0102030405',
         '片外 W25Q64 读出的数据，十六进制显示；芯片不在线或无记录时显示 EX:--'],
        ['第 4 行', 'W25Q64 OK',
         '状态提示：开机显示 W25Q64 是否在线，之后显示最近一次操作结果，'
         '如 IN SAVED / EX SAVED / IN EMPTY / EX EMPTY / NO W25Q64'],
        ['说明', '数据超过 6 字节时截断显示',
         '一行 16 个 8x8 字符，扣掉 IN: 标签还剩 13 格，最多完整显示 6 个字节；'
         '超过 6 字节只显示前 5 个字节并补 ..，保证永远不顶出屏幕。'
         '完整数据在串口以十六进制打印，屏上与串口各司其职'],
    ])
    E[97].getparent().replace(E[97], new_line_tbl)

    # ============================================================ 16. 3.4 存储模块引言
    set_ptext(E[115],
              '存储使用片内 Flash 的最后两页。STM32F103ZE 属于大容量产品，主存储区 512KB、'
              '页大小 2KB、共 256 页；程序只占最前面 17KB 左右，后面大片空闲。'
              '本工程用了最后两页：最后一页 0x0807F800 存设备状态与文本（见 3.4.1 至 3.4.3 节），'
              '倒数第二页 0x0807F000 存本任务的上位机数据记录（见 3.4.4 至 3.4.5 节）。'
              '两页各擦各的，互不影响。')

    # ============================================================ 17. 常量表补行
    const_rows = rows_of(E[121])
    anchor = None
    for tr in const_rows:
        if cell_text(tr.findall(q('tc'))[0]) == 'STORE_PAGE_ADDR':
            anchor = tr
    if anchor is None:
        raise RuntimeError('常量表里没找到 STORE_PAGE_ADDR 行')
    for vals in [
        ['DATA_PAGE_ADDR', '0x0807F000', '数据记录页起始地址，即内部 Flash 倒数第二页'],
        ['DATA_REC_SIZE', '24', '一条数据记录的总长度，单位字节'],
        ['DATA_MAX_LEN', '20', '单条数据最多 20 字节（任务书规定）'],
        ['DATA_EXT_ADDR', '0x000000', '片外 W25Q64 里存放记录的地址（扇区 0 起始处）'],
    ]:
        anchor = clone_row_after(anchor, vals)

    # ============================================================ 18. 数据页保护
    set_ptext(E[137],
              '两页都在内部 Flash 的尾部，地址分别是 0x0807F000 与 0x0807F800。'
              'Keil 工程默认的下载范围覆盖整个主存储区，每次按 F8 下载都会顺手把这两页擦掉，'
              '表现出来的现象是"标定值、保存的状态与存下的数据每次下载后就没了"。')
    set_ptext(E[138],
              '处理办法是把下载范围限制到数据页之前，即把工程 Flash Download 设置里的容量'
              '由 512K 改为 508K（命令行参数 -FL07F000），这样下载只覆盖 '
              '0x08000000~0x0807EFFF 共 508KB，最后两页留给掉电保存的内容。')

    new_prot_tbl = make_table_like(E[139], [
        ['情况', '结果', '说明'],
        ['Keil 按 F8 下载（下载范围已限制到 -FL07F000）', '两页都保留',
         '标定值、文本、设备状态与存下的数据都不用重做，开机横幅会显示已标定并打印两片 Flash 里的数据'],
        ['手动勾选 Erase Full Chip，或用其他工具整片擦除', '两页都被擦掉',
         '重新发一次 K 加室温值即可恢复标定，文本、状态与数据需要重新保存'],
        ['串口发 C 命令清除 Flash', '状态页被擦掉', '效果同上，属于主动清除，需要重新保存与标定'],
    ])
    E[139].getparent().replace(E[139], new_prot_tbl)

    # ============================================================ 19. 新增 3.4.4 / 3.4.5 / 3.5
    cur = Cursor(new_prot_tbl)

    # ---- 3.4.4 数据记录格式
    cur.para(TMPL_H4, '3.4.4 数据记录格式')
    cur.para(TMPL_BODY,
             '片内数据页与片外 W25Q64 存的是同一种记录，按字节流排布，不用结构体，'
             '避开编译器对齐填充的坑。记录固定 24 字节，格式如下：')
    cur.table(TBL_T4, [
        ['偏移', '长度', '取值', '说明'],
        ['第 0 字节', '1', '0x46（字符 F）', '魔数 0'],
        ['第 1 字节', '1', '0x53（字符 S）', '魔数 1'],
        ['第 2 字节', '1', '1 ~ 20', '本次数据的有效字节数'],
        ['第 3 ~ 22 字节', '20', '数据', '上位机下发的数据，不足部分补 0xFF'],
        ['第 23 字节', '1', '累加和', '前 23 个字节的累加和取低 8 位'],
    ])
    cur.para(TMPL_BODY,
             '两个魔数都不匹配（例如从没写过的页读出来是全 0xFF）、长度越界或校验和不符时，'
             '记录被判为无效，读出的数据不会显示到屏上，串口也会回一行 empty。'
             '校验范围是前 23 字节，不含校验字节自身。')
    cur.para(TMPL_BODY,
             '片内 Flash 按半字（2 字节）编程，24 字节能被 2 整除，正好写 12 次，不需要额外补齐；'
             '片外 W25Q64 按字节写，长度也不受页大小限制。')

    # ---- 3.4.5 数据存储接口
    cur.para(TMPL_H4, '3.4.5 数据存储接口')
    cur.para(TMPL_BODY,
             '写入片内数据页时先 FLASH_Unlock 解锁，擦除整页后按半字逐次编程，'
             '最后 FLASH_Lock 上锁；任一步返回失败都会立刻上锁并上报失败。'
             '读取时直接用指针访问数据页，先校验记录再取数据。接口如下：')
    cur.table(TBL_T2, [
        ['函数原型', 'void DataRec_Build(uint8_t *rec, const uint8_t *data, uint8_t len)'],
        ['描述', '按记录格式打包一条 24 字节记录：写魔数、长度与数据（不足补 0xFF），最后算累加和填到第 23 字节'],
        ['参数', 'rec 输出缓冲，至少 24 字节；data 待存数据；len 数据长度，取值 1~20'],
        ['返回值', 'void'],
        ['函数原型', 'uint8_t DataRec_Check(const uint8_t *rec)'],
        ['描述', '校验一条 24 字节记录：魔数、长度范围与累加和三项全部通过才算有效'],
        ['参数', 'rec 待校验记录的首地址'],
        ['返回值', '校验通过返回数据长度（1~20），失败返回 0'],
        ['函数原型', 'uint8_t Data_SaveInternal(const uint8_t *data, uint8_t len)'],
        ['描述', '把数据写入片内 Flash 数据页 0x0807F000：解锁、擦除整页、按半字写 12 次、上锁'],
        ['参数', 'data 待存数据；len 数据长度，取值 1~20'],
        ['返回值', '1 = 写入成功，0 = 擦除或编程失败'],
        ['函数原型', 'uint8_t Data_LoadInternal(uint8_t *out, uint8_t *outLen)'],
        ['描述', '从片内数据页读出记录，校验通过后把数据拷到输出缓冲'],
        ['参数', 'out 输出缓冲，至少 20 字节；outLen 输出本次数据长度'],
        ['返回值', '1 = 读到有效记录，0 = 无有效记录'],
        ['函数原型', 'uint8_t RefreshInternal(void)'],
        ['描述', '重新读片内数据页并刷新全局缓存，供 KEY1 与开机流程调用'],
        ['参数', 'void'],
        ['返回值', '1 = 有有效数据，0 = 无有效数据'],
        ['函数原型', 'void ReportDataHex(const uint8_t *data, uint8_t len)'],
        ['描述', '把一段数据按十六进制打印到串口，字节之间用空格分隔；空数据打印 (empty)'],
        ['参数', 'data 数据首地址；len 数据长度'],
        ['返回值', 'void'],
    ], cycle=4)

    # ---- 3.5 片外 FLASH（W25Q64）模块
    cur.para(TMPL_H3, '3.5 片外 FLASH（W25Q64）模块及接口说明')
    cur.para(TMPL_BODY,
             '片上 Flash 之外，板上还焊了一颗华邦 W25Q64（8MB，位号 U9），通过 SPI2 与 MCU 相连。'
             '它与片内 Flash 的区别在于：片内 Flash 地址直接映射在 0x08000000 之后，用指针就能读；'
             'W25Q64 只能通过命令字访问，写之前必须先发写使能（0x06），'
             '写与擦除期间要轮询状态寄存器的 BUSY 位，擦除的最小单位是 4KB 扇区。')
    cur.para(TMPL_BODY,
             '芯片是否在线靠读 JEDEC ID 判断：正常返回 0xEF4017，即厂商 0xEF（Winbond）、'
             '类型 0x40、容量 0x17（8MB）。如果这颗芯片没焊或接线异常，MISO 悬空会读回全 0 或全 1；'
             '固件连续读两次并取一致值，避免把悬空随机数误判成芯片在线。'
             '检测结果在开机横幅里直接打印，OLED 第 4 行也会显示 W25Q64 OK 或 NO W25Q64。')

    cur.para(TMPL_H4, '3.5.1 硬件连接')
    cur.table(TBL_T4, [
        ['信号', 'W25Q64 引脚', 'MCU 引脚', '说明'],
        ['片选 CS#', 'pin1', 'PB12', '软件片选，普通推挽输出，低电平选中'],
        ['时钟 CLK', 'pin6', 'PB13', 'SPI2_SCK'],
        ['数据输出 DO', 'pin2', 'PB14', 'SPI2_MISO，MCU 输入'],
        ['数据输入 DI', 'pin5', 'PB15', 'SPI2_MOSI，MCU 输出'],
        ['写保护 WP# / 保持 HOLD#', 'pin3、pin7', '板上固定为高', '不占用 IO'],
    ])
    cur.para(TMPL_BODY,
             'SPI2 配置为主机全双工、8 位数据、模式 3（CPOL = 1，时钟空闲为高；'
             'CPHA = 1，在第二个边沿采样）、时钟 9MHz，由 PCLK1 的 36MHz 四分频得到。'
             '旁边 J4 排针同样引出了 PB12 / PB13 / PB14，与 Flash 共用这条 SPI2 总线。')

    cur.para(TMPL_H4, '3.5.2 W25Q64 驱动接口')
    cur.table(TBL_T2, [
        ['函数原型', 'uint8_t W25Q64_Init(void)'],
        ['描述', '初始化 SPI2 与片选引脚，并读一次 JEDEC ID 判断芯片在不在；上电初始化时调用'],
        ['参数', 'void'],
        ['返回值', '1 = 检测到 W25Q64，0 = 没检测到（未焊接或接线异常）'],
        ['函数原型', 'uint32_t W25Q64_ReadID(void)'],
        ['描述', '读 3 字节 JEDEC ID 并合成 32 位值；连续读两次，两次一致才返回，否则返回 0xFFFFFF'],
        ['参数', 'void'],
        ['返回值', '0xEF4017 表示芯片在线；0x000000 或 0xFFFFFF 表示芯片不在'],
        ['函数原型', 'uint8_t W25Q64_IsPresent(void)'],
        ['描述', '返回最近一次初始化时的检测结果，不重新访问总线'],
        ['参数', 'void'],
        ['返回值', '1 = 芯片在线，0 = 不在线'],
        ['函数原型', 'void W25Q64_Read(uint32_t addr, uint8_t *buf, uint16_t len)'],
        ['描述', '发送 0x03 读数据命令后连续读出 len 个字节，地址自动递增'],
        ['参数', 'addr 起始地址（24 位，0x000000~0x7FFFFF）；buf 输出缓冲；len 读取长度'],
        ['返回值', 'void'],
        ['函数原型', 'uint8_t W25Q64_EraseSector(uint32_t addr)'],
        ['描述', '擦除 addr 所在的 4KB 扇区；擦前自动发写使能，擦后轮询 BUSY 直到空闲'],
        ['参数', 'addr 扇区内的任意地址'],
        ['返回值', '1 = 成功，0 = 超时或失败'],
        ['函数原型', 'uint8_t W25Q64_PageProgram(uint32_t addr, const uint8_t *buf, uint16_t len)'],
        ['描述', '页内编程；addr 必须落在同一页内，且 addr 除以 256 的余数加 len 不超过 256；调用前该页必须已擦除'],
        ['参数', 'addr 页内起始地址；buf 数据；len 长度（不超过 256）'],
        ['返回值', '1 = 成功，0 = 参数越界或超时'],
        ['函数原型', 'uint8_t W25Q64_WriteData(uint32_t addr, const uint8_t *buf, uint16_t len)'],
        ['描述', '供上层直接使用：先擦掉覆盖到的所有扇区，再从起始地址逐页写，写满 256 字节自动切到下一页'],
        ['参数', 'addr 起始地址；buf 数据；len 长度'],
        ['返回值', '1 = 成功，0 = 失败'],
    ], cycle=4)

    cur.para(TMPL_BODY, '驱动里用到的命令字与关键常量如下：')
    cur.table(TBL_T3, [
        ['名称', '取值', '说明'],
        ['W25Q64_JEDEC_ID', '0xEF4017', '芯片标识：厂商 0xEF + 类型 0x40 + 容量 0x17（8MB）'],
        ['写使能', '0x06', '每次写或擦除前必须先发，否则操作会被芯片忽略'],
        ['读状态寄存器', '0x05', 'bit0 为 BUSY 位，写与擦除期间为 1'],
        ['读数据', '0x03', '发送后连续读出，地址自动递增'],
        ['页编程', '0x02', '一次最多写一页，不能跨页'],
        ['扇区擦除', '0x20', '一次擦 4KB，是最小擦除单位'],
        ['W25Q64_SPI_TIMEOUT', '0x2000', '单次传输的忙等上限，防止总线异常时卡在死循环'],
        ['W25Q64_BUSY_TIMEOUT', '0x00FFFFFF', '擦写后 BUSY 轮询上限；扇区擦除典型耗时 45ms，余量充足'],
    ])

    cur.para(TMPL_H4, '3.5.3 擦写时序与注意事项')
    cur.para(TMPL_BODY,
             'Flash 的存储单元只能把 1 变成 0，擦除是把整块拉回全 1，'
             '所以"改一个字节"的实际代价是擦掉整个扇区再重写整条记录。'
             'W25Q64_WriteData 把这套动作封起来：先按地址范围擦掉覆盖到的所有扇区，'
             '再从起始地址开始逐页写，长度跨页也能正确写完。相关参数如下：')
    cur.table(TBL_T3, [
        ['项目', '取值', '说明'],
        ['页大小', '256 字节', '一次页编程不能跨页'],
        ['扇区大小', '4096 字节', '最小擦除单位'],
        ['块大小', '64KB', '芯片支持整块擦除，本工程未使用'],
        ['总容量', '8MB', '24 位地址空间 0x000000 ~ 0x7FFFFF'],
        ['写前必须擦除', '是', '不擦除直接写会出现新旧数据相与后的残留'],
        ['数据记录地址', '0x000000', '本工程把记录放在扇区 0 的起始处'],
        ['单次写入耗时', '约 45ms', '主要是扇区擦除的耗时；驱动内部轮询 BUSY 等待，不返回上层'],
        ['写使能', '每次写或擦前必发', '命令字 0x06，驱动在每个写与擦函数内部自动发出'],
    ])

    cur.para(TMPL_H4, '3.5.4 片外数据读写接口')
    cur.para(TMPL_BODY,
             '片外存储复用与片内完全相同的 24 字节记录格式与校验逻辑，只是底层换成 W25Q64 的读写。'
             '芯片不在线时接口直接返回失败，不会去访问总线。接口如下：')
    cur.table(TBL_T2, [
        ['函数原型', 'uint8_t Data_SaveExternal(const uint8_t *data, uint8_t len)'],
        ['描述', '把数据打包成记录写入片外 W25Q64 的 0x000000 处；芯片不在线时直接返回失败'],
        ['参数', 'data 待存数据；len 数据长度，取值 1~20'],
        ['返回值', '1 = 成功，0 = 写入失败或芯片不在线'],
        ['函数原型', 'uint8_t Data_LoadExternal(uint8_t *out, uint8_t *outLen)'],
        ['描述', '从片外读一条记录并校验，通过后把数据拷到输出缓冲'],
        ['参数', 'out 输出缓冲，至少 20 字节；outLen 输出本次数据长度'],
        ['返回值', '1 = 读到有效记录，0 = 无有效记录或芯片不在线'],
        ['函数原型', 'uint8_t RefreshExternal(void)'],
        ['描述', '重新读片外记录并刷新全局缓存，供 KEY3 与开机流程调用'],
        ['参数', 'void'],
        ['返回值', '1 = 有有效数据，0 = 无有效数据'],
    ], cycle=4)

    # ============================================================ 20. 章节重编号
    renames = [
        (E[140], '3.5 系统时基模块及接口说明', '3.6 系统时基模块及接口说明'),
        (E[142], '3.5.1 SysTick 接口', '3.6.1 SysTick 接口'),
        (E[144], '3.6 ADC 模块及接口说明', '3.7 ADC 模块及接口说明'),
        (E[148], '3.6.1 ADC 采集接口', '3.7.1 ADC 采集接口'),
        (E[150], '3.6.2 温度换算与量程检查', '3.7.2 温度换算与量程检查'),
        (E[154], '3.6.3 温度单点标定', '3.7.3 温度单点标定'),
        (E[160], '3.7 按键模块及接口说明', '3.8 按键模块及接口说明'),
        (E[164], '3.7.1 按键驱动接口', '3.8.1 按键驱动接口'),
        (E[169], '3.8 软件 PWM（呼吸灯）模块及接口说明', '3.9 软件 PWM（呼吸灯）模块及接口说明'),
        (E[173], '3.8.1 呼吸灯接口', '3.9.1 呼吸灯接口'),
        (E[176], '3.9 转向灯模块及接口说明', '3.10 转向灯模块及接口说明'),
    ]
    for el, old, new in renames:
        if ptext(el) != old:
            raise RuntimeError('重编号对不上：期望 %r，实际 %r' % (old, ptext(el)))
        set_ptext(el, new)

    # ============================================================ 21. 交叉引用
    replace_in_cell(E[147], '3.6.3 节', '3.7.3 节')
    replace_in_p(E[77], '3.9 节的转向灯模块', '3.10 节的转向灯模块')
    replace_in_p(E[77], '3.8 节的软件 PWM', '3.9 节的软件 PWM')
    replace_in_p(E[177], '3.8 节的软件 PWM', '3.9 节的软件 PWM')

    # ============================================================ 22. ADC 模块说明
    set_ptext(E[145],
              '本模块负责采集芯片内部温度传感器并输出温度值。温度传感器做在芯片内部，'
              '接在 ADC1 的通道 16 上，不需要任何外部器件，每 2 秒采集一次。'
              '按任务书要求，本任务屏上只显示温度、串口也只上报温度；'
              'ADC 原始值与换算电压仅在固件内部用于换算，不再对外输出。')

    # 关键设置表：去掉重复行 + 修交叉引用
    adc_rows = rows_of(E[147])
    if len(adc_rows) != 10:
        raise RuntimeError('ADC 关键设置表行数不对：%d（应为 10）' % len(adc_rows))
    seen = set()
    for tr in adc_rows:
        tcs = tr.findall(q('tc'))
        if len(tcs) != 3:
            raise RuntimeError('ADC 表有行不是 3 个单元格，文档已被破坏')
        key = cell_text(tcs[0]) + '|' + cell_text(tcs[1])
        if not cell_text(tcs[0]):
            raise RuntimeError('ADC 表出现空首列，文档已被破坏')
        if key in seen:
            tr.getparent().remove(tr)
            continue
        seen.add(key)

    # 换算表：同样去重
    conv_rows = rows_of(E[153])
    if len(conv_rows) != 9:
        raise RuntimeError('温度换算表行数不对：%d（应为 9）' % len(conv_rows))
    seen = set()
    for tr in conv_rows:
        tcs = tr.findall(q('tc'))
        if len(tcs) != 3:
            raise RuntimeError('换算表有行不是 3 个单元格，文档已被破坏')
        key = cell_text(tcs[0]) + '|' + cell_text(tcs[1])
        if not cell_text(tcs[0]):
            raise RuntimeError('换算表出现空首列，文档已被破坏')
        if key in seen:
            tr.getparent().remove(tr)
            continue
        seen.add(key)

    # ============================================================ 23. 按键表
    new_key_tbl = make_table_like(E[163], [
        ['按键', '引脚', '功能'],
        ['KEY1', 'PG3', '读取片内 Flash 数据页的记录，显示到 OLED 第 1 行，同时在串口打印十六进制数据'],
        ['KEY2', 'PG4', '左转向灯（左上角 RGB 灯珠 PG0 / PG1 / PG2）呼吸灯 开 / 关'],
        ['KEY3', 'PG5', '读取片外 W25Q64 的记录，显示到 OLED 第 3 行；芯片不在线时提示 NO W25Q64'],
    ])
    E[163].getparent().replace(E[163], new_key_tbl)

    # ============================================================ 24. 静态目录
    # 模板里的章节标题用的是 Normal 样式（不是 heading 1），挂自动目录域会漏掉章标题，
    # 所以这里直接排一份静态目录：纯文本段落，任何渲染器都不会出错。
    heads = []
    for el in body:
        if etree.QName(el).localname != 'p':
            continue
        st = pstyle(el)
        if st in ('1', '3', '4'):
            heads.append((st, ptext(el)))
    if len(heads) < 10:
        raise RuntimeError('标题数量异常：%d' % len(heads))
    heads = heads[1:]                     # 第 1 条是封面标题，不进目录
    lvl_map = {'1': 0, '3': 1, '4': 2}
    toc_cur = Cursor(E[20])               # 目录标题下面那两个空段之后
    for st, t in heads:
        toc_cur.add(mk_toc_line(E[19], t, lvl_map[st]))
    print('静态目录写入 %d 行' % len(heads))

    # ============================================================ 保存
    parts['word/document.xml'] = etree.tostring(
        root, xml_declaration=True, encoding='UTF-8', standalone=True)
    if fix_footer(parts):
        print('页脚已改为标准居中段落 + PAGE 域')
    save_parts(parts, OUT)
    print('已写出：%s' % OUT)

    # ============================================================ 回读校验
    chk = load_parts(OUT)
    root2 = etree.fromstring(chk['word/document.xml'])
    body2 = root2.find(q('body'))
    heads = []
    for el in body2:
        if etree.QName(el).localname != 'p':
            continue
        st = pstyle(el)
        if st in ('1', '3', '4'):
            t = ptext(el)
            heads.append((st, t))
            if len(t) > 40 and not t[:1].isdigit():
                raise RuntimeError('疑似标题被正文覆盖：%r' % t)
    tbl_cnt = sum(1 for el in body2 if etree.QName(el).localname == 'tbl')
    p_cnt = sum(1 for el in body2 if etree.QName(el).localname == 'p')

    print('---- 标题清单 ----')
    for st, t in heads:
        print('  %s  %s' % (st, t))
    print('表格 %d 张 / 段落 %d 个 / body 子元素 %d 个' % (tbl_cnt, p_cnt, len(body2)))


if __name__ == '__main__':
    main()
