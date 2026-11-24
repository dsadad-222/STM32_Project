# -*- coding: utf-8 -*-
"""
_app_ir_read.py —— 直接读 App 自己算出来的红外结果（走的就是交付路径：按键 -> 测量 -> 显示）

为什么不靠串口：
    板载 USB-TTL 要插上扬声器的 USB 线才有 COM 口；而 App 测量的结果本来就存在
    RAM 里（符号地址从 Keil 的 .map 里查），用调试器直接读出来即可，
    这样验证的是【固件真实行为】，而不是"另写一段测试代码"。

符号（from Listings/IrAvoid_Full.map，改代码后地址会变，脚本会先自检）：
    s_irL = 0x20000130   IrResult_t 左路
    s_irR = 0x2000013A   IrResult_t 右路
    IrResult_t 布局：dark(u16) lit(u16) diff(u16) level(u8) strength(u8) valid(u8)

读法：每 150ms 一次 halt -> 块读 32 字节 -> resume，避免长时间停核影响按键扫描
（按键消抖 20ms 级，1ms 级暂停不会漏按键）。

用法：python _app_ir_read.py [监听秒数]
"""

import io
import struct
import sys
import time

from pyocd.core.helpers import ConnectHelper

UID = '37FF71064E5734360B791543'

ADDR_L, ADDR_R = 0x20000130, 0x2000013A
ADDR_FLAGS = 0x20000045           # s_line3Mode, s_irLeft, s_irRight, vL, vR (5 字节)

LEVEL_WORD = {0: 'FAR ', 1: 'MID ', 2: 'NEAR'}

SECS = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0

LOG = io.open(r'D:\STM32_Project\_app_ir_read.log', 'w', encoding='utf-8', newline='\n')


def log(m=''):
    print(m, flush=True)
    LOG.write(m + '\n')
    LOG.flush()


log('=== 连接（halt 模式；读的时候停一下再放开，App 继续跑）===')
sess = ConnectHelper.session_with_chosen_probe(
    unique_id=UID, target_override='stm32f103ze',
    options={'connect_mode': 'halt'})
sess.open()
t = sess.target
log('  %s  %s' % (t.part_number, t.get_state()))
t.resume()                      # 让 App 跑起来，按键才有用


def read_state():
    """停一下 -> 读 -> 放开；返回 (left, right, flags)"""
    t.halt()
    try:
        blk = bytes(t.read_memory_block8(ADDR_L, 26))   # 两路 + 中间空隙一起读回
        flg = bytes(t.read_memory_block8(ADDR_FLAGS, 5))
    finally:
        t.resume()
    l = struct.unpack_from('<HHHBBB', blk, 0)
    r = struct.unpack_from('<HHHBBB', blk, ADDR_R - ADDR_L)
    return l, r, flg


log()
log('=== 先自检符号地址：打印当前 RAM 内容 ===')
l, r, flg = read_state()
log('  s_line3Mode=%d s_irLeft=%d s_irRight=%d vL=%d vR=%d'
    % (flg[0], flg[1], flg[2], flg[3], flg[4]))
log('  s_irL: dark=%d lit=%d diff=%d level=%d(%s) strength=%d valid=%d'
    % (l[0], l[1], l[2], l[3], LEVEL_WORD.get(l[3], '?'), l[4], l[5]))
log('  s_irR: dark=%d lit=%d diff=%d level=%d(%s) strength=%d valid=%d'
    % (r[0], r[1], r[2], r[3], LEVEL_WORD.get(r[3], '?'), r[4], r[5]))
if l[0] > 4096 or r[0] > 4096:
    log('  ★ 有字段超出 12 位范围，说明 .map 里的符号地址已经变了（改过代码），'
        '请重新从 Listings/IrAvoid_Full.map 查 s_irL / s_irR 地址')
    sess.close()
    sys.exit(1)

log()
log('=== 开始监听 %.0f 秒：请按 KEY1 / KEY2 / KEY3，我会把变化打出来 ===' % SECS)
log('    KEY1=测左侧   KEY2=测右侧   KEY3=左右都测并打串口')

prev = None
t0 = time.time()
n = 0
try:
    while time.time() - t0 < SECS:
        l, r, flg = read_state()
        key = (l, r, flg)
        if key != prev:
            n += 1
            log('[%6.1fs] #%d  L: dark=%4d lit=%4d diff=%4d level=%s valid=%d | '
                'R: dark=%4d lit=%4d diff=%4d level=%s valid=%d  (mode=%d L=%d R=%d)'
                % (time.time() - t0, n,
                   l[0], l[1], l[2], LEVEL_WORD.get(l[3], '?'), l[5],
                   r[0], r[1], r[2], LEVEL_WORD.get(r[3], '?'), r[5],
                   flg[0], flg[1], flg[2]))
            prev = key
        time.sleep(0.15)
except KeyboardInterrupt:
    pass

log()
log('监听结束（App 未被停核，仍在正常运行）')
sess.close()
