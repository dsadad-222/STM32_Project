# -*- coding: utf-8 -*-
import shutil, os, re, glob

SRC = r"D:\STM32_Project\AdcTemp_Full"
DST = r"D:\STM32_Project\SerialCtrl_Std"

if os.path.exists(DST):
    print("DST exists, abort"); raise SystemExit(1)

shutil.copytree(SRC, DST)

# 1. delete drivers not needed + usergui leak + build artifacts
kill = []
for pat in ["oled_drv.*","adc_drv.*","flash_drv.*","key_drv.*","pwm_drv.*",
            "font8x8.*","cn_font16.*"]:
    kill += glob.glob(os.path.join(DST,"Drv_Common",pat))
kill.append(os.path.join(DST,"App_User","cn_msg.h"))
kill.append(os.path.join(DST,"Project","AdcTemp_Full.uvguix.y7000"))
for p in kill:
    if os.path.exists(p):
        os.remove(p); print("del", os.path.basename(p))

# clean build outputs
for sub in ["Objects","Listings","build","DebugConfig"]:
    d = os.path.join(DST,"Project",sub)
    if os.path.isdir(d):
        shutil.rmtree(d); print("rmdir", sub)
# Outputs dir
o = os.path.join(DST,"Outputs")
if os.path.isdir(o):
    shutil.rmtree(o); print("rmdir Outputs")
# old build logs
for f in glob.glob(os.path.join(DST,"Project","build_*.log")):
    os.remove(f)

# 2. patch uvprojx: rename outputs, drop removed source files
px = os.path.join(DST,"Project","AdcTemp_Full.uvprojx")
newpx = os.path.join(DST,"Project","SerialCtrl_Std.uvprojx")
s = open(px, encoding="utf-8").read()
drop = ["oled_drv.c","adc_drv.c","flash_drv.c","key_drv.c","pwm_drv.c","font8x8.c","cn_font16.c"]
def drop_files(xml):
    out, pos = [], 0
    for m in re.finditer(r"<File>.*?</File>", xml, re.S):
        blk = m.group(0)
        if any(d in blk for d in drop):
            out.append((m.start(), m.end()))
    for a,b in reversed(out):
        xml = xml[:a] + xml[b:]
    return xml
s = drop_files(s)
s = s.replace("AdcTemp_Full", "SerialCtrl_Std")
open(newpx,"w",encoding="utf-8").write(s)
os.remove(px)
print("uvprojx ->", os.path.basename(newpx))
n = s.count("<File>")
print("remaining <File> entries:", n)

# 3. also patch uvoptx name if exists
opt = os.path.join(DST,"Project","AdcTemp_Full.uvoptx")
if os.path.exists(opt):
    t = open(opt, encoding="utf-8").read().replace("AdcTemp_Full","SerialCtrl_Std")
    open(os.path.join(DST,"Project","SerialCtrl_Std.uvoptx"),"w",encoding="utf-8").write(t)
    os.remove(opt)
    print("uvoptx renamed")
print("DONE")
