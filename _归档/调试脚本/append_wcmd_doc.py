# -*- coding: utf-8 -*-
"""给 XCOM 清单追加 W 快捷命令一节（保持 UTF-8 BOM + CRLF）。"""
import codecs

P = r'C:\Users\y7000\Desktop\chapter9串口工具\XCOM发送帧清单.txt'

ADD = """
【八、W 快捷命令（ASCII 模式，不用勾 HEX 发送）】

  固件新增 W 命令，在 XCOM 里切成 ASCII 模式直接敲：

      W1DEADBEEF      片内 FLASH 存 DE AD BE EF
      W2AABB          片外 W25Q64 存 AA BB
      W1AA            片内 FLASH 存 AA
      W20102030405    片外 W25Q64 存 01 02 03 04 05

  格式：W + 控制单元（1 = 片内 / 2 = 片外）+ 十六进制数据，回车或换行结束
        数据 1~20 字节（也就是 2~40 个十六进制字符）
        大小写都认，中间可以加空格（W1 DE AD BE EF 也行）

  ★ 效果和发 0x07 协议帧完全一样 —— 走的是同一条存储通路，
    串口回显、屏上提示、错误处理都一致
  ★ 正式演示建议用协议帧（任务书要求）；W 命令适合平时调试，敲起来快

  期望回显：
      W1DEADBEEF -> STORE: internal flash saved -> DE AD BE EF
      W2AABB     -> STORE: external flash saved -> AA BB
"""

raw = open(P, 'rb').read()
text = raw.decode('utf-8-sig').rstrip('\r\n')

if 'W 快捷命令' in text:
    print('already patched, skip')
else:
    text = text + '\r\n' + ADD
    text = text.replace('\r\n', '\n').replace('\n', '\r\n')
    open(P, 'wb').write(codecs.BOM_UTF8 + text.encode('utf-8'))
    print('appended, total %d bytes' % (len(text) + 3))

print('bom =', open(P, 'rb').read(3) == codecs.BOM_UTF8)
