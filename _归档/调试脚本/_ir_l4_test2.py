# -*- coding: utf-8 -*-
"""
_ir_l4_test2.py —— 带对照的严格判定：左发射管 L4 到底亮不亮

上一版测试只测了"L4 常亮对右路本底的影响"，是单向的，结论不够硬。
这一版做完整矩阵，而且每一步都有【对照组】：

     条件                        测左路本底(KEY1)   测右路本底(KEY2)
     ① 两个发射管都强制熄灭         A                  B
     ② 强制 PE5 拉低(L4 常亮)       C                  D
     ③ 强制 PE6 拉低(L5 常亮)       E                  F

判读：
  * F 是【对照组】：L5 已知在发光，且右对管前方现在有强反射物
    -> F 一定远小于 B。如果 F 没变小，说明测试方法本身不成立。
  * C 是【待测组】：把 L4 强行点亮，再看左接收管的本底。
    本底 = 测量时"发射管灭"那一次的读数；如果 L4 一直亮着，那么左接收管
    在这一步读到的就是"含 L4 反射"的值 -> 只要 L4 在发光，C 必然远小于 A。
      - C 明显 < A  -> L4 确实在发光，左路收发通路完好（之前 diff=0 是因为
                       左对管前方没有反射物）
      - C ≈ A       -> L4 没发光（或左对管前方完全没有反射物，
                       那么再结合 E 判断：E 若明显 < A，说明右发射管的光
                       能照到左接收管的视野 -> 前方其实有东西 -> 那就是 L4 坏了）

每格测 3 次取平均，减少抖动。
"""

import io
import struct
import time

from pyocd.core.helpers import ConnectHelper

LOG = io.open(r'D:\STM32_Project\_ir_l4_test2.log', 'w', encoding='utf-8', newline='\n')


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
    return (struct.unpack_from('<HHHBBB', blk, 0),
            struct.unpack_from('<HHHBBB', blk, S_IRR - S_IRL))


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
    time.sleep(0.45)


def force(port_pin, on):
    """开漏：BRR 写 1 = 拉低 = 亮；BSRR 写 1 = 高阻 = 灭"""
    t.halt()
    set_pin(GPIOE_CRL, port_pin, 0x7)
    t.write32(GPIOE_BRR if on else GPIOE_BSRR, 1 << port_pin)
    t.resume()
    time.sleep(0.03)


t.reset_and_halt()
time.sleep(0.1)
t.resume()
time.sleep(1.5)
log('  App 已启动，GPIOE_CRL=%08X' % t.read32(GPIOE_CRL))

log()
log('%-30s %-22s %-22s' % ('条件', '左路本底(KEY1)', '右路本底(KEY2)'))
log('-' * 78)

res = {}
for name, l_force, r_force in [('① 两灯都强制熄灭', None, None),
                               ('② 强制 PE5 拉低(L4 常亮)', True, False),
                               ('③ 强制 PE6 拉低(L5 常亮)', False, True)]:
    if l_force is not None:
        force(5, l_force)
        force(6, r_force)
    else:
        force(5, False)
        force(6, False)

    lds, rds = [], []
    for _ in range(3):
        press_key(3)                    # KEY1 -> 测左
        l, _ = read_app()
        lds.append(l[0])
        press_key(4)                    # KEY2 -> 测右
        _, r = read_app()
        rds.append(r[0])
    res[name] = (sum(lds) // len(lds), sum(rds) // len(rds))
    log('%-30s %-22s %-22s' % (name, 'dark=%d  (原始 %s)' % (res[name][0], lds),
                               'dark=%d  (原始 %s)' % (res[name][1], rds)))

# 还原
force(5, False)
force(6, False)

A, B = res['① 两灯都强制熄灭']
C, D = res['② 强制 PE5 拉低(L4 常亮)']
E, F = res['③ 强制 PE6 拉低(L5 常亮)']

log()
log('=' * 78)
log('  对照 F：右路本底  两灯灭 %d -> L5 常亮 %d   变化 %+d' % (B, F, F - B))
log('  待测 C：左路本底  两灯灭 %d -> L4 常亮 %d   变化 %+d' % (A, C, C - A))
log('  旁证 E：左路本底  两灯灭 %d -> L5 常亮 %d   变化 %+d' % (A, E, E - A))
log('  旁证 D：右路本底  两灯灭 %d -> L4 常亮 %d   变化 %+d' % (B, D, D - B))
log('=' * 78)

if F - B > -50:
    log('  ⚠ 对照组 F 没有变小（%+d）—— 右发射管测不出来本底变化，'
        '说明右对管前方此刻已经空了，本测试的前提（前方有强反射物）不成立，'
        '结论无效，需要重新摆位置再测。' % (F - B))
else:
    log('  ✔ 对照组 F 成立（%+d）：右路本底被 L5 明显压低，测试方法有效。' % (F - B))
    if C - A <= -50:
        log('  ✔ 结论：C 也明显变小（%+d）-> 【左发射管 L4 在正常发光】，'
            '左路收发通路完好；之前 diff=0 只是因为左对管前方没有反射物。' % (C - A))
    elif E - A <= -50:
        log('  ✘ 结论：L4 常亮时左路本底不变（%+d），但 L5 常亮却能压低它（%+d）'
            '-> 左对管前方是有东西的，可左发射管 L4 【没有发光】，'
            '左路发射管回路（L4 本体 / Q2 / R25）需要查硬件。' % (C - A, E - A))
    else:
        log('  ✘ 结论：L4、L5 都压不动左路本底（%+d / %+d）'
            '-> 左对管前方确实是空的；左发射管是否发光仍无法判定，'
            '需要在左对管正前方 2~3cm 放一个实物再复测。' % (C - A, E - A))

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
