from PIL import Image
import numpy as np

SRC = (r'E:\xwechat_files\wxid_ifph2dohbkn729_0e86\temp\RWTemp\2026-09'
       r'\9e20f478899dc29eb19741386f9343c8\3116062ad7800ea7baf57c39a8b9ce02.jpg')

im = Image.open(SRC).convert('L')
W, H = im.size
print('src size', W, H)

sx = W / 959.25
sy = H / 1279.5


def enhance(x0, y0, x1, y1, zoom, dst):
    box = (int(x0 * sx), int(y0 * sy), int(x1 * sx), int(y1 * sy))
    c = im.crop(box)
    c = c.resize((c.width * zoom, c.height * zoom), Image.LANCZOS)
    a = np.asarray(c).astype(np.float32)
    lo = np.percentile(a, 3.0)
    hi = np.percentile(a, 99.0)
    if hi - lo < 1.0:
        hi = lo + 1.0
    a = np.clip((a - lo) / (hi - lo), 0.0, 1.0) * 255.0
    out = Image.fromarray(a.astype(np.uint8))
    out.save(dst)
    print(dst, out.size, 'lo=%.1f hi=%.1f' % (lo, hi))


enhance(275, 615, 545, 775, 4, r'D:\STM32_Project\_oled_enh.png')
enhance(275, 725, 545, 780, 6, r'D:\STM32_Project\_oled_row4.png')
