# -*- coding: utf-8 -*-
"""红外避障对管遮挡测试 —— 定位两路对管输出的 MCU 引脚。

做法：
  1) 把「当前为浮空输入」的引脚临时改成上拉输入（对管接收管截止时应为高，
     被障碍物反射导通后拉低）
  2) 连续采样 30 秒，按 10 秒分 3 段统计每个引脚的低电平占比
  3) 哪两个引脚在某一段低占比明显升高，就是两路对管

配合动作（测试期间请照做）：
    第 0~10 秒  : 用手/纸板挡住【左侧】对管，保持不动
    第 10~20 秒 : 用手/纸板挡住【右侧】对管，保持不动
    第 20~30 秒 : 手移开，让对管前方空着

安全性：只改 nibble==0x4（浮空输入）的引脚，结束前逐字节恢复。
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
SEC_PER_SEG = 10.0
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_ir_scan_data")

# 对管是反相输出：有障碍 -> 高电平，无障碍 -> 低电平（实测确认）
SEGS = [
    "用手掌盖住【左边】那对红外对管（两个圆柱形元件），靠近到 1~2cm，保持不动",
    "改用【右边】那对红外对管，同样盖住保持不动",
    "把【手完全拿开】，让对管前方空着",
]


GPIOG_CRH = 0x40012004      # PG8..PG15 配置
GPIOG_BSRR = 0x40012010     # 置位
GPIOG_BRR = 0x40012014      # 复位
BEEP_BIT = 1 << 12          # PG12 = 蜂鸣器，高电平鸣叫


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


def beep(t, times, on_ms=120, off_ms=120):
    """用板载蜂鸣器(PG12)发提示音：第 N 段就响 N 声，用户听声数就知道该做哪个动作。"""
    for _ in range(times):
        t.write32(GPIOG_BSRR, BEEP_BIT)
        time.sleep(on_ms / 1000.0)
        t.write32(GPIOG_BRR, BEEP_BIT)
        time.sleep(off_ms / 1000.0)


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

        backup, cand = {}, []
        for p in PORTS:
            base = GPIO_BASE[p]
            backup[p] = (t.read32(base + 0x00), t.read32(base + 0x04))
            crl, crh = backup[p]
            n_crl, n_crh = crl, crh
            odr = t.read32(base + 0x0C)
            n_odr = odr
            for n in range(16):
                shift = (n if n < 8 else n - 8) * 4
                nib = ((crl if n < 8 else crh) >> shift) & 0xF
                if nib != 0x4:
                    continue
                if n < 8:
                    n_crl = (n_crl & ~(0xF << shift)) | (0x8 << shift)
                else:
                    n_crh = (n_crh & ~(0xF << shift)) | (0x8 << shift)
                n_odr |= (1 << n)
                cand.append((p, n))
            if n_crl != crl:
                t.write32(base + 0x00, n_crl)
            if n_crh != crh:
                t.write32(base + 0x04, n_crh)
            if n_odr != odr:
                t.write32(base + 0x0C, n_odr)

        print("[准备] %d 个浮空输入引脚已临时改为上拉输入" % len(cand))

        # 蜂鸣器 PG12 准备好（固件已配成推挽输出，这里只兜底检查）
        crh_beep = t.read32(GPIOG_CRH)
        nib12 = (crh_beep >> 16) & 0xF
        if nib12 & 0x3 == 0:                 # MODE=00 -> 是输入，补配成推挽输出
            t.write32(GPIOG_CRH, (crh_beep & ~(0xF << 16)) | (0x3 << 16))
            print("[蜂鸣器] PG12 原为输入(0x%X)，已临时配成推挽输出" % nib12)
        t.write32(GPIOG_BRR, BEEP_BIT)       # 先确保不响

        print("[采样] 共 %d 段、每段 %.0f 秒。每段开始响提示音：\n" % (len(SEGS), SEC_PER_SEG))
        for i, s_ in enumerate(SEGS):
            print("        [%d] 响 %d 声 -> %s" % (i + 1, i + 1, s_))
        print()

        seg = [[[0, 0, 0, None] for _ in cand] for _ in range(len(SEGS))]
        rounds = [0] * len(SEGS)
        t0 = time.time()
        last_seg = -1
        while True:
            el = time.time() - t0
            k = min(int(el / SEC_PER_SEG), len(SEGS) - 1)
            if el >= len(SEGS) * SEC_PER_SEG:
                break
            if k != last_seg:
                beep(t, k + 1)
                last_seg = k
                print("   [第 %d 段开始] 听到 %d 声提示音" % (k + 1, k + 1))
                continue
            for p in PORTS:
                idr = t.read32(GPIO_BASE[p] + 0x08)
                for i, (pp, n) in enumerate(cand):
                    if pp != p:
                        continue
                    b = (idr >> n) & 1
                    st = seg[k][i]
                    st[1 if b else 0] += 1
                    if st[3] is not None and st[3] != b:
                        st[2] += 1
                    st[3] = b
            rounds[k] += 1
            time.sleep(0.02)

        print("[采样] 完成，各段轮数 %r\n" % rounds)
        names = ["P%s%d" % (p, n) for (p, n) in cand]
        ns = len(SEGS)

        hi = {}
        for i, k in enumerate(names):
            hi[k] = [seg[j][i][1] / max(rounds[j], 1) for j in range(ns)]

        hdr = " ".join("%13s" % x for x in ("①盖左", "②盖右", "③手拿开")[:ns])
        print("%-6s %s   %s" % ("引脚", hdr, "判定"))
        print("-" * 72)
        findings = []
        for k in names:
            h = hi[k]
            idx = h.index(max(h))
            others = max(h[:idx] + h[idx + 1:])
            tag = ""
            if max(h) - others > 0.30:
                tag = "★ 第%d段【变高】" % (idx + 1)
                findings.append((k, idx + 1, max(h), others))
            if tag:
                print("%-6s %s   %s"
                      % (k, " ".join("%12.0f%%" % (x * 100) for x in h), tag))
        print("-" * 72)
        if findings:
            for k, segno, top, oth in findings:
                side = {1: "【左侧】", 2: "【右侧】", 3: "手拿开时"}.get(segno, "第%d段" % segno)
                print(">>> %-6s  第%d段%s 高电平 %.0f%%（其他段最高仅 %.0f%%）"
                      % (k, segno, side, top * 100, oth * 100))
        else:
            print(">>> 没有任何引脚随手掌位置变化")
        json.dump({"rounds": rounds,
                   "hi": {k: [round(x, 3) for x in v] for k, v in hi.items()},
                   "findings": findings},
                  open(os.path.join(DATA, "block_test.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)

        for p in PORTS:
            t.write32(GPIO_BASE[p] + 0x00, backup[p][0])
            t.write32(GPIO_BASE[p] + 0x04, backup[p][1])
        t.write32(GPIOG_BRR, BEEP_BIT)         # 关蜂鸣器
        print("[恢复] GPIO 配置已还原，蜂鸣器已关")
    finally:
        s.close()


if __name__ == "__main__":
    main()
