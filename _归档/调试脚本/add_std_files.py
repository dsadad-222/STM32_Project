# -*- coding: utf-8 -*-
import re, os
d = r"D:\STM32_Project\SerialCtrl_Std\Project"
px = os.path.join(d, "SerialCtrl_Std.uvprojx")
s = open(px, encoding="utf-8").read()

assert "key_drv.c" not in s and "pwm_drv.c" not in s

TPL = ('<File><FileName>%s</FileName><FileType>1</FileType>'
       '<FilePath>..\\Drv_Common\\%s</FilePath></File>')
add = TPL % ("key_drv.c", "key_drv.c") + TPL % ("pwm_drv.c", "pwm_drv.c")

m = re.search(r"<File>(?:(?!</File>).)*?led_drv\.c.*?</File>", s, re.S)
assert m, "led_drv block not found"
s = s[:m.end()] + add + s[m.end():]
open(px, "w", encoding="utf-8").write(s)
print("added key_drv.c pwm_drv.c | total <File>:", s.count("<File>"))
