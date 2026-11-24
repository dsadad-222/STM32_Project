# -*- coding: utf-8 -*-
"""
_ir_bothon.py —— 让左右两颗红外发射管【同时常亮】DUR 秒

用途（两种判灯好坏的现场测试，都要"灯亮着"这个前提）：

  A) 手机摄像头对比法（0 成本，最先做）
     红外光肉眼看不见，但手机摄像头能拍到【紫白色亮斑】。
     两颗同时亮 -> 屏幕上直接并排对比：一颗有亮斑、一颗全黑，一眼定案。
     注意：很多手机【后置】摄像头带红外滤光片(IR-cut)，看不到红外；
           【前置】摄像头多数没有滤镜，用前置更靠谱。

  B) 万用表直流电压法（定位到"哪一段"）
     灯亮时用直流档量 L4 两端（1脚=靠 5V 的阳极 / 2脚=靠 R25 的阴极），
     再量 L5 两端做参照。正常那颗约 1.2~1.4V，坏那颗会明显不同。

蜂鸣器节拍：
    启动       三声短鸣
    每 20 秒   一短鸣（表示"灯还亮着"）
    结束       两声长鸣 -> 灯灭

注意：测试期间【不要按 KEY1/KEY2/KEY3】，按键会让固件自行翻转灯态。
"""

import io
import time

from pyocd.core.helpers import ConnectHelper

UID = '37FF71064E5734360B791543'
DUR = 180.0                    # 默认常亮 180 秒
BEAT = 20.0                    # 心跳间隔

LOG = io.open(r'D:\STM32_Project\_ir_bothon.log', 'w', encoding='utf-8', newline='\n')


def log(m=''):
    print(m, flush=True)
    LOG.write(str(m) + '\n')
    LOG.flush()


GPIOE_CRL = 0x40011800
GPIOE_IDR = 0x40011808
GPIOE_BSRR = 0x40011810
GPIOE_BRR = 0x40011814
GPIOG_CRH = 0x40012004
GPIOG_BSRR = 0x40012010
GPIOG_BRR = 0x40012014
RCC_APB2ENR = 0x40021018
BUZ_PIN = 12

sess = ConnectHelper.session_with_chosen_probe(
    unique_id=UID, target_override='stm32f103ze',
    options={'connect_mode': 'halt'})
sess.open()
t = sess.target


def set_mode(base, pin, val):
    """base 传 CRL 基址；偏移在函数内部算（★ 别再让调用方传 CRH，会重复加 0x04 写进 IDR）"""
    a = base + (0x04 if pin >= 8 else 0x00)
    sh = (pin - 8 if pin >= 8 else pin) * 4
    cur = t.read32(a)
    t.write32(a, (cur & ~(0xF << sh)) | ((val & 0xF) << sh))


def buzz(ms=80):
    t.write32(GPIOG_BSRR, 1 << BUZ_PIN)
    time.sleep(ms / 1000.0)
    t.write32(GPIOG_BRR, 1 << BUZ_PIN)


def led_left(on):
    if on:
        t.write32(GPIOE_BRR, 1 << 5)      # 开漏 ODR=0 -> 拉低 -> 基极拉低 -> 亮
    else:
        t.write32(GPIOE_BSRR, 1 << 5)     # 开漏 ODR=1 -> 高阻 -> 灭


def led_right(on):
    if on:
        t.write32(GPIOE_BRR, 1 << 6)
    else:
        t.write32(GPIOE_BSRR, 1 << 6)


try:
    t.reset_and_halt()
    time.sleep(0.1)
    t.resume()
    time.sleep(1.8)                       # 等固件初始化完（OLED/W25Q64 自检）

    # 时钟 + 引脚模式
    t.write32(RCC_APB2ENR, t.read32(RCC_APB2ENR) | (1 << 6) | (1 << 7))
    set_mode(GPIOG_CRH, BUZ_PIN, 0x3)     # 蜂鸣器 推挽50MHz
    t.write32(GPIOG_BRR, 1 << BUZ_PIN)
    set_mode(GPIOE_CRL, 5, 0x7)           # PE5 开漏（与固件一致）
    set_mode(GPIOE_CRL, 6, 0x7)           # PE6 开漏

    led_left(False)
    led_right(False)
    time.sleep(0.05)

    log('=== 两颗红外发射管【同时常亮】%d 秒 ===' % int(DUR))
    log('  启动前：GPIOE_CRL=0x%08X（PE5/PE6 应为 nibble=7 开漏）'
        % t.read32(GPIOE_CRL))
    log('  启动前：IDR5=%d IDR6=%d（灭=1）'
        % ((t.read32(GPIOE_IDR) >> 5) & 1, (t.read32(GPIOE_IDR) >> 6) & 1))
    log()

    for _ in range(3):
        buzz(70)
        time.sleep(0.08)

    led_left(True)
    led_right(True)
    idr = t.read32(GPIOE_IDR)
    log('  >>>>>> 三声短鸣 = 两颗灯已点亮。现在做这两件事：<<<<<<')
    log('     A) 手机【前置】摄像头对着板子前缘两颗透明 LED，看有没有紫白色亮斑')
    log('     B) 万用表【直流电压档】量 L4 两端 与 L5 两端，对比读数')
    log('  IDR5=%d IDR6=%d（点亮后应为 0，说明引脚确实被拉到地）'
        % ((idr >> 5) & 1, (idr >> 6) & 1))
    log('  参考值：正常那颗灯两端 ≈1.2~1.4V；若 ≈4.5~5V = 该支路没有电流（灯开路/虚焊）')
    log('  每 20 秒一声长鸣报进度；结束两声长鸣')
    log()

    t0 = time.time()
    while time.time() - t0 < DUR:
        time.sleep(BEAT)
        el = time.time() - t0
        buzz(300)
        log('     [%5.1fs] 灯仍亮着... IDR5=%d IDR6=%d'
            % (el, (t.read32(GPIOE_IDR) >> 5) & 1, (t.read32(GPIOE_IDR) >> 6) & 1))

    log()
    log('  常亮阶段结束（共 %.0f 秒）' % (time.time() - t0))
except Exception as e:
    import traceback
    log('  [异常] %r' % (e,))
    log(traceback.format_exc())
finally:
    try:
        led_left(False)
        led_right(False)
        for _ in range(2):
            buzz(500)
            time.sleep(0.25)
        log('  >>>>>> 两声长鸣 = 两颗灯已熄灭 <<<<<<')
        log()
        log('=== 判读 ===')
        log('  手机法：某一颗【完全没有亮斑】-> 那颗(或它的驱动支路)坏了')
        log('  万用表法：灯亮时 L4/L5 两端电压')
        log('        ≈1.2~1.4V -> 该灯导通正常（在发光）')
        log('        ≈4.5~5V   -> 该支路无电流 -> 灯开路/焊点虚焊/R25 断')
        log('        ≈0V       -> 灯击穿短路')
        log('        L4 异常但 L5 正常 -> 故障在 L4 那一路（L4 本体 / 焊点 / R25 / Q2 集电极侧）')
        log()
        log('  已复位，探针释放')
        t.reset_and_halt()
        time.sleep(0.1)
        t.resume()
    except Exception as e:
        log('  [收尾异常] %r' % (e,))
    sess.close()
