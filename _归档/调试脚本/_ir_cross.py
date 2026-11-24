# -*- coding: utf-8 -*-
"""
_ir_cross.py —— 查左发射管 L4 到底亮不亮（不需要用户操作）

思路：
    右路已经确认能测到反射（App 实测 diff=226/231）。左路始终 diff=0。
    可能有两种原因：
        (a) 左发射管 L4 是坏的 / 没焊 → 左边根本发不出红外；
        (b) 左对管前方确实空旷 → 发了也没东西反射回来。
    两对对管在板上挨得很近（几毫米到一两厘米），所以"串扰"可以当探针：
        点亮【左】发射管时，如果 L4 在发光，它的光会照到【右】对管前方的那个
        反射物上，于是【右接收管 PF10】的读数会有变化（哪怕很小）。
    之前用数字 IDR 看不出来（施密特门限 1.65V，小变化被吃掉），所以这次用
    ADC 高精度比：每种灯态各采 32 次平均，看 3 种灯态下两个接收管的差异。

★ 这次采样时间写的是 SMPR2（通道 0~9），不是 SMPR1 —— 上次写错寄存器
  导致读数恒为垃圾值 66，教训见 _ir_selftest.py。
"""

import io
import time

from pyocd.core.helpers import ConnectHelper

LOG = io.open(r'D:\STM32_Project\_ir_cross.log', 'w', encoding='utf-8', newline='\n')


def log(m=''):
    print(m, flush=True)
    LOG.write(m + '\n')
    LOG.flush()


UID = '37FF71064E5734360B791543'
RCC_APB2ENR = 0x40021018
RCC_CFGR = 0x40021004
GPIOE_CRL = 0x40011800
GPIOE_BSRR = 0x40011810
GPIOE_BRR = 0x40011814
GPIOF_CRL = 0x40011C00
GPIOF_CRH = 0x40011C04

ADC3 = 0x40013C00
ADC_SR, ADC_CR1, ADC_CR2, ADC_SMPR2, ADC_SQR3, ADC_DR = (
    0x00, 0x04, 0x08, 0x10, 0x34, 0x4C)

sess = ConnectHelper.session_with_chosen_probe(
    unique_id=UID, target_override='stm32f103ze', options={'connect_mode': 'halt'})
sess.open()
t = sess.target
log('=== 连接 %s %s ===' % (t.part_number, t.get_state()))


def set_pin(base, pin, val):
    sh = (pin if pin < 8 else pin - 8) * 4
    a = base + (0x04 if pin >= 8 else 0x00)
    t.write32(a, (t.read32(a) & ~(0xF << sh)) | ((val & 0xF) << sh))


t.write32(RCC_APB2ENR, t.read32(RCC_APB2ENR) | (1 << 6) | (1 << 7) | (1 << 15))
t.write32(RCC_CFGR, (t.read32(RCC_CFGR) & ~(3 << 14)) | (2 << 14))

set_pin(GPIOE_CRL, 5, 0x7)
set_pin(GPIOE_CRL, 6, 0x7)
t.write32(GPIOE_BSRR, (1 << 5) | (1 << 6))

for p in (7, 8, 9, 10):
    set_pin(GPIOF_CRL if p < 8 else GPIOF_CRH, p, 0x0)
log('  GPIOF_CRL=%08X GPIOF_CRH=%08X' % (t.read32(GPIOF_CRL), t.read32(GPIOF_CRH)))

t.write32(ADC3 + ADC_CR1, 0)
t.write32(ADC3 + ADC_CR2, 1)
time.sleep(0.02)
t.write32(ADC3 + ADC_CR2, 1 | (1 << 3))
while t.read32(ADC3 + ADC_CR2) & (1 << 3):
    pass
t.write32(ADC3 + ADC_CR2, 1 | (1 << 2))
while t.read32(ADC3 + ADC_CR2) & (1 << 2):
    pass

# ★ SMPR2 = 通道 0~9 的采样时间（SMPR1 是通道 10~17）
smpr2 = t.read32(ADC3 + ADC_SMPR2)
for ch in (5, 6, 7, 8):
    smpr2 = (smpr2 & ~(0x7 << (ch * 3))) | (0x7 << (ch * 3))
t.write32(ADC3 + ADC_SMPR2, smpr2)
log('  ADC3 CR2=%08X SMPR2=%08X' % (t.read32(ADC3 + ADC_CR2), t.read32(ADC3 + ADC_SMPR2)))


def conv(ch):
    t.write32(ADC3 + ADC_SQR3, (t.read32(ADC3 + ADC_SQR3) & ~0x1F) | ch)
    time.sleep(0.002)
    t.write32(ADC3 + ADC_CR2, t.read32(ADC3 + ADC_CR2) | (1 << 22))
    n = 0
    while n < 200 and not (t.read32(ADC3 + ADC_SR) & 0x02):
        n += 1
    return t.read32(ADC3 + ADC_DR) & 0x0FFF


def avg(ch, n=32):
    conv(ch)
    conv(ch)
    tot = 0
    for _ in range(n):
        tot += conv(ch)
    return tot // n


def leds(l_on, r_on):
    t.write32(GPIOE_BRR if l_on else GPIOE_BSRR, 1 << 5)
    t.write32(GPIOE_BRR if r_on else GPIOE_BSRR, 1 << 6)
    time.sleep(0.03)


log()
log('每格是 ADC3 原始值（12 位，满量程 4096；值越小说明接收管被拉得越低 = 反射越强）')
log()
log('%-16s %-14s %-14s %-14s' % ('灯态', 'PF9 左接收', 'PF10 右接收', 'PF7(BAT) 参照'))
log('-' * 62)
res = {}
for name, lo, ro in [('两灯都灭', False, False),
                     ('只亮左灯 L4', True, False),
                     ('只亮右灯 L5', False, True)]:
    leds(lo, ro)
    v9 = avg(7)
    v10 = avg(8)
    v7 = avg(5)                     # BAT 当参照：灯态不该影响它
    res[name] = (v9, v10, v7)
    log('%-16s %-14d %-14d %-14d' % (name, v9, v10, v7))
log('-' * 62)

off9, off10, _ = res['两灯都灭']
l9, l10, _ = res['只亮左灯 L4']
r9, r10, _ = res['只亮右灯 L5']

log()
log('灯态差分（相对"两灯都灭"）：')
log('  PF9  左接收：亮左灯 %+d    亮右灯 %+d' % (l9 - off9, r9 - off9))
log('  PF10 右接收：亮左灯 %+d    亮右灯 %+d' % (l10 - off10, r10 - off10))
log()
if abs(l10 - off10) >= 5:
    log('  ✔ 亮【左】灯时 PF10 有 %+d 的变化 -> 左发射管 L4 确实在发光'
        '（它的光串到了右对管前方的反射物上）' % (l10 - off10))
elif abs(l9 - off9) >= 5:
    log('  ✔ 亮【左】灯时 PF9 有 %+d 的变化 -> 左路收发配对工作' % (l9 - off9))
else:
    log('  ✘ 亮左灯时两个接收管都没有任何变化 —— 左发射管 L4 可能没发光，'
        '或者左对管前方确实空旷（需要用实物在左对管正前方 5cm 处验证）')

leds(False, False)
t.halt()
t.write32(ADC3 + ADC_CR2, 0)
t.reset_and_halt()
time.sleep(0.1)
t.resume()
sess.close()
log()
log('  已复位重启 App，探针已释放')
