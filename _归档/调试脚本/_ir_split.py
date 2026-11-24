# -*- coding: utf-8 -*-
"""
_ir_split.py —— 分开驱动两个发射管，做近距离 2x2 判决

上一轮 _ir_guide.py 是"两个发射管同时点亮"，所以左接收管 PF9 收到的 40 点数
分不清是【左发射管 L4 的光】还是【右发射管 L5 的强反射串光】。本脚本把两个
发射管【单独】点亮，逐格填出 2x2 表：

                    PF9(左接收)          PF10(右接收)
   只亮 PE5(L4)     A                    C
   只亮 PE6(L5)     B                    D

判读（用户手指同时挡住两对管的前提下）：
  * D 很大（几百~几千）      -> 右路自洽（已知）
  * A 明显（>200）           -> 左发射管 L4 会发光、左接收管 D7 也灵 -> 左路本来就好
  * A ≈ 0 而 C 明显          -> L4 会发光，但 D7 收不到 -> 【左接收管 D7 有问题】
  * A ≈ 0 且 C ≈ 0 而 B 明显 -> L4 根本不发光 -> 【左发射管 L4 不亮】；B 是右路串光
  * A ≈ B（两者相近）        -> PF9 收到的全是右路串光，L4 无贡献

蜂鸣器节拍：
    每 ~6s 一短鸣 = 还在采样
    A 首次 > 200  -> 三声急促鸣（左发射管有效！）
    结束 -> 两长鸣
"""

import io
import sys
import time

from pyocd.core.helpers import ConnectHelper

UID = '37FF71064E5734360B791543'
DURATION = float(sys.argv[1]) if len(sys.argv) > 1 else 90.0
LOG = io.open(r'D:\STM32_Project\_ir_split.log', 'w', encoding='utf-8', newline='\n')


def log(m=''):
    print(m, flush=True)
    LOG.write(m + '\n')
    LOG.flush()


RCC_APB2ENR = 0x40021018
RCC_CFGR = 0x40021004
GPIOE_CRL = 0x40011800
GPIOE_BSRR = 0x40011810
GPIOE_BRR = 0x40011814
GPIOF_CRL = 0x40011C00
GPIOG_CRH = 0x40012004
GPIOG_BSRR = 0x40012010
GPIOG_BRR = 0x40012014

ADC3 = 0x40013C00
A_SR, A_CR1, A_CR2, A_SMPR1, A_SMPR2, A_SQR3, A_DR = (
    0x00, 0x04, 0x08, 0x0C, 0x10, 0x34, 0x4C)
CH_L, CH_R = 7, 8
EXTSEL_SWSTART = 0x000E0000
CR2_EXTTRIG_SWSTART = 0x00500000
BUZ_PIN = 12

sess = ConnectHelper.session_with_chosen_probe(
    unique_id=UID, target_override='stm32f103ze',
    options={'connect_mode': 'halt'})
sess.open()
t = sess.target


def set_mode(base, pin, val):
    """★ base 一律传 CRL 基址；偏移在这里算（传 CRH 会被重复加 0x04 写进 IDR）"""
    a = base + (0x04 if pin >= 8 else 0x00)
    sh = (pin - 8 if pin >= 8 else pin) * 4
    cur = t.read32(a)
    t.write32(a, (cur & ~(0xF << sh)) | ((val & 0xF) << sh))


def buzz(ms=80):
    t.write32(GPIOG_BSRR, 1 << BUZ_PIN)
    time.sleep(ms / 1000.0)
    t.write32(GPIOG_BRR, 1 << BUZ_PIN)


t.reset_and_halt()
time.sleep(0.1)
t.resume()
time.sleep(1.6)

t.write32(RCC_APB2ENR, t.read32(RCC_APB2ENR) | (1 << 6) | (1 << 7) | (1 << 8) | (1 << 15))
t.write32(RCC_CFGR, (t.read32(RCC_CFGR) & ~(3 << 14)) | (2 << 14))
set_mode(GPIOG_CRH, BUZ_PIN, 0x3)
t.write32(GPIOG_BRR, 1 << BUZ_PIN)
for p in (9, 10):
    set_mode(GPIOF_CRL, p, 0x0)
set_mode(GPIOE_CRL, 5, 0x7)
set_mode(GPIOE_CRL, 6, 0x7)
t.write32(GPIOE_BSRR, (1 << 5) | (1 << 6))

t.write32(ADC3 + A_CR1, 0)
t.write32(ADC3 + A_CR2, 1 | EXTSEL_SWSTART)
time.sleep(0.02)
t.write32(ADC3 + A_CR2, 1 | EXTSEL_SWSTART | (1 << 3))
for _ in range(3000):
    if not (t.read32(ADC3 + A_CR2) & (1 << 3)):
        break
t.write32(ADC3 + A_CR2, 1 | EXTSEL_SWSTART | (1 << 2))
for _ in range(3000):
    if not (t.read32(ADC3 + A_CR2) & (1 << 2)):
        break
smpr2 = t.read32(ADC3 + A_SMPR2)
for ch in (CH_L, CH_R):
    smpr2 = (smpr2 & ~(0x7 << (ch * 3))) | (0x7 << (ch * 3))
t.write32(ADC3 + A_SMPR2, smpr2)
t.write32(ADC3 + A_SMPR1, 0)


def conv(ch):
    t.write32(ADC3 + A_SQR3, (t.read32(ADC3 + A_SQR3) & ~0x1F) | ch)
    time.sleep(0.0015)
    t.write32(ADC3 + A_CR2, (t.read32(ADC3 + A_CR2) & ~CR2_EXTTRIG_SWSTART)
              | CR2_EXTTRIG_SWSTART)
    n = 0
    while n < 300:
        if t.read32(ADC3 + A_SR) & 0x02:
            break
        n += 1
    return t.read32(ADC3 + A_DR) & 0x0FFF


def avg(ch, n=8):
    conv(ch)
    conv(ch)
    s = 0
    for _ in range(n):
        s += conv(ch)
    return s // n


def led(pe5_on, pe6_on):
    if pe5_on:
        t.write32(GPIOE_BRR, 1 << 5)
    else:
        t.write32(GPIOE_BSRR, 1 << 5)
    if pe6_on:
        t.write32(GPIOE_BRR, 1 << 6)
    else:
        t.write32(GPIOE_BSRR, 1 << 6)


# 本底（两灯全灭）只采一次，之后每格与它比
led(0, 0)
time.sleep(0.03)
BASE_L = avg(CH_L)
BASE_R = avg(CH_R)
log('=== 分开驱动判决（%d 秒）===' % int(DURATION))
log('本底(两灯全灭):  PF9=%d   PF10=%d' % (BASE_L, BASE_R))
log()

for _ in range(3):
    buzz(70)
    time.sleep(0.07)
log('  >>> 三声短鸣 = 请用手掌【横扫】两对对管正前方 1~2cm，左->右->左 来回 3 遍 <<<')
log()
log('    时刻   [只亮 PE5/L4]  PF9=%-5s PF10=%-5s | [只亮 PE6/L5]  PF9=%-5s PF10=%-5s')

t0 = time.time()
maxA = maxB = maxC = maxD = 0
best_d = -1
best_d_a = -1
gotA = False
next_tick = 6.0
while time.time() - t0 < DURATION:
    el = time.time() - t0
    led(1, 0)
    time.sleep(0.012)
    A = BASE_L - avg(CH_L)
    C = BASE_R - avg(CH_R)
    led(0, 1)
    time.sleep(0.012)
    B = BASE_L - avg(CH_L)
    D = BASE_R - avg(CH_R)
    led(0, 0)
    if D > best_d:
        best_d = D
        best_d_a = A
    maxA = max(maxA, A); maxB = max(maxB, B)
    maxC = max(maxC, C); maxD = max(maxD, D)
    log('    %5.1fs  只亮L4: PF9=%4d PF10=%4d  |  只亮L5: PF9=%4d PF10=%4d'
        % (el, A, C, B, D))
    if A > 200 and not gotA:
        gotA = True
        log('    ★★★ 左发射管 L4 单独点亮时 PF9 有反应 (%d) —— L4 会发光！' % A)
        for _ in range(3):
            buzz(60)
            time.sleep(0.05)
    if el >= next_tick:
        buzz(70)
        next_tick += 6.0

log()
log('    ---------------------------------------------------')
log('    峰值表（各格最大值，已扣本底）：')
log('                     PF9(左接收)   PF10(右接收)')
log('      只亮 PE5(L4)      A=%5d        C=%5d' % (maxA, maxC))
log('      只亮 PE6(L5)      B=%5d        D=%5d' % (maxB, maxD))
log()
if maxD < 100:
    log('    ？ 右路自照射量也掉了 (%d) —— 手指可能已经松开，本次数据无效，请重跑' % maxD)
elif maxA > 200 and maxA > maxB * 2:
    log('    ✔ 结论：L4 会发光、D7 也灵 -> 左路本来是好的')
elif maxA < 80 and maxC < 80 and maxB > 40:
    log('    ★ 结论：L4 对两个接收管都无贡献，而 L5 的光能漏到 PF9 (%d)' % maxB)
    log('      -> 【左发射管 L4 不发光】（B 那格是右路串光，不是 L4 的功劳）')
elif maxA < 80 and maxC > 200:
    log('    ★ 结论：L4 会发光（PF10 收到了 %d），但左接收管 PF9 收不到 (%d)' % (maxC, maxA))
    log('      -> 【左接收管 D7 有问题】')
else:
    log('    ? 数据不典型，见上表人工判读')
log()
log('    参考：右路自照 D=%d，右路串到左 PF9 的 B=%d，比值 %s'
    % (maxD, maxB, ('%.1f 倍' % (float(maxD) / maxB)) if maxB else 'inf'))

log('    覆盖最强那一刻（D 最大时）：左路 PF9 只有 A=%d' % best_d_a)
for _ in range(2):
    buzz(420)
    time.sleep(0.18)

t.write32(GPIOE_BSRR, (1 << 5) | (1 << 6))
t.write32(GPIOG_BRR, 1 << BUZ_PIN)
for p in (9, 10):
    set_mode(GPIOF_CRL, p, 0x0)
t.reset_and_halt()
time.sleep(0.1)
t.resume()
sess.close()
log('  已复位，探针释放')
