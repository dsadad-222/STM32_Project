# -*- coding: utf-8 -*-
"""
_ir_l4probe.py —— 【单发射管】【慢速长相位】判决：左发射管 L4 到底亮不亮

【为什么要重做】
  上一轮 _ir_split.py 是 L4/L5 每 12ms 交替点亮，用户根本无从知道某一刻亮的是哪个；
  而且从头到尾【没有任何东西放在左对管正前方】——手指一直死死压在右对管上
  （D=3955 持续 40 秒不动，说明反射物根本没移动）。
  所以 A=5 只能说明"左对管前面是空的"，【不能】说明 L4 不发光。
  ★ 结论作废，本轮重做。

【本脚本设计】
  Phase A（30s）：只亮 PE5/L4     —— 蜂鸣 1 长声
  Phase B（30s）：只亮 PE6/L5     —— 蜂鸣 2 长声
  每个相位内连续采样 PF9/PF10 的 diff（扣"两灯全灭"本底），~10Hz 打点。
  用户只需：听到 1 长声 → 用手掌/名片贴着前缘从左扫到右来回 3 遍；
            听到 2 长声 → 再扫 3 遍。

【判读】
  Phase A 中 PF9 出现大尖峰（>300）        -> L4 会发光、D7 也灵 -> 左路本来就好（此前的"坏"是假象）
  Phase A 中 PF9 恒 0 而 PF10 有明显包（>80）-> L4 会发光，但 D7 收不到 -> 左接收管有问题
  Phase A 中 PF9/PF10 都恒 0                -> L4 真的不发光
  Phase B 中 PF10 大尖峰（~4000）           -> 右路自洽（对照，已知正常）
"""

import io
import sys
import time

from pyocd.core.helpers import ConnectHelper

UID = '37FF71064E5734360B791543'
PHASE_A = float(sys.argv[1]) if len(sys.argv) > 1 else 30.0
PHASE_B = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
LOG = io.open(r'D:\STM32_Project\_ir_l4probe.log', 'w', encoding='utf-8', newline='\n')


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
    set_mode(GPIOF_CRL, p, 0x0)          # PF9/PF10 模拟输入
set_mode(GPIOE_CRL, 5, 0x7)              # PE5 开漏
set_mode(GPIOE_CRL, 6, 0x7)              # PE6 开漏
t.write32(GPIOE_BSRR, (1 << 5) | (1 << 6))   # 两灯先灭

# ADC3：EXTSEL=111(SWSTART) 必须先设；启动靠 EXTTRIG|SWSTART 两位同时置
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


# ---------- 本底（两灯全灭） ----------
led(0, 0)
time.sleep(0.04)
BASE_L = avg(CH_L, 12)
BASE_R = avg(CH_R, 12)
log('=== 单发射管慢速判决  PhaseA(L4 only)=%ds  PhaseB(L5 only)=%ds ==='
    % (int(PHASE_A), int(PHASE_B)))
log('本底(两灯全灭):  PF9=%d   PF10=%d' % (BASE_L, BASE_R))
log()

for _ in range(3):
    buzz(70)
    time.sleep(0.07)
log('  >>>>>> 三声短鸣 = 脚本已启动 <<<<<<')
log('  >>>>>> 15 秒后开始 Phase A，请先把名片/手掌放到板子前缘备用 <<<<<<')
for _i in range(3):
    time.sleep(5)
    buzz(60)
    log('     倒计时 %d 秒' % (15 - 5 * (_i + 1)))
log()


def run_phase(name, pe5_on, pe6_on, dur, nong, tick_s=6.0):
    """返回 (maxL, maxR, argmaxL_t, argmaxR_t)"""
    led(pe5_on, pe6_on)
    log('  ================ %s 开始（灯态 %s，持续 %ds）================'
        % (name, ('PE5/L4 亮' if pe5_on else 'PE6/L5 亮'), int(dur)))
    for _ in range(nong):
        buzz(420)
        time.sleep(0.18)
    log('  >>>>>> 长鸣 %d 声：开始【用手掌/名片贴着板子前缘，从一端慢慢扫到另一端，'
        '来回 3 遍，约 10 秒走完】<<<<<<' % nong)
    log('     时刻     PF9diff  PF10diff')
    t0 = time.time()
    mL = mR = -9999
    aL = aR = 0.0
    hit = False
    next_tick = tick_s
    while time.time() - t0 < dur:
        el = time.time() - t0
        dL = BASE_L - avg(CH_L)
        dR = BASE_R - avg(CH_R)
        if dL > mL:
            mL, aL = dL, el
        if dR > mR:
            mR, aR = dR, el
        bar = ''
        if dL > 300:
            bar = '  <== PF9 有反应!'
        log('    %5.1fs   %5d    %5d%s' % (el, dL, dR, bar))
        if dL > 300 and not hit:
            hit = True
            log('    ★★★ 左发射管单独点亮时 PF9 出现 %d —— L4 会发光！' % dL)
            for _ in range(3):
                buzz(60)
                time.sleep(0.05)
        if el >= next_tick:
            buzz(70)
            next_tick += tick_s
    led(0, 0)
    log('  ---- %s 峰值:  PF9 max=%d (t=%.1fs)   PF10 max=%d (t=%.1fs)'
        % (name, mL, aL, mR, aR))
    log()
    time.sleep(0.2)
    return mL, mR, aL, aR


A_L, A_R, A_tL, A_tR = run_phase('Phase A  只亮 PE5 / L4', 1, 0, PHASE_A, 1)
time.sleep(0.4)
B_L, B_R, B_tL, B_tR = run_phase('Phase B  只亮 PE6 / L5', 0, 1, PHASE_B, 2)

log('====================================================')
log('             PF9(左接收)        PF10(右接收)')
log('Phase A 只亮L4   %5d              %5d' % (A_L, A_R))
log('Phase B 只亮L5   %5d              %5d' % (B_L, B_R))
log('====================================================')
if B_R < 300:
    log('？ 右路自照也不高 (%d) —— 手可能没扫到 / 悬得太远，本次数据参考价值低' % B_R)
if A_L > 300:
    log('✔✔ 结论：Phase A 里 PF9 被扫出 %d 的尖峰' % A_L)
    log('    -> 【左发射管 L4 会发光，左接收管 D7 也灵】')
    log('    -> 此前"左路坏了"的结论是假象：那些测试里左对管正前方【从来没有放过东西】')
elif A_L <= 300 and A_R > 120:
    log('★ 结论：L4 会发光（手扫过左对管时 PF10 收到 %d 的串光），但 PF9 收不到 (%d)' % (A_R, A_L))
    log('    -> 【左接收管 D7 / 其 10K 上拉 有问题】')
elif A_L <= 300 and A_R <= 120:
    log('★ 结论：单独点亮 PE5 时两个接收管都无反应 (PF9=%d, PF10=%d)' % (A_L, A_R))
    log('    -> 【左发射管 L4 不发光】')
    log('    对照：Phase B 两次都正常的话，说明采样链路没问题，是 L4 支路的问题')
    log('    待查：Q2(SS8550) 是否贴装/虚焊、R25(100R) 是否虚焊、L4 本体是否开路')
else:
    log('? 数据不典型，见上表人工判读')

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
