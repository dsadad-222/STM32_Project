# -*- coding: utf-8 -*-
"""把片内状态页里的 STORE_BIT_RIGHT 清掉，让复位后不再自动闪右转向灯。

只改 flags 字段，文本 / 标定值原样保留，校验和按固件算法（前 46 字节累加和）重算。

⚠ attach 模式下直接编程会踩 HardFault（IPSR=3）：固件还在跑，SysTick 中断打断了
  闪存算法。必须先 reset_and_halt 把固件停住再写。
⚠ 写完还要再复位一次 —— 否则固件 RAM 里那份 s_rightTurnOn 还是开机时从旧内容
  恢复的 1，灯会继续闪到下次复位。
"""
import struct

from pyocd.core.helpers import ConnectHelper
from pyocd.flash.loader import FlashLoader

ADDR = 0x0807F800
MAGIC = 0x5A5AA5A5


def u32(b, off):
    return struct.unpack_from('<I', b, off)[0]


def u16(b, off):
    return struct.unpack_from('<H', b, off)[0]


s = ConnectHelper.session_with_chosen_probe(
    unique_id='37FF71064E5734360B791543',
    target_override='stm32f103ze',
    connect_mode='halt',                 # 停住内核再操作，避开固件中断
    options={'auto_unlock': False},
    blocking=False)
if s is None:
    raise SystemExit('没有可用探针')

with s:
    t = s.target
    t.reset_and_halt()

    rec = bytearray(t.read_memory_block8(ADDR, 48))
    print('改前: magic=0x%08X flags=0x%08X cks=0x%04X' % (u32(rec, 0), u32(rec, 4), u16(rec, 46)))
    if u32(rec, 0) != MAGIC:
        raise SystemExit('魔数不是 0x5A5AA5A5，状态页为空，无需修改')

    struct.pack_into('<I', rec, 4, 0x00000000)
    struct.pack_into('<H', rec, 46, sum(rec[0:46]) & 0xFFFF)
    print('待写: magic=0x%08X flags=0x%08X cks=0x%04X' % (u32(rec, 0), u32(rec, 4), u16(rec, 46)))

    flm = FlashLoader(s)
    flm.add_data(ADDR, bytes(rec))
    flm.commit()
    flm.uninit()

    back = bytes(t.read_memory_block8(ADDR, 48))
    print('回读: magic=0x%08X flags=0x%08X cks=0x%04X  逐字节一致=%s'
          % (u32(back, 0), u32(back, 4), u16(back, 46), back == bytes(rec)))

    t.reset()                            # 再复位一次，让固件按新状态重新开机
    print('已复位，固件按 flags=0 重新启动')
