# -*- coding: utf-8 -*-
"""扫描 STM32F103ZET6 全部 GPIO 的配置与电平，用于找出红外避障对管接在哪两个 IO。

用法：
    python _ir_scan.py base               # 采一次基线快照
    python _ir_scan.py snap  <标签>        # 再采一次（存到 JSON）
    python _ir_scan.py diff  <A> <B>      # 对比两次快照，列出电平变化的引脚

原理：
    STM32 复位后所有 IO 默认是「浮空输入」(CRL/CRH = 0x44444444)。
    固件没动过的引脚保持浮空输入 —— 此时 IDR 依然跟随引脚外部电平，
    所以红外对管只要挂在某个未初始化的 IO 上，读 IDR 就能看到它。
    唯一前提是端口时钟已使能，否则读 IDR 恒为 0。
"""
import json
import os
import sys
import time

from pyocd.core.helpers import ConnectHelper

UID = "37FF71064E5734360B791543"

RCC_APB2ENR = 0x40021018          # bit2..8 = GPIOA..GPIOG 时钟使能
GPIO_BASE = {
    "A": 0x40010800, "B": 0x40010C00, "C": 0x40011000, "D": 0x40011400,
    "E": 0x40011800, "F": 0x40011C00, "G": 0x40012000,
}
PORTS = list("ABCDEFG")

# 已知被 0918 固件占用的引脚（这些即使在变化也不代表红外避障）
KNOWN = {
    "A": [9, 10],                    # USART1 TX/RX
    "B": [6, 7, 12, 13, 14, 15],     # OLED 软 I2C + W25Q64 SPI2
    "D": [9, 10, 11],                # 预留（SPI2 相关）
    "E": [2, 3, 4],                  # 右 RGB
    "F": [11, 12],                   # 超声波 TRIG/ECHO
    "G": [0, 1, 2, 3, 4, 5, 11, 12, 14, 15],   # 左RGB/KEY/HS0038B/蜂鸣/LED
}

SNAP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_ir_scan_data")


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


def pin_state(t, port, pin):
    """返回 (mode, cnf, idr, odr)；mode 0=输入 1=输出"""
    base = GPIO_BASE[port]
    if pin < 8:
        cfg = t.read32(base + 0x00)
        shift = pin * 4
    else:
        cfg = t.read32(base + 0x04)
        shift = (pin - 8) * 4
    nib = (cfg >> shift) & 0xF
    mode = nib & 0x3
    cnf = (nib >> 2) & 0x3
    idr = (t.read32(base + 0x08) >> pin) & 1
    odr = (t.read32(base + 0x0C) >> pin) & 1
    return mode, cnf, idr, odr


def snapshot(t, tag):
    # 确保所有端口时钟打开，否则读 IDR 恒 0（不改 GPIO 配置，只开时钟）
    enr = t.read32(RCC_APB2ENR)
    need = 0
    for i, p in enumerate(PORTS):
        if not (enr >> (2 + i)) & 1:
            need |= 1 << (2 + i)
    if need:
        t.write32(RCC_APB2ENR, enr | need)
        time.sleep(0.05)
        print("[时钟] 补开端口时钟掩码 0x%03X（仅开时钟，未改任何 GPIO 配置）" % need)

    data = {"tag": tag, "ts": time.strftime("%Y-%m-%d %H:%M:%S"), "pins": {}}
    for p in PORTS:
        for n in range(16):
            mode, cnf, idr, odr = pin_state(t, p, n)
            data["pins"]["P%s%d" % (p, n)] = [mode, cnf, idr, odr]
    return data


def fmt_cnf(mode, cnf):
    if mode == 0:
        return {0: "模拟", 1: "浮空", 2: "上/下拉", 3: "保留"}[cnf]
    return {0: "推挽", 1: "开漏", 2: "复用推挽", 3: "复用开漏"}[cnf]


def show(data):
    print("\n标签=%s  时间=%s" % (data["tag"], data["ts"]))
    print("%-6s %-5s %-8s %-5s %-5s  %s" % ("引脚", "模式", "类型", "IDR", "ODR", "备注"))
    print("-" * 62)
    for p in PORTS:
        for n in range(16):
            k = "P%s%d" % (p, n)
            mode, cnf, idr, odr = data["pins"][k]
            known = n in KNOWN.get(p, [])
            # 只列：输入引脚且 IDR=1（可能有上拉/外部驱动），或已知占用引脚
            if mode == 0 and (idr == 1 or known):
                print("%-6s %-5s %-8s %-5d %-5d  %s"
                      % (k, "输入", fmt_cnf(mode, cnf), idr, odr,
                         "已知占用" if known else "** 高电平 **"))
    print("-" * 62)
    print("（只列出「配置为输入」的引脚；输出/复用引脚不列，它们由固件驱动）")


def main():
    os.makedirs(SNAP_DIR, exist_ok=True)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "base"

    if cmd == "diff":
        a, b = sys.argv[2], sys.argv[3]
        da = json.load(open(os.path.join(SNAP_DIR, a + ".json"), encoding="utf-8"))
        db = json.load(open(os.path.join(SNAP_DIR, b + ".json"), encoding="utf-8"))
        print("对比 %s -> %s" % (a, b))
        print("%-6s %-22s %-22s %s" % ("引脚", a, b, "变化"))
        print("-" * 70)
        changed = []
        for k in da["pins"]:
            va, vb = da["pins"][k], db["pins"][k]
            if va != vb:
                changed.append(k)
                print("%-6s %-22s %-22s 模式%s 电平 %d->%d"
                      % (k, str(va), str(vb), "不变" if va[0] == vb[0] else "变了",
                         va[2], vb[2]))
        if not changed:
            print("（无任何引脚变化）")
        return

    tag = sys.argv[2] if len(sys.argv) > 2 else cmd
    s = connect()
    try:
        t = s.target
        d = snapshot(t, tag)
        show(d)
        path = os.path.join(SNAP_DIR, tag + ".json")
        json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("\n已保存: %s" % path)
    finally:
        s.close()


if __name__ == "__main__":
    main()
