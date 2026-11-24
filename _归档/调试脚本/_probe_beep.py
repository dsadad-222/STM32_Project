# -*- coding: utf-8 -*-
"""读 GPIOG_ODR 看蜂鸣器位 PG12（Buzzer）是否被拉高。"""
import time
from pyocd.core.helpers import ConnectHelper

sess = ConnectHelper.session_with_chosen_probe(
    unique_id="37FF71064E5734360B791543", target_override="stm32f103ze",
    connect_mode="attach", options={"frequency": 1000000})
sess.open()
t = sess.target
print("GPIOG_ODR 采样（bit12 = PG12 = 蜂鸣器）")
for i in range(8):
    v = t.read32(0x4001200C)
    print("  #%d 0x%08X   PG12=%d" % (i, v, (v >> 12) & 1))
    time.sleep(0.08)
sess.close()
