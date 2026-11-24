# -*- coding: utf-8 -*-
import re, os
d = r"D:\STM32_Project\SerialCtrl_Std\Project"
px = os.path.join(d, "AdcTemp_Full.uvprojx")
s = open(px, encoding="utf-8").read()
drop = ["oled_drv.c","adc_drv.c","flash_drv.c","key_drv.c","pwm_drv.c","font8x8.c","cn_font16.c"]
spans = []
for m in re.finditer(r"<File>.*?</File>", s, re.S):
    if any(x in m.group(0) for x in drop):
        spans.append((m.start(), m.end()))
for a,b in reversed(spans):
    s = s[:a] + s[b:]
s = s.replace("AdcTemp_Full", "SerialCtrl_Std")
open(os.path.join(d,"SerialCtrl_Std.uvprojx"),"w",encoding="utf-8").write(s)
os.remove(px)
print("dropped file blocks:", len(spans), "| remaining <File>:", s.count("<File>"))
# uvoptx
opt = os.path.join(d,"AdcTemp_Full.uvoptx")
if os.path.exists(opt):
    t = open(opt, encoding="utf-8").read().replace("AdcTemp_Full","SerialCtrl_Std")
    open(os.path.join(d,"SerialCtrl_Std.uvoptx"),"w",encoding="utf-8").write(t)
    os.remove(opt)
    print("uvoptx renamed")
