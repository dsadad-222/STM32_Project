# -*- coding: utf-8 -*-
"""
_ir_guide.py —— 蜂鸣器引导的判决性采集（用户只需遮一次手）

为什么要有蜂鸣器提示：
    用户没法一边看屏幕一边操作板子。所以用板载蜂鸣器 PG12 当"节拍器"：
      * 每 5 秒 1 声短鸣      -> "我还在采样，继续遮着"
      * 左路 PF9 首次被点亮(>300) -> 立刻 3 声急促鸣叫  ★ 这是关键信号！
      * 结束时 2 声长鸣        -> "采样结束，可以松手了"

判读：
    全程只听到"每 5 秒一短鸣"，最后"两长鸣"，从没听到三声急促鸣
        -> 左接收管 PF9 全程没反应 = 【左发射管 L4 不发光，或左接收管 D7 失效】
    中途听到三声急促鸣
        -> 左路是好的，之前只是左对管前方没东西

★ ADC 启动的正确写法（标准库源码钉死）：
    CR2 = ADON | EXTSEL(111)  且启动时 CR2 |= 0x00500000 (EXTTRIG | SWSTART)，两个位缺一不可
"""

import io
import sys
import time

from pyocd.core.helpers import ConnectHelper

UID = '37FF71064E5734360B791543'
DURATION = float(sys.argv[1]) if len(sys.argv) > 1 else 75.0
LOG = io.open(r'D:\STM32_Project\_ir_guide.log', 'w', encoding='utf-8', newline='\n')


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
    """★ base 必须传 CRL 基址，偏移在这里算 —— 传 CRH 会重复加 0x04 写进 IDR"""
    a = base + (0x04 if pin >= 8 else 0x00)
    sh = (pin - 8 if pin >= 8 else pin) * 4
    cur = t.read32(a)
    t.write32(a, (cur & ~(0xF << sh)) | ((val & 0xF) << sh))


# ---------- 蜂鸣器 PG12 ----------
def buzz(ms=80):
    t.write32(GPIOG_BSRR, 1 << BUZ_PIN)
    time.sleep(ms / 1000.0)
    t.write32(GPIOG_BRR, 1 << BUZ_PIN)


# ---------- 复位 App，让固件把时钟/引脚都配好，再接管 ----------
t.reset_and_halt()
time.sleep(0.1)
t.resume()
time.sleep(1.6)

t.write32(RCC_APB2ENR, t.read32(RCC_APB2ENR) | (1 << 6) | (1 << 7) | (1 << 8) | (1 << 15))
t.write32(RCC_CFGR, (t.read32(RCC_CFGR) & ~(3 << 14)) | (2 << 14))
set_mode(GPIOG_CRH, BUZ_PIN, 0x3)                  # PG12 推挽输出
t.write32(GPIOG_BRR, 1 << BUZ_PIN)

for p in (9, 10):
    set_mode(GPIOF_CRL, p, 0x0)                    # 模拟输入
set_mode(GPIOE_CRL, 5, 0x7)                        # 开漏
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


def avg(ch, n=6):
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


def bar(v, scale=400, width=22):
    n = int(min(width, v * width // scale))
    return '#' * n + '.' * (width - n)


log()
log('=== 蜂鸣器引导采集（%d 秒）===' % int(DURATION))
log('  节拍：每 5s 一短鸣 = 还在采样 / 左路点亮 = 三声急促鸣 / 结束 = 两长鸣')
log()
log('    时刻    左PF9: dark/lit/diff        右PF10: dark/lit/diff')

# 起始信号：三声急促鸣 = "请开始把手指顶在两对管正前方"
for _ in range(3):
    buzz(70)
    time.sleep(0.07)

t0 = time.time()
peak_l = peak_r = 0
first_peak = None
sig_l = False
next_tick = 5.0
sig_start = None
while time.time() - t0 < DURATION:
    el = time.time() - t0
    dl, ll, xl = measure(CH_L)
    dr, lr, xr = measure(CH_R)
    peak_l = max(peak_l, xl)
    peak_r = max(peak_r, xr)
    if xl > 300 and not sig_l:
        sig_l = True
        first_peak = (el, xl, dr, lr, xr)
        log('    %5.1fs  ★★★ 左路 PF9 首次有反应！diff=%d  (右路此时 diff=%d)' % (el, xl, xr))
        for _ in range(3):
            buzz(60)
            time.sleep(0.05)
        continue
    log('    %5.1fs  L %4d/%4d/%4d %-22s R %4d/%4d/%4d %-22s'
        % (el, dl, ll, xl, bar(xl), dr, lr, xr, bar(xr)))
    if el >= next_tick:
        buzz(70)
        next_tick += 5.0

log()
log('    ---------------------------------------------------------------')
log('    峰值：  左PF9 diff_max=%d      右PF10 diff_max=%d' % (peak_l, peak_r))
log()

# 结束信号：两长鸣
for _ in range(2):
    buzz(420)
    time.sleep(0.18)

if sig_l:
    log('  ★ 结论：左路有反应（峰值 %d）-> 左发射管 L4 与左接收管 D7 都是好的；' % peak_l)
    log('         之前的 diff=0 只是因为左对管正前方没有反射物。')
elif peak_r > 300:
    log('  ★ 结论：右路全程有强反射（峰值 %d），左路全程为 0（峰值 %d）' % (peak_r, peak_l))
    log('         -> 手指已同时挡住两对管，左路仍完全无反应：')
    log('            【左通道失效】= 左发射管 L4 不发光 或 左接收管 D7 无响应（二者之一）')
    log('            进一步的区分办法：')
    log('              · 用手机相机对着两个发射管（LED）看有无紫白亮斑 -> 判发射管')
    log('              · 用电视遥控器（红外）对着两个接收管按一下      -> 判接收管')
else:
    log('  ?  两路都没动 -> 遮挡动作没被捕捉到，请重跑')

t.write32(GPIOE_BSRR, (1 << 5) | (1 << 6))
t.write32(GPIOG_BRR, 1 << BUZ_PIN)
for p in (9, 10):
    set_mode(GPIOF_CRL, p, 0x0)
t.reset_and_halt()
time.sleep(0.1)
t.resume()
sess.close()
log('  已复位，探针释放')
