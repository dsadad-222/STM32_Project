# -*- coding: utf-8 -*-
r"""把模板 docx 中「节0 分节符」之后的正文段落全部删掉，只保留分节符与文末 sectPr。

模板结构（word/document.xml 的 w:body 子元素序列）:
    ... 封面 / 修订记录表 / 目录 / 1 简介 / 1.1~1.4 ...
    <w:p>  ← 它的 w:pPr 里带 <w:sectPr>，是「第 1 节的结束分节符」
    2 场景和流程 ... <w:tbl> ... （要删的部分，约 250 段）
    <w:sectPr>  ← w:body 的直接子元素，是最后一节的页面设置（必须保留）

用法:
    python trim_template_body.py <docx路径>
"""
import shutil
import sys
import zipfile
from pathlib import Path

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


def q(tag: str) -> str:
    return f"{{{W}}}{tag}"


def main() -> int:
    path = Path(sys.argv[1]).resolve()
    tmp = path.with_suffix(".tmp.docx")

    zin = zipfile.ZipFile(path, "r")
    xml = zin.read("word/document.xml")
    root = etree.fromstring(xml)
    body = root.find(q("body"))
    if body is None:
        print("ERROR: 没找到 w:body")
        return 1

    children = list(body)
    print(f"body 子元素总数: {len(children)}")

    # 定位「带 pPr/sectPr 的段落」= 分节符所在段
    break_idx = None
    for i, ch in enumerate(children):
        if ch.tag == q("p"):
            ppr = ch.find(q("pPr"))
            if ppr is not None and ppr.find(q("sectPr")) is not None:
                break_idx = i
    if break_idx is None:
        print("ERROR: 没找到分节符所在段落")
        return 1
    print(f"分节符所在段落 = body 子元素 #{break_idx}")

    # 文末 sectPr（w:body 直接子元素）
    final_sectpr = None
    for ch in children:
        if ch.tag == q("sectPr"):
            final_sectpr = ch
    print(f"文末 sectPr: {'找到' if final_sectpr is not None else '没有'}")

    removed = 0
    for ch in children[break_idx + 1:]:
        if ch is final_sectpr:
            continue
        body.remove(ch)
        removed += 1
    print(f"已删除 body 子元素: {removed}")
    print(f"剩余 body 子元素: {len(list(body))}")

    new_xml = etree.tostring(
        root, xml_declaration=True, encoding="UTF-8", standalone=True
    )

    # 只替换 word/document.xml，其余部件原样拷过去
    zout = zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED)
    for item in zin.infolist():
        data = zin.read(item.filename)
        if item.filename == "word/document.xml":
            data = new_xml
        zout.writestr(item, data)
    zout.close()
    zin.close()

    shutil.move(str(tmp), str(path))
    print("OK ->", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
