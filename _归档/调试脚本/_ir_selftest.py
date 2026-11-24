# -*- coding: utf-8 -*-
"""
_ir_selftest.py —— 不依赖用户操作的自动化验收

分两部分：

A. 把"PF9 的 ADC 读数 vs 数字电平"这个矛盾查清
   同一个引脚，用两条完全独立的路径各测一次：
     路径① ADC3 读模拟值（配成 AIN）
     路径② 配成浮空输入读 IDR 的数字电平
   再拿 PF7(BAT)、PF8(LIGHT) 两个已知中间电压的引脚当"标尺"，
   验证 ADC3 的通道映射与读取流程本身对不对。
   如果标尺准、PF9 两条路径还打架，那就是 PF9 这个网络本身有问题。

B. 用 SWD 模拟按键，走真实交付路径
   按键驱动是【轮询 + 20ms 消抖 + 按下沿触发】，所以把 PG3/PG4/PG5
   临时配成推挽输出拉低 250ms 再放开，就等价于一次真实点击。
   点完之后直接读 App 算出来的 s_irL / s_irR / s_msg，验收整条链路。

符号地址（from Listings/IrAvoid_Full.map）：
    s_line3Mode 0x20000045  s_irLeft 0x46  s_irRight 0x47  vL 0x48  vR 0x49
    s_msg       0x200000E0 (17B)
    s_irL       0x20000130 (10B)  s_irR 0x2000013A (10B)
    IrResult_t: dark(u16) lit(u16) diff(u16) level(u8) strength(u8) valid(u8)
"""

import io
import struct
import sys
import time

from pyocd.core.helpers import ConnectHelper

UID = '37FF71064E5734360B791543'
LOG = io.open(r'D:\STM32_Project\_ir_selftest.log', 'w', encoding='utf-8', newline='\n')


def log(m=''):
    print(m, flush=True)
    LOG.write(m + '\n')
    LOG.flush()


RCC_APB2ENR = 0x40021018
RCC_CFGR    = 0x40021004
GPIOE_CRL   = 0x40011800
GPIOE_IDR   = 0x40011808
GPIOE_BSRR  = 0x40011810
GPIOF_CRL   = 0x40011C00
GPIOF_CRH   = 0x40011C04
GPIOF_IDR   = 0x40011C08
GPIOG_CRL   = 0x40012000
GPIOG_CRH   = 0x40012004
GPIOG_IDR   = 0x40012008
GPIOG_BSRR  = 0x40012010
GPIOG_BRR   = 0x40012014

ADC3 = 0x40013C00
ADC_SR, ADC_CR1, ADC_CR2, ADC_SMPR1, ADC_SMPR2, ADC_SQR3, ADC_DR = (
    0x00, 0x04, 0x08, 0x0C, 0x10, 0x34, 0x4C)

sess = ConnectHelper.session_with_chosen_probe(
    unique_id=UID, target_override='stm32f103ze',
    options={'connect_mode': 'halt'})
sess.open()
t = sess.target
log('=== 连接 %s %s ===' % (t.part_number, t.get_state()))


def nib(pin):
    return (pin if pin < 8 else pin - 8) * 4, (pin >= 8)


def addr_of(port_base, pin):
    return port_base + (0x04 if pin >= 8 else 0x00), nib(pin)[0]


def set_pin(port_base, pin, val):
    a, sh = addr_of(port_base, pin)
    cur = t.read32(a)
    t.write32(a, (cur & ~(0xF << sh)) | ((val & 0xF) << sh))


def idr_hi_ratio(pin, n=200, port_idr=GPIOF_IDR):
    hi = 0
    for _ in range(n):
        hi += (t.read32(port_idr) >> pin) & 1
    return hi * 100 // n


# ======================================================================
# A. ADC3 通道映射 + PF9 矛盾排查
# ======================================================================
log()
log('### A. ADC3 通道映射与 PF9 排查 ###')

# 让 App 跑一下再停，保证时钟/GPIO 是固件配好的状态 —— 这里直接自己配，避免依赖
t.write32(RCC_APB2ENR, t.read32(RCC_APB2ENR) | (1 << 6) | (1 << 7) | (1 << 8) | (1 << 15))
t.write32(RCC_CFGR, (t.read32(RCC_CFGR) & ~(3 << 14)) | (2 << 14))   # ADCPRE=/6

# 发射管先全灭
set_pin(GPIOE_CRL, 5, 0x7)
set_pin(GPIOE_CRL, 6, 0x7)
t.write32(GPIOE_BSRR, (1 << 5) | (1 << 6))

# 把 PF6..PF10 全配成模拟输入
for p in (6, 7, 8, 9, 10):
    set_pin(GPIOF_CRL if p < 8 else GPIOF_CRH, p, 0x0)
log('  GPIOF_CRL=%08X GPIOF_CRH=%08X' % (t.read32(GPIOF_CRL), t.read32(GPIOF_CRH)))

# ADC3 初始化
t.write32(ADC3 + ADC_CR1, 0)
t.write32(ADC3 + ADC_CR2, 1)                    # ADON
time.sleep(0.02)
t.write32(ADC3 + ADC_CR2, 1 | (1 << 3))
_r1 = 0
for _ in range(2000):
    if not (t.read32(ADC3 + ADC_CR2) & (1 << 3)):
        break
    _r1 += 1
t.write32(ADC3 + ADC_CR2, 1 | (1 << 2))
_r2 = 0
for _ in range(2000):
    if not (t.read32(ADC3 + ADC_CR2) & (1 << 2)):
        break
    _r2 += 1
log('  校准：RSTCAL 等 %d 次、CAL 等 %d 次（都应为 0~1，大就是时钟没起）' % (_r1, _r2))

# ch4..ch8 的采样时间设成 7（239.5 周期）
# ★★ 关键坑：STM32F1 的 SMPR1 是【通道 10~17】的采样时间，SMPR2 才是【通道 0~9】！
#    写错寄存器 -> 通道 4~8 保持复位值 0（1.5 周期）-> 10K 源阻抗下采样电容根本充不满
#    -> 读回来是个固定的垃圾值（实测恒为 66），而且各通道一模一样。
smpr2 = t.read32(ADC3 + ADC_SMPR2)
for ch in range(4, 9):
    smpr2 = (smpr2 & ~(0x7 << (ch * 3))) | (0x7 << (ch * 3))
t.write32(ADC3 + ADC_SMPR2, smpr2)
t.write32(ADC3 + ADC_SQR3, 0)
log('  ADC3 CR2=%08X SMPR1=%08X SMPR2=%08X（ch4~8 应为 7）'
    % (t.read32(ADC3 + ADC_CR2), t.read32(ADC3 + ADC_SMPR1), t.read32(ADC3 + ADC_SMPR2)))

SPINS = [0]


def adc_conv(ch):
    sqr3 = t.read32(ADC3 + ADC_SQR3)
    t.write32(ADC3 + ADC_SQR3, (sqr3 & ~0x1F) | ch)
    time.sleep(0.002)                     # 等 SQR3 生效
    t.write32(ADC3 + ADC_CR2, t.read32(ADC3 + ADC_CR2) | (1 << 22))   # SWSTART
    n = 0
    while n < 200:
        if t.read32(ADC3 + ADC_SR) & 0x02:   # EOC
            break
        n += 1
    SPINS[0] += n
    return t.read32(ADC3 + ADC_DR) & 0x0FFF


def adc_avg(ch, n=8):
    adc_conv(ch)        # 丢首次（切通道后采样保持电容还没稳）
    adc_conv(ch)
    tot = 0
    for _ in range(n):
        tot += adc_conv(ch)
    return tot // n


log()
log('  通道映射标尺（PF6/IN4、PF7/IN5、PF8/IN6、PF9/IN7、PF10/IN8）：')
refs = {}
for ch, name, expect in [(4, 'PF6(CCD-AO)', '~3000'), (5, 'PF7(BAT)', '~650'),
                         (6, 'PF8(LIGHT)', '~2200'), (7, 'PF9(左接收)', '~4080'),
                         (8, 'PF10(右接收)', '~4040')]:
    v = adc_avg(ch)
    refs[name] = v
    log('    ch%d  %-12s = %4d   (期望 %s)' % (ch, name, v, expect))
log('  EOC 轮询累计空转 %d 次（越接近 0 越好）' % SPINS[0])

log()
log('  同一批引脚改用【浮空输入】读数字电平（0x4），与 ADC 结果对照：')
for p, name in [(6, 'PF6'), (7, 'PF7'), (8, 'PF8'), (9, 'PF9'), (10, 'PF10')]:
    set_pin(GPIOF_CRL if p < 8 else GPIOF_CRH, p, 0x4)
time.sleep(0.05)
for p, name in [(6, 'PF6'), (7, 'PF7'), (8, 'PF8'), (9, 'PF9'), (10, 'PF10')]:
    r = idr_hi_ratio(p)
    v = refs.get(name + ('(CCD-AO)' if p == 6 else '(BAT)' if p == 7
                         else '(LIGHT)' if p == 8 else '(左接收)' if p == 9 else '(右接收)'))
    mv = (v * 3300) // 4096 if v is not None else -1
    log('    %-5s  IDR 高占比=%3d%%   ADC=%4d (≈%4d mV)  %s'
        % (name, r, v if v is not None else -1, mv,
           '一致' if ((r > 50) == (mv > 1650)) else '★ 不一致'))

# ======================================================================
# B. 模拟按键，验证真实交付路径
# ======================================================================
log()
log('### B. 模拟按键（PG3/PG4/PG5 拉低 250ms），验证 App 真实行为 ###')

S_LINE3 = 0x20000045
S_MSG = 0x200000E0
S_IRL = 0x20000130
S_IRR = 0x2000013A
LEVEL = {0: 'FAR ', 1: 'MID ', 2: 'NEAR'}


def read_app():
    t.halt()
    try:
        flg = bytes(t.read_memory_block8(S_LINE3, 5))
        msg = bytes(t.read_memory_block8(S_MSG, 17))
        blk = bytes(t.read_memory_block8(S_IRL, 26))
    finally:
        t.resume()
    l = struct.unpack_from('<HHHBBB', blk, 0)
    r = struct.unpack_from('<HHHBBB', blk, S_IRR - S_IRL)
    txt = msg.split(b'\x00')[0].decode('ascii', 'replace')
    return flg, l, r, txt


def press_key(pin, hold=0.25):
    """把 PG<pin> 拉低 hold 秒再放开 = 一次真实单击"""
    t.halt()
    set_pin(GPIOG_CRL if pin < 8 else GPIOG_CRH, pin, 0x3)   # 推挽输出
    t.write32(GPIOG_BRR, 1 << pin)                          # 拉低
    t.resume()
    time.sleep(hold)
    t.halt()
    t.write32(GPIOG_BSRR, 1 << pin)                          # 先放高
    set_pin(GPIOG_CRL if pin < 8 else GPIOG_CRH, pin, 0x8)   # 还原成上拉输入
    t.resume()
    time.sleep(0.45)


def show(tag):
    flg, l, r, msg = read_app()
    log('  [%s] mode=%d msg="%s"' % (tag, flg[0], msg))
    log('        L: dark=%4d lit=%4d diff=%4d level=%s strength=%3d valid=%d'
        % (l[0], l[1], l[2], LEVEL.get(l[3], '?'), l[4], l[5]))
    log('        R: dark=%4d lit=%4d diff=%4d level=%s strength=%3d valid=%d'
        % (r[0], r[1], r[2], LEVEL.get(r[3], '?'), r[4], r[5]))


# 复位重启 App，等它初始化完（含启动横幅）
t.reset_and_halt()
time.sleep(0.1)
t.resume()
time.sleep(1.5)
show('复位后基线')

for pin, name in [(3, 'KEY1=测左侧'), (4, 'KEY2=测右侧'), (5, 'KEY3=左右都测')]:
    log()
    log('  >>> 模拟按 %s' % name)
    press_key(pin)
    show(name)

log()
log('### 收尾 ###')
t.halt()
t.write32(ADC3 + ADC_CR2, 0)
t.write32(GPIOE_BSRR, (1 << 5) | (1 << 6))
t.reset_and_halt()
time.sleep(0.1)
t.resume()
sess.close()
log('  已复位重启 App，探针已释放')
