# -*- coding: utf-8 -*-
"""复位并放行内核，然后连续采样右侧灯珠与板载小灯，确认复位后不再自动闪右转向灯。"""
import struct
import time

from pyocd.core.helpers import ConnectHelper

GPIOG_ODR = 0x4001200C
GPIOE_ODR = 0x4001180C
STATE = 0x0807F800


def u32(t, addr):
    return struct.unpack('<I', bytes(t.read_memory_block8(addr, 4)))[0]


s = ConnectHelper.session_with_chosen_probe(
    unique_id='37FF71064E5734360B791543',
    target_override='stm32f103ze',
    connect_mode='attach',
    options={'auto_unlock': False},
    blocking=False)
if s is None:
    raise SystemExit('没有可用探针')

with s:
    t = s.target

    # 先读一次状态页
    magic = u32(t, STATE)
    flags = u32(t, STATE + 4)
    print('状态页 magic=0x%08X flags=0x%08X  -> %s'
          % (magic, flags,
             '空（按默认状态开机，全灭）' if magic != 0x5A5AA5A5 else '有效'))

    # 复位并放行，让固件从头跑
    t.reset()
    time.sleep(2.5)                       # 等开机横幅 + 自检跑完

    print('\n复位后采样 2.0 秒（每 50ms 一次）：')
    print('  时刻    PE2(右灯红)  PG14(LED1)  PG15(LED2)  PG1(左灯红)')
    seen = {'PE2': set(), 'PG14': set(), 'PG15': set(), 'PG1': set()}
    for i in range(40):
        t.halt()
        g = u32(t, GPIOG_ODR)
        e = u32(t, GPIOE_ODR)
        t.resume()
        pe2 = (e >> 2) & 1
        pg14 = (g >> 14) & 1
        pg15 = (g >> 15) & 1
        pg1 = (g >> 1) & 1
        seen['PE2'].add(pe2)
        seen['PG14'].add(pg14)
        seen['PG15'].add(pg15)
        seen['PG1'].add(pg1)
        if i % 5 == 0:
            print('  %4.2fs      %d           %d           %d           %d'
                  % (i * 0.05, pe2, pg14, pg15, pg1))
        time.sleep(0.05)

    print('\n结果：')
    for name, vals in seen.items():
        state = '恒定 %d（不闪）' % list(vals)[0] if len(vals) == 1 else '在 %s 之间翻转（在闪！）' % sorted(vals)
        print('  %-16s %s' % (name, state))
    print('\n判定：%s' % ('右转向灯已不再自动闪' if len(seen['PE2']) == 1 and len(seen['PG15']) == 1
                        else '仍有灯在闪，需继续排查'))
