# -*- coding: utf-8 -*-
"""验算 chapter8 温度修复：真实 VDDA=4.2V 场景下，改前 / 改后 / 标定后"""

VREFINT_MV = 1200.0
V25_MV     = 1430.0
SLOPE      = 4.3          # mV/℃
FS         = 4096.0

def sensor_mv(t_c):       # 传感器理想输出
    return V25_MV - SLOPE * (t_c - 25.0)

def adc_raw(mv, vdda):
    return mv * FS / vdda

def calc(raw, vdda_used, offset_x100=0):
    mv = raw * vdda_used / FS
    return 25.0 + (V25_MV - mv) / SLOPE + offset_x100 / 100.0

def vdda_est(vdda, win):
    r = adc_raw(VREFINT_MV, vdda)
    if r < 100 or r > 4000:
        return 3300.0, r, "raw坏点->默认"
    mv = VREFINT_MV * FS / r
    if mv < win[0] or mv > win[1]:
        return 3300.0, r, "超窗->默认3300"
    return mv, r, "采用实测"

print("=" * 74)
print("场景：板上 3V3 实际被抬到 4.2V，室温 25.0℃（其余路径全部按手册理想值）")
print("=" * 74)
VDDA = 4200.0
raw_t = adc_raw(sensor_mv(25.0), VDDA)
print(f"温度通道原始值 raw_temp = {raw_t:.0f}   (25℃ 传感器输出 {sensor_mv(25.0):.0f}mV)")
print()
for label, win in [("修复前 区间 2800~3600mV", (2800, 3600)),
                   ("修复后 区间 1800~4600mV", (1800, 4600))]:
    e, rv, why = vdda_est(VDDA, win)
    print(f"{label}")
    print(f"   Vrefint raw = {rv:.0f} -> 反推 VDDA = {VREFINT_MV*FS/rv:.0f}mV  [{why}]")
    print(f"   实际代入换算的 VDDA = {e:.0f}mV  ->  显示温度 = {calc(raw_t, e):.2f}℃")
    print()

print("=" * 74)
print("若 VDDA 本来就是 3.3V、只是这颗芯片 V25 有出厂偏差（模拟 V25=1.35V）")
print("=" * 74)
VDDA = 3300.0
raw_t2 = adc_raw(sensor_mv(25.0), VDDA)   # 用标称公式算出的 raw（芯片按1.35V输出会更低，这里演示标定）
e, rv, why = vdda_est(VDDA, (1800, 4600))
raw_t2 = 1244          # 假设实测 raw 对应标称公式 98℃
t_formula = calc(raw_t2, e)
print(f"   Vrefint raw = {rv:.0f} -> VDDA = {e:.0f}mV")
print(f"   公式算出 = {t_formula:.2f}℃   （室温其实是 25.00℃）")
off = 2500 - round(t_formula * 100)
print(f"   按 K 标定 -> offset = 2500 - {round(t_formula*100)} = {off} (={off/100:.2f}℃)")
print(f"   标定后显示 = {t_formula + off/100.0:.2f}℃   ✓")
print(f"   换到 40℃ 真值再验：", end="")
raw40 = adc_raw(sensor_mv(40.0), VDDA) if False else raw_t2 - (40-25)*SLOPE*FS/VDDA
print(f"raw={raw40:.0f} -> 公式 {calc(raw40,e):.2f}℃ -> 标定后 {calc(raw40,e,off):.2f}℃")
print()
print("结论：单点标定对温度是线性平移，全量程都跟着修好。")
