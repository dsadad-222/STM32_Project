# -*- coding: utf-8 -*-
"""提取 chapter9 任务书文本，定位协议帧定义与任务需求 2。"""
import pymupdf

SRC = (r'E:\xwechat_files\wxid_ifph2dohbkn729_0e86\msg\file'
       r'\2026-09\chapter9.pdf')

doc = pymupdf.open(SRC)
print('pages =', len(doc))
print()

for i, page in enumerate(doc):
    t = page.get_text().strip()
    if not t:
        continue
    print('=' * 72)
    print('PAGE %d  (%d chars)' % (i + 1, len(t)))
    print('=' * 72)
    print(t[:900])
    print()
