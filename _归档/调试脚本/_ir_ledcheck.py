# -*- coding: utf-8 -*-
"""
_ir_ledcheck.py —— 手机摄像头定位并确认两颗红外发射管

红外光肉眼看不见，但【手机摄像头】能看到紫白色亮斑。本脚本把两颗发射管
【轮流单独点亮】（每颗 20 秒，交替 2 轮，共 80 秒），用户用手机摄像头对着
板子前缘那两颗透明 LED 灯珠观察，即可：
   1. 确认哪一颗会亮、哪一颗完全不亮
   2. 顺带定位"不亮的那一颗"的物理位置（= L4，就是故障件所在处）

蜂鸣器节拍：
    三声短鸣 + 倒计时      = 启动
    1 长声                 = 只亮 L4（PE5）
    2 长声                 = 只亮 L5（PE6）
    重复 2 轮
    最后 2 长声            = 结束

同步记录 PF9/PF10 的 diff（作为电子学旁证）。
"""

import io
import time

from pyocd.core.helpers import ConnectHelper

UID = '37FF71064E5734360B791543'
PHASE = 20.0
ROUNDS = 2
LOG = io.open(r'D:\STM32_Project\_ir_ledcheck.log', 'w', encoding='utf-8', newline='\n')


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
set_mode(GPIOE_CRL, 5, 0x7)          # 与固件一致：开漏
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
    time.sleep(0.0012)
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
    s = 0
    for _ in range(n):
        s += conv(ch)
    return s // n


log('=== 手机摄像头定位红外发射管（每颗 %ds，共 %d 轮）===' % (int(PHASE), ROUNDS))
t.write32(GPIOE_BSRR, (1 << 5) | (1 << 6))
time.sleep(0.05)
BASE_L = avg(CH_L, 10)
BASE_R = avg(CH_R, 10)
log('本底(两灯全灭): PF9=%d PF10=%d' % (BASE_L, BASE_R))
log()

for _ in range(3):
    buzz(70)
    time.sleep(0.07)
log('  >>>>>> 三声短鸣 = 启动。请立刻打开手机相机，对着板子前缘那两颗透明 LED 灯珠 <<<<<<')
log('  >>>>>> 10 秒倒计时后开始。手机屏幕里红外光会显示为【紫白色亮斑】 <<<<<<')
for _i in range(2):
    time.sleep(5)
    buzz(60)
    log('     倒计时 %d 秒' % (10 - 5 * (_i + 1)))
log()


def phase(name, pin, base, chan, nong, dur=PHASE):
    other = 6 if pin == 5 else 5
    t.write32(GPIOE_BSRR, 1 << other)                # 另一颗确保灭
    t.write32(GPIOE_BRR, 1 << pin)                   # 开漏拉低 = 点亮
    time.sleep(0.01)
    log('  ============== %s 点亮（持续 %ds）' % (name, int(dur)))
    for _ in range(nong):
        buzz(420)
        time.sleep(0.2)
    try:
        lvl = t.read32(GPIOE_IDR)
        log('     IDR5=%d IDR6=%d   (点亮脚应为 0 = 确实拉到地)'
            % ((lvl >> 5) & 1, (lvl >> 6) & 1))
    except Exception as e:
        log('     [IDR readback failed] %r' % (e,))
    t0 = time.time()
    mx = -9999
    n_ok = n_err = 0
    while time.time() - t0 < dur:
        try:
            d = base - avg(chan)
            mx = max(mx, d)
            n_ok += 1
        except Exception as e:
            n_err += 1
            log('     [sample err #%d] %r' % (n_err, e))
        time.sleep(0.25)
    log('     采样 %d 次成功 / %d 次失败' % (n_ok, n_err))
    t.write32(GPIOE_BSRR, 1 << pin)                  # 熄灭
    log('     %s 相位内 %s 最大 diff = %d' % (name, 'PF9' if chan == CH_L else 'PF10', mx))
    log()


for r in range(ROUNDS):
    log('  ---------- 第 %d 轮 ----------' % (r + 1))
    phase('%s (PE5 -> L4)' % ('1 长声' if r == 0 else '又 1 长声'), 5, BASE_L, CH_L, 1)
    time.sleep(0.6)
    phase('%s (PE6 -> L5)' % ('2 长声' if r == 0 else '又 2 长声'), 6, BASE_R, CH_R, 2)
    time.sleep(0.6)

log('=========================== 结束 ===========================')
log('  看手机屏幕的结论填这里：')
log('   第 1/3 段（PE5->L4）：哪一颗亮？  ______')
log('   第 2/4 段（PE6->L5）：哪一颗亮？  ______')
log('   * 某一颗【两段都不亮】-> 就是它 / 或它的支路坏了 = 故障件')
log('   * 两颗都亮 -> 之前的"无光"结论有误，回到电子学重新查')
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
