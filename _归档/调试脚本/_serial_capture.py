# -*- coding: utf-8 -*-
"""
_serial_capture.py —— 抓串口输出到日志（用于验收需求5-2 的"数据通过串口打印到PC"）

用法：
    python _serial_capture.py                 # 自动找口，抓 20 秒
    python _serial_capture.py COM7 30         # 指定口，抓 30 秒
    python _serial_capture.py COM7 30 "V\n"   # 打开后先发 "V\\n" 再抓

自动找口的思路：优先挑描述里带 USB 转串口特征词的口（CH340 / CP210 / FTDI /
USB-SERIAL / USB 串行），蓝牙虚拟串口和真正的板载 USB-TTL 区分开。
板子上的 USB-TTL 是 U8，接 PA9/PA10，插上板子的 USB 口就会出现新口。
"""

import io
import sys
import time

import serial
import serial.tools.list_ports as lp

BAUD = 115200

USB_HINT = ('ch340', 'ch341', 'cp210', 'ftdi', 'ft232', 'usb-serial', 'usb serial',
            'usb 串行', 'silicon labs', 'prolific', 'pl2303')


def pick_port():
    ports = list(lp.comports())
    print('当前串口：')
    for p in ports:
        mark = ''
        d = (p.description or '').lower()
        if any(h in d for h in USB_HINT):
            mark = '  <== USB 转串口（很可能是开发板）'
        print('   %-6s %s%s' % (p.device, p.description, mark))

    cands = [p for p in ports
             if any(h in (p.description or '').lower() for h in USB_HINT)]
    if not cands:
        cands = [p for p in ports if '蓝牙' not in (p.description or '')]
    if not cands:
        return None
    # 有多个时优先 CH340（板载 U8 常见）
    cands.sort(key=lambda p: 0 if 'ch34' in (p.description or '').lower() else 1)
    return cands[0].device


def main():
    args = sys.argv[1:]
    port = None
    secs = 20.0
    send = None

    if args and args[0].upper().startswith('COM'):
        port = args[0]
        if len(args) > 1:
            secs = float(args[1])
        if len(args) > 2:
            send = args[2]
    else:
        if args:
            secs = float(args[0])
        port = pick_port()

    if port is None:
        print('!! 没找到可用的串口。请把开发板的 USB 口用数据线插到电脑上（板载 USB-TTL 是 U8，'
              '接 PA9/PA10），再重跑本脚本。')
        return 1

    print('打开 %s @ %d/8/N/1，抓 %.0f 秒' % (port, BAUD, secs))
    ser = serial.Serial(port, BAUD, timeout=0.2)
    time.sleep(0.3)
    ser.reset_input_buffer()

    if send:
        payload = send.encode('latin-1').decode('unicode_escape').encode('latin-1')
        ser.write(payload)
        print('已发送 %r' % payload)

    raw = bytearray()
    t0 = time.time()
    while time.time() - t0 < secs:
        chunk = ser.read(4096)
        if chunk:
            raw.extend(chunk)
    ser.close()

    stamp = time.strftime('%H%M%S')
    p_raw = r'D:\STM32_Project\_serial_%s.raw' % stamp
    p_txt = r'D:\STM32_Project\_serial_%s.txt' % stamp
    io.open(p_raw, 'wb').write(bytes(raw))
    io.open(p_txt, 'w', encoding='utf-8', newline='\n').write(
        raw.decode('gbk', errors='replace'))

    print('收到 %d 字节 -> %s' % (len(raw), p_raw))
    print('-------- GBK 解码后的内容 --------')
    print(raw.decode('gbk', errors='replace'))
    print('---------------------------------')
    return 0


if __name__ == '__main__':
    sys.exit(main())
