# -*- coding: utf-8 -*-
"""
_ir_thr_check.py —— 验证【新门限】是否已生效（只跑 Part B，不碰 ADC 寄存器）

判据：空旷环境下右路 diff 约 226~231。
      旧门限 IR_DIFF_MID=200 -> 会判 MID
      新门限 IR_DIFF_MID=600 -> 应判 FAR
      所以只要 KEY2/KEY3 后右路 level==FAR，就证明新固件在跑。

顺带把 app 里所有相关符号都读出来，方便对照。
"""

import io
import struct
import time

from pyocd.core.helpers import ConnectHelper

UID = '37FF71064E5734360B791543'
LOG = io.open(r'D:\STM32_Project\_ir_thr_check.log', 'w', encoding='utf-8', newline='\n')


def log(m=''):
    print(m, flush=True)
    LOG.write(m + '\n')
    LOG.flush()


GPIOG_CRL = 0x40012000
GPIOG_CRH = 0x40012004
GPIOG_BSRR = 0x40012010
GPIOG_BRR = 0x40012014

S_LINE3 = 0x20000045      # s_line3Mode / s_irLeft / s_irRight / valid 标志
S_MSG = 0x200000E0        # SetMessage 缓冲区 (17B)
S_IRL = 0x20000130        # IrResult_t s_irL  (10B)
S_IRR = 0x2000013A        # IrResult_t s_irR
LEVEL = {0: 'FAR ', 1: 'MID ', 2: 'NEAR'}

sess = ConnectHelper.session_with_chosen_probe(
    unique_id=UID, target_override='stm32f103ze',
    options={'connect_mode': 'halt'})
sess.open()
t = sess.target
log('=== %s  %s ===' % (t.part_number, t.get_state()))


def set_pin(port_base, pin, val):
    a = port_base + (0x04 if pin >= 8 else 0x00)
    sh = (pin - 8 if pin >= 8 else pin) * 4
    cur = t.read32(a)
    t.write32(a, (cur & ~(0xF << sh)) | ((val & 0xF) << sh))


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
    t.halt()
    set_pin(GPIOG_CRL if pin < 8 else GPIOG_CRH, pin, 0x3)
    t.write32(GPIOG_BRR, 1 << pin)
    t.resume()
    time.sleep(hold)
    t.halt()
    t.write32(GPIOG_BSRR, 1 << pin)
    set_pin(GPIOG_CRL if pin < 8 else GPIOG_CRH, pin, 0x8)
    t.resume()
    time.sleep(0.45)


def show(tag):
    flg, l, r, msg = read_app()
    log('  [%-16s] mode=%d  Lvalid=%d Rvalid=%d  msg="%s"'
        % (tag, flg[0], flg[3], flg[4], msg))
    log('        L: dark=%4d lit=%4d diff=%4d  level=%s strength=%3d valid=%d'
        % (l[0], l[1], l[2], LEVEL.get(l[3], '?'), l[4], l[5]))
    log('        R: dark=%4d lit=%4d diff=%4d  level=%s strength=%3d valid=%d'
        % (r[0], r[1], r[2], LEVEL.get(r[3], '?'), r[4], r[5]))
    return l, r


log()
log('### 复位 App，等启动 ###')
t.reset_and_halt()
time.sleep(0.1)
t.resume()
time.sleep(1.6)
show('复位基线')

log()
log('### 模拟按键 ###')
for pin, name in [(3, 'KEY1 测左侧'), (4, 'KEY2 测右侧'), (5, 'KEY3 左右都测')]:
    log()
    log('  >>> %s' % name)
    press_key(pin)
    show(name)

log()
log('### 判据 ###')
_, l, r = show('末次')
ok = True
if r[5] == 1 and r[2] < 600 and r[3] == 0:
    log('  OK  右路 diff=%d < 600 且判 FAR -> 【新门限已生效】' % r[2])
elif r[5] == 1 and r[3] == 1:
    log('  ★★ 右路 diff=%d 判 MID -> 说明跑的还是【旧门限 200】的固件！' % r[2])
else:
    log('  ?   右路 diff=%d level=%s，请人工判读' % (r[2], LEVEL.get(r[3], '?')))

t.halt()
t.write32(GPIOG_BSRR, (1 << 3) | (1 << 4) | (1 << 5))
t.reset_and_halt()
time.sleep(0.1)
t.resume()
sess.close()
log()
log('  已复位，探针释放')
