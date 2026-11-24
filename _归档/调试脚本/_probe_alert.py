# -*- coding: utf-8 -*-
"""在环验证需求4 的三档闪烁：把 ALERT_LEFT2 / ALERT_RIGHT2 / ALERT_BOTH5
状态直接写进 RAM，让固件里真正的 AlertService() 跑起来，采样左右灯珠 ODR。

地址取自 Project/Listings/FlashRW_Full.map：
    s_alertKind 0x20000046  s_alertTotal 0x20000047
    s_alertDone 0x20000048  s_alertPhase 0x20000049  s_alertTick 0x2000004C
枚举：ALERT_NONE=0 BEEP=1 LEFT2=2 RIGHT2=3 BOTH5=4     半周期 250ms

比对方式：把序列首尾的"恒定段"剪掉，只比中间的翻转区，
避免起始那一两个采样因单端口写 vs 双端口写的微小时间差被误判成"不同相"。
"""
import time
from pyocd.core.helpers import ConnectHelper

UID = "37FF71064E5734360B791543"
G_ODR, E_ODR = 0x4001200C, 0x4001180C
A_KIND, A_TOTAL, A_DONE, A_PHASE, A_TICK = (0x20000046, 0x20000047,
                                            0x20000048, 0x20000049, 0x2000004C)
S_LEFT_TURN, S_RIGHT_TURN = 0x20000014, 0x20000015
ALERT_NONE = 0
b = lambda v, n: (v >> n) & 1


def trim(seq):
    """剪掉首尾的恒定段，返回中间翻转区"""
    s = "".join(map(str, seq))
    i, j = 0, len(s) - 1
    while i < j and s[i] == s[i + 1]:
        i += 1
    while j > i and s[j] == s[j - 1]:
        j -= 1
    return s[i:j + 1]


def blinks(seq):
    """统计"亮→灭"次数 = 闪了几次"""
    return sum(1 for i in range(1, len(seq)) if seq[i - 1] == 1 and seq[i] == 0)


sess = ConnectHelper.session_with_chosen_probe(
    unique_id=UID, target_override="stm32f103ze", connect_mode="attach",
    options={"frequency": 1000000})
sess.open()
t = sess.target

results = []
for kind, total, label, dur in ((2, 2, "ALERT_LEFT2  (10~50cm)", 1.8),
                                (3, 2, "ALERT_RIGHT2 (50cm~1m)", 1.8),
                                (4, 5, "ALERT_BOTH5  (>1m)", 3.2)):
    # 清场
    t.write8(A_KIND, ALERT_NONE)
    t.write8(S_LEFT_TURN, 0)
    t.write8(S_RIGHT_TURN, 0)
    time.sleep(0.15)

    t.write8(A_TOTAL, total)
    t.write8(A_DONE, 0)
    t.write8(A_PHASE, 0)
    t.write32(A_TICK, 0)
    t.write8(A_KIND, kind)                  # 起跑枪

    pg1, pe2, pg14, pg15, pg12 = [], [], [], [], []
    t0 = time.time()
    while (time.time() - t0) < dur:
        g = t.read32(G_ODR)
        e = t.read32(E_ODR)
        pg1.append(b(g, 1)); pg14.append(b(g, 14)); pg12.append(b(g, 12))
        pe2.append(b(e, 2)); pg15.append(b(g, 15))
        time.sleep(0.05)

    left, right = trim(pg1), trim(pe2)
    n_l, n_r = blinks(pg1), blinks(pe2)
    ended = t.read8(A_KIND)
    print("── %s ──" % label)
    print("   左灯珠 PG1 : %s   → 闪 %d 次" % (left, n_l))
    print("   右灯珠 PE2 : %s   → 闪 %d 次" % (right, n_r))
    print("   板载LED1/2 : %s / %s" % (trim(pg14), trim(pg15)))
    print("   收手后 kind = %d %s\n" % (ended, "（Alert_Stop 已归零 ✅）" if ended == 0 else "⚠"))
    results.append((label, n_l, n_r, total, ended))

t.write8(A_KIND, ALERT_NONE)
sess.close()

print("=" * 62)
print("%-24s %-12s %-12s %s" % ("档位", "左灯珠闪次", "右灯珠闪次", "判定"))
for label, n_l, n_r, total, ended in results:
    if "LEFT2" in label:
        ok = (n_l == 2 and n_r == 0)
    elif "RIGHT2" in label:
        ok = (n_l == 0 and n_r == 2)
    else:
        ok = (n_l == 5 and n_r == 5)
    print("%-24s %-12d %-12d %s" % (label.split()[0], n_l, n_r, "✅ 通过" if ok else "❌"))
