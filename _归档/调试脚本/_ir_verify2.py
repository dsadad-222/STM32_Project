# -*- coding: utf-8 -*-
"""
_ir_verify2.py —— 纯数字法验证红外两路（不用 ADC，结论最硬）

思路：
    板上接收管集电极被 10K 上拉到 3V3，见光（有反射）就导通把电压拉低。
    所以只要把 PF9 / PF10 配成【浮空输入】直接读 IDR 的数字电平就够了：
        前方无反射 -> 1（被 10K 拉高）
        前方有反射 -> 0（被光敏管拉低）
    不需要 ADC，也就绕开了 ADC3 那套寄存器配置，结果最不容易出错。

同时读 GPIOE 的 IDR bit5/bit6：
    PE5/PE6 是开漏输出。熄灭态（高阻）时，如果 P1/P3 真的接着 PNP 基极电路，
    引脚会被基极回路抬到接近 5V，IDR 读回 1；
    点亮态（输出低）时 IDR 读回 0。
    —— 所以"IDR 随灯态翻转"本身就证明这两个引脚确实接到了基极电路上，
       而不是空脚。这一条不需要任何遮挡操作，先把它验掉。

阶段与蜂鸣提示（用 PG12 蜂鸣器报段号）：
    5 声短鸣 = 就绪
    1 声     -> 手全部拿开
    2 声     -> 手掌贴住【左】对管 3~5cm
    3 声     -> 手掌贴住【右】对管 3~5cm
    1 声长鸣 -> 手全部拿开
"""

import io
import json
import time

LOG = io.open(r'D:\STM32_Project\_ir_verify2.log', 'w', encoding='utf-8', newline='\n')


def log(msg=''):
    print(msg, flush=True)
    LOG.write(msg + '\n')
    LOG.flush()


from pyocd.core.helpers import ConnectHelper  # noqa: E402

UID = '37FF71064E5734360B791543'

RCC_APB2ENR = 0x40021018
GPIOE_CRL = 0x40011800
GPIOE_IDR = 0x40011808
GPIOE_BSRR = 0x40011810
GPIOE_BRR = 0x40011814
GPIOF_CRH = 0x40011C04
GPIOF_IDR = 0x40011C08
GPIOG_CRH = 0x40012004
GPIOG_BSRR = 0x40012010
GPIOG_BRR = 0x40012014

log('=== 连接探针 ===')
sess = ConnectHelper.session_with_chosen_probe(
    unique_id=UID, target_override='stm32f103ze',
    options={'connect_mode': 'halt'})
sess.open()
t = sess.target
log('  %s  %s' % (t.part_number, t.get_state()))


def set_pin(addr, pin, val):
    sh = (pin if pin < 8 else pin - 8) * 4
    cur = t.read32(addr)
    t.write32(addr, (cur & ~(0xF << sh)) | ((val & 0xF) << sh))


def beep(ms):
    t.write32(GPIOG_BSRR, 1 << 12)
    time.sleep(ms / 1000.0)
    t.write32(GPIOG_BRR, 1 << 12)


def beeps(n, short=90):
    for i in range(n):
        beep(short)
        if i != n - 1:
            time.sleep(0.12)


log('=== 配 GPIO ===')
t.write32(RCC_APB2ENR, t.read32(RCC_APB2ENR) | (1 << 6) | (1 << 7) | (1 << 8))
set_pin(GPIOG_CRH, 12, 0x3)                 # 蜂鸣器推挽输出
set_pin(GPIOE_CRL, 5, 0x7)                  # PE5 开漏输出
set_pin(GPIOE_CRL, 6, 0x7)                  # PE6 开漏输出
set_pin(GPIOF_CRH, 9, 0x4)                  # PF9 浮空输入
set_pin(GPIOF_CRH, 10, 0x4)                 # PF10 浮空输入
log('  GPIOE_CRL=%08X (PE5/PE6 应为 7=开漏)  GPIOF_CRH=%08X (PF9/PF10 应为 4=浮空输入)'
    % (t.read32(GPIOE_CRL), t.read32(GPIOF_CRH)))


def set_leds(l_on, r_on):
    """开漏：写 BRR = 拉低 = 亮；写 BSRR = 高阻 = 灭"""
    t.write32(GPIOE_BRR if l_on else GPIOE_BSRR, 1 << 5)
    t.write32(GPIOE_BRR if r_on else GPIOE_BSRR, 1 << 6)


def sample(n=300):
    """三种灯态各读 n 次 IDR，返回各路高电平占比（0~100）"""
    out = {}
    for name, l_on, r_on in [('off', False, False),
                             ('L',   True,  False),
                             ('R',   False, True)]:
        set_leds(l_on, r_on)
        time.sleep(0.02)
        e5 = e6 = f9 = f10 = 0
        for _ in range(n):
            eidr = t.read32(GPIOE_IDR)
            fidr = t.read32(GPIOF_IDR)
            e5 += (eidr >> 5) & 1
            e6 += (eidr >> 6) & 1
            f9 += (fidr >> 9) & 1
            f10 += (fidr >> 10) & 1
        out[name] = {'PE5': e5 * 100 // n, 'PE6': e6 * 100 // n,
                     'PF9': f9 * 100 // n, 'PF10': f10 * 100 // n}
    set_leds(False, False)
    return out


log()
log('=== 免操作检查：先测 SWD 读取速度，据此决定采样次数 ===')
_t0 = time.time()
for _ in range(50):
    t.read32(GPIOF_IDR)
MS = (time.time() - _t0) / 50 * 1000.0
log('  单次 read32 ≈ %.2f ms' % MS)
# 每个灯态目标采样时长 ~0.7s，且不少于 40 次、不多于 400 次
NSAMP = int(max(40, min(400, 700.0 / max(MS, 0.01))))
log('  取每个灯态采样 %d 次（约 %.1f 秒/灯态）' % (NSAMP, NSAMP * MS / 1000.0))

log()
log('=== 免操作检查：灯态翻转时 PE5/PE6 自身电平有没有跟着翻 ===')
s = sample(NSAMP)
log('  灯态   PE5高%%  PE6高%%  PF9高%%  PF10高%%')
for k in ('off', 'L', 'R'):
    log('  %-5s  %5d  %5d  %6d  %6d' % (k, s[k]['PE5'], s[k]['PE6'], s[k]['PF9'], s[k]['PF10']))
if s['off']['PE5'] > 50 and s['L']['PE5'] < 50:
    log('  ✔ PE5 在灯态翻转时电平跟着翻（高阻=1 / 拉低=0）-> P1 确实接着基极电路')
else:
    log('  ✘ PE5 电平没跟着翻，P1 驱动回路可能不通')
if s['off']['PE6'] > 50 and s['R']['PE6'] < 50:
    log('  ✔ PE6 在灯态翻转时电平跟着翻 -> P3 确实接着基极电路')
else:
    log('  ✘ PE6 电平没跟着翻，P3 驱动回路可能不通')

# ---------------- 遮挡分段 ----------------
log()
log('=== 就绪信号：5 声短鸣… ===')
beeps(5, 120)
time.sleep(3.0)

PHASES = [
    (1, 4.0, 'P0 手指全部拿开'),
    (2, 6.0, 'P1 手指贴住第 1 对对管(1cm)'),
    (3, 6.0, 'P2 手指贴住另外那一对(1cm)'),
    (0, 5.0, 'P3 两根手指同时贴住两对'),
]

result = {}
for nbeep, dur, title in PHASES:
    if nbeep == 0:
        beep(600)
    else:
        beeps(nbeep)
    log('  >> %s (%.0fs)' % (title, dur))

    t0 = time.time()
    acc = {}
    k = 0
    while time.time() - t0 < dur - 1.0:
        s = sample(NSAMP)
        for st in ('off', 'L', 'R'):
            acc.setdefault(st, {'PE5': 0, 'PE6': 0, 'PF9': 0, 'PF10': 0})
            for pin in ('PE5', 'PE6', 'PF9', 'PF10'):
                acc[st][pin] += s[st][pin]
        k += 1
        log('     ...%s 第 %d 轮 off:PF9=%d%% PF10=%d%%  亮左:PF9=%d%% PF10=%d%%  亮右:PF9=%d%% PF10=%d%%'
            % (title[:2], k, s['off']['PF9'], s['off']['PF10'],
               s['L']['PF9'], s['L']['PF10'], s['R']['PF9'], s['R']['PF10']))
    time.sleep(min(1.0, dur * 0.2))

    row = {}
    for st in ('off', 'L', 'R'):
        row[st] = {pin: (acc[st][pin] // max(1, k)) for pin in ('PE5', 'PE6', 'PF9', 'PF10')}
    result[title] = row
    log('     轮数=%d  off: PF9=%d%% PF10=%d%% | 亮左灯: PF9=%d%% PF10=%d%% | 亮右灯: PF9=%d%% PF10=%d%%'
        % (k, row['off']['PF9'], row['off']['PF10'],
           row['L']['PF9'], row['L']['PF10'], row['R']['PF9'], row['R']['PF10']))

log()
log('=' * 76)
log('%-24s %-18s %-18s %-18s' % ('分段', '灯全灭 PF9/PF10', '亮左灯 PF9/PF10', '亮右灯 PF9/PF10'))
log('-' * 76)
for title, row in result.items():
    log('%-24s   %3d%% / %3d%%        %3d%% / %3d%%        %3d%% / %3d%%'
        % (title, row['off']['PF9'], row['off']['PF10'],
           row['L']['PF9'], row['L']['PF10'], row['R']['PF9'], row['R']['PF10']))
log('=' * 76)
log('判读方法：')
log('  ① 亮左灯 + 盖左 时 PF9 应该明显变低（0%附近），其余情况应该接近 100%')
log('  ② 亮右灯 + 盖右 时 PF10 应该明显变低')

set_leds(False, False)
t.reset_and_halt()
time.sleep(0.1)
t.resume()
sess.close()

json.dump(result, io.open(r'D:\STM32_Project\_ir_scan_data\verify_v2.json', 'w',
                          encoding='utf-8'), ensure_ascii=False, indent=1)
log('已保存 verify_v2.json，并复位重启了 App')
