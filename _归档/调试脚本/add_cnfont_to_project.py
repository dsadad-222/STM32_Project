# -*- coding: utf-8 -*-
"""把 cn_font16.c 挂进 Keil 工程的 Drv_Common 组"""
import io
import re

path = r"D:\STM32_Project\AdcTemp_Full\Project\AdcTemp_Full.uvprojx"
with io.open(path, "r", encoding="utf-8") as f:
    src = f.read()

if "cn_font16.c" in src:
    print("cn_font16.c 已在工程里，跳过")
else:
    # 找到 adc_drv.c 的 File 节点，在其后插入 cn_font16.c 节点
    pat = re.compile(
        r"(            <File>\s*\n"
        r"              <FileName>adc_drv\.c</FileName>\s*\n"
        r"              <FileType>1</FileType>\s*\n"
        r"              <FilePath>\.\.\\Drv_Common\\adc_drv\.c</FilePath>\s*\n"
        r"            </File>\s*\n)"
    )
    m = pat.search(src)
    assert m, "没找到 adc_drv.c 的 File 节点"

    node = (
        "            <File>\n"
        "              <FileName>cn_font16.c</FileName>\n"
        "              <FileType>1</FileType>\n"
        "              <FilePath>..\\Drv_Common\\cn_font16.c</FilePath>\n"
        "            </File>\n"
    )
    src = src[:m.end(1)] + node + src[m.end(1):]

    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(src)
    print("已把 cn_font16.c 加入 Drv_Common 组")
