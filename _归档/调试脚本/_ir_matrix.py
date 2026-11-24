# -*- coding: utf-8 -*-
"""
_ir_matrix.py —— 发射管 × 接收管 2x2 矩阵（判左发射管 L4 是否发光 + 是否交叉配对）

思路：
  直接写 GPIOE 控制两个发射管（开漏，低=亮），直接读 ADC3 两个接收通道。
  得到 2x2 表：

              PF9(左接收)      PF10(右接收)
  灭灯(本底)     A                C
  PE5(L4)亮      B                D
  PE6(L5)亮      E                F

  判读：
    * 若 F-C 很大  -> PE6 驱动的发射管确实在发光（右路自洽）
    * 若 B-A 很小  -> PE5 驱动的发射管【对它自己的接收管】没作用
    * 若 D-C 明显  -> PE5 的发射管居然照亮了右接收管 => PE5 其实是右路发射管（配对反了）
    * 若 B-A 与 D-C 都≈0，而 C/F 通道本身正常 => 左发射管 L4 实体损坏/未焊

  另外再顺手把 PE5/PE6 引脚本身的 IDR 读一下，确认开漏写 0 时确实被拉低（说明接在有效负载上）。

★ 铁律：STM32F1 的 ADC_SMPR1 是【通道10~17】，SMPR2 才是【通道0~9】。
"""

import io
import time

from pyocd.core.helpers import ConnectHelper

UID = '37FF71064E5734360B791543'
LOG = io.open(r'D:\STM32_Project\_ir_matrix.log', 'w', encoding='utf-8', newline='\n')


def log(m=''):
    print(m, flush=True)
    LOG.write(m + '\n')
    LOG.flush()


RCC_APB2ENR = 0x40021018
RCC_CFGR = 0x40021004
GPIOE_CRL = 0x40011800
GPIOE_IDR = 0x40011808
GPIOE_BSRR = 0x40011810
GPIOE_BRR = 0x40011814
GPIOF_CRL = 0x40011C00
GPIOF_CRH = 0x40011C04

ADC3 = 0x40013C00
A_SR, A_CR1, A_CR2, A_SMPR1, A_SMPR2, A_SQR3, A_DR = (
    0x00, 0x04, 0x08, 0x0C, 0x10, 0x34, 0x4C)
CH_L, CH_R = 7, 8      # PF9=ADC3_IN7, PF10=ADC3_IN8

sess = ConnectHelper.session_with_chosen_probe(
    unique_id=UID, target_override='stm32f103ze',
    options={'connect_mode': 'halt'})
sess.open()
t = sess.target
log('=== %s  %s ===' % (t.part_number, t.get_state()))


def set_pin(base, pin, val):
    a = base + (0x04 if pin >= 8 else 0x00)
    sh = (pin - 8 if pin >= 8 else pin) * 4
    cur = t.read32(a)
    t.write32(a, (cur & ~(0xF << sh)) | ((val & 0xF) << sh))


# ---------- 1. 时钟 / GPIO ----------
t.write32(RCC_APB2ENR, t.read32(RCC_APB2ENR) | (1 << 6) | (1 << 7) | (1 << 15))
t.write32(RCC_CFGR, (t.read32(RCC_CFGR) & ~(3 << 14)) | (2 << 14))     # ADCPRE=/6

for p in (9, 10):
    set_pin(GPIOF_CRL if p < 8 else GPIOF_CRH, p, 0x0)                  # 模拟输入
set_pin(GPIOE_CRL, 5, 0x7)                                              # PE5 开漏
set_pin(GPIOE_CRL, 6, 0x7)                                              # PE6 开漏
t.write32(GPIOE_BSRR, (1 << 5) | (1 << 6))                              # 先都灭
log('GPIOE_CRL=%08X  GPIOF_CRH=%08X' % (t.read32(GPIOE_CRL), t.read32(GPIOF_CRH)))

# ---------- 2. ADC3 ----------
# ★★ 血泪坑（2026-09-20 用标准库源码钉死）：
#   ① SWSTART 只在 EXTSEL=111 时有效 —— 标准库 ADC_ExternalTrigConv_None = 0x000E0000 就是这个意思。
#   ② 而且 EXTTRIG(bit20) 也必须置 1！
#      stm32f10x_adc.c:92  #define CR2_EXTTRIG_SWSTART_Set ((uint32_t)0x00500000)
#      即 ADC_SoftwareStartConvCmd() = CR2 |= (EXTTRIG | SWSTART) —— 两个位【缺一不可】。
#   少了 EXTTRIG，转换根本不启动，EOC 永不置位，DR 一直读回陈旧值（实测恒为 66，
#   而且因为它不随通道/灯态变化，极易被误判成"左右传感器一模一样"）。
EXTSEL_SWSTART = 0x000E0000       # EXTSEL = 111（SWSTART）
CR2_EXTTRIG_SWSTART = 0x00500000  # EXTTRIG | SWSTART
t.write32(ADC3 + A_CR1, 0)
t.write32(ADC3 + A_CR2, 1 | EXTSEL_SWSTART)                 # ADON + EXTSEL=111
time.sleep(0.02)
t.write32(ADC3 + A_CR2, 1 | EXTSEL_SWSTART | (1 << 3))      # RSTCAL
for _ in range(3000):
    if not (t.read32(ADC3 + A_CR2) & (1 << 3)):
        break
t.write32(ADC3 + A_CR2, 1 | EXTSEL_SWSTART | (1 << 2))      # CAL
for _ in range(3000):
    if not (t.read32(ADC3 + A_CR2) & (1 << 2)):
        break

# ★ ch7/ch8 的采样时间是 SMPR2 里的事（SMPR1 只管 ch10~17）
smpr2 = t.read32(ADC3 + A_SMPR2)
for ch in (CH_L, CH_R):
    smpr2 = (smpr2 & ~(0x7 << (ch * 3))) | (0x7 << (ch * 3))
t.write32(ADC3 + A_SMPR2, smpr2)
t.write32(ADC3 + A_SMPR1, 0)
log('ADC3 CR2=%08X SMPR1=%08X SMPR2=%08X' %
    (t.read32(ADC3 + A_CR2), t.read32(ADC3 + A_SMPR1), t.read32(ADC3 + A_SMPR2)))


def conv(ch):
    t.write32(ADC3 + A_SQR3, (t.read32(ADC3 + A_SQR3) & ~0x1F) | ch)
    time.sleep(0.002)
    t.write32(ADC3 + A_CR2, (t.read32(ADC3 + A_CR2) & ~CR2_EXTTRIG_SWSTART)
              | CR2_EXTTRIG_SWSTART)
    n = 0
    while n < 300:
        if t.read32(ADC3 + A_SR) & 0x02:
            break
        n += 1
    SPIN[0] += n
    return t.read32(ADC3 + A_DR) & 0x0FFF


def avg(ch, n=10):
    conv(ch)
    conv(ch)
    s = 0
    for _ in range(n):
        s += conv(ch)
    return s // n


SPIN = [0]


def led(pe5_on, pe6_on):
    """开漏：写 0 = 拉低 = 亮；写 1 = 高阻 = 灭"""
    if pe5_on:
        t.write32(GPIOE_BRR, 1 << 5)
    else:
        t.write32(GPIOE_BSRR, 1 << 5)
    if pe6_on:
        t.write32(GPIOE_BRR, 1 << 6)
    else:
        t.write32(GPIOE_BSRR, 1 << 6)


def sample(tag):
    time.sleep(0.012)
    l = avg(CH_L)
    r = avg(CH_R)
    idr = t.read32(GPIOE_IDR)
    log('  %-14s PF9(左收)=%4d   PF10(右收)=%4d   | PE5 IDR=%d  PE6 IDR=%d'
        % (tag, l, r, (idr >> 5) & 1, (idr >> 6) & 1))
    return l, r


# ---------- 3. 2x2 矩阵 ----------
log()
log('### 2x2 矩阵（开漏驱动，低=亮）###')
led(0, 0)
A, C = sample('灭灯(本底)')
led(1, 0)
B, D = sample('PE5(L4) 亮')
led(0, 1)
E, F = sample('PE6(L5) 亮')
led(0, 0)
G, H = sample('再灭灯')

log()
log('### 判读 ###')
log('  EOC 轮询累计空转 %d 次（0~2 才正常；大就是 SWSTART 没生效）' % SPIN[0])
log('  左接收 PF9 :  本底=%4d  PE5亮=%4d (%+d)  PE6亮=%4d (%+d)'
    % (A, B, B - A, E, E - A))
log('  右接收 PF10:  本底=%4d  PE5亮=%4d (%+d)  PE6亮=%4d (%+d)'
    % (C, D, D - C, F, F - C))
log('  灭灯复现:  PF9=%4d(%+d)  PF10=%4d(%+d)' % (G, G - A, H, H - C))
log()

d_pe5_pf9 = A - B       # PE5(L4) 照亮左接收的量
d_pe6_pf10 = C - F      # PE6(L5) 照亮右接收的量
d_pe5_pf10 = C - D      # PE5(L4) 串到右接收的量
d_pe6_pf9 = A - E       # PE6(L5) 串到左接收的量

log('  自照射量：  PE5->PF9 = %4d      PE6->PF10 = %4d' % (d_pe5_pf9, d_pe6_pf10))
log('  串扰量  ：  PE5->PF10= %4d      PE6->PF9  = %4d' % (d_pe5_pf10, d_pe6_pf9))
log()

if d_pe6_pf10 > 200:
    log('  [OK]   PE6(右发射) -> PF10(右接收) 反射明显，右路收发自洽')
else:
    log('  [!!]   PE6->PF10 也没反应 —— 前方反射物可能已挪走，本次矩阵无效')

if d_pe5_pf9 > 200:
    log('  [OK]   PE5(左发射) -> PF9(左接收) 有反应，左路正常')
elif d_pe5_pf10 > 200:
    log('  [★]    PE5 的发射管照亮了【右】接收管 => 配对反了！PE5 应配 PF10')
elif d_pe5_pf9 < 30 and d_pe5_pf10 < 30:
    log('  [★]    PE5 对两个接收管都无贡献 => 左发射管 L4 未发光（或该对管前无反射物）')
    log('         注意区分：若此刻右路强、左路弱，很可能是【左对管正前方没有反射物】')
else:
    log('  [?]    数据不典型，见上表人工判读')

log()
log('  提示：本测试只写 GPIO/ADC 寄存器，App 仍在跑，结束后已复位。')

t.write32(GPIOE_BSRR, (1 << 5) | (1 << 6))
t.reset_and_halt()
time.sleep(0.1)
t.resume()
sess.close()
log('  已复位，探针释放')
