# -*- coding: utf-8 -*-
"""采样左/右灯珠 ODR。

寄存器偏移（STM32F1 GPIO）：
    0x00 CRL  0x04 CRH  0x08 IDR  0x0C ODR  0x10 BSRR  0x14 BRR  0x18 LCKR
⚠ 上一版把 ODR 写成 0x14（那是 BRR，只写寄存器，读永远 0），所以看到"全 0"。

DHCSR @ 0xE000EDF0：
    bit0 C_DEBUGEN（调试使能，接上调试器就是 1，不代表 halt）
    bit1 C_HALT    bit2 C_STEP    bit17 S_HALT（=1 才是内核真的停住了）
"""
import time
from pyocd.core.helpers import ConnectHelper

UID = "37FF71064E5734360B791543"
DHCSR = 0xE000EDF0
GPIOG_ODR = 0x4001200C
GPIOE_ODR = 0x4001180C
GPIOG_CRL = 0x40012000
GPIOE_CRL = 0x40011800

sess = ConnectHelper.session_with_chosen_probe(
    unique_id=UID, target_override="stm32f103ze", connect_mode="attach",
    options={"frequency": 1000000})
sess.open()
t = sess.target

dh = t.read32(DHCSR)
running = ((dh >> 17) & 1) == 0
print("DHCSR = 0x%08X  C_DEBUGEN=%d C_HALT=%d S_HALT=%d  ->  内核%s"
      % (dh, dh & 1, (dh >> 1) & 1, (dh >> 17) & 1,
         "在运行" if running else "被 halt 住了"))
if not running:
    t.resume()
    time.sleep(0.3)
    print("已 resume，DHCSR = 0x%08X" % t.read32(DHCSR))

print("\nGPIOG_CRL = 0x%08X   GPIOE_CRL = 0x%08X" % (t.read32(GPIOG_CRL), t.read32(GPIOE_CRL)))
print("PG1=左灯珠红  PG2=左灯珠蓝  PG14/15=板载LED1/2  |  PE2/3/4=右灯珠  PE7=左灯珠绿")
print(" %-4s %-12s %-12s %s" % ("#", "GPIOG_ODR", "GPIOE_ODR", "PG1 PG2 PG14 PG15 | PE2 PE3 PE4 PE7"))

pg1, pg15, pe2 = [], [], []
b = lambda v, n: (v >> n) & 1
for i in range(20):
    g = t.read32(GPIOG_ODR)
    e = t.read32(GPIOE_ODR)
    pg1.append(b(g, 1)); pg15.append(b(g, 15)); pe2.append(b(e, 2))
    print(" %-4d 0x%08X   0x%08X    %d   %d    %d    %d   |  %d   %d   %d   %d"
          % (i, g, e, b(g, 1), b(g, 2), b(g, 14), b(g, 15),
             b(e, 2), b(e, 3), b(e, 4), b(e, 7)))
    time.sleep(0.12)

print("\nPG1 （左灯珠红）序列:", "".join(map(str, pg1)))
print("PG15（板载LED2）序列:", "".join(map(str, pg15)))
print("PE2 （右灯珠红）序列:", "".join(map(str, pe2)))
for name, seq in (("左灯珠红 PG1", pg1), ("板载LED2 PG15", pg15), ("右灯珠红 PE2", pe2)):
    print("  %-16s %s" % (name, "在翻转 ✅" if len(set(seq)) > 1
                          else ("恒为 1（常亮）" if seq[0] else "恒为 0（没动）")))
sess.close()
