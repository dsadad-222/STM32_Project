# -*- coding: utf-8 -*-
"""侵入式探测：把「当前为浮空输入」的引脚临时改成上拉输入，连续采样 IDR，
找出被外部电路主动拉低 / 抖动最频繁的引脚 —— 那就是红外避障对管挂的 IO。

安全性：
  * 只改 nibble == 0x4（浮空输入）的引脚，绝不碰固件已配置的引脚
  * halt 状态下操作（固件不跑，纯硬件对管不受影响）
  * 结束前逐字节恢复原 CRL/CRH
"""
import json
import os
import sys
import time

from pyocd.core.helpers import ConnectHelper

UID = "37FF71064E5734360B791543"
GPIO_BASE = {"A": 0x40010800, "B": 0x40010C00, "C": 0x40011000, "D": 0x40011400,
             "E": 0x40011800, "F": 0x40011C00, "G": 0x40012000}
PORTS = list("ABCDEFG")
RCC_APB2ENR = 0x40021018

SECONDS = float(sys.argv[1]) if len(sys.argv) > 1 else 12.0
TAG = sys.argv[2] if len(sys.argv) > 2 else "pullup"
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_ir_scan_data")


def connect():
    last = None
    for mode in ("halt", "attach"):
        try:
            s = ConnectHelper.session_with_chosen_probe(
                unique_id=UID, target_override="stm32f103ze", connect_mode=mode)
            s.open()
            return s
        except Exception as exc:                       # noqa: BLE001
            last = exc
    raise SystemExit("cannot connect: %s" % last)


def main():
    os.makedirs(DATA, exist_ok=True)
    s = connect()
    t = s.target
    try:
        enr = t.read32(RCC_APB2ENR)
        need = 0
        for i, p in enumerate(PORTS):
            if not (enr >> (2 + i)) & 1:
                need |= 1 << (2 + i)
        if need:
            t.write32(RCC_APB2ENR, enr | need)
            time.sleep(0.05)
            print("[时钟] 补开 0x%03X" % need)

        # ---- 1. 备份 + 把浮空输入改成上拉输入 ----
        backup, touched, cand = {}, [], []
        for p in PORTS:
            base = GPIO_BASE[p]
            backup[p] = (t.read32(base + 0x00), t.read32(base + 0x04))
            crl, crh = backup[p]
            n_crl, n_crh = crl, crh
            odr = t.read32(base + 0x0C)
            n_odr = odr
            for n in range(16):
                if n < 8:
                    shift = n * 4
                    nib = (crl >> shift) & 0xF
                else:
                    shift = (n - 8) * 4
                    nib = (crh >> shift) & 0xF
                if nib != 0x4:            # 不是浮空输入 -> 跳过，绝不动
                    continue
                newnib = 0x8              # CNF=10 MODE=00 = 上/下拉输入
                if n < 8:
                    n_crl = (n_crl & ~(0xF << shift)) | (newnib << shift)
                else:
                    n_crh = (n_crh & ~(0xF << shift)) | (newnib << shift)
                n_odr |= (1 << n)         # ODR=1 -> 上拉
                touched.append("P%s%d" % (p, n))
                cand.append((p, n))
            if n_crl != crl:
                t.write32(base + 0x00, n_crl)
            if n_crh != crh:
                t.write32(base + 0x04, n_crh)
            if n_odr != odr:
                t.write32(base + 0x0C, n_odr)

        print("[改动] 把 %d 个浮空输入引脚临时改为上拉输入：" % len(touched))
        print("       " + " ".join(touched))
        print("[采样] %.0f 秒，每 20ms 一轮 ..." % SECONDS)

        # ---- 2. 连续采样 ----
        stat = {k: {"zero": 0, "one": 0, "flip": 0, "last": None} for k in touched}
        rounds = 0
        t0 = time.time()
        while time.time() - t0 < SECONDS:
            for p in PORTS:
                idr = t.read32(GPIO_BASE[p] + 0x08)
                for (pp, n) in cand:
                    if pp != p:
                        continue
                    b = (idr >> n) & 1
                    st = stat["P%s%d" % (p, n)]
                    if b:
                        st["one"] += 1
                    else:
                        st["zero"] += 1
                    if st["last"] is not None and st["last"] != b:
                        st["flip"] += 1
                    st["last"] = b
            rounds += 1
            time.sleep(0.02)

        print("[采样] 完成 %d 轮\n" % rounds)
        print("%-6s %-8s %-8s %-8s %s" % ("引脚", "低电平", "高电平", "翻转次数", "判定"))
        print("-" * 62)
        hits = []
        for k in touched:
            st = stat[k]
            # 上拉输入下仍常读到低 = 被外部主动拉低；频繁翻转 = 对光敏感
            low_ratio = st["zero"] / max(rounds, 1)
            flag = ""
            if low_ratio > 0.15 or st["flip"] >= 3:
                flag = "★ 可疑（对管）"
                hits.append(k)
            print("%-6s %-8d %-8d %-8d %s"
                  % (k, st["zero"], st["one"], st["flip"], flag))
        print("-" * 62)
        if hits:
            print("★ 可疑引脚 %d 个：%s" % (len(hits), " ".join(hits)))
        else:
            print("★ 未发现明显可疑引脚 —— 可能是阈值太严或对管未被遮挡/未焊")

        json.dump({"tag": TAG, "rounds": rounds, "stat": stat, "hits": hits,
                   "touched": touched},
                  open(os.path.join(DATA, TAG + ".json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("已保存: %s" % os.path.join(DATA, TAG + ".json"))

        # ---- 3. 恢复原配置 ----
        for p in PORTS:
            base = GPIO_BASE[p]
            t.write32(base + 0x00, backup[p][0])
            t.write32(base + 0x04, backup[p][1])
        print("[恢复] 已逐字节还原 GPIO 配置寄存器")
    finally:
        s.close()


if __name__ == "__main__":
    main()
