# -*- coding: utf-8 -*-
"""
在 0918 成品接口文档（超声波测距与外部FLASH存储）上增量生成
0920 红外避障传感器采集 接口文档。

做法（沿用 chapter8->chapter9 验证过的 lxml 增量法）：
  1. 封面标题替换
  2. 修订记录表克隆末行 -> 追加 V4.0
  3. 静态目录追加 3.13 及其 5 个子项
  4. 正文末尾（sectPr 之前）追加 3.13 章节：1 个 H2 + 5 个 H3 + 段落 + 6 张表
  5. 结构自检：改前改后的标题集合必须只多不少，段落/表格增量符合预期
"""
import copy
import os
import shutil
import zipfile

from lxml import etree

SRC = r'D:\STM32_Project\docs\超声波测距与外部FLASH存储_接口文档.docx'
DST = r'D:\STM32_Project\docs\红外避障传感器采集_接口文档.docx'

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
XMLNS = '{http://www.w3.org/XML/1998/namespace}'


def q(t):
    return W + t


# --------------------------------------------------------------------------
# 基础工具
# --------------------------------------------------------------------------
def ptext(el):
    return ''.join(t.text or '' for t in el.iter(q('t')))


def set_ptext(p, s):
    """把一个段落（只能传段落！）的文字整体设为 s，保留首个 run 的格式。"""
    assert etree.QName(p).localname == 'p', 'set_ptext 只接受段落，收到 ' + etree.QName(p).localname
    ts = p.findall('.//' + q('t'))
    if not ts:
        r = p.find(q('r'))
        if r is None:
            r = etree.SubElement(p, q('r'))
        t = etree.SubElement(r, q('t'))
        ts = [t]
    ts[0].text = s
    ts[0].set(XMLNS + 'space', 'preserve')
    for t in ts[1:]:
        t.text = ''


def set_cell(tc, s):
    ps = tc.findall(q('p'))
    assert ps, '单元格里没有段落'
    set_ptext(ps[0], s)
    for extra in ps[1:]:
        tc.remove(extra)


# CT_PPr 内子元素的合法顺序（jc 必须排在 ind 之后、rPr 之前）
_PPR_ORDER = ['pStyle', 'keepNext', 'keepLines', 'pageBreakBefore', 'framePr',
              'widowControl', 'numPr', 'suppressLineNumbers', 'pBdr', 'shd', 'tabs',
              'suppressAutoHyphens', 'kinsoku', 'wordWrap', 'overflowPunct', 'topLinePunct',
              'autoSpaceDE', 'autoSpaceDN', 'bidi', 'adjustRightInd', 'snapToGrid',
              'spacing', 'ind', 'contextualSpacing', 'mirrorIndents', 'suppressOverlap',
              'jc', 'textDirection', 'textAlignment', 'textboxTightWrap', 'outlineLvl',
              'divId', 'cnfStyle', 'rPr', 'sectPr', 'pPrChange']


def force_left(tbl):
    """把表内所有单元格设为左对齐。模板单元格默认两端对齐，
    长中文串在窄列里会被拉成「字距忽大忽小」的难看样子。"""
    for p in tbl.iter(q('p')):
        ppr = p.find(q('pPr'))
        if ppr is None:
            ppr = etree.Element(q('pPr'))
            p.insert(0, ppr)
        jc = ppr.find(q('jc'))
        if jc is None:
            jc = etree.Element(q('jc'))
            try:
                rank = _PPR_ORDER.index('jc')
            except ValueError:
                rank = len(_PPR_ORDER) - 1
            pos = len(ppr)
            for i, child in enumerate(ppr):
                name = etree.QName(child).localname
                if name in _PPR_ORDER and _PPR_ORDER.index(name) > rank:
                    pos = i
                    break
            ppr.insert(pos, jc)
        jc.set(q('val'), 'left')
    return tbl


def clone(tmpl, text=None):
    el = copy.deepcopy(tmpl)
    if text is not None:
        set_ptext(el, text)
    return el


def build_table(src_tbl, rows, head_from_row0=True):
    """用 src_tbl 克隆一张新表。rows[0]=表头，其余为数据行。
    表头用 src 的 tr[0]，数据行用 src 的 tr[1]。"""
    new = copy.deepcopy(src_tbl)
    trs = new.findall(q('tr'))
    assert len(trs) >= 2, '模板表至少要有 2 行'
    head_tmpl, body_tmpl = trs[0], trs[1]
    for tr in trs:
        new.remove(tr)

    def mk(tmpl, vals):
        tr = copy.deepcopy(tmpl)
        tcs = tr.findall(q('tc'))
        assert len(tcs) == len(vals), '列数不符：模板 %d 列，数据 %d 列' % (len(tcs), len(vals))
        for tc, v in zip(tcs, vals):
            set_cell(tc, v)
        return tr

    new.append(mk(head_tmpl, rows[0]))
    for r in rows[1:]:
        new.append(mk(body_tmpl, r))
    return new


def build_api_table(src_tbl, funcs):
    """接口表：模板 tr[0..3] 分别是 函数原型/描述/参数/返回值 四种行。"""
    new = copy.deepcopy(src_tbl)
    trs = new.findall(q('tr'))
    assert len(trs) >= 4, '接口表模板至少要 4 行'
    kinds = [copy.deepcopy(trs[i]) for i in range(4)]
    for tr in trs:
        new.remove(tr)
    for f in funcs:
        assert len(f) == 4, '每个函数要 4 个字段对'
        for tmpl, (label, val) in zip(kinds, f):
            tr = copy.deepcopy(tmpl)
            tcs = tr.findall(q('tc'))
            assert len(tcs) == 2, '接口表应为 2 列'
            set_cell(tcs[0], label)
            set_cell(tcs[1], val)
            new.append(tr)
    return new


# --------------------------------------------------------------------------
# 1. 打开并取模板
# --------------------------------------------------------------------------
shutil.copy2(SRC, DST)

with zipfile.ZipFile(SRC) as z:
    parts = [(it, z.read(it.filename)) for it in z.infolist()]

xml_bytes = dict((it.filename, d) for it, d in parts)['word/document.xml']
root = etree.fromstring(xml_bytes)
body = root.find(q('body'))
els = list(body)

TBL_HW = els[279]    # 4 列：信号 | 模块/MCU | 引脚 | 说明
TBL_API = els[282]   # 2 列：函数原型/描述/参数/返回值
TBL_FIELD = els[165]  # 3 列：行号 | 内容 | 说明
TBL_3A = els[255]    # 3 列：按键 | 引脚 | 功能
TBL_3B = els[189]    # 3 列：宏名 | 取值 | 说明
TBL_4 = els[296]     # 4 列：距离区间 | 报警类型 | 声光动作 | 屏上提示
P_H2 = els[288]      # 二级标题模板
P_H3 = els[290]      # 三级标题模板
P_BODY = els[289]    # 正文段模板
DIR_ANCHOR = els[73]   # 目录最后一行：3.12.4 报警服务接口
TOC_ROW = els[70]      # 目录条目模板（ind=210 / 420 由脚本改）
REV_TBL = els[16]      # 修订记录表
SECT = None
for el in body:
    if etree.QName(el).localname == 'sectPr':
        SECT = el
assert SECT is not None, 'body 末尾没有独立 sectPr'

orig_titles = [ptext(p) for p in body.iter(q('p'))
               if p.find(q('pPr')) is not None
               and p.find(q('pPr')).find(q('pStyle')) is not None]
orig_para_cnt = len(body.findall(q('p')))
orig_tbl_cnt = len([e for e in body if etree.QName(e).localname == 'tbl'])

log = []


def add(el):
    if etree.QName(el).localname == 'tbl':
        force_left(el)
    SECT.addprevious(el)
    return el


# --------------------------------------------------------------------------
# 2. 封面标题
# --------------------------------------------------------------------------
set_ptext(els[0], '红外避障传感器采集方案文档（接口）')
set_ptext(els[5], '拟制：陈相林')
log.append('封面标题已替换')

# --------------------------------------------------------------------------
# 3. 修订记录表追加 V4.0
# --------------------------------------------------------------------------
rev_rows = REV_TBL.findall(q('tr'))
last = rev_rows[-1]
new_rev = copy.deepcopy(last)
vals = ['2026.09.20', 'V4.0',
        '新增左右两路红外避障对管采集模块（需求 5）：PE5/PE6 开漏驱动发射管、'
        'PF9/PF10 走 ADC3 差分测反射强度；KEY1 测左侧、KEY2 测右侧、KEY3 测双路并打印串口，'
        'OLED 第 3、4 行改为红外档位与原始差值；原 KEY1（测距存储）与 KEY3（读片外 FLASH）'
        '分别改为串口快捷命令 O 与 E',
        '陈相林']
tcs = new_rev.findall(q('tc'))
assert len(tcs) == 4, '修订记录表应为 4 列'
for tc, v in zip(tcs, vals):
    set_cell(tc, v)
last.addnext(new_rev)
log.append('修订记录追加 V4.0')

# --------------------------------------------------------------------------
# 4. 目录追加 3.13 六行
# --------------------------------------------------------------------------
TOC_ITEMS = [
    ('3.13 红外避障传感器模块及接口说明', 210),
    ('3.13.1 硬件连接', 420),
    ('3.13.2 红外对管驱动接口', 420),
    ('3.13.3 差分测量原理与门限标定', 420),
    ('3.13.4 按键交互与显示', 420),
    ('3.13.5 串口输出格式', 420),
]
pre = DIR_ANCHOR
for text, ind in TOC_ITEMS:
    row = clone(TOC_ROW, text)
    ppr = row.find(q('pPr'))
    indv = ppr.find(q('ind'))
    if indv is None:
        indv = etree.SubElement(ppr, q('ind'))
    indv.set(q('left'), str(ind))
    indv.set(q('firstLine'), '0')
    pre.addnext(row)
    pre = row
log.append('目录追加 %d 行' % len(TOC_ITEMS))

# --------------------------------------------------------------------------
# 5. 正文新增 3.13 章节
# --------------------------------------------------------------------------
h2 = lambda s: clone(P_H2, s)
h3 = lambda s: clone(P_H3, s)
para = lambda s: clone(P_BODY, s)

# --- 3.13 总述 ---------------------------------------------------------
add(h2('3.13 红外避障传感器模块及接口说明'))
add(para('本模块是需求 5 的核心，完成左右两路红外避障传感器的数据采集。'
         '板载红外避障电路不是常见的三线一体模块，而是两组分立对管：一颗红外发射管配一颗红外接收管，'
         '左右各一组，装在超声波探头两侧的板子前缘。发射管由 MCU 通过 PNP 三极管驱动，'
         '接收管集电极经 10K 电阻上拉到 3V3，反射光越强则该节点电压越低。'))
add(para('因为接收端是模拟节点而不是数字电平，模块采用 ADC3 差分测量：先熄灯采一次本底，再点亮采一次反射，'
         '两者之差就是反射强度，环境光被自动扣掉。测量、分档、显示、串口上报四件事由驱动层和应用层分开承担，'
         '应用层只拿到一个结构体和一句布尔结论。'))

# --- 3.13.1 硬件连接 ---------------------------------------------------
add(h3('3.13.1 硬件连接'))
add(para('两路红外对管与主控的连线关系如下表，网络名取自原理图：'))
add(build_table(TBL_HW, [
    ['信号', '网络', 'MCU 引脚', '说明'],
    ['左发射管驱动', 'P1', 'PE5', '开漏输出，低电平点亮；经 R30(1K) 驱动 Q2(SS8550 PNP) 基极'],
    ['右发射管驱动', 'P3', 'PE6', '开漏输出，低电平点亮；经 R29(1K) 驱动 Q1(SS8550 PNP) 基极'],
    ['左接收管输出', 'P2', 'PF9', '模拟输入，ADC3_IN7；D7 集电极经 R17(10K) 上拉到 3V3'],
    ['右接收管输出', 'P4', 'PF10', '模拟输入，ADC3_IN8；D8 集电极经 R18(10K) 上拉到 3V3'],
]))
add(para('发射管驱动必须用开漏（GPIO_Mode_Out_OD）而不是推挽：驱动管的基极回路接在 5V 上，'
         '而 MCU 推挽输出高只有 3.3V，此时 Vbe 仍有约 1.7V，三极管关不掉。'
         '开漏写 0 把基极拉到地、灯亮；写 1 呈高阻，基极被 5V 经 1K 抬到约 4.2V、灯灭。'))
add(para('开漏「熄」的时候引脚会被基极回路抬到 5V 附近，所以这两个脚必须是 5V 容忍脚。'
         '数据手册中 PE5、PE6 均标注为 FT，可以直接这样接；换成非 FT 脚会长期过压。'))
add(para('接收侧的另一条电学结论是「有障碍 = 低电平」：接收管见光导通，把 10K 上拉节点往下拉；'
         '反射越强，节点电压越低，所以 ADC 读数越小表示越近。这一点极易写反，'
         '驱动里以「本底减反射」的差分形式固定下来，不需要再判方向。'))

# --- 3.13.2 驱动接口 ---------------------------------------------------
add(h3('3.13.2 红外对管驱动接口'))
add(para('模块对上层提供以下接口，应用层不接触任何 GPIO 或 ADC 寄存器：'))
add(build_api_table(TBL_API, [
    [('函数原型', 'void Ir_Init(void)'),
     ('描述', '把 PE5/PE6 配成开漏输出并置为熄灭，PF9/PF10 配成模拟输入；'
              'ADC3 配为独立模式、单通道、软件触发，并完成复位校准与校准'),
     ('参数', 'void'),
     ('返回值', 'void')],
    [('函数原型', 'void Ir_Emit(uint8_t isLeft, uint8_t on)'),
     ('描述', '单独控制某一侧发射管的亮灭，供测量流程与诊断使用；两边分时点亮，不会互相串光'),
     ('参数', 'isLeft：1 = 左侧（PE5），0 = 右侧（PE6）；on：1 = 点亮，0 = 熄灭'),
     ('返回值', 'void')],
    [('函数原型', 'void Ir_Measure(uint8_t isLeft, IrResult_t *r)'),
     ('描述', '完成一次差分测量：先熄灯采本底，再点灯采反射，算出差值并按门限分档；'
              '结果同时写入模块内部的最近一次缓存'),
     ('参数', 'isLeft：1 = 左侧，0 = 右侧；r：结果结构体的输出指针'),
     ('返回值', 'void')],
    [('函数原型', 'void Ir_MeasureBoth(IrResult_t *left, IrResult_t *right)'),
     ('描述', '把左右两路依次测完，供 KEY3 与串口快捷命令 V 使用'),
     ('参数', 'left、right：两侧结果的输出指针'),
     ('返回值', 'void')],
    [('函数原型', 'const IrResult_t *Ir_Last(uint8_t isLeft)'),
     ('描述', '取最近一次测量结果的只读指针，不触发新的测量，供显示与判断复用'),
     ('参数', 'isLeft：1 = 左侧，0 = 右侧'),
     ('返回值', '结果结构体只读指针；从未测量过时其 valid 字段为 0')],
    [('函数原型', 'uint8_t Ir_IsBlocked(uint8_t isLeft)'),
     ('描述', '把最近一次结果转成布尔结论，方便上位机或外部模块直接取 0/1'),
     ('参数', 'isLeft：1 = 左侧，0 = 右侧'),
     ('返回值', '1 = 有遮挡（MID 或 NEAR 档）；0 = 无障碍，或该侧尚未测量')],
    [('函数原型', 'const char *Ir_LevelWord(uint8_t level)'),
     ('描述', '把档位编号转成定宽英文单词，供 OLED 按固定列宽显示，避免行尾抖动'),
     ('参数', 'level：0 = FAR，1 = MID，2 = NEAR'),
     ('返回值', '"FAR "、"MID "、"NEAR"，均为 4 字符定宽')],
]))
add(para('测量结果统一用 IrResult_t 结构体返回，字段含义如下：'))
add(build_table(TBL_FIELD, [
    ['字段', '类型', '说明'],
    ['dark', 'uint16_t', '熄灯时的 ADC3 读数，即本底值，其中包含环境光'],
    ['lit', 'uint16_t', '点灯时的 ADC3 读数，反射越强该值越低'],
    ['diff', 'uint16_t', 'dark 减 lit，即反射强度；值越大表示反射物越近'],
    ['level', 'uint8_t', '分档结果：0 = FAR，1 = MID，2 = NEAR'],
    ['strength', 'uint8_t', '归一化强度，diff 相对满量程的百分比，上限 100'],
    ['valid', 'uint8_t', '1 = 本次结果有效；0 = 该侧尚未测量过'],
]))

# --- 3.13.3 差分测量与门限 ---------------------------------------------
add(h3('3.13.3 差分测量原理与门限标定'))
add(para('一次测量的四步：一是熄灭该侧发射管，延时 1ms 等接收管恢复，读 ADC3 得到本底 dark；'
         '二是点亮该侧发射管，延时 1ms 等光稳定，读 ADC3 得到 lit；三是熄灭发射管，恢复默认状态；'
         '四是求 diff，若 dark 不大于 lit 则取 0，滤掉反射极弱时的负值。'))
add(para('单次读数取 8 个样本，丢掉第一个（通道切换后的首次转换不可信），'
         '再掐头去尾各丢一个极值后取平均，抑制工频干扰和随机噪声。'
         '采样时间为 239.5 个 ADCCLK 周期，对应约 12MHz 的 ADCCLK（PCLK2 六分频），'
         '足以把 10K 源阻抗的采样电容充满。'))
add(para('档位门限按上板实测标定，实测数据如下：'))
add(build_table(TBL_3A, [
    ['前方状况', 'diff 实测范围', '判定档位'],
    ['完全空旷，前方无反射物', '0 ~ 30', 'FAR'],
    ['约 30cm 处有漫反射物（桌面、支架）', '150 ~ 260', 'FAR，低于 MID 门限，不误报'],
    ['约 1cm 内贴住，接收管接近饱和', '3900 ~ 3960', 'NEAR'],
]))
add(para('三档门限与相关常量取值如下：'))
add(build_table(TBL_3B, [
    ['宏名', '取值', '说明'],
    ['IR_DIFF_MID', '600', '判定 MID 的下限，取在「桌面漫反射」与「近距离遮挡」之间'],
    ['IR_DIFF_NEAR', '2000', '判定 NEAR 的下限'],
    ['IR_DIFF_FULL', '4000', '归一化 strength 的满量程参考值'],
    ['IR_ADC_AVG', '8', '每侧每态的采样次数，掐头去尾后取平均'],
    ['IR_SETTLE_MS', '1', '灯态切换后的稳定等待，单位毫秒'],
]))
add(para('门限之所以比早期版本定得高一截，是因为 30cm 外桌面的漫反射也能产生 200 左右的差值，'
         '若门限取 200 就会把「前方空旷」误判成有障碍。取 600 之后，空旷与桌面反射都稳定判 FAR，'
         '只有真正靠近的遮挡物才会进入 MID 或 NEAR。判档之外，原始三条数据 dark、lit、diff 都从串口输出，'
         '现场可以直接对照量值，不必只信一个档位结论。'))

# --- 3.13.4 按键交互 ---------------------------------------------------
add(h3('3.13.4 按键交互与显示'))
add(para('任务书要求按 KEY1 测左侧、按 KEY2 测右侧、按 KEY3 测两路并把数据打印到 PC。'
         '按键分工与显示表现如下：'))
add(build_table(TBL_4, [
    ['按键', '动作', 'OLED 显示', '串口输出'],
    ['KEY1', '测左侧，PE5 发射、PF9 接收',
     '第 3 行左半显示 L: 后接档位单词，第 4 行 dL 显示原始差值',
     'IR : left 一行，含 diff、dark、lit、level'],
    ['KEY2', '测右侧，PE6 发射、PF10 接收',
     '第 3 行右半显示 R: 后接档位单词，第 4 行 dR 显示原始差值',
     'IR : right 一行，字段同上'],
    ['KEY3', '左右两路依次测完',
     '第 3、4 行同时刷新',
     'both sensors measured、RESULT、DETECT 共三行'],
]))
add(para('第 3 行显示的是档位单词，未测量过的一侧显示四个短横，'
         '这样就不会把「还没测」和「测得 FAR」混为一谈。'
         '第 4 行显示的是原始差值，四位右对齐，现场判断灵敏度时比档位更直观。'))
add(para('因为本章把三个按键全部让给需求 5，需求 1 到需求 4 原先占用 KEY1、KEY3 的两个功能改为串口命令触发：'
         '快捷命令 O 触发一次超声波测距并存入片内 Flash，快捷命令 E 读出片外 Flash 中保存的文本记录。'
         '其余既有功能（呼吸灯、转向灯、温度采集、片内存储）不受影响。'))

# --- 3.13.5 串口输出格式 -----------------------------------------------
add(h3('3.13.5 串口输出格式'))
add(para('需求 5 第二项要求把两路数据打印到 PC。串口参数维持 115200-8-N-1 不变，'
         '含中文的提示串以 GBK 编码发出，串口助手按 GBK 解码即可正常显示。'))
add(para('单路测量的输出形如（左侧被近距离遮挡、右侧前方空旷）：'))
add(para('IR   : left   diff=3952  dark=4075  lit=0123  level=NEAR'))
add(para('IR   : right  diff=0088  dark=4082  lit=3994  level=FAR'))
add(para('按 KEY3 把两路都测完之后，会连续输出五行，先给结论再给明细：'))
add(para('IR   : ----- both sensors measured -----'))
add(para('IR   : left   diff=3952  dark=4075  lit=0123  level=NEAR'))
add(para('IR   : right  diff=0088  dark=4082  lit=3994  level=FAR'))
add(para('IR   : RESULT  L=NEAR  R=FAR   (FAR=CLEAR  MID/NEAR=BLOCKED)'))
add(para('IR   : DETECT  L=1  R=0   (1=blocked  0=clear)'))
add(para('其中 RESULT 行给出档位文字，DETECT 行把同一结论压成 0/1，'
         '方便上位机或外部模块直接解析，不必再解析英文单词。'))
add(para('另外提供一条诊断命令 #，在排查接线时把两路原始值和引脚分配一起打印出来：'))
add(para('IR   : scan  (dark = LED off / lit = LED on / diff = dark - lit)'))
add(para('IR   : pins  LED_L=PE5 LED_R=PE6  RX_L=PF9(ADC3_IN7) RX_R=PF10(ADC3_IN8)'))
add(para('IR   : left   diff=3952  dark=4075  lit=0123  level=NEAR'))
add(para('IR   : right  diff=0088  dark=4082  lit=3994  level=FAR'))

# --------------------------------------------------------------------------
# 6. 结构自检 + 写回
# --------------------------------------------------------------------------
new_titles = [ptext(p) for p in body.iter(q('p'))
              if p.find(q('pPr')) is not None
              and p.find(q('pPr')).find(q('pStyle')) is not None]
ALLOW_REPLACED = {'超声波测距与外部 FLASH 存储方案文档（接口）'}   # 封面标题按当日任务名替换
missing = [t for t in orig_titles if t not in new_titles and t not in ALLOW_REPLACED]
new_para_cnt = len(body.findall(q('p')))
new_tbl_cnt = len([e for e in body if etree.QName(e).localname == 'tbl'])

log.append('标题 %d -> %d' % (len(orig_titles), len(new_titles)))
log.append('段落 %d -> %d' % (orig_para_cnt, new_para_cnt))
log.append('表格 %d -> %d' % (orig_tbl_cnt, new_tbl_cnt))
if missing:
    raise RuntimeError('原有标题丢失: %r' % missing)
if new_tbl_cnt - orig_tbl_cnt != 6:
    raise RuntimeError('表格增量应为 6，实际 %d' % (new_tbl_cnt - orig_tbl_cnt))
if len(new_titles) - len(orig_titles) != 6:
    raise RuntimeError('标题增量应为 6（1 个 H2 + 5 个 H3），实际 %d'
                       % (len(new_titles) - len(orig_titles)))

new_xml = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)

with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zout:
    for it, data in parts:
        if it.filename == 'word/document.xml':
            data = new_xml
        zout.writestr(it, data)

print('\n'.join('  ' + x for x in log))
print()
print('OK ->', DST, os.path.getsize(DST), 'bytes')
