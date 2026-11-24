# -*- coding: utf-8 -*-
"""chapter8 接口文档 v3 —— 同步 OLED 温度数据页的新版式。

源：D:/STM32_Project/docs/ADC内部温度采集_接口文档_v2.docx   （80 张表）
目标：D:/STM32_Project/docs/ADC内部温度采集_接口文档_v3.docx

背景：2026-09-16 下午，按任务书截图要求，AdcTemp_Full 的温度数据页由
      「上半屏 16x16 大字 + 下半屏小字」改为任务书规定的三行标签格式：
          ADCvalue:  1738
          Voltage:  1.390V
          Temp:     35.9C
          L0 R0 B0 D0 CAL      <- 第 4 行设备状态（任务书之外的加做项，保留）
      放大字接口（OLED_ShowCharBig / OLED_ShowStringBig）仍保留在驱动里，
      只是本工程不再调用，因此文档不删接口，只改写描述与布局表。

改动（锚点全部按内容查找，不用裸索引）：
  1. 修订记录表      ：补一行 V1.2
  2. 1.1 前言        ：「OLED 大字与中文显示」-> 「OLED 数据页显示与中文提示」
  3. 3.2.3 放大字段落：改写为「接口保留、温度页改用任务书标签版式」
  4. 3.2.3 小数点段  ：补一句「本工程未调用」
  5. 3.2.3 显示页段落：改写布局说明
  6. 3.2.3 布局表    ：重写为三行标签格式（新增 1 行，共 8 行）
"""
import copy
import zipfile

from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
XML = 'http://www.w3.org/XML/1998/namespace'
q = lambda t: '{%s}%s' % (W, t)

SRC = r'D:/STM32_Project/docs/ADC内部温度采集_接口文档_v2.docx'
DST = r'D:/STM32_Project/docs/ADC内部温度采集_接口文档_v3.docx'

zin = zipfile.ZipFile(SRC)
root = etree.fromstring(zin.read('word/document.xml'))
body = root.find(q('body'))
log = []


# ------------------------------------------------------------------ 工具
def ptext(e):
    """段落纯文本"""
    return ''.join(t.text or '' for t in e.iter(q('t')))


def set_text(elem, text):
    """把元素内的第一个 w:t 设成 text，清空其余 w:t（保留段落/字符格式）"""
    ts = list(elem.iter(q('t')))
    if not ts:
        raise RuntimeError('no w:t in %s' % elem.tag)
    ts[0].text = text
    ts[0].set('{%s}space' % XML, 'preserve')
    for t in ts[1:]:
        t.text = ''
    return elem


def row_texts(tr):
    """一行的各单元格文本"""
    out = []
    for tc in tr.findall(q('tc')):
        out.append(' '.join(''.join(x.text or '' for x in tc.iter(q('t'))).split()))
    return out


def tbl_texts(tbl):
    return [row_texts(tr) for tr in tbl.findall(q('tr'))]


def set_cell(tc, text):
    """写单元格：第一个段落的首个 w:t = text，其余段落与 w:t 清空"""
    ps = tc.findall(q('p'))
    if not ps:
        raise RuntimeError('cell without w:p')
    set_text(ps[0], text)
    for p in ps[1:]:
        for t in p.iter(q('t')):
            t.text = ''
    return tc


def set_row(tr, values):
    tcs = tr.findall(q('tc'))
    if len(tcs) != len(values):
        raise RuntimeError('列数不符：%d vs %d' % (len(tcs), len(values)))
    for tc, v in zip(tcs, values):
        set_cell(tc, v)
    return tr


def find_para(pred, what):
    for e in body:
        if e.tag == q('p') and pred(ptext(e)):
            return e
    raise RuntimeError('找不到段落：' + what)


def find_tbl(pred, what):
    for e in body:
        if e.tag == q('tbl'):
            t = tbl_texts(e)
            if pred(t):
                return e
    raise RuntimeError('找不到表格：' + what)


def heading_set():
    """所有标题样式段落的文本集合（样式 val 是数字 ID：00001e/000020/000021）"""
    ids = {'00001e', '000020', '000021'}
    s = set()
    for e in body:
        if e.tag == q('p'):
            st = e.find(q('pPr') + '/' + q('pStyle'))
            if st is not None and st.get(q('val')) in ids:
                s.add(ptext(e).strip())
    return s


before_head = heading_set()
before_paras = sum(1 for e in body if e.tag == q('p'))
before_tbls = sum(1 for e in body if e.tag == q('tbl'))

# ------------------------------------------------- 1. 修订记录：补 V1.2
tbl_rev = find_tbl(lambda t: t[0][:2] == ['日期', '版本'] and any('首次发布' in r[2] for r in t),
                   '修订记录表')
# 空行里的单元格没有 w:t 节点（直接写会报错），所以克隆最近一条有内容的行来做模板，
# 继承它的段落/字符格式，插到空行之前；表行数保持不变。
tmpl_row = None
empty_row = None
for tr in tbl_rev.findall(q('tr'))[1:]:
    if all(not c for c in row_texts(tr)):
        empty_row = tr
        break
    tmpl_row = tr
if empty_row is None or tmpl_row is None:
    raise RuntimeError('修订记录表结构不符：空行=%s 模板行=%s' % (empty_row is not None, tmpl_row is not None))
new_row = copy.deepcopy(tmpl_row)
empty_row.addprevious(new_row)
set_row(new_row, ['2026.09.16', 'V1.2',
                  '修订：温度数据页按任务书格式改为 ADCvalue / Voltage / Temp 三行标签显示；'
                  '放大字接口保留在驱动中供扩展使用', ''])
log.append('修订记录：补 V1.2 一行（5 行 -> 6 行）')
rev_rows_expected = len(tbl_rev.findall(q('tr')))

# --------------------------------------------- 2. 1.1 前言：措辞同步
p = find_para(lambda s: 'OLED 大字与中文显示' in s, '1.1 前言')
set_text(p, ptext(p).replace('OLED 大字与中文显示', 'OLED 数据页显示与中文提示'))
log.append('1.1 前言：OLED 大字与中文显示 -> OLED 数据页显示与中文提示')

# ------------------------------------- 3. 3.2.3 放大字段落：改为「接口保留」
p = find_para(lambda s: s.strip().startswith('屏最上面一行文字用放大字显示'), '放大字说明')
set_text(p,
         '驱动里另有一套放大字接口：不做新的字模，把 8x8 字模按「每行像素复制一遍、'
         '每列像素复制一遍」放大 2 倍，得到 16x16 的点阵，纵向跨相邻两页，字号立刻翻倍，'
         '一行最多放 8 个放大字。本工程的温度数据页按任务书规定的标签格式改用 8x8 字符显示，'
         '放大字接口保留在驱动中，留给后续扩展使用。放大字相关的接口如下：')
log.append('3.2.3：放大字段落改写为「接口保留」')

# ------------------------------------- 4. 3.2.3 小数点段落：补「未调用」
p = find_para(lambda s: s.strip().startswith('放大字的小数点单独处理'), '小数点说明')
set_text(p,
         '放大字的小数点单独处理：8x8 字模里句点只有 2x2 个像素，放大后也只有 4x4，'
         '在屏上很不显眼，因此绕过字模，直接画一个 6x6 的实心方块，贴着底线、'
         '在 16 像素宽的格子里水平居中。温度数据页现在用 8x8 字符显示，小数点直接由字模给出，'
         '不再走这条加粗路径。')
log.append('3.2.3：小数点段落补「温度页不再走加粗路径」')

# ------------------------------------- 5. 3.2.3 显示页段落：布局说明改写
p = find_para(lambda s: s.strip().startswith('屏分温度数据页与文本页两个显示页'), '显示页说明')
set_text(p,
         '屏分温度数据页与文本页两个显示页。温度页按任务书规定的三行标签格式，'
         '用 8x8 字符自上而下依次显示 ADC 原始值、换算电压与温度，第 4 行显示设备状态；'
         '文本页保留两行 32 字符的文本，下半屏用 16x16 汉字显示中文提示：')
log.append('3.2.3：显示页说明改写为三行标签格式')

# ------------------------------------- 6. 布局表：重写 + 新增一行
tbl_layout = find_tbl(lambda t: t[0] == ['行号', '内容', '说明'] and any('温度页' in r[0] for r in t),
                      '显示页布局表')
trs = tbl_layout.findall(q('tr'))
if len(trs) != 7:
    raise RuntimeError('布局表行数变了：%d' % len(trs))

# r1 温度页上半屏 -> 温度页第 1 行（ADCvalue）
# 示例按屏上真实字符串写：标签 + 固定 5 格数值域（"ADCvalue:" 9 格 + " 1738" 5 格）
set_row(trs[1], ['温度页 第 1 行', 'ADCvalue: 1738',
                 'ADC 原始值（0~4095）；标签长度固定，数值在固定 5 格内右对齐，位数变化时数字不左右跳'])
# r2 温度页第 3 行 -> 温度页第 2 行（Voltage）
set_row(trs[2], ['温度页 第 2 行', 'Voltage: 1.390V',
                 '换算后的模拟量，保留 3 位小数，数值同样在固定 5 格内右对齐'])
# 新增一行：温度页第 3 行（Temp），插在 r2 之后
tr_new = copy.deepcopy(trs[2])
trs[2].addnext(tr_new)
set_row(tr_new, ['温度页 第 3 行', 'Temp:  35.9C',
                 '芯片温度，保留 1 位小数（已标定时为标定后的值）；读数无效时显示 --.-C，不会把离谱数字当真值'])
# r3 温度页第 4 行（状态行，只改行号描述）
set_row(trs[3], ['温度页 第 4 行', 'L0 R0 B0 D0 CAL',
                 '设备状态与模式提示（任务书之外的加做项）：L/R 左右转向灯、B 蜂鸣器、D 灯条；'
                 '尾部 CAL 表示已标定、BRTH 表示正在呼吸、RST / NEW 标识开机来源'])
# r6 说明行 -> 改为标签/对齐说明
set_row(trs[6], ['说明', '标签定长 + 值域定宽',
                 '三行标签与串口上报的三个量一一对应（ADC 原始值、换算电压、温度），'
                 '方便屏上读数与串口数据对照；数值统一在固定 5 格内右对齐，'
                 '读数位数变化时数字不会左右抖动'])
log.append('3.2.3：显示页布局表改为三行标签格式（7 行 -> 8 行）')

# ------------------------------------------------------------------ 校验
after_head = heading_set()
after_paras = sum(1 for e in body if e.tag == q('p'))
after_tbls = sum(1 for e in body if e.tag == q('tbl'))

missing = before_head - after_head
added = after_head - before_head
if missing or added:
    raise RuntimeError('标题集合变了！缺失=%s 新增=%s' % (missing, added))
if after_tbls != before_tbls:
    raise RuntimeError('表格数变了：%d -> %d' % (before_tbls, after_tbls))
if after_paras != before_paras:
    raise RuntimeError('段落数变了：%d -> %d' % (before_paras, after_paras))

# 结构体检：标题位置的段落不应被正文覆盖
for e in body:
    if e.tag == q('p'):
        st = e.find(q('pPr') + '/' + q('pStyle'))
        if st is not None and st.get(q('val')) in {'00001e', '000020', '000021'}:
            s = ptext(e).strip()
            if len(s) > 40 and not s[0].isdigit():
                raise RuntimeError('疑似标题段被覆盖：%s' % s[:60])

print('标题数 %d -> %d（集合一致）' % (len(before_head), len(after_head)))
print('段落 %d -> %d，表格 %d -> %d' % (before_paras, after_paras, before_tbls, after_tbls))

# ------------------------------------------------------------------ 落盘
out = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zout:
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename == 'word/document.xml':
            data = out
        zout.writestr(item, data)
zin.close()

print('== 改动清单 ==')
for x in log:
    print('   -', x)
print('SAVED ->', DST)
