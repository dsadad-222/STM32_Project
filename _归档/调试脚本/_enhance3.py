from PIL import Image
import numpy as np

SRC = (r'E:\xwechat_files\wxid_ifph2dohbkn729_0e86\temp\RWTemp\2026-09'
       r'\9e20f478899dc29eb19741386f9343c8\40207233cc67cf404e7df488a8f95a7d.jpg')

im = Image.open(SRC).convert('L')
W, H = im.size
print('src size', W, H)

x0, y0 = int(W * 0.26), int(H * 0.46)
x1, y1 = int(W * 0.82), int(H * 0.62)
c = im.crop((x0, y0, x1, y1))
c = c.resize((c.width * 3, c.height * 3), Image.LANCZOS)

a = np.asarray(c).astype(np.float32)
lo = float(np.percentile(a, 3.0))
hi = float(np.percentile(a, 99.0))
if hi - lo < 1.0:
    hi = lo + 1.0
a = np.clip((a - lo) / (hi - lo), 0.0, 1.0) * 255.0
Image.fromarray(a.astype(np.uint8)).save(r'D:\STM32_Project\_oled_now.png')
print('crop', (x0, y0, x1, y1), '->', c.size, 'lo=%.1f hi=%.1f' % (lo, hi))
