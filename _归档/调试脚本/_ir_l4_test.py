# -*- coding: utf-8 -*-
"""
_ir_l4_test.py —— 自动判断【左发射管 L4 到底亮不亮】（不需要用户操作）

原理（串扰当探针）：
    右对管前方明显有东西（App 实测右路 diff≈226~231，而左路恒为 0）。
    两对对管在板上相邻，如果左发射管 L4 真的在发光，它的红外也会照到右对管
    前方那个物体上，于是【右接收管的"本底"读数】会被压低。

    做法：把 PE5（左发射管驱动）强行拉低 = L4 常亮，然后让 App 测右路
    （Ir_Measure(0) 只切右发射管，不会动 PE5），比较：
        基线右路本底（L4 灭）  vs  L4 常亮时的右路本底
    本底只受"灭灯时的环境光 + 别的灯串过来的光"影响，所以：
        本底明显下降  -> L4 在发光 ✔
        本底基本不变  -> L4 没发光（或它的光到不了那个物体）✘

为什么不用自己搓的 ADC 读取：
    自己写 SMPR/SQR/CR2 那套读出来恒为 66（连 PF7 参照都是 66），
    而 App 走标准库 ADC_RegularChannelConfig 读出来是对的（PF9=4091），
    所以统一改用"模拟按键 + 读 App 的 s_irL / s_irR"这条路，最可靠。
"""

import io
import struct
import time

from pyocd.core.helpers import ConnectHelper

LOG = io.open(r'D:\STM32_Project\_ir_l4_test.log', 'w', encoding='utf-8', newline='\n')


def log(m=''):
    print(m, flush=True)
    LOG.write(m + '\n')
    LOG.flush()


UID = '37FF71064E5734360B791543'
GPIOE_CRL = 0x40011800
GPIOE_BSRR = 0x40011810
GPIOE_BRR = 0x40011814
GPIOG_CRL = 0x40012000
GPIOG_BSRR = 0x40012010
GPIOG_BRR = 0x40012014

S_LINE3 = 0x20000045
S_IRL = 0x20000130
S_IRR = 0x2000013A

sess = ConnectHelper.session_with_chosen_probe(
    unique_id=UID, target_override='stm32f103ze', options={'connect_mode': 'halt'})
sess.open()
t = sess.target
log('=== 连接 %s %s ===' % (t.part_number, t.get_state()))


def set_pin(base, pin, val):
    sh = (pin if pin < 8 else pin - 8) * 4
    a = base + (0x04 if pin >= 8 else 0x00)
    t.write32(a, (t.read32(a) & ~(0xF << sh)) | ((val & 0xF) << sh))


def read_app():
    t.halt()
    try:
        blk = bytes(t.read_memory_block8(S_IRL, 26))
    finally:
        t.resume()
    l = struct.unpack_from('<HHHBBB', blk, 0)
    r = struct.unpack_from('<HHHBBB', blk, S_IRR - S_IRL)
    return l, r


def press_key(pin, hold=0.25):
    t.halt()
    set_pin(GPIOG_CRL, pin, 0x3)
    t.write32(GPIOG_BRR, 1 << pin)
    t.resume()
    time.sleep(hold)
    t.halt()
    t.write32(GPIOG_BSRR, 1 << pin)
    set_pin(GPIOG_CRL, pin, 0x8)
    t.resume()
    time.sleep(0.5)


# 复位重启 App
t.reset_and_halt()
time.sleep(0.1)
t.resume()
time.sleep(1.5)
log('  App 已启动，GPIOE_CRL=%08X（PE5/PE6 应为 7=开漏）' % t.read32(GPIOE_CRL))


def force_led(is_left, on):
    """把某一侧发射管强行常亮/熄灭（开漏：BRR=拉低=亮，BSRR=高阻=灭）"""
    t.halt()
    set_pin(GPIOE_CRL, 5 if is_left else 6, 0x7)
    t.write32(GPIOE_BRR if on else GPIOE_BSRR, 1 << (5 if is_left else 6))
    t.resume()
    time.sleep(0.05)


log()
log('=== 第 1 步：基线（两灯都灭，App 正常测右路）===')
for _ in range(2):
    press_key(4)                       # KEY2 = 测右侧
_, r = read_app()
base_r = r
log('  右路：dark=%d lit=%d diff=%d' % (r[0], r[1], r[2]))

log()
log('=== 第 2 步：把 PE5 拉低 = 左发射管 L4 常亮 -> 再让 App 测右路 ===')
force_led(True, True)
for _ in range(2):
    press_key(4)
_, r = read_app()
on_r = r
log('  右路：dark=%d lit=%d diff=%d' % (r[0], r[1], r[2]))
force_led(True, False)

log()
log('=== 第 3 步：对照 —— 把 PE6 拉低（右发射管常亮）-> 让 App 测左路 ===')
force_led(False, True)
for _ in range(2):
    press_key(3)                       # KEY1 = 测左侧
l, _ = read_app()
log('  左路：dark=%d lit=%d diff=%d' % (l[0], l[1], l[2]))
force_led(False, False)

log()
log('=' * 66)
log('右路本底对照（本底 = 灭灯时的读数，只反映环境光 + 别的灯串过来的光）')
log('  L4 灭：dark=%4d      L4 常亮：dark=%4d     变化 %+d'
    % (base_r[0], on_r[0], on_r[0] - base_r[0]))
log('=' * 66)
d = on_r[0] - base_r[0]
if d <= -10:
    log('  ✔ L4 常亮让右路本底下降 %d -> 【左发射管 L4 确实在发光】，'
        '它的光串到了右对管前方的物体上' % d)
elif d >= 10:
    log('  ? 本底反而升高 %d，可能是测量漂移，需要复测' % d)
else:
    log('  ✘ L4 常亮时右路本底几乎不变（%+d）-> 左发射管 L4 很可能【没有发光】，'
        '或它的光到不了右对管前方那个物体' % d)

t.halt()
set_pin(GPIOE_CRL, 5, 0x7)
set_pin(GPIOE_CRL, 6, 0x7)
t.write32(GPIOE_BSRR, (1 << 5) | (1 << 6))
t.reset_and_halt()
time.sleep(0.1)
t.resume()
sess.close()
log()
log('  已复位重启 App，探针已释放')
