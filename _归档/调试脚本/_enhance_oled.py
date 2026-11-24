import pymupdf

SRC = (r'E:\xwechat_files\wxid_ifph2dohbkn729_0e86\temp\RWTemp\2026-09'
       r'\9e20f478899dc29eb19741386f9343c8\3116062ad7800ea7baf57c39a8b9ce02.jpg')

doc = pymupdf.open(SRC)
page = doc[0]

# OLED 面板区域
clip = pymupdf.Rect(275, 615, 545, 775)
mat = pymupdf.Matrix(8, 8)
pix = page.get_pixmap(matrix=mat, clip=clip, colorspace=pymupdf.csGRAY)

w, h = pix.width, pix.height
data = pix.samples
avg = sum(data) / float(len(data))
thr = int(max(25, min(110, avg * 1.15)))

tbl = bytes(255 if i > thr else 0 for i in range(256))
out = data.translate(tbl)

p2 = pymupdf.Pixmap(pymupdf.csGRAY, pymupdf.IRect(0, 0, w, h), False)
p2.set_rect(p2.irect, out)
p2.save(r'D:\STM32_Project\_oled_bw.png')

print('avg=%.1f thr=%d size=%dx%d' % (avg, thr, w, h))
