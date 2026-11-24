# -*- coding: utf-8 -*-
"""
_ir_pe5probe.py —— 左发射支路【驱动极性】判决

【背景】
  Phase A 实测：只亮 PE5（开漏拉低）时，PF9/PF10 全程纹丝不动（max=4 / -5）；
  Phase B 实测：只亮 PE6（开漏拉低）时 PF10 到 3909 —— 采样链路完全正常。
  => 右路 PNP + 开漏拉低 = 正确；左路照抄却完全没光。

  板子是【V2.0】，原理图 PDF 是【V1.0】——元件/极性可能与图不符。
  若左路驱动管实际是 NPN（发射极接地、LED 接 5V），则：
      PE5 开漏拉低 -> 基极无电流 -> 永远不亮（= 我们观察到的现象）
      PE5 推挽拉高 -> 基极有电流 -> 亮！

【本脚本】
  Phase 1（20s）：PE5 配【推挽输出 + 输出高 3.3V】   —— 蜂鸣 1 长声
  Phase 2（20s）：PE5 配【开漏输出 + 拉低】          —— 蜂鸣 2 长声（已知失败的对照组）
  同步打印 PE5/PE6 的 IDR 回读，判断引脚到底有没有被拉到位。

【判读】
  Phase 1 里 PF9 出现尖峰 -> 左路是 NPN 驱动 -> 【纯改软件就能修好】(推挽拉高点亮)
  两个相位都没反应      -> 左发射支路硬件故障（LED 开路 / Q2 漏贴虚焊 / R25 虚焊）
"""

import io
import sys
import time

from pyocd.core.helpers import ConnectHelper

UID = '37FF71064E5734360B791543'
DUR = float(sys.argv[1]) if len(sys.argv) > 1 else 20.0
LOG = io.open(r'D:\STM32_Project\_ir_pe5probe.log', 'w', encoding='utf-8', newline='\n')


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
    """★ base 一律传 CRL 基址；偏移在这里算"""
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
t.write32(GPIOE_BSRR, (1 << 5) | (1 << 6))          # 两灯先灭

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


t.write32(GPIOE_BSRR, (1 << 5) | (1 << 6))
time.sleep(0.04)
BASE_L = avg(CH_L, 12)
BASE_R = avg(CH_R, 12)
log('=== PE5 驱动极性判决  （本底 PF9=%d PF10=%d）===' % (BASE_L, BASE_R))
log()

for _ in range(3):
    buzz(70)
    time.sleep(0.07)
log('  >>>>>> 三声短鸣 = 启动，15 秒后进入 Phase 1，请把名片/手掌放到板子前缘备用 <<<<<<')
for _i in range(3):
    time.sleep(5)
    buzz(60)
    log('     倒计时 %d 秒' % (15 - 5 * (_i + 1)))
log()


def run_phase(name, mode_val, odr_high, dur, nong, tick_s=6.0):
    set_mode(GPIOE_CRL, 5, mode_val)
    if odr_high:
        t.write32(GPIOE_BSRR, 1 << 5)
    else:
        t.write32(GPIOE_BRR, 1 << 5)
    t.write32(GPIOE_BSRR, 1 << 6)       # PE6 保持灭
    time.sleep(0.02)
    log('  ============ %s（PE5 模式=0x%X，ODR=%d）持续 %ds ============'
        % (name, mode_val, 1 if odr_high else 0, int(dur)))
    for _ in range(nong):
        buzz(420)
        time.sleep(0.18)
    log('  >>>>>> 长鸣 %d 声：用手掌/名片贴着板子前缘左右横向扫，来回 3 遍 <<<<<<' % nong)
    log('     时刻     PF9diff  PF10diff   IDR5 IDR6')
    t0 = time.time()
    mL = mR = -9999
    aL = aR = 0.0
    hit = False
    next_tick = tick_s
    while time.time() - t0 < dur:
        el = time.time() - t0
        dL = BASE_L - avg(CH_L)
        dR = BASE_R - avg(CH_R)
        idr = t.read32(GPIOE_IDR)
        b5 = (idr >> 5) & 1
        b6 = (idr >> 6) & 1
        if dL > mL:
            mL, aL = dL, el
        if dR > mR:
            mR, aR = dR, el
        flag = ''
        if dL > 200:
            flag = '  <== PF9 有反应!'
        log('    %5.1fs   %5d    %5d      %d    %d%s' % (el, dL, dR, b5, b6, flag))
        if dL > 200 and not hit:
            hit = True
            log('    ★★★ PE5 在这种驱动下 PF9 出现 %d —— 左发射管点亮了！' % dL)
            for _ in range(3):
                buzz(60)
                time.sleep(0.05)
        if el >= next_tick:
            buzz(70)
            next_tick += tick_s
    log('  ---- %s 峰值: PF9 max=%d (t=%.1fs)   PF10 max=%d (t=%.1fs)'
        % (name, mL, aL, mR, aR))
    log()


# 相位 1：推挽输出 + 输出高（NPN / 低边开关 假设下才会亮）
run_phase('Phase 1  PE5 推挽输出 + 拉高', 0x3, 1, DUR, 1)
time.sleep(0.4)
# 相位 2：推挽输出 + 输出低（NPN 假设下应熄灭；PNP/直挂 LED 假设下才会亮）
run_phase('Phase 2  PE5 推挽输出 + 拉低', 0x3, 0, DUR, 2)

log('=========================================================')
log('  判读：')
log('   * Phase 1 有峰、Phase 2 无峰')
log('       -> 左路是 NPN / 低有效驱动 -> 改固件【推挽输出：高=亮 低=灭】即可，纯软件可修')
log('   * Phase 1 无峰、Phase 2 有峰')
log('       -> 左路与右路同为 PNP，但需要【推挽拉低】才能导通（开漏拉不到底）')
log('   * 两个相位都无峰 -> 左发射支路硬件故障（L4 开路 / Q2 漏贴虚焊 / R25 虚焊）')
log('   * 看 IDR5：Phase 2 拉低时 IDR5 若仍=1，说明引脚被外部强上拉压住，拉不到地')
log()

for _ in range(2):
    buzz(500)
    time.sleep(0.22)
t.write32(GPIOE_BSRR, (1 << 5) | (1 << 6))
t.write32(GPIOG_BRR, 1 << BUZ_PIN)
t.reset_and_halt()
time.sleep(0.1)
t.resume()
sess.close()
log('  已复位，探针释放')
