# -*- coding: utf-8 -*-
"""
_ir_diag.py —— 定位 _ir_verify.py 卡死在哪一步（每步都打日志、所有等待都有上限）

教训：_ir_verify.py 里 `while t.read32(ADC3+CR2) & (1<<3): pass` 是【无界等待】，
      ADC3 只要有一个环节没配对，就会在这里永久自旋；
      而 `| tail -40` 又把 stdout 全缓冲住，所以外面看起来"一点输出都没有"。
      这个版本改成：
        * 每步 print(flush=True) 并同时写日志文件
        * 所有等待都有最大次数上限，超时就打印现场寄存器并退出
"""

import io
import sys
import time

LOG = io.open(r'D:\STM32_Project\_ir_diag.log', 'w', encoding='utf-8', newline='\n')


def log(msg):
    print(msg, flush=True)
    LOG.write(msg + '\n')
    LOG.flush()


log('=== 步骤 0：导入 pyocd ===')
from pyocd.core.helpers import ConnectHelper   # noqa: E402
log('  ok')

UID = '37FF71064E5734360B791543'

log('=== 步骤 1：连接探针（halt）===')
sess = ConnectHelper.session_with_chosen_probe(
    unique_id=UID, target_override='stm32f103ze',
    options={'connect_mode': 'halt'})
sess.open()
t = sess.target
log('  ok: %s  state=%s' % (t.part_number, t.get_state()))

RCC_APB2ENR = 0x40021018
RCC_CFGR    = 0x40021004
GPIOE_CRL   = 0x40011800
GPIOE_BSRR  = 0x40011810
GPIOE_BRR   = 0x40011814
GPIOF_CRH   = 0x40011C04
GPIOG_CRH   = 0x40012004
GPIOG_BSRR  = 0x40012010
GPIOG_BRR   = 0x40012014

ADC3 = 0x40013C00
ADC_SR, ADC_CR1, ADC_CR2, ADC_SMPR1, ADC_SQR3, ADC_DR = (
    0x00, 0x04, 0x08, 0x0C, 0x34, 0x4C)

log('=== 步骤 2：读现场寄存器 ===')
log('  RCC_APB2ENR=%08X  RCC_CFGR=%08X' % (t.read32(RCC_APB2ENR), t.read32(RCC_CFGR)))
log('  GPIOE_CRL =%08X  GPIOF_CRH=%08X' % (t.read32(GPIOE_CRL), t.read32(GPIOF_CRH)))
log('  ADC3 SR=%08X CR1=%08X CR2=%08X' % (t.read32(ADC3 + ADC_SR),
                                          t.read32(ADC3 + ADC_CR1),
                                          t.read32(ADC3 + ADC_CR2)))
log('  GPIOF_IDR=%08X（PF9 位9 / PF10 位10）' % t.read32(0x40011C08))


def nib_addr(addr, pin):
    return addr, (pin if pin < 8 else pin - 8) * 4


def set_pin(addr, pin, val):
    a, sh = nib_addr(addr, pin)
    cur = t.read32(a)
    t.write32(a, (cur & ~(0xF << sh)) | ((val & 0xF) << sh))


log('=== 步骤 3：配 GPIO ===')
clk = t.read32(RCC_APB2ENR)
t.write32(RCC_APB2ENR, clk | (1 << 15) | (1 << 6) | (1 << 7) | (1 << 8))

cfgr = t.read32(RCC_CFGR)
t.write32(RCC_CFGR, (cfgr & ~(3 << 14)) | (2 << 14))     # ADCPRE = /6

set_pin(GPIOG_CRH, 12, 0x3)                 # 蜂鸣器
set_pin(GPIOE_CRL, 5, 0x7)                  # PE5 开漏
set_pin(GPIOE_CRL, 6, 0x7)                  # PE6 开漏
t.write32(GPIOE_BSRR, (1 << 5) | (1 << 6))  # 先灭（高阻）
set_pin(GPIOF_CRH, 9, 0x4)                  # PF9 浮空输入
set_pin(GPIOF_CRH, 10, 0x4)                 # PF10 浮空输入
log('  GPIOE_CRL=%08X  GPIOF_CRH=%08X' % (t.read32(GPIOE_CRL), t.read32(GPIOF_CRH)))

log('=== 步骤 4：ADC3 上电 ===')
t.write32(ADC3 + ADC_CR2, 0x00000001)          # ADON = 1
time.sleep(0.01)
log('  CR2=%08X' % t.read32(ADC3 + ADC_CR2))

log('=== 步骤 5：复位校准（上限 2000 次）===')
t.write32(ADC3 + ADC_CR2, 0x00000001 | (1 << 3))
n = 0
while (t.read32(ADC3 + ADC_CR2) & (1 << 3)) and n < 2000:
    n += 1
log('  RSTCAL 循环 %d 次后 CR2=%08X  %s'
    % (n, t.read32(ADC3 + ADC_CR2), '已清零' if n < 2000 else '★ 超时没清零！'))

log('=== 步骤 6：校准（上限 2000 次）===')
t.write32(ADC3 + ADC_CR2, 0x00000001 | (1 << 2))
n = 0
while (t.read32(ADC3 + ADC_CR2) & (1 << 2)) and n < 2000:
    n += 1
log('  CAL 循环 %d 次后 CR2=%08X  %s'
    % (n, t.read32(ADC3 + ADC_CR2), '已清零' if n < 2000 else '★ 超时没清零！'))

log('=== 步骤 7：配通道 7（PF9）采样时间 239.5 周期 ===')
smpr1 = t.read32(ADC3 + ADC_SMPR1)
smpr1 = (smpr1 & ~(0x7 << 21)) | (0x7 << 21)
smpr1 = (smpr1 & ~(0x7 << 24)) | (0x7 << 24)
t.write32(ADC3 + ADC_SMPR1, smpr1)
t.write32(ADC3 + ADC_SQR3, 7)
t.write32(ADC3 + ADC_SQR3, (t.read32(ADC3 + ADC_SQR3) & ~0x1F) | 7)
log('  SMPR1=%08X SQR3=%08X' % (t.read32(ADC3 + ADC_SMPR1), t.read32(ADC3 + ADC_SQR3)))

log('=== 步骤 8：单次转换（上限 3000 次）===')
cr2 = t.read32(ADC3 + ADC_CR2)
t.write32(ADC3 + ADC_CR2, cr2 | (1 << 22))     # SWSTART
n = 0
while n < 3000:
    if t.read32(ADC3 + ADC_SR) & 0x02:
        break
    n += 1
log('  EOC 等待 %d 次  SR=%08X  %s'
    % (n, t.read32(ADC3 + ADC_SR), 'EOC 置位了' if n < 3000 else '★ EOC 一直没置位！'))
log('  DR=%d' % (t.read32(ADC3 + ADC_DR) & 0x0FFF))

log('=== 步骤 9：三种灯态下读 PF9 / PF10 的数字电平（不用 ADC）===')
for name, l_on, r_on in [('两灯都灭', False, False),
                         ('只亮左灯', True, False),
                         ('只亮右灯', False, True)]:
    t.write32(GPIOE_BSRR if not l_on else GPIOE_BRR, 1 << 5)
    t.write32(GPIOE_BSRR if not r_on else GPIOE_BRR, 1 << 6)
    time.sleep(0.01)
    hi9 = hi10 = 0
    for _ in range(200):
        idr = t.read32(0x40011C08)
        hi9 += (idr >> 9) & 1
        hi10 += (idr >> 10) & 1
    log('  %-10s  PF9 高占比=%3d%%  PF10 高占比=%3d%%'
        % (name, hi9 * 100 // 200, hi10 * 100 // 200))
t.write32(GPIOE_BSRR, (1 << 5) | (1 << 6))

log('=== 步骤 10：收尾 ===')
t.write32(ADC3 + ADC_CR2, 0x00000000)
t.reset_and_halt()
time.sleep(0.1)
t.resume()
sess.close()
log('  已复位重启 App，探针已释放')
log('=== 诊断结束 ===')
