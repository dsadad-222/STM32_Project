# -*- coding: utf-8 -*-
"""把 main.c 里所有 SetMessage(CN_xxx) 换成 ASCII 短串。

原因：OLED 用 8x8 ASCII 字库（font8x8，覆盖 0x20~0x7E），
CN_xxx 宏是 GBK 中文（每个汉字 2 字节 > 0x7E），
送进 SetMessage 后 OLED_ShowChar 会把每个字节判成非法字符并画成 '?'，
屏上第 4 行就变成一串问号。

串口打印里的 CN_xxx 不动 —— 那些是给串口助手看的，GBK 能正常显示中文。
"""
import shutil

SRC = r'D:\STM32_Project\FlashRW_Full\App_User\main.c'

# 屏上第 4 行用的 ASCII 文案（OLED_COL_MAX = 16，别超）
MAP = {
    'CN_BOOTING':    'BOOTING',
    'CN_BREATH_OFF': 'BREATH OFF',
    'CN_BREATH_ON':  'BREATH ON',
    'CN_BAD_CODE':   'BAD CODE',
    'CN_CTRL_OK':    'CTRL OK',
    'CN_FLASH_ERR':  'FLASH ERR',
    'CN_SAVED':      'SAVED',
    'CN_CLEARED':    'CLEARED',
    'CN_BOOT_FLASH': 'READ FLASH',
    'CN_NO_FLASH':   'NO FLASH DATA',
    'CN_CAL_SKIP':   'CAL SKIP',
    'CN_CAL_OK':     'CAL OK',
    'CN_CAL_CLEAR':  'CAL CLEAR',
}

shutil.copy2(SRC, SRC + '.bak')

data = open(SRC, 'rb').read()
total = 0
for cn, en in MAP.items():
    old = b'SetMessage(' + cn.encode('ascii') + b');'
    new = b'SetMessage("' + en.encode('ascii') + b'");'
    n = data.count(old)
    if n:
        data = data.replace(old, new)
        total += n
        print('%-16s -> %-14s x%d' % (cn, en, n))
    else:
        print('%-16s -- not found' % cn)

open(SRC, 'wb').write(data)
print('total replaced:', total)

# 复查：还有没有漏网的 SetMessage(CN_
left = data.count(b'SetMessage(CN_')
print('remaining SetMessage(CN_):', left)
for line in data.split(b'\n'):
    if b'SetMessage(CN_' in line:
        print('  ', line.strip().decode('ascii', 'replace'))
