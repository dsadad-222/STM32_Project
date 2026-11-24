# -*- coding: utf-8 -*-
"""
在 0917 成品《片内片外FLASH读写_接口文档.docx》上增量生成
0918《超声波测距与外部FLASH存储_接口文档.docx》。

方法 B（skill engineering-delivery-pipeline Step 3）：不碰模板，直接克隆上一章
成品里的现有元素（标题段 / 正文段 / 表格行）再改文字 —— 样式、手打编号、表格
边框全部原样继承，绕开 markdown 插入的转义坑。

硬规矩（skill Pitfalls #11 / #16）：
  * 锚点一律「按内容查」，不用裸索引；
  * set_ptext 只接受段落，传表格直接 raise；
  * 改完做结构自检：原有标题集合必须一个不少。
"""
import os
import shutil
import sys
import zipfile

from lxml import etree

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
XMLSPACE = '{http://www.w3.org/XML/1998/namespace}space'

BASE = r'D:/STM32_Project/docs/片内片外FLASH读写_接口文档.docx'
OUT = r'D:/STM32_Project/docs/超声波测距与外部FLASH存储_接口文档.docx'


# --------------------------------------------------------------------------
# 基础工具
# --------------------------------------------------------------------------
def qn(tag):
    return W + tag


def ptext(el):
    """取一个元素（段落或表格）里的全部文字"""
    return ''.join(t.text or '' for t in el.iter(qn('t')))


def is_p(el):
    return etree.QName(el).localname == 'p'


def is_tbl(el):
    return etree.QName(el).localname == 'tbl'


def style_of(p):
    st = p.find(qn('pPr') + '/' + qn('pStyle'))
    return st.get(qn('val')) if st is not None else None


def set_ptext(p, text):
    """改写段落的文字，保留第一个 run 的格式，删掉多余 run。

    ⚠ 只能传段落：表格的 ptext 是所有单元格文字拼起来的，写进来会把整张表压成
       一个单元格（skill Pitfall #16）。
    """
    if not is_p(p):
        raise RuntimeError('set_ptext 只能传段落，收到 <%s>' % etree.QName(p).localname)

    runs = p.findall(qn('r'))
    if not runs:
        raise RuntimeError('段落里一个 run 都没有，无法改写：%r' % ptext(p)[:40])

    keep = runs[0]
    for r in runs[1:]:
        p.remove(r)

    # 分页标记会把标题首字位置搞乱，顺手摘掉
    for lr in keep.findall(qn('lastRenderedPageBreak')):
        keep.remove(lr)

    ts = keep.findall(qn('t'))
    if not ts:
        t = etree.SubElement(keep, qn('t'))
        t.set(XMLSPACE, 'preserve')
        ts = [t]
    for extra in ts[1:]:
        keep.remove(extra)
    ts[0].text = text
    ts[0].set(XMLSPACE, 'preserve')


def set_cell(tc, text):
    """改写一个单元格：只留第一个段落，多余段落删掉"""
    ps = tc.findall(qn('p'))
    if not ps:
        raise RuntimeError('单元格里没有段落')
    set_ptext(ps[0], text)
    for extra in ps[1:]:
        tc.remove(extra)


def set_row(row, values):
    tcs = row.findall(qn('tc'))
    if len(tcs) != len(values):
        raise RuntimeError('列数不符：表格 %d 列，给了 %d 个值' % (len(tcs), len(values)))
    for tc, v in zip(tcs, values):
        set_cell(tc, v)


def clone(el):
    import copy
    return copy.deepcopy(el)


def find_para(body, needle, start=0):
    """按内容找段落（Pitfall #11：锚点按内容查，别用裸索引）"""
    kids = list(body)
    for i in range(start, len(kids)):
        el = kids[i]
        if is_p(el) and needle in ptext(el):
            return i, el
    raise RuntimeError('找不到包含 %r 的段落' % needle)


def find_tbl(body, needle, start=0):
    kids = list(body)
    for i in range(start, len(kids)):
        el = kids[i]
        if is_tbl(el) and needle in ptext(el):
            return i, el
    raise RuntimeError('找不到包含 %r 的表格' % needle)


def find_tbl_by_row(body, row_text, start=0):
    """按「第一行文本」找表格，比按内容找更精确"""
    kids = list(body)
    for i in range(start, len(kids)):
        el = kids[i]
        if not is_tbl(el):
            continue
        rows = el.findall(qn('tr'))
        if rows and ptext(rows[0]).strip().startswith(row_text):
            return i, el
    raise RuntimeError('找不到首行为 %r 的表格' % row_text)


# --------------------------------------------------------------------------
# 建段落 / 建表格（全部靠克隆现有元素）
# --------------------------------------------------------------------------
def make_para(anchor_para, text):
    p = clone(anchor_para)
    set_ptext(p, text)
    return p


def make_iface_table(anchor_tbl, funcs):
    """克隆一张「函数原型/描述/参数/返回值」2 列表，按 funcs 重建行。

    funcs = [(原型, 描述, 参数, 返回值), ...]
    """
    tbl = clone(anchor_tbl)
    rows = tbl.findall(qn('tr'))
    if not rows:
        raise RuntimeError('锚点表没有行')
    tpl = clone(rows[0])            # 2 列的行模板

    for r in rows:
        tbl.remove(r)

    for proto, desc, params, ret in funcs:
        for label, content in (('函数原型', proto), ('描述', desc),
                               ('参数', params), ('返回值', ret)):
            nr = clone(tpl)
            set_row(nr, [label, content])
            tbl.append(nr)
    return tbl


def make_grid_table(anchor_tbl, header, data_rows):
    """克隆一张 N 列表，重建成 header + data_rows"""
    tbl = clone(anchor_tbl)
    rows = tbl.findall(qn('tr'))
    if not rows:
        raise RuntimeError('锚点表没有行')
    ncol = len(rows[0].findall(qn('tc')))
    if len(header) != ncol:
        raise RuntimeError('表头 %d 列，锚点表 %d 列' % (len(header), ncol))
    tpl = clone(rows[0])
    for r in rows:
        tbl.remove(r)
    for vals in [header] + data_rows:
        if len(vals) != ncol:
            raise RuntimeError('数据行 %d 列，锚点表 %d 列：%r' % (len(vals), ncol, vals[:2]))
        nr = clone(tpl)
        set_row(nr, vals)
        tbl.append(nr)
    return tbl


def append_rows(tbl, data_rows):
    """在已有表格尾部追加数据行（克隆末行做模板）"""
    rows = tbl.findall(qn('tr'))
    if not rows:
        raise RuntimeError('表没有行')
    tpl = clone(rows[-1])
    ncol = len(rows[-1].findall(qn('tc')))
    for vals in data_rows:
        if len(vals) != ncol:
            raise RuntimeError('追加行 %d 列，表 %d 列' % (len(vals), ncol))
        nr = clone(tpl)
        set_row(nr, vals)
        tbl.append(nr)


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def main():
    if not os.path.exists(BASE):
        sys.exit('基稿不存在：%s' % BASE)

    # 改前留档（Pitfall #18）
    if os.path.exists(OUT):
        shutil.copy2(OUT, OUT + '.bak')
    shutil.copy2(BASE, OUT)

    zin = zipfile.ZipFile(OUT)
    items = {n: zin.read(n) for n in zin.namelist()}
    zin.close()

    root = etree.fromstring(items['word/document.xml'])
    body = root.find(qn('body'))

    # ---- 改前记录标题集合（自检用）----
    before_titles = [ptext(e).strip() for e in body
                     if is_p(e) and style_of(e) in ('3', '4')]
    before_titles = [t for t in before_titles if t]

    log = []

    # ======================================================================
    # E1 封面标题
    # ======================================================================
    _, p = find_para(body, 'FLASH 读写方案文档（接口）')
    set_ptext(p, '超声波测距与外部 FLASH 存储方案文档（接口）')
    log.append('E1  封面标题')

    # ======================================================================
    # E2 修订记录：把末尾空行换成 V3.0 行
    #     空单元格没有 w:t（Pitfall #13），所以克隆上一条有内容的数据行
    # ======================================================================
    _, rev = find_tbl(body, '修订说明')
    rows = rev.findall(qn('tr'))
    tpl = rows[2]                                   # V2.0 那一行
    last = rows[-1]
    new_row = clone(tpl)
    set_row(new_row, [
        '2026.09.18', 'V3.0',
        '新增 HC-SR04 超声波测距驱动与片外 FLASH 距离记录区（扇区 1）；'
        'KEY1 改为「测距并存储」、KEY2 改为「顺序读回并触发四档声光联动」，'
        '原 KEY1/KEY2 功能分别挪到快捷命令 I 与 W；呼吸灯改为只驱动左灯珠红色通道',
        '陈相林',
    ])
    rev.replace(last, new_row)
    log.append('E2  修订记录 V3.0')

    # ======================================================================
    # E3 目录：在「3.10 转向灯模块及接口说明」后补 3.11 / 3.12 两组
    # ======================================================================
    toc_idx, toc_310 = find_para(body, '3.10 转向灯模块及接口说明')
    toc_39, toc_391 = find_para(body, '3.9 软件 PWM（呼吸灯）模块及接口说明')
    ind_l2 = toc_310.find(qn('pPr') + '/' + qn('ind')).get(qn('left'))
    ind_l3 = toc_391.find(qn('pPr') + '/' + qn('ind')).get(qn('left'))

    toc_new = [
        ('3.11 超声波测距模块及接口说明', ind_l2),
        ('3.11.1 硬件连接', ind_l3),
        ('3.11.2 HC-SR04 驱动接口', ind_l3),
        ('3.11.3 测距时序与失败码', ind_l3),
        ('3.12 距离记录与声光联动模块及接口说明', ind_l2),
        ('3.12.1 片外距离记录区布局', ind_l3),
        ('3.12.2 四档声光联动规则', ind_l3),
        ('3.12.3 距离记录接口', ind_l3),
        ('3.12.4 报警服务接口', ind_l3),
    ]
    anchor = toc_310
    for text, ind in toc_new:
        np = make_para(toc_310, text)
        ind_el = np.find(qn('pPr') + '/' + qn('ind'))
        ind_el.set(qn('left'), ind)
        anchor.addnext(np)
        anchor = np
    log.append('E3  目录 +9 项')

    # ======================================================================
    # E4 1.1 前言 / 1.2 范围 / 1.3 背景
    # ======================================================================
    _, p = find_para(body, '本文档用于说明片内片外 FLASH 读写工程的模块划分')
    set_ptext(p, (
        '本文档用于说明超声波测距与外部 FLASH 存储工程的模块划分、对外接口与使用方法，'
        '作为开发、调试与验收的统一依据。本工程在片内片外 FLASH 读写工程的基础上扩展而来：'
        '新增 HC-SR04 超声波测距驱动，并把 KEY1 与 KEY2 重新分配给「测距并存入片外 FLASH」'
        '与「顺序读回并触发四档声光联动」两条需求，原有的片内 FLASH 读取、片外文本记录读取'
        '与呼吸灯开关分别挪到串口快捷命令 I、KEY3 与 W，保证前几章的验收项一个不少。'
    ))
    _, p = find_para(body, '本文档适用于基于 STM32F103ZET6 与 STM32F10x 标准外设库 V3.6')
    set_ptext(p, (
        '本文档适用于基于 STM32F103ZET6 与 STM32F10x 标准外设库 V3.6 的超声波测距与外部 FLASH '
        '存储工程，覆盖串口协议控制板载外设、串口不定长数据帧接收、HC-SR04 超声波测距、'
        '片内 Flash 数据页擦写、片外 W25Q64 的 SPI2 驱动、文本记录与距离记录两套存储区、'
        '按键交互、OLED 四行显示、四档声光联动、软件 PWM 呼吸灯以及温度采集上报等内容。'
    ))
    _, p = find_para(body, '本工程为嵌入式培训课程 FLASH 章节的实践任务')
    set_ptext(p, (
        '本工程为嵌入式培训课程的综合实践任务，在片内片外 FLASH 读写工程的基础上扩展而来。'
        '片内 Flash 与片外 SPI Flash 都是掉电不丢失的存储器，但操作方式差别很大：片内 Flash '
        '按半字编程、必须先擦整页；片外 W25Q64 走 SPI2、以 4KB 扇区为最小擦除单位，容量却有 8MB，'
        '因此更适合做成「一条一条往后追加」的记录区。本工程把超声波测得的距离按 2 字节一条'
        '追加写进片外的独立扇区，再顺序读回来驱动声光提示，完整走通了「采集—存储—回读—执行」'
        '这条链路，也把片内与片外两种 Flash 的用法都覆盖到了。'
    ))
    log.append('E4  1.1 / 1.2 / 1.3')

    # ======================================================================
    # E5 1.4 缩略语表：补 HC-SR04 / TRIG / ECHO
    # ======================================================================
    _, g = find_tbl_by_row(body, '缩略语')
    append_rows(g, [
        ['HC-SR04', '—', '板载超声波测距模块（J1 座，丝印 Ultrasonic），测距范围约 2cm~4m'],
        ['TRIG', 'Trigger', '超声波模块的触发输入脚，接 MCU 的 PF11，发一个 10us 以上的高电平即启动一次测距'],
        ['ECHO', 'Echo', '超声波模块的回波输出脚，接 MCU 的 PF12，高电平宽度与声波往返时间相等'],
    ])
    log.append('E5  缩略语 +3 行')

    # ======================================================================
    # E6 2.1 系统组成表
    # ======================================================================
    _, sys_tbl = find_tbl_by_row(body, '组成')
    rows = sys_tbl.findall(qn('tr'))
    set_row(rows[3], [
        '下位机', 'YB-DSF01-V1.0 开发板（STM32F103ZET6）',
        '解析协议帧，控制外设、刷新 OLED、超声波测距、读写片内 Flash 与片外 W25Q64',
    ])
    set_row(rows[4], [
        '执行与显示', '板载外设',
        'LED1、LED2、左右两颗 RGB 转向灯珠、有源蜂鸣器、0.86 寸 OLED',
    ])
    set_row(rows[7], [
        '按键输入', '板载 KEY1 / KEY2 / KEY3',
        'KEY1 超声波测距并存入片外 Flash，KEY2 顺序读回一条距离记录并触发声光联动，'
        'KEY3 读取片外 Flash 的文本记录',
    ])
    set_row(rows[9], [
        '转向灯', '左、右两颗 RGB 灯珠',
        '左转向灯纯红呼吸、右转向灯彩虹闪烁；距离报警时左右同时纯红闪烁',
    ])
    # 在「温度采集」行前插一行「超声波测距」
    dist_row = clone(rows[6])
    set_row(dist_row, [
        '超声波测距', 'HC-SR04 超声波模块（板上 J1 座）',
        'TRIG 接 PF11、ECHO 接 PF12，用 TIM4 以 1us 分辨率量回波高电平宽度，连测 3 次取中值',
    ])
    rows[6].addprevious(dist_row)
    log.append('E6  2.1 系统组成表')

    # ======================================================================
    # E7 2.2 分层设计表：驱动个数 12 -> 13
    # ======================================================================
    _, layer = find_tbl_by_row(body, '层次')
    rows = layer.findall(qn('tr'))
    for r in rows:
        if '把外设细节封装成函数接口' in ptext(r):
            set_row(r, [
                '驱动层', 'Drv_Common',
                '把外设细节封装成函数接口，向上屏蔽寄存器操作；本工程共 13 个驱动与 2 份字库：'
                'LED/RGB、蜂鸣器、OLED、串口、内部 Flash、片外 W25Q64、SysTick、ADC、按键、'
                '软件 PWM、RGB 转向灯珠、超声波测距、中文消息，以及 8x8 与 16x16 两份字库数据',
            ])
            break
    log.append('E7  2.2 分层设计')

    # ======================================================================
    # E8 2.3 模块设计表：改引脚 + 新增超声波测距模块行
    # ======================================================================
    _, mod_tbl = find_tbl_by_row(body, '模块')
    rows = mod_tbl.findall(qn('tr'))
    idx_led = idx_pwm = None
    for i, r in enumerate(rows):
        t = ptext(r)
        if 'LED 与 RGB 模块' in t:
            idx_led = i
        if '呼吸灯模块' in t:
            idx_pwm = i
    if idx_led is None or idx_pwm is None:
        sys.exit('2.3 表结构变了，找不到 LED / 呼吸灯 行')

    set_row(rows[idx_led], [
        'LED 与 RGB 模块', 'led_drv.c / .h',
        'LED1、LED2 与左右两颗 RGB 转向灯珠的开关、翻转与颜色设置',
        'PG14、PG15、PG1、PE7、PG2、PE2、PE3、PE4',
    ])
    set_row(rows[idx_pwm], [
        '呼吸灯模块', 'pwm_drv.c / .h',
        'TIM2 定时中断产生软件 PWM，在左转向灯珠的红色通道上输出呼吸效果',
        'PG1（左灯珠红色通道）',
    ])
    new_mod = clone(rows[idx_pwm])
    set_row(new_mod, [
        '超声波测距模块', 'hcsr04_drv.c / .h',
        'HC-SR04 触发脉冲输出、回波高电平宽度计时、连测三次取中值、失败码诊断',
        'PF11（TRIG）、PF12（ECHO）',
    ])
    rows[idx_pwm].addnext(new_mod)
    log.append('E8  2.3 模块设计表')

    # ======================================================================
    # E9 3.1 初始化代码：补 Hcsr04_Init()
    # ======================================================================
    _, p_breath = find_para(body, 'Breath_Init();')
    p_hcsr = make_para(p_breath, 'Hcsr04_Init();                  // 超声波 HC-SR04：TRIG=PF11 ECHO=PF12，计时用 TIM4')
    p_breath.addnext(p_hcsr)
    log.append('E9  3.1 初始化补 Hcsr04_Init')

    # ======================================================================
    # E10 主循环：补 AlertService()
    # ======================================================================
    _, p_bs = find_para(body, 'Breath_Service();')
    p_al = make_para(p_bs, 'AlertService(); // 距离报警：250ms 半周期推进闪烁 / 等蜂鸣结束')
    p_bs.addnext(p_al)
    log.append('E10 主循环补 AlertService')

    # ======================================================================
    # E11 3.1.2 控制单元表：左右转向灯 / LED 灯条的引脚
    # ======================================================================
    _, ctrl = find_tbl_by_row(body, '控制单元')
    rows = ctrl.findall(qn('tr'))
    set_row(rows[1], ['0x00', '左转向灯（板载左灯珠红色通道）', 'PG1'])
    set_row(rows[2], ['0x01', '右转向灯（板载右灯珠红色通道）', 'PE2'])
    set_row(rows[4], ['0x03', 'LED 灯（左灯珠三色）', 'PG1、PE7、PG2'])
    log.append('E11 3.1.2 控制单元表引脚')

    # ======================================================================
    # E12 3.1.2 ASCII 快捷命令说明
    # ======================================================================
    _, p = find_para(body, '为方便调试，固件额外支持 ASCII 快捷命令')
    set_ptext(p, (
        '为方便调试，固件额外支持 ASCII 快捷命令（仅在空闲态识别，不影响协议帧）：'
        '字母 L/R/B/D 后跟数字 1/0 直接开/关 左转向灯/右转向灯/蜂鸣器/LED 灯条，'
        '省略数字则翻转一次（如 B1 开蜂鸣器、B0 关、单独 B 翻转）；'
        'T 加文本立即屏显并保存，回车或换行结束；S/C/P 分别把状态保存到 Flash / '
        '清除 Flash 记录 / 重新读回；A 立即采集一次温度并上报；K 加参考温度按室温标定，'
        'Z 清除标定；M 立即测一次距离（不存储，等价于按下 KEY1 但不写 Flash），'
        'N 等价于按下 KEY2：顺序读下一条距离记录并触发四档声光联动，'
        'X 清空片外 Flash 的距离记录区，W 开关左转向灯呼吸灯，'
        'I 读取片内 Flash 的数据页（原 KEY1 的功能，为测距让位后挪到这里）。'
    ))
    log.append('E12 3.1.2 ASCII 命令')

    # ======================================================================
    # E13 3.1.3 状态上报：补距离相关回显
    # ======================================================================
    _, p_err = find_para(body, 'ERROR: data length must be 1~20')
    extra = [
        'KEY1 : distance 85 mm, saved as record #1 in ext flash sector 1',
        'KEY2 : record #1 = 85 mm (9 cm) -> BEEP 1s (<10cm)',
        'KEY2 : record #2 = 197 mm (20 cm) -> LEFT TURN x2 (10-50cm)',
        'KEY2 : record #3 = 514 mm (51 cm) -> RIGHT TURN x2 (50cm-1m)',
        'KEY2 : record #4 = 3661 mm (366 cm) -> HAZARD x5 (>1m)',
        'KEY2 : no distance record yet, press KEY1 first',
        'KEY1 : ultrasonic no echo, err=1 raw=0 us  (1=no rising 2=stuck high 3=out of range 4=too close)',
    ]
    anchor = p_err
    for line in extra:
        np = make_para(p_err, line)
        anchor.addnext(np)
        anchor = np
    log.append('E13 3.1.3 状态上报 +7 行')

    # ======================================================================
    # E14 3.2.1 引脚描述
    # ======================================================================
    _, p = find_para(body, 'LED1（PG14）与 LED2（PG15）是板载小指示灯')
    set_ptext(p, (
        'LED1（PG14）与 LED2（PG15）是板载小指示灯，各自串了一颗 10K 电阻，'
        '电流只有约 0.13mA，肉眼几乎看不见，只能当「电平指示」用，不能当转向灯。'
        '板上左右各有一颗四脚 RGB 灯珠构成真正的车灯，每路各串 150R 限流电阻（约 8.7mA，很亮）：'
        '左灯珠的红色通道在 PG1、绿色通道在 PE7、蓝色通道在 PG2（RGB_Init / RGB_Set），'
        '右灯珠的红色通道在 PE2、绿色通道在 PE3、蓝色通道在 PE4（RGB2_Init / RGB2_Set），'
        '所有通道都是高电平点亮。注意左灯珠的绿色通道单独挂在 GPIOE 上，'
        '与另外两路不同端口，所以呼吸灯只驱动红色通道 PG1。'
    ))
    log.append('E14 3.2.1 引脚描述')

    # ======================================================================
    # E15 3.2.1 函数表里 RGB_Set / RGB2_Set 的描述与参数
    # ======================================================================
    _, iface = find_tbl(body, 'void RGB_Init(void)')
    rows = iface.findall(qn('tr'))
    for i, r in enumerate(rows):
        tcs = r.findall(qn('tc'))
        label = ptext(tcs[0]).strip()
        content = ptext(tcs[1]).strip()
        if label == '描述' and content.startswith('把 RGB 灯条的三个引脚'):
            set_cell(tcs[1], '把左灯珠的三个引脚配置为推挽输出，上电后全灭')
        elif label == '描述' and content.startswith('设置 RGB 灯条的显示颜色'):
            set_cell(tcs[1], '设置左灯珠的显示颜色，一次调用同时决定三路的亮灭')
        elif label == '参数' and content.startswith('color：RGB_NONE'):
            set_cell(tcs[1], (
                'color：RGB_NONE（全灭）、RGB_R（PG1 红）、RGB_G（PE7 绿）、RGB_B（PG2 蓝）、'
                'RGB_YELLOW（红加绿）、RGB_CYAN（绿加蓝）、RGB_MAGENTA（红加蓝，呈紫色）、'
                'RGB_ALL（三色全亮，呈偏粉的白）'
            ))
        elif label == '描述' and content.startswith('设置右转向灯珠的颜色'):
            set_cell(tcs[1], (
                '设置右转向灯珠的颜色；颜色枚举与 RGB_Set 完全相同。'
                '手动打开右转向灯时由转向灯服务在每次闪烁时轮换一种颜色（彩虹效果），'
                '距离报警时固定用 RGB_R 纯红'
            ))
    log.append('E15 3.2.1 函数表')

    # ======================================================================
    # E16 3.2.3 屏上第 3 行的双模式说明
    # ======================================================================
    _, p = find_para(body, '屏不再分页，按任务书要求固定为四行')
    set_ptext(p, (
        '屏不再分页，固定为四行：第 1 行显示片内 Flash 读出的数据，第 2 行显示温度，'
        '第 3 行按最近一次操作在「片外 Flash 文本数据」与「超声波距离」之间切换'
        '（按 KEY1 / KEY2 或敲 M / N 后切到距离，按 KEY3 或 P 后切回文本），'
        '第 4 行显示状态提示。ADC 原始值与换算电压已按任务书要求取消显示：'
    ))
    _, scr = find_tbl_by_row(body, '行号')
    rows = scr.findall(qn('tr'))
    set_row(rows[3], [
        '第 3 行',
        'DIST 123CM #3 或 EX:0102030405',
        '测距模式下显示距离（mm 四舍五入到 cm）并标出这是第几条记录；'
        '文本模式下显示片外 W25Q64 读出的数据。芯片不在线或无记录时显示 DIST -- / EX:--',
    ])
    log.append('E16 3.2.3 屏上第 3 行')

    # ======================================================================
    # E17 3.8 按键功能表
    # ======================================================================
    _, key_tbl = find_tbl_by_row(body, '按键')
    rows = key_tbl.findall(qn('tr'))
    if len(rows) == 4:
        set_row(rows[1], ['KEY1', 'PG3', '超声波测距一次，把结果追加存进片外 Flash 的距离记录区（需求4-1）'])
        set_row(rows[2], ['KEY2', 'PG4', '从片外 Flash 顺序读一条距离记录，屏显并触发四档声光联动（需求4-2）'])
        set_row(rows[3], ['KEY3', 'PG5', '读片外 Flash 的文本记录（需求3 保留）'])
    else:
        sys.exit('3.8 按键表行数不是 4，实际 %d' % len(rows))
    log.append('E17 3.8 按键功能表')

    # ======================================================================
    # E18 3.8.1 结尾段（呼吸模式与 KEY2 的旧描述）
    # ======================================================================
    _, p = find_para(body, '一次按下只上报一次事件')
    set_ptext(p, (
        '一次按下只上报一次事件，不放着不管也不会重复触发。按下 KEY2 读回一条记录后，'
        '报警提示期间灯由报警服务独占，提示结束后自动交回按键/串口设定的状态；'
        '距离记录区读完后会自动回到第 1 条重新开始，演示时可以反复按，不用先清空。'
        '呼吸灯现在由串口快捷命令 W 开关（原来挂在 KEY2 上，为需求4-2 让位）。'
    ))
    log.append('E18 3.8.1 结尾段')

    # ======================================================================
    # E19 3.9 呼吸灯：引脚改为只驱动 PG1
    # ======================================================================
    _, p = find_para(body, '本模块在左转向灯上产生呼吸效果')
    set_ptext(p, (
        '本模块在左转向灯上产生呼吸效果。左转向灯就是板上左上角那颗四脚 RGB 灯珠（原理图 L1），'
        '三个颜色通道分别接在 PG1（红）、PE7（绿）、PG2（蓝）上，各经 150R 限流电阻。'
        '按任务书需求2「让左转向灯（红色）呈现呼吸灯的效果」，呼吸只驱动红色通道 PG1：'
        '若把 PG1 与 PG2 一起驱动，红加蓝在屏上呈紫色，与「红色呼吸」的要求不符。'
        '绿色通道挂在 GPIOE，与红色通道不同端口，不参与呼吸。'
    ))
    log.append('E19 3.9 呼吸灯引脚')

    # ======================================================================
    # E20 3.10 转向灯：更新描述
    # ======================================================================
    _, p = find_para(body, '板上左右各有一颗四脚 RGB 灯珠构成车灯')
    set_ptext(p, (
        '板上左右各有一颗四脚 RGB 灯珠构成车灯，两盏灯的颜色由各自的驱动接口设置。'
        '左灯珠接在 PG1（红）、PE7（绿）、PG2（蓝）上，由 3.9 节的软件 PWM 模块驱动红色通道做呼吸；'
        '右灯珠接在 PE2（红）、PE3（绿）、PE4（蓝）上，手动打开时由本模块在每次闪烁时轮换一种颜色。'
        '两颗灯珠各经 150R 限流（约 8.7mA），亮度足够；板载 LED1 / LED2 串的是 10K，'
        '只有约 0.13mA，肉眼几乎看不见，只作电平指示。'
    ))
    _, p = find_para(body, '转向灯的闪烁由主循环里的 TurnSignalService 统一调度')
    set_ptext(p, (
        '转向灯的闪烁由主循环里的 TurnSignalService 统一调度，左右灯共用同一个 500ms 半周期，'
        '因此同时打开时两盏灯同步闪烁。距离报警的闪烁由 AlertService 单独调度，'
        '半周期 250ms（比转向灯快一倍），且固定使用纯红，不受右灯的彩虹效果影响；'
        '报警期间转向灯服务与呼吸灯都会让位，提示结束后按原状态恢复。'
    ))
    log.append('E20 3.10 转向灯')

    # ======================================================================
    # E22 3.10 转向灯参数表：左转向灯那行还写着 PG0 / PG1 / PG2（漏网）
    #     按「彩虹色序」定位，避免误命中 3.9 呼吸灯的参数表
    # ======================================================================
    _, tl = find_tbl(body, '彩虹色序')
    for r in tl.findall(qn('tr')):
        tcs = r.findall(qn('tc'))
        label = ptext(tcs[0]).strip()
        if label == '左转向灯':
            set_cell(tcs[1], 'PG1（左灯珠红色通道）')
            set_cell(tcs[2], '打开时纯红呼吸；呼吸期间由软件 PWM 模块独占红色通道 PG1')
        elif label == '同步小灯':
            set_cell(tcs[2], (
                '与对应灯珠一起亮灭；注意这两颗各串一颗 10K 电阻，只有约 0.13mA，'
                '肉眼几乎看不见，仅作电平指示'
            ))
    log.append('E22 3.10 参数表引脚')

    # ======================================================================
    # E23 3.9 呼吸灯参数表：「驱动对象」行还写着 PG0/PG1/PG2 三路
    # ======================================================================
    _, bt = find_tbl(body, '驱动对象')
    for r in bt.findall(qn('tr')):
        tcs = r.findall(qn('tc'))
        if ptext(tcs[0]).strip() == '驱动对象':
            set_cell(tcs[1], 'PG1（左灯珠红色通道）')
            set_cell(tcs[2], (
                '中断里用 BSRR 直接置位/复位红色通道，按占空比输出。'
                '只走红色：PG1 与 PG2 一起驱动会变成红加蓝 = 紫色，'
                '与任务书「左转向灯（红色）呼吸」不符'
            ))
    log.append('E23 3.9 参数表驱动对象')

    # ======================================================================
    # E21 新增 3.11 超声波测距 + 3.12 距离记录与声光联动
    # ======================================================================
    h2_src = None
    h3_src = None
    body_src = None
    for e in body:
        if not is_p(e):
            continue
        t = ptext(e).strip()
        if t == '3.10 转向灯模块及接口说明':
            h2_src = e
        elif t == '3.9.1 呼吸灯接口':
            h3_src = e
    # 正文段模板：拿「3.10」下第一段无样式正文
    _, body_src = find_para(body, '板上左右各有一颗四脚 RGB 灯珠构成车灯')
    if h2_src is None or h3_src is None:
        sys.exit('找不到 3.10 / 3.9.1 标题做模板')

    # 表格模板
    _, iface_tpl = find_tbl(body, 'void RGB2_Init(void)')      # 2 列：函数原型/描述/参数/返回值
    _, grid3_tpl = find_tbl_by_row(body, '项目')                # 3 列：项目/取值/说明
    _, grid4_tpl = find_tbl_by_row(body, '信号')                # 4 列：信号/引脚/引脚/说明
    _, grid3b_tpl = find_tbl_by_row(body, '偏移')               # 3 列（数据记录格式表）
    _, grid4b_tpl = find_tbl_by_row(body, '情况')               # 3 列（数据页保护表）

    def H2(t):
        return make_para(h2_src, t)

    def H3(t):
        return make_para(h3_src, t)

    def P(t):
        return make_para(body_src, t)

    new_elems = []

    # ---------- 3.11 ----------
    new_elems.append(H2('3.11 超声波测距模块及接口说明'))
    new_elems.append(P(
        '本模块负责驱动板载 HC-SR04 超声波模块完成一次测距。模块装在板上 J1 座（丝印 Ultrasonic），'
        '由 MCU 发出一个 10us 以上的高电平触发脉冲，模块内部自动发出 8 个 40kHz 方波并等待回波，'
        '回波到达后 ECHO 引脚输出一段与声波往返时间等长的高电平；MCU 只要量出这段高电平的宽度，'
        '按声速换算即得距离。'
    ))
    new_elems.append(P(
        '距离换算用整数运算完成，避免引入浮点：距离(mm) = 高电平宽度(us) × 34 / 200。'
        '例如测得 500us，距离 = 500 × 34 / 200 = 85mm。'
    ))
    new_elems.append(H3('3.11.1 硬件连接'))
    new_elems.append(make_grid_table(grid4_tpl, ['信号', '模块 / MCU', '引脚', '说明'], [
        ['VCC', 'J1.1', '5V', '模块供电，超声波模块需要 5V'],
        ['TRIG', 'J1.2 → MCU', 'PF11', '推挽输出，发触发脉冲；该脚为 FT 脚，容忍 5V'],
        ['ECHO', 'J1.3 → MCU', 'PF12', '浮空输入，读回波高电平宽度；该脚为 FT 脚，容忍 5V'],
        ['GND', 'J1.4', 'GND', '与开发板共地'],
        ['计时', '—', 'TIM4', '1MHz 计数、1us 分辨率，与呼吸灯用的 TIM2 互不干扰'],
    ]))
    new_elems.append(H3('3.11.2 HC-SR04 驱动接口'))
    new_elems.append(P('模块对上层提供以下接口，应用层不接触任何 GPIO 或定时器寄存器：'))
    new_elems.append(make_iface_table(iface_tpl, [
        ('void Hcsr04_Init(void)',
         '把 TRIG 配置为推挽输出、ECHO 配置为浮空输入，并初始化 TIM4 为 1MHz 自由计数；上电后 TRIG 保持低电平',
         'void', 'void'),
        ('uint16_t Hcsr04_GetDistanceMm(void)',
         '发一次触发脉冲并等待回波，量出高电平宽度后换算成毫米；整个过程带超时保护，不会卡住主循环',
         'void',
         '距离，单位毫米；返回 0xFFFF 表示本次测量失败（超时、无回波或超出量程）'),
        ('uint16_t Hcsr04_GetDistanceMid3(void)',
         '连续测量 3 次取中值，挤掉单次测量容易被余波或串扰带偏的毛刺；只要有一次成功就返回有效值',
         'void', '3 次测量的中值距离（mm）；三次全部失败时返回 0xFFFF'),
        ('uint8_t Hcsr04_GetLastErr(void)',
         '返回上一次测量的失败原因码，插错线时能一眼看出卡在哪一步',
         'void',
         '0 = 成功；1 = ECHO 始终没拉高（模块没响应）；2 = ECHO 一直是高（短路或模块卡死）；'
         '3 = 脉宽超出 2cm~4m 量程；4 = 脉宽小于 116us（太近或自激）'),
        ('uint16_t Hcsr04_GetLastRawUs(void)',
         '返回上一次测到的 ECHO 高电平宽度，用于人工核对换算是否正确',
         'void', '高电平宽度（us）；0 = 没测到；0xFFFF = 一直为高'),
        ('uint8_t Hcsr04_EchoLevel(void)',
         '读 ECHO 引脚当前电平，接线排查时用来确认模块到底有没有在动',
         'void', '1 = 高电平；0 = 低电平'),
    ]))
    new_elems.append(H3('3.11.3 测距时序与失败码'))
    new_elems.append(P('一次测距分三步，每一步都有超时保护，任何一步失败都会带着失败码立刻返回：'))
    new_elems.append(make_grid_table(grid3_tpl, ['步骤', '动作', '超时与判据'], [
        ['1', 'TRIG 先拉低 2us 以上，再拉高至少 10us，然后拉低', '触发一次测量'],
        ['2', '等待 ECHO 由低变高', '超过约 30ms 仍未变高 → 失败码 1'],
        ['3', 'ECHO 变高后启动 TIM4 计时，等 ECHO 变低', '超过约 35ms 仍未变低 → 失败码 2'],
        ['4', '按 2cm~4m 量程做范围检查', '超出量程 → 失败码 3；宽度小于 116us → 失败码 4'],
    ]))
    new_elems.append(P(
        'KEY1 测距失败时，失败码与原始宽度会一起从串口打印出来，例如：'
    ))
    new_elems.append(P(
        'KEY1 : ultrasonic no echo, err=1 raw=0 us  (1=no rising 2=stuck high 3=out of range 4=too close)'
    ))

    # ---------- 3.12 ----------
    new_elems.append(H2('3.12 距离记录与声光联动模块及接口说明'))
    new_elems.append(P(
        '本模块是需求4 的核心，把「测距结果」变成「可掉电保存的记录」，再按记录值触发四档声光提示。'
        '它由三部分组成：片外 Flash 上一块独立的距离记录区、一组距离记录读写接口，'
        '以及一个把距离映射成灯语与蜂鸣的报警服务。'
    ))
    new_elems.append(H3('3.12.1 片外距离记录区布局'))
    new_elems.append(P(
        '距离记录单独占用 W25Q64 的扇区 1（地址 0x001000），与需求3 的 24 字节文本记录区'
        '（扇区 0，0x000000）彻底分开，两者互不覆盖。区头只在初始化时写一次，'
        '之后每条记录都追加到新地址上，永远不重复写同一个位置，因此不需要反复擦除扇区。'
    ))
    new_elems.append(make_grid_table(grid3b_tpl, ['偏移 / 范围', '长度', '内容', '说明'], [
        ['0x001000', '1 字节', '0x44（字符 D）', '区头魔数 0'],
        ['0x001001', '1 字节', '0x52（字符 R）', '区头魔数 1'],
        ['0x001002', '1 字节', '0x01', '区头版本号'],
        ['0x001003', '1 字节', '0xFF', '预留字节，保持擦除后的默认值'],
        ['0x001004 起', '2 字节 / 条', '小端 mm', '距离记录，0xFFFF 表示该位置为空'],
        ['容量', '—', '2046 条', '4KB 扇区扣掉 4 字节区头，每条 2 字节'],
    ]))
    new_elems.append(P(
        '模块量程 4m = 4000mm，永远取不到 65535，所以拿 0xFFFF 当「空记录」是安全的。'
        '扇区写满后追加接口返回失败，屏上提示 DIST FAIL，串口打印 external flash write failed (sector full?)。'
    ))
    new_elems.append(H3('3.12.2 四档声光联动规则'))
    new_elems.append(P(
        '记录读出后按任务书给定的四个区间决定动作，区间用三个阈值切分：DIST_NEAR_MM = 100、'
        'DIST_LEFT_MM = 500、DIST_RIGHT_MM = 1000。判断是自上而下逐个比较，'
        '所以只需要写「小于」，不必写区间两端。'
    ))
    new_elems.append(make_grid_table(grid3b_tpl, ['距离区间', '报警类型', '声光动作', '屏上提示 / 串口文字'], [
        ['小于 10cm（mm < 100）', 'ALERT_BEEP', '蜂鸣器响 1 秒',
         'DIST BEEP ／ BEEP 1s (<10cm)'],
        ['10cm ~ 50cm（mm < 500）', 'ALERT_LEFT2', '左转向灯闪 2 次',
         'DIST L x2 ／ LEFT TURN x2 (10-50cm)'],
        ['50cm ~ 1m（mm < 1000）', 'ALERT_RIGHT2', '右转向灯闪 2 次',
         'DIST R x2 ／ RIGHT TURN x2 (50cm-1m)'],
        ['1m 以上（mm ≥ 1000）', 'ALERT_BOTH5', '左右转向灯同时闪 5 次',
         'DIST D x5 ／ HAZARD x5 (>1m)'],
    ]))
    new_elems.append(P(
        '提示闪烁的半周期是 250ms，比手动转向灯的 500ms 快一倍，现场一眼能区分「报警闪」与「转向闪」。'
        '「闪 N 次」按一次「亮 + 灭」算一次，所以闪 2 次占 1 秒、闪 5 次占 2.5 秒。'
    ))
    new_elems.append(P(
        '点亮的是灯珠而不是板载小灯：左转向灯点亮左灯珠的红色通道（PG1，经 150R，约 8.7mA），'
        '右转向灯点亮右灯珠的红色通道（PE2）。板载 LED1（PG14）与 LED2（PG15）各串一颗 10K 电阻，'
        '电流只有约 0.13mA，肉眼几乎看不见 —— 如果只驱动板载小灯，左右双闪看起来会像「只有右边在闪」。'
    ))
    new_elems.append(H3('3.12.3 距离记录接口'))
    new_elems.append(make_iface_table(iface_tpl, [
        ('uint8_t Dist_AreaFormat(void)',
         '擦除扇区 1 并写入 4 字节区头，把距离记录区整体归零',
         'void', '1 = 成功；0 = 片外芯片不在线或擦写失败'),
        ('uint8_t Dist_AreaScan(void)',
         '开机时扫描整个记录区，数出已存记录条数并把读取游标归零；遇到第一条空记录即停止',
         'void', '1 = 扫描完成；0 = 片外芯片不在线'),
        ('uint8_t Dist_Append(uint16_t mm)',
         '把一条距离追加写到记录区末尾，并让已存条数加一',
         'mm：距离，单位毫米',
         '1 = 写入成功；0 = 芯片不在线、区头无效或扇区已满'),
        ('uint8_t Dist_Read(uint16_t idx, uint16_t *mm)',
         '按序号读取一条距离记录，序号从 0 开始',
         'idx：记录序号（0 到已存条数减 1）；mm：输出参数，返回读到的距离',
         '1 = 读取成功；0 = 芯片不在线、序号越界或该位置为空'),
    ]))
    new_elems.append(H3('3.12.4 报警服务接口'))
    new_elems.append(make_iface_table(iface_tpl, [
        ('void Alert_Start(uint16_t mm)',
         '按距离值启动对应的提示动作：先按三个阈值比较决定报警类型，再设定闪烁次数或蜂鸣时长。'
         '启动前若呼吸灯正在运行会先停掉，并记住它，结束后自动恢复',
         'mm：距离，单位毫米', 'void'),
        ('void Alert_Stop(void)',
         '结束提示：熄灭左右灯珠与板载小灯、关闭蜂鸣器，把报警类型归零，'
         '并把灯与蜂鸣器交回按键 / 串口设定的状态',
         'void', 'void'),
        ('void AlertService(void)',
         '主循环每轮调用，按 250ms 半周期推进闪烁相位：亮相位按报警类型点亮对应灯珠，'
         '灭相位熄灭并累加闪次，达到设定次数后自动调用 Alert_Stop',
         'void', 'void'),
    ]))
    new_elems.append(P(
        '报警服务与手动控制的关系：提示期间灯由报警服务独占，转向灯闪烁服务与呼吸灯都会让位；'
        '提示结束后按用户原先设定的状态恢复 —— 例如提示前左转向灯正在呼吸，提示结束后会接着呼吸。'
    ))

    # 插到文末 sectPr 之前（Pitfall #12：这里 sectPr 是 body 的直接子元素）
    sect = body.find(qn('sectPr'))
    if sect is None:
        sys.exit('body 末尾没有独立 sectPr，改用 body.append 策略')
    for el in new_elems:
        sect.addprevious(el)
    log.append('E21 新增 3.11 / 3.12 共 %d 个元素' % len(new_elems))

    # ======================================================================
    # 结构自检（Pitfall #11）：原有标题一个都不能少
    # ======================================================================
    after_titles = [ptext(e).strip() for e in body
                    if is_p(e) and style_of(e) in ('3', '4')]
    after_titles = [t for t in after_titles if t]
    missing = [t for t in before_titles if t not in after_titles]
    if missing:
        sys.exit('自检失败：以下原有标题丢失 %r' % missing)

    # 标题位置不能出现长正文（被打掉的信号）
    bad = [t for t in after_titles if len(t) > 40 and not t[0].isdigit()]
    if bad:
        sys.exit('自检失败：标题位置出现长文本 %r' % bad[:3])

    print('自检通过：改前标题 %d 个全部保留，改后共 %d 个' % (len(before_titles), len(after_titles)))

    # ---- 写回 ----
    items['word/document.xml'] = etree.tostring(
        root, xml_declaration=True, encoding='UTF-8', standalone=True)

    with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name, data in items.items():
            zout.writestr(name, data)

    # ---- 回读校验 ----
    z = zipfile.ZipFile(OUT)
    bad = z.testzip()
    xml2 = z.read('word/document.xml').decode('utf-8')
    print('回读：testzip =', bad)
    print('回读：段落 %d / 表格 %d / 体积 %d 字节'
          % (xml2.count('<w:p '), xml2.count('<w:tbl>'), os.path.getsize(OUT)))
    z.close()

    print('---- 改动清单 ----')
    for line in log:
        print('  ' + line)
    print('\n输出：%s' % OUT)


if __name__ == '__main__':
    main()
