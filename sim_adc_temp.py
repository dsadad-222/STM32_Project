# -*- coding: utf-8 -*-
"""把 adc_drv.c / main.c 里的换算与排版逻辑照抄到 Python 里跑一遍，
   确认：温度公式、电压换算、OLED 每行 16 字符、串口三行格式都正确。"""

V25_MV = 1430
SLOPE_X10 = 43          # 4.3mV/℃ x10


def raw_to_mv(raw, vdda_mv):
    return raw * vdda_mv // 4096


def raw_to_temp_x100(raw, vdda_mv):
    vsense = raw_to_mv(raw, vdda_mv)
    delta = (V25_MV - vsense) * 1000 // SLOPE_X10
    return 2500 + delta


def vdda_from_vref(raw_vref):
    if raw_vref < 100 or raw_vref > 4000:
        return 3300
    mv = 1200 * 4096 // raw_vref
    if mv < 2800 or mv > 3600:
        return 3300
    return mv


def format_fixed(scaled, decimals):
    div = 10 ** decimals
    neg = scaled < 0
    if neg:
        scaled = -scaled
    int_part = scaled // div
    frac = scaled % div
    s = str(int_part)
    if neg:
        s = '-' + s
    if decimals:
        s += '.' + str(frac).rjust(decimals, '0')
    return s


def pad_value(scaled, decimals, width=5):
    return format_fixed(scaled, decimals).rjust(width)


def build_lines(raw, vdda):
    mv = raw_to_mv(raw, vdda)
    t = raw_to_temp_x100(raw, vdda)
    l0 = ('ADCvalue:' + pad_value(raw, 0)).ljust(16)
    l1 = ('Voltage :' + pad_value(mv, 3)).ljust(16)
    l2 = ('Temp    :' + pad_value(t, 2)).ljust(16)
    return l0, l1, l2, mv, t


print('=== 1. VDDA 反推（Vrefint=1200mV）===')
for raw_vref in (1446, 1489, 1536, 900):
    print(f'  Vrefint raw={raw_vref:5d} -> VDDA={vdda_from_vref(raw_vref)} mV')
# 1489 -> 1200*4096/1489 = 3301 mV

print()
print('=== 2. 温度公式核对（按任务书公式手算对照）===')
cases = [
    # raw, vdda, 期望说明
    (1720, 3300),   # 电压 1.385V -> 高于 25℃，约 35℃
    (1774, 3300),   # 电压 1.429V -> 约 25℃
    (1900, 3300),   # 电压 1.531V -> 低于 25℃，约 1.4℃
    (4095, 3300),   # 上限
    (0,    3300),   # 下限
]
ok = 0
for raw, vdda in cases:
    l0, l1, l2, mv, t = build_lines(raw, vdda)
    vsense = mv / 1000.0
    expect = (1.43 - vsense) / 0.0043 + 25
    diff = abs(t / 100.0 - expect)
    flag = 'OK' if diff < 0.02 else 'DIFF'
    if flag == 'OK':
        ok += 1
    print(f'  raw={raw:5d} Vsense={vsense:.3f}V  程序={t/100:.2f}℃  公式={expect:.2f}℃  {flag}')
print(f'  公式一致性: {ok}/{len(cases)}')

print()
print('=== 3. OLED 排版（每行必须正好 16 字符，冒号对齐）===')
samples = [(2018, 3300), (4095, 3300), (0, 3300), (1774, 3300), (1900, 3245)]
for raw, vdda in samples:
    l0, l1, l2, mv, t = build_lines(raw, vdda)
    print(f'  |{l0}|{l1}|{l2}|')
    assert len(l0) == len(l1) == len(l2) == 16, '行宽错误'
    assert l0[8] == l1[8] == l2[8] == ':', '冒号没对齐'
print('  行宽 16 / 冒号第 9 列：PASS')

print()
print('=== 4. 串口上报三行格式 ===')
raw, vdda = 2018, 3300
l0, l1, l2, mv, t = build_lines(raw, vdda)
print('Current ADC_Value is ' + format_fixed(raw, 0))
print('Current Voltage is ' + format_fixed(mv, 3))
print('Current Temperature is ' + format_fixed(t, 2))

print()
print('=== 5. 状态行 16 字符核对 ===')
for left, right, beep, led, tail in ((0, 0, 0, 0, ' NEW '), (1, 0, 1, 0, 'BRTH '),
                                     (0, 1, 0, 0, 'TEXT '), (1, 1, 1, 1, ' RST ')):
    line = f'L{left} R{right} B{beep} D{led}' + tail
    print(f'  |{line}|  len={len(line)}')
    assert len(line) == 16

print()
print('=== 6. 呼吸灯占空比曲线（每 20ms 调 2 级）===')
level, up, duty = 0, True, []
for step in range(110):
    if up:
        if level + 2 >= 100:
            level, up = 100, False
        else:
            level += 2
    else:
        if level <= 2:
            level, up = 0, True
        else:
            level -= 2
    duty.append(level)
print('  前 10 级:', duty[:10])
print('  峰值    :', max(duty), ' 最低:', min(duty))
print('  半程时间: %.2f s   一个来回: %.2f s' % (len(duty) * 20 / 1000 / 2, len(duty) * 20 / 1000))
print('  PWM 频率: %d Hz（20kHz / 100 级）' % (20000 // 100))

print()
print('=== 7. 超量程保护（TSVREFE 没打开时通道读回 0）===')
def temp_is_valid(raw, t):
    if raw == 0 or raw >= 4095:
        return False
    return -4000 <= t <= 12500

for raw in (0, 4095, 1774, 2018):
    t = raw_to_temp_x100(raw, 3300)
    v = temp_is_valid(raw, t)
    if v:
        line2 = ('Temp    :' + pad_value(t, 2)).ljust(16)
        out = format_fixed(t, 2)
    else:
        line2 = ('Temp    :' + '  --.--').ljust(16)
        out = '--'
    print(f'  raw={raw:5d} -> 换算 {t/100:8.2f}℃  有效={v}  屏|{line2}|  串口 Current Temperature is {out}')
    assert len(line2) == 16

print()
print('ALL SIM CHECKS DONE')
