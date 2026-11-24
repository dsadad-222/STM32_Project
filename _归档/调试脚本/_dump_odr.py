# -*- coding: utf-8 -*-
import time
from pyocd.core.helpers import ConnectHelper
sess = ConnectHelper.session_with_chosen_probe(
    unique_id="37FF71064E5734360B791543", target_override="stm32f103ze",
    connect_mode="attach", options={"frequency": 1000000})
sess.open(); t = sess.target
print("CRL: G=0x%08X  E=0x%08X" % (t.read32(0x40012000), t.read32(0x40011800)))
print(" %-3s %-12s %-12s %s" % ("#", "GPIOG_ODR", "GPIOE_ODR", "PG1 PG2 PE7 | PG14 PG15 | PE2 PE3 PE4"))
b = lambda v,n:(v>>n)&1
for i in range(12):
    g = t.read32(0x4001200C); e = t.read32(0x4001180C)
    print(" %-3d 0x%08X   0x%08X    %d   %d   %d  |  %d    %d   |  %d   %d   %d"
          % (i, g, e, b(g,1), b(g,2), b(e,7), b(g,14), b(g,15), b(e,2), b(e,3), b(e,4)))
    time.sleep(0.15)
sess.close()
