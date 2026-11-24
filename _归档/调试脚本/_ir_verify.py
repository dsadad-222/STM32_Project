# -*- coding: utf-8 -*-
"""
_ir_verify.py —— 上板验证红外避障的两路引脚与"灭灯/亮灯差分"测量法

为什么要这么验：
    不用按键、不依赖串口，直接用调试器把 ADC3 + GPIO 配好，自己采数据。
    这样能一次性回答三个问题：
        ① PF9 / PF10 到底是不是两路接收管的输出（遮哪一路，哪一路的数变）；
        ② PE5 / PE6 开漏点亮发射管有没有效果（亮灯读数是不是明显低于灭灯）；
        ③ 门限 IR_DIFF_MID / IR_DIFF_NEAR 该定多少。

提示方式：用板载蜂鸣器（PG12）报段号，用户按蜂鸣次数操作：
    1 声  -> 把手拿开（空旷基线）
    2 声  -> 用手掌贴住【左边】那对对管，距离 3~5cm
    3 声  -> 用手掌贴住【右边】那对对管
    1 长声 -> 全部拿开
"""

import json
import time

from pyocd.core.helpers import ConnectHelper

UID = '37FF71064E5734360B791543'

RCC_APB2ENR = 0x40021018
RCC_CFGR    = 0x40021004
GPIOE_CRL   = 0x40011800
GPIOE_BSRR  = 0x40011810
GPIOE_BRR   = 0x40011814
GPIOF_CRH   = 0x40011C04
GPIOG_CRH   = 0x40012004
GPIOG_BSRR  = 0x40012010
GPIOG_BRR   = 0x40012014

ADC3 = 0x40013C00
ADC_SR, ADC_CR1, ADC_CR2, ADC_SMPR1, ADC_SMPR2, ADC_SQR1, ADC_SQR3, ADC_DR = (
    0x00, 0x04, 0x08, 0x0C, 0x10, 0x2C, 0x34, 0x4C)

CH_L = 7        # PF9  = ADC3_IN7  左接收
CH_R = 8        # PF10 = ADC3_IN8  右接收
AVG  = 8

# ---------- 连接 ----------
sess = ConnectHelper.session_with_chosen_probe(
    unique_id=UID, target_override='stm32f103ze',
    options={'connect_mode': 'halt'})
sess.open()
t = sess.target
print('connected:', t.part_number, t.get_state())


def nib(addr, pin):
    return (addr, (pin if pin < 8 else pin - 8) * 4)


def set_pin(addr, pin, val):
    a, sh = nib(addr, pin)
    cur = t.read32(a)
    cur = (cur & ~(0xF << sh)) | ((val & 0xF) << sh)
    t.write32(a, cur)


def read_pin(addr, pin):
    a, sh = nib(addr, pin)
    return (t.read32(a) >> sh) & 0xF


# ---------- 蜂鸣器 ----------
def beep(ms):
    t.write32(GPIOG_BSRR, 1 << 12)
    time.sleep(ms / 1000.0)
    t.write32(GPIOG_BRR, 1 << 12)


def beeps(n, short=90):
    for i in range(n):
        beep(short)
        if i != n - 1:
            time.sleep(0.12)


# ---------- 硬件准备 ----------
print('--- 配置 GPIO / ADC3 ---')
clk = t.read32(RCC_APB2ENR)
t.write32(RCC_APB2ENR, clk | (1 << 15) | (1 << 6) | (1 << 7) | (1 << 8))

# ADCPRE = PCLK2 / 6
cfgr = t.read32(RCC_CFGR)
t.write32(RCC_CFGR, (cfgr & ~(3 << 14)) | (2 << 14))

# PG12 蜂鸣器 -> 推挽输出
set_pin(GPIOG_CRH, 12, 0x3)

# PE5 / PE6 -> 开漏输出 50MHz，先置高 = 高阻 = 发射管灭
set_pin(GPIOE_CRL, 5, 0x7)
set_pin(GPIOE_CRL, 6, 0x7)
t.write32(GPIOE_BSRR, (1 << 5) | (1 << 6))

# PF9 / PF10 -> 模拟输入
set_pin(GPIOF_CRH, 9, 0x0)
set_pin(GPIOF_CRH, 10, 0x0)

print('  GPIOE_CRL=%08X  GPIOF_CRH=%08X' % (t.read32(GPIOE_CRL), t.read32(GPIOF_CRH)))

# ADC3 上电 + 校准
t.write32(ADC3 + ADC_CR1, 0x00000000)
t.write32(ADC3 + ADC_CR2, 0x00000001)            # ADON
t.write32(ADC3 + ADC_CR2, 0x00000001 | (1 << 3))  # RSTCAL
while t.read32(ADC3 + ADC_CR2) & (1 << 3):
    pass
t.write32(ADC3 + ADC_CR2, 0x00000001 | (1 << 2))  # CAL
while t.read32(ADC3 + ADC_CR2) & (1 << 2):
    pass

# 通道 7 在 SMPR1 的 bit23:21，通道 8 在 bit26:24；采样时间=111(239.5 周期)
smpr1 = t.read32(ADC3 + ADC_SMPR1)
smpr1 = (smpr1 & ~(0x7 << 21)) | (0x7 << 21)
smpr1 = (smpr1 & ~(0x7 << 24)) | (0x7 << 24)
t.write32(ADC3 + ADC_SMPR1, smpr1)
t.write32(ADC3 + ADC_SQR1, 0x00000000)           # 1 次转换

print('  ADC3 CR2=%08X SMPR1=%08X' % (t.read32(ADC3 + ADC_CR2), t.read32(ADC3 + ADC_SMPR1)))


def adc_conv(ch):
    sqr3 = t.read32(ADC3 + ADC_SQR3)
    t.write32(ADC3 + ADC_SQR3, (sqr3 & ~0x1F) | ch)
    cr2 = t.read32(ADC3 + ADC_CR2)
    t.write32(ADC3 + ADC_CR2, cr2 | (1 << 22))   # SWSTART
    for _ in range(20000):
        if t.read32(ADC3 + ADC_SR) & 0x02:
            break
    return t.read32(ADC3 + ADC_DR) & 0x0FFF


def adc_avg(ch, times=AVG):
    """丢 2 次 + 取平均（这里不追求极值滤波，够看趋势就行）"""
    adc_conv(ch)
    adc_conv(ch)
    tot = 0
    for _ in range(times):
        tot += adc_conv(ch)
    return tot // times


def led_left(on):
    t.write32(GPIOE_BRR if on else GPIOE_BSRR, 1 << 5)


def led_right(on):
    t.write32(GPIOE_BRR if on else GPIOE_BSRR, 1 << 6)


def measure(side):
    """side: 'L' 或 'R'；返回 (dark, lit, diff)"""
    ch = CH_L if side == 'L' else CH_R
    setled = led_left if side == 'L' else led_right
    setled(False)
    time.sleep(0.02)
    dark = adc_avg(ch)
    setled(True)
    time.sleep(0.02)
    lit = adc_avg(ch)
    setled(False)
    return dark, lit, max(0, dark - lit)


# ---------- 分段验证 ----------
PHASES = [
    (1, 3.0, 'P0 手拿开（空旷基线）'),
    (2, 6.0, 'P1 手掌贴住【左】对管 3~5cm'),
    (3, 6.0, 'P2 手掌贴住【右】对管 3~5cm'),
    (0, 3.0, 'P3 全部拿开'),
]

print()
print('=== 请按蜂鸣器提示操作（1声=拿开 2声=盖左 3声=盖右 长声=拿开）===')
result = {'phases': []}

# 就绪信号：连响 5 声，听到就说明测试开始了，准备操作
print('  >> 就绪信号：5 声短鸣…')
beeps(5, 120)
time.sleep(3.0)

for nbeep, dur, title in PHASES:
    if nbeep == 0:
        beep(600)
    else:
        beeps(nbeep)
    print('  >> %s  (%.0fs)' % (title, dur))

    t0 = time.time()
    acc = {'L': [], 'R': []}
    while time.time() - t0 < dur - 1.2:          # 留 1.2s 给用户就位
        acc['L'].append(measure('L'))
        acc['R'].append(measure('R'))
    time.sleep(min(1.2, dur * 0.2))

    row = {'title': title}
    for side in ('L', 'R'):
        ds = [x[0] for x in acc[side]]
        ls = [x[1] for x in acc[side]]
        df = [x[2] for x in acc[side]]
        n = max(1, len(df))
        row[side] = {
            'n': len(df),
            'dark': sum(ds) // n,
            'lit': sum(ls) // n,
            'diff': sum(df) // n,
            'diff_max': max(df) if df else 0,
        }
    result['phases'].append(row)
    print('     L: dark=%4d lit=%4d diff=%4d(max %4d)   R: dark=%4d lit=%4d diff=%4d(max %4d)'
          % (row['L']['dark'], row['L']['lit'], row['L']['diff'], row['L']['diff_max'],
             row['R']['dark'], row['R']['lit'], row['R']['diff'], row['R']['diff_max']))

# ---------- 汇总 ----------
print()
print('=' * 78)
print('%-34s %-23s %-23s' % ('分段', '左路(dark/lit/diff)', '右路(dark/lit/diff)'))
print('-' * 78)
for row in result['phases']:
    print('%-34s %5d/%5d/%5d        %5d/%5d/%5d'
          % (row['title'], row['L']['dark'], row['L']['lit'], row['L']['diff'],
             row['R']['dark'], row['R']['lit'], row['R']['diff']))
print('=' * 78)

p0, p1, p2, p3 = result['phases']
verdict = []
verdict.append('左路对遮挡的响应：盖左 diff=%d，其他地方 diff=%d/%d'
               % (p1['L']['diff'], p0['L']['diff'], p2['L']['diff']))
verdict.append('右路对遮挡的响应：盖右 diff=%d，其他地方 diff=%d/%d'
               % (p2['R']['diff'], p0['R']['diff'], p1['R']['diff']))
for v in verdict:
    print(v)

# ---------- 收尾：关灯、恢复 ADC3、复位重启 App ----------
t.write32(GPIOE_BSRR, (1 << 5) | (1 << 6))
t.write32(ADC3 + ADC_CR2, 0x00000000)
t.reset_and_halt()
time.sleep(0.1)
t.resume()
sess.close()

json.dump(result, open(r'D:\STM32_Project\_ir_scan_data\verify_v2.json', 'w'),
          ensure_ascii=False, indent=1)
print()
print('已保存 D:\\STM32_Project\\_ir_scan_data\\verify_v2.json，并复位重启了 App')
