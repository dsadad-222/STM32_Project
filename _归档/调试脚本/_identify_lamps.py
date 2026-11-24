# -*- coding: utf-8 -*-
"""灯珠物理对应测试：左灯珠只亮红(PG1)、右灯珠只亮绿(PE3)，其余全灭，保持不动。

目的：让用户一眼看出"最顶上那两颗灯"分别由哪个引脚驱动，确认引脚定义没搞错。
先把各服务状态清干净（转向灯/报警/呼吸），否则它们会把引脚改回去。
"""
import time
from pyocd.core.helpers import ConnectHelper

UID = "37FF71064E5734360B791543"
GPIOG_BSRR, GPIOG_ODR = 0x40012010, 0x4001200C
GPIOE_BSRR, GPIOE_ODR = 0x40011810, 0x4001180C

# 状态变量地址（取自 FlashRW_Full.map）
S_LEFT_TURN, S_RIGHT_TURN = 0x20000014, 0x20000015
S_LED_ON, S_ALERT_KIND = 0x20000017, 0x20000046
S_BREATH_ACTIVE, S_RGB_MASK = 0x200000AA, 0x200000B4

sess = ConnectHelper.session_with_chosen_probe(
    unique_id=UID, target_override="stm32f103ze", connect_mode="attach",
    options={"frequency": 1000000})
sess.open()
t = sess.target

print("清场前状态：")
print("  s_leftTurnOn=%d  s_rightTurnOn=%d  s_ledOn=%d  s_alertKind=%d"
      % (t.read8(S_LEFT_TURN), t.read8(S_RIGHT_TURN), t.read8(S_LED_ON),
         t.read8(S_ALERT_KIND)))
print("  呼吸灯 s_active=%d  s_rgbMask=0x%02X" % (t.read8(S_BREATH_ACTIVE),
                                                 t.read8(S_RGB_MASK)))

# 关掉所有会写灯珠的服务
t.write8(S_LEFT_TURN, 0)
t.write8(S_RIGHT_TURN, 0)
t.write8(S_ALERT_KIND, 0)
t.write8(S_BREATH_ACTIVE, 0)     # 呼吸停止
t.write8(S_RGB_MASK, 0)          # ISR 里 if(mask) 不成立 -> 不再写 RGB 引脚
time.sleep(0.2)

# 全灭：清 PG1/PG2/PG12/PG14/PG15 与 PE2/PE3/PE4/PE7
t.write32(GPIOG_BSRR, (1 << (16 + 1)) | (1 << (16 + 2)) | (1 << (16 + 12))
          | (1 << (16 + 14)) | (1 << (16 + 15)))
t.write32(GPIOE_BSRR, (1 << (16 + 2)) | (1 << (16 + 3)) | (1 << (16 + 4))
          | (1 << (16 + 7)))
time.sleep(0.15)

# 只点亮：左灯珠红(PG1) + 右灯珠绿(PE3)
t.write32(GPIOG_BSRR, (1 << 1))       # PG1 = 左灯珠 红
t.write32(GPIOE_BSRR, (1 << 3))       # PE3 = 右灯珠 绿
time.sleep(0.15)

g = t.read32(GPIOG_ODR)
e = t.read32(GPIOE_ODR)
b = lambda v, n: (v >> n) & 1
print("\n已设置（保持不动）：")
print("  GPIOG_ODR = 0x%08X  ->  PG1(左灯珠红)=%d  PG2=%d  PG14=%d  PG15=%d"
      % (g, b(g, 1), b(g, 2), b(g, 14), b(g, 15)))
print("  GPIOE_ODR = 0x%08X  ->  PE2=%d  PE3(右灯珠绿)=%d  PE4=%d  PE7=%d"
      % (e, b(e, 2), b(e, 3), b(e, 4), b(e, 7)))
sess.close()
print("\n请用户观察板子：应该 左边那颗亮【红】、右边那颗亮【绿】。")
