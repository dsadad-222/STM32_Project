# -*- coding: utf-8 -*-
"""用 ADC 精读红外对管的模拟输出 —— 数字阈值读不出变化时用这个。

覆盖 F103ZET6 上全部可用于外部输入的 ADC 通道：
    ADC1 : PA0~PA7(IN0~7) PB0(8) PB1(9) PC0~PC5(IN10~15)
    ADC3 : PF6~PF10(IN4~IN8)

配合动作与 _ir_block_test.py 相同（三段各 10 秒，蜂鸣器提示音报段号）。
输出每段的 ADC 平均值，谁在某一段明显下降就是那一路对管。

安全性：结束前逐字节恢复 CRL/CRH，并关闭 ADC。
"""
import io
import json
import os
import sys
import time

from pyocd.core.helpers import ConnectHelper

UID = "37FF71064E5734360B791543"
RCC_CFGR = 0x40021004
RCC_APB2ENR = 0x40021018
GPIO_BASE = {"A": 0x40010800, "B": 0x40010C00, "C": 0x40011000, "D": 0x40011400,
             "E": 0x40011800, "F": 0x40011C00, "G": 0x40012000}
ADC1 = 0x40012400
ADC3 = 0x40013C00
SR, CR2, SMPR1, SMPR2, SQR1, SQR3, DR = 0x00, 0x08, 0x0C, 0x10, 0x2C, 0x34, 0x4C

GPIOG_CRH = 0x40012004
GPIOG_BSRR = 0x40012010
GPIOG_BRR = 0x40012014
BEEP_BIT = 1 << 12
SEC_PER_SEG = 10.0
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_ir_scan_data")

# (ADC 基址, 通道号, 引脚名, 端口, 引脚位)
CHANNELS = (
    [(ADC1, i, "PA%d" % i, "A", i) for i in range(8)] +
    [(ADC1, 8, "PB0", "B", 0), (ADC1, 9, "PB1", "B", 1)] +
    [(ADC1, 10 + i, "PC%d" % i, "C", i) for i in range(6)] +
    [(ADC3, 4 + i, "PF%d" % (6 + i), "F", 6 + i) for i in range(5)]
)


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
    for _ in range(times):
        t.write32(GPIOG_BSRR, BEEP_BIT)
        time.sleep(on_ms / 1000.0)
        t.write32(GPIOG_BRR, BEEP_BIT)
        time.sleep(off_ms / 1000.0)


def adc_init(t, base):
    """上电 + 校准，采样时间全设 239.5 周期。"""
    cr2 = t.read32(base + CR2)
    is_on = cr2 & 1
    t.write32(base + CR2, 1)                       # ADON
    t.write32(base + CR2, (1 << 3) | 1)            # RSTCAL
    for _ in range(200):
        if not (t.read32(base + SR) & (1 << 3)):
            break
        time.sleep(0.001)
    t.write32(base + CR2, (1 << 2) | 1)            # CAL
    for _ in range(200):
        if not (t.read32(base + SR) & (1 << 2)):
            break
        time.sleep(0.001)
    t.write32(base + SMPR1, 0x3FFFFFFF)            # ch10~17 全 7
    t.write32(base + SMPR2, 0x3FFFFFFF)            # ch0~9 全 7
    t.write32(base + SQR1, 0)                      # 1 个转换
    # EXTSEL=111(SWSTART) + EXTTRIG
    t.write32(base + CR2, (0x7 << 17) | (1 << 20) | 1)
    return is_on


def adc_read(t, base, ch):
    t.write32(base + SQR3, ch & 0x1F)
    t.write32(base + CR2, (0x7 << 17) | (1 << 20) | 1 | (1 << 22))   # SWSTART
    for _ in range(400):
        if t.read32(base + SR) & (1 << 1):         # EOC
            break
    return t.read32(base + DR) & 0xFFF


def main():
    os.makedirs(DATA, exist_ok=True)
    s = connect()
    t = s.target
    try:
        # ---- 时钟 ----
        enr = t.read32(RCC_APB2ENR)
        t.write32(RCC_APB2ENR, enr | (1 << 9) | (1 << 15))      # ADC1EN + ADC3EN
        cfgr = t.read32(RCC_CFGR)
        t.write32(RCC_CFGR, (cfgr & ~(3 << 14)) | (3 << 14))    # ADCPRE=PCLK2/8
        time.sleep(0.05)

        # ---- 引脚改模拟输入（逐引脚改 nibble，绝不能整端口清零：
        #      PA13/PA14 是 SWD，整端口清零会当场把自己调试通道干掉）----
        backup = {}
        for p in set(c[3] for c in CHANNELS):
            base = GPIO_BASE[p]
            backup[p] = (t.read32(base + 0x00), t.read32(base + 0x04))
        for _base, _ch, name, port, pin in CHANNELS:
            base = GPIO_BASE[port]
            reg = base + (0x00 if pin < 8 else 0x04)
            shift = (pin if pin < 8 else pin - 8) * 4
            t.write32(reg, t.read32(reg) & ~(0xF << shift))     # CNF=00 MODE=00 = 模拟
        print("[引脚] %d 个 ADC 引脚已配成模拟输入：%s"
              % (len(CHANNELS), " ".join(c[2] for c in CHANNELS)))

        # ---- 蜂鸣器 ----
        crh_beep = t.read32(GPIOG_CRH)
        if (crh_beep >> 16) & 0x3 == 0:
            t.write32(GPIOG_CRH, (crh_beep & ~(0xF << 16)) | (0x3 << 16))
        t.write32(GPIOG_BRR, BEEP_BIT)

        # ---- ADC 上电校准 ----
        adc_init(t, ADC1)
        adc_init(t, ADC3)
        print("[ADC ] ADC1 / ADC3 已上电并校准，采样时间 239.5 周期\n")

        names = [c[2] for c in CHANNELS]
        acc = [[0] * len(CHANNELS) for _ in range(3)]
        cnt = [0, 0, 0]

        print("[采样] 30 秒，三段各 10 秒。每段开始响提示音：")
        print("        [1] 响 1 声 -> 挡住【左侧】对管，靠近 2~3cm，保持不动")
        print("        [2] 响 2 声 -> 改用【右侧】对管")
        print("        [3] 响 3 声 -> 手移开\n")

        t0 = time.time()
        last_seg = -1
        while True:
            el = time.time() - t0
            k = min(int(el / SEC_PER_SEG), 2)
            if el >= 3 * SEC_PER_SEG:
                break
            if k != last_seg:
                beep(t, k + 1)
                last_seg = k
                print("   [第 %d 段开始]" % (k + 1))
                continue
            for i, (base, ch, _n, _p, _b) in enumerate(CHANNELS):
                acc[k][i] += adc_read(t, base, ch)
            cnt[k] += 1
            time.sleep(0.005)

        print("[采样] 完成，三段轮数 %r\n" % cnt)
        avg = [[acc[j][i] / max(cnt[j], 1) for i in range(len(CHANNELS))] for j in range(3)]

        rows = []
        for i, n in enumerate(names):
            v1, v2, v3 = avg[0][i], avg[1][i], avg[2][i]
            spread = max(v1, v2, v3) - min(v1, v2, v3)
            rows.append((spread, n, v1, v2, v3))
        rows.sort(reverse=True)

        print("%-6s %-22s %-8s %-8s %-8s %s" % ("引脚", "电压V(挡左/挡右/移开)", "挡左", "挡右", "移开", "判定"))
        print("-" * 74)
        for sp, n, v1, v2, v3 in rows:
            tov = lambda v: v / 4095.0 * 3.3
            tag = ""
            if v1 + 150 < min(v2, v3):
                tag = "★ 挡左时降低 -> 【左侧】"
            elif v2 + 150 < min(v1, v3):
                tag = "★ 挡右时降低 -> 【右侧】"
            if tag or sp > 60:
                print("%-6s %-22s %-8.2f %-8.2f %-8.2f %s"
                      % (n, "%.2f/%.2f/%.2f" % (tov(v1), tov(v2), tov(v3)),
                         tov(v1), tov(v2), tov(v3), tag))
        print("-" * 74)
        print("（完整 22 通道原始均值见 JSON）")

        json.dump({"cnt": cnt, "avg": {names[i]: [round(avg[j][i], 1) for j in range(3)]
                                       for i in range(len(names))}},
                  io.open(os.path.join(DATA, "adc_scan.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)

        # ---- 恢复 ----
        for p, (crl, crh) in backup.items():
            t.write32(GPIO_BASE[p] + 0x00, crl)
            t.write32(GPIO_BASE[p] + 0x04, crh)
        t.write32(ADC1 + CR2, 0)        # 关 ADC1
        t.write32(ADC3 + CR2, 0)        # 关 ADC3
        t.write32(RCC_CFGR, cfgr)       # 还原 ADCPRE
        t.write32(RCC_APB2ENR, enr)     # 还原 ADC1EN / ADC3EN
        t.write32(GPIOG_CRH, crh_beep)
        t.write32(GPIOG_BRR, BEEP_BIT)
        print("[恢复] GPIO / ADC / RCC 配置全部已还原")
    finally:
        s.close()


if __name__ == "__main__":
    main()
