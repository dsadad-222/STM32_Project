# -*- coding: utf-8 -*-
"""通用 uvprojx 补丁：改 OutputName，并往指定分组里补源文件。

用法:
    python patch_uvprojx_generic.py <工程目录> <工程名> <分组名> <文件1> <文件2> ...
"""
import re, io, sys, os


def main():
    proj_dir, proj_name, group = sys.argv[1], sys.argv[2], sys.argv[3]
    new_files = sys.argv[4:]

    P = os.path.join(proj_dir, "Project", proj_name + ".uvprojx")
    s = io.open(P, encoding="utf-8", errors="ignore").read()
    orig_len = len(s)

    # 1) 输出名
    s = re.sub(r"<OutputName>.*?</OutputName>",
               f"<OutputName>{proj_name}</OutputName>", s, count=1)
    assert f"<OutputName>{proj_name}</OutputName>" in s, "OutputName 未替换"

    # 2) 分组补文件
    m = re.search(r"(<Group>\s*<GroupName>" + re.escape(group) + r"</GroupName>.*?)(</Group>)",
                  s, re.S)
    assert m, f"没找到分组 {group}"
    block = m.group(1)

    extra = ""
    for fn in new_files:
        if fn in block:
            continue
        extra += (
            '            <File>\r\n'
            f'              <FileName>{fn}</FileName>\r\n'
            '              <FileType>1</FileType>\r\n'
            f'              <FilePath>..\\Drv_Common\\{fn}</FilePath>\r\n'
            '            </File>\r\n'
        )

    if extra:
        idx = block.rfind("</File>") + len("</File>") + 2
        insert_at = m.start(1) + idx
        s = s[:insert_at] + extra + s[insert_at:]

    io.open(P, "w", encoding="utf-8", newline="").write(s)
    print(f"patched -> {P}")
    print("改动字节数 =", len(s) - orig_len)
    print("新增文件 =", new_files)


if __name__ == "__main__":
    main()
