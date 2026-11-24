# -*- coding: utf-8 -*-
"""
_ir_conn.py —— 判断 PE5/PE6 到底有没有接负载（真正的连通性测试）

为什么之前那招不算数：
    把 PE5 配成【开漏】写 1，IDR 读回 1 —— 这只能说明引脚处于高阻，
    ★ 悬空脚也长这样。所以"IDR 跟着灯态翻"证明不了 PE5 接了东西。

正确的测法：把引脚配成【输入 + 内部下拉】(CRL nibble = 0x8) 再读 IDR。
    * PE5 若真接在 Q2 基极：基极回路经 R30(1K) 通向 PNP 发射极(5V)，
      5V - 0.7V(BE结) = 4.3V 这点电压经过 1K 串到引脚上，
      内部下拉才 40K，压不住 -> 引脚仍读【1】(≈4.2V)。
    * PE5 若是空脚：40K 下拉轻松拉到 0 -> 读【0】。

同时把 PE 口其余脚全部当【对照组】扫一遍：正常悬空脚应当读 0。
再对 PF9/PF10 做同样的事：它们经 10K 上拉到 3V3，下拉时也应读 1。

附带：顺便验证 PE5/PE6 是否 5V 容忍（数据手册 p19 说 FT），
      这里只读不驱动，不会伤片子。
"""

import io
import time

from pyocd.core.helpers import ConnectHelper

UID = '37FF71064E5734360B791543'
LOG = io.open(r'D:\STM32_Project\_ir_conn.log', 'w', encoding='utf-8', newline='\n')


def log(m=''):
    print(m, flush=True)
    LOG.write(m + '\n')
    LOG.flush()


RCC_APB2ENR = 0x40021018
GPIOE_CRL = 0x40011800
GPIOE_CRH = 0x40011804
GPIOE_IDR = 0x40011808
GPIOE_BSRR = 0x40011810
GPIOE_BRR = 0x40011814
GPIOF_CRL = 0x40011C00
GPIOF_CRH = 0x40011C04
GPIOF_IDR = 0x40011C08
GPIOF_BSRR = 0x40011C10
GPIOF_BRR = 0x40011C14

sess = ConnectHelper.session_with_chosen_probe(
    unique_id=UID, target_override='stm32f103ze',
    options={'connect_mode': 'halt'})
sess.open()
t = sess.target
log('=== %s  %s ===' % (t.part_number, t.get_state()))

t.write32(RCC_APB2ENR, t.read32(RCC_APB2ENR) | (1 << 6) | (1 << 7))


def set_mode(base, pin, val):
    a = base + (0x04 if pin >= 8 else 0x00)
    sh = (pin - 8 if pin >= 8 else pin) * 4
    cur = t.read32(a)
    t.write32(a, (cur & ~(0xF << sh)) | ((val & 0xF) << sh))


def idr_ratio(idr_addr, pin, n=120):
    hi = 0
    for _ in range(n):
        hi += (t.read32(idr_addr) >> pin) & 1
    return hi * 100 // n


MODE_IPD = 0x8    # 输入 + 下拉
MODE_IPU = 0x8    # 输入 + 上拉（ODR=1）
MODE_FLOAT = 0x4  # 浮空输入


def probe_pe(pin):
    """返回 (输入下拉时高占比, 浮空时高占比)"""
    base = GPIOE_CRL                         # ★ 必须传 CRL 基址，偏移由 set_mode 算
    set_mode(base, pin, MODE_IPD)            # 输入模式 + 0x8
    t.write32(GPIOE_BRR, 1 << pin)           # ODR=0 -> 下拉
    time.sleep(0.03)
    pd = idr_ratio(GPIOE_IDR, pin)
    set_mode(base, pin, MODE_FLOAT)
    time.sleep(0.03)
    fl = idr_ratio(GPIOE_IDR, pin)
    return pd, fl


log()
log('### A. PE 口全部脚：输入下拉 vs 浮空（悬空脚下拉应读 0）###')
log('    %-6s %-10s %-10s %s' % ('引脚', '下拉高占比', '浮空高占比', '判读'))
pe5 = pe6 = None
for pin in range(0, 16):
    pd, fl = probe_pe(pin)
    if pin == 5:
        pe5 = (pd, fl)
    if pin == 6:
        pe6 = (pd, fl)
    if pin in (5, 6):
        note = '★ 被测对象'
    elif pd >= 80:
        note = '下拉仍为高 -> 该脚外部有上拉/有源'
    elif pd <= 20:
        note = '空脚（对照）'
    else:
        note = '中间态'
    log('    PE%-4d %-10s %-10s %s' % (pin, '%d%%' % pd, '%d%%' % fl, note))

log()
log('### B. PF9 / PF10（经 10K 上拉到 3V3，下拉应仍读高）###')
for pin, name in [(9, 'PF9 (左接收)'), (10, 'PF10(右接收)')]:
    base = GPIOF_CRL                         # ★ 同上：传 CRL 基址
    set_mode(base, pin, MODE_IPD)
    t.write32(GPIOF_BRR, 1 << pin)            # ODR=0 -> 下拉
    time.sleep(0.03)
    pd = idr_ratio(GPIOF_IDR, pin)
    set_mode(base, pin, MODE_FLOAT)
    time.sleep(0.03)
    fl = idr_ratio(GPIOF_IDR, pin)
    ver = '有上拉 -> 接收管/10K 在位' if pd >= 80 else '下拉压住了 -> 该脚可能悬空!'
    log('    %-12s 下拉高占比=%3d%%  浮空高占比=%3d%%   %s' % (name, pd, fl, ver))

log()
log('### C. 结论 ###')
pd5, fl5 = pe5
pd6, fl6 = pe6
log('    PE5: 下拉时高占比 %d%%' % pd5)
if pd5 >= 80:
    log('      -> PE5 【接了负载】: 外部能把引脚拉到高(≈4.2V)，符合"接 PNP 基极回路(5V)"')
else:
    log('      -> ★ PE5 【下拉能压住】= 该脚基本悬空/无有效上拉 -> 发射管驱动电路可能没接上')
log('    PE6: 下拉时高占比 %d%%' % pd6)
if pd6 >= 80:
    log('      -> PE6 【接了负载】: 与 PE6 驱动右发射管"发光有效"的实测一致 ✔')
else:
    log('      -> ★ PE6 【下拉能压住】= 该脚基本悬空（但 PE6 确实能让 PF10 变暗，存疑）')

log()
log('  说明：本次只把引脚配成输入(+内部电阻)读 IDR，没有向外部驱动电流，不会损伤电路。')

# 收尾：把 PE5/PE6 还原成固件原本的开漏，其他脚还原浮空输入
for pin in range(0, 16):
    set_mode(GPIOE_CRL, pin, MODE_FLOAT)
set_mode(GPIOE_CRL, 5, 0x7)
set_mode(GPIOE_CRL, 6, 0x7)
t.write32(GPIOE_BSRR, (1 << 5) | (1 << 6))
for pin in (9, 10):
    set_mode(GPIOF_CRL, pin, 0x0)
t.reset_and_halt()
time.sleep(0.1)
t.resume()
sess.close()
log('  已复位，探针释放')
