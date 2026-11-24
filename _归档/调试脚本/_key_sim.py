# -*- coding: utf-8 -*-
"""通过 pyOCD 直接操作 GPIOG 寄存器，把 PG3(KEY1) 拉低来等价模拟一次按键。
按键在硬件上就是 PG3 -- 按键 -- GND，拉低 = 按下，电气上完全一致。"""
import sys
import time

from pyocd.core.helpers import ConnectHelper

UID = "37FF71064E5734360B791543"
GPIOG_CRL = 0x40012000      # PG0..PG7 配置寄存器
GPIOG_BSRR = 0x40012010     # 置位
GPIOG_BRR = 0x40012014      # 复位
PIN = 3                     # PG3 = KEY1
SHIFT = PIN * 4             # CRL 里 PG3 占 bit15..12
MASK = 0xF << SHIFT

PRESS_HOLD = 0.20           # 按下保持 200ms（消抖阈值 20ms，留足余量）
RELEASE_HOLD = 0.45         # 松开后等待，让主循环完成一次记录写入

N = int(sys.argv[1]) if len(sys.argv) > 1 else 1
# 第二个参数可选：按下保持多少毫秒。用来测"按住不放会不会反复触发"
# （固件是按下沿触发，长按应当只算一次单击）。
if len(sys.argv) > 2:
    PRESS_HOLD = float(sys.argv[2]) / 1000.0


def connect():
    last = None
    for mode in ("attach", "halt"):
        try:
            s = ConnectHelper.session_with_chosen_probe(
                unique_id=UID, target_override="stm32f103ze", connect_mode=mode)
            s.open()
            print("connected (connect_mode=%s)" % mode)
            return s
        except Exception as exc:                      # noqa: BLE001
            last = exc
            print("connect_mode=%s failed: %s" % (mode, exc))
    raise SystemExit("cannot connect: %s" % last)


session = connect()
target = session.target
try:
    crl0 = target.read32(GPIOG_CRL)
    print("GPIOG_CRL before = 0x%08X  (PG3 field = 0x%X)" % (crl0, (crl0 & MASK) >> SHIFT))

    # PG3 -> 通用推挽输出 50MHz：MODE=11 CNF=00 -> 0b0011
    crl_out = (crl0 & ~MASK) | (0x3 << SHIFT)

    for i in range(N):
        target.write32(GPIOG_CRL, crl_out)            # 切成输出
        target.write32(GPIOG_BRR, 1 << PIN)           # 拉低 -> 按下
        time.sleep(PRESS_HOLD)
        target.write32(GPIOG_BSRR, 1 << PIN)          # 拉高 -> 松开
        time.sleep(RELEASE_HOLD)
        print("key1 press #%d done" % (i + 1))

    target.write32(GPIOG_CRL, crl0)                   # 还原成原来的输入配置
    print("GPIOG_CRL restored = 0x%08X" % target.read32(GPIOG_CRL))
finally:
    session.close()
    print("closed")
