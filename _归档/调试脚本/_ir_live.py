# -*- coding: utf-8 -*-
"""
_ir_live.py —— 实时监视两路红外（判决性实验）

用途：让用户【把手指同时挡在两对对管正前方 1~2cm】，然后看两路 diff 怎么动。

判读：
  * PF10(右) diff 大幅上升、而 PF9(左) 始终纹丝不动
      -> 左发射管 L4 确实不发光（基极回路已在 _ir_conn.py 里证明在位）
  * 两路都涨 -> 左路其实是好的，之前只是"左对管前方没东西"

★ 本次已用标准库源码钉死 ADC 的正确启动方式：
    CR2 |= 0x00500000   (EXTTRIG | SWSTART，两个位缺一不可)
    另外 SWSTART 只在 EXTSEL=111 时有效 -> CR2 的 EXTSEL 必须是 0x7<<17
"""

import io
import sys
import time

from pyocd.core.helpers import ConnectHelper

UID = '37FF71064E5734360B791543'
DURATION = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
LOG = io.open(r'D:\STM32_Project\_ir_live.log', 'w', encoding='utf-8', newline='\n')


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

ADC3 = 0x40013C00
A_SR, A_CR1, A_CR2, A_SMPR1, A_SMPR2, A_SQR3, A_DR = (
    0x00, 0x04, 0x08, 0x0C, 0x10, 0x34, 0x4C)
CH_L, CH_R = 7, 8
EXTSEL_SWSTART = 0x000E0000
CR2_EXTTRIG_SWSTART = 0x00500000

sess = ConnectHelper.session_with_chosen_probe(
    unique_id=UID, target_override='stm32f103ze',
    options={'connect_mode': 'halt'})
sess.open()
t = sess.target


def set_mode(base, pin, val):
    a = base + (0x04 if pin >= 8 else 0x00)
    sh = (pin - 8 if pin >= 8 else pin) * 4
    cur = t.read32(a)
    t.write32(a, (cur & ~(0xF << sh)) | ((val & 0xF) << sh))


t.write32(RCC_APB2ENR, t.read32(RCC_APB2ENR) | (1 << 6) | (1 << 7) | (1 << 15))
t.write32(RCC_CFGR, (t.read32(RCC_CFGR) & ~(3 << 14)) | (2 << 14))

for p in (9, 10):
    set_mode(GPIOF_CRL, p, 0x0)                  # 模拟输入
set_mode(GPIOE_CRL, 5, 0x7)                      # 开漏
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


def avg(ch, n=6):
    conv(ch)
    conv(ch)
    s = 0
    for _ in range(n):
        s += conv(ch)
    return s // n


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


def measure(ch):
    led(0, 0)
    time.sleep(0.010)
    dark = avg(ch)
    led(1, 1)
    time.sleep(0.010)
    lit = avg(ch)
    led(0, 0)
    time.sleep(0.004)
    return dark, lit, (dark - lit if dark > lit else 0)


def bar(v, scale=400, width=24):
    n = int(min(width, v * width // scale))
    return '#' * n + '.' * (width - n)


log()
log('=== 红外两路实时监视（%d 秒，每 ~0.3s 一行）===' % int(DURATION))
log('    时刻    左PF9: dark/lit/diff      右PF10: dark/lit/diff')
log('    ---------------------------------------------------------------')

t0 = time.time()
peak_l = peak_r = 0
while time.time() - t0 < DURATION:
    dl, ll, xl = measure(CH_L)
    dr, lr, xr = measure(CH_R)
    peak_l = max(peak_l, xl)
    peak_r = max(peak_r, xr)
    log('    %5.1fs  L %4d/%4d/%4d %-12s R %4d/%4d/%4d %-12s'
        % (time.time() - t0, dl, ll, xl, bar(xl), dr, lr, xr, bar(xr)))

log('    ---------------------------------------------------------------')
log('    峰值：  左PF9 diff_max=%d      右PF10 diff_max=%d' % (peak_l, peak_r))
log()
if peak_r > 300 and peak_l < 50:
    log('  结论：右路正常、左路全程无响应 -> 【左发射管 L4 不发光】')
elif peak_l > 300:
    log('  结论：左路也有响应（diff_max=%d）-> 左路是好的，之前只是前方无反射物' % peak_l)
else:
    log('  结论：两路都没动 -> 遮挡动作没被捕捉到，或前方确实没东西，请重跑并确保手指同时挡住两对管')

t.write32(GPIOE_BSRR, (1 << 5) | (1 << 6))
for p in (9, 10):
    set_mode(GPIOF_CRL, p, 0x0)
t.reset_and_halt()
time.sleep(0.1)
t.resume()
sess.close()
log('  已复位，探针释放')
