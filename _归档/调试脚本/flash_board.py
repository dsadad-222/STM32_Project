# -*- coding: utf-8 -*-
"""
flash_board.py —— 一键烧录 0920 固件（换板子后用这个）

★ 为什么不能只用 Keil 或裸 pyocd load：
    2026-09-20 实测踩过一次坑 —— 板子上出现了【半新半旧的拼接固件】：
      前半段(0x08000000~0x080057FF)还是 0918 的老程序 RadarFlash_Full，
      后半段(0x08005800~0x08005ED3)才是新的红外避障程序。
    结果就是：横幅打印的是新工程名，但按键走的还是需求4 的老映射
    （KEY1 回 "SAVED"、KEY2 回 "BEEP"、KEY3 回 "EMPTY"），
    表面看"烧过了"，实际跑的是旧逻辑。
    Keil / pyocd 都支持"只擦要改的扇区"，遇到留在板上的旧镜像就会留下这种拼接产物。

★ 所以本脚本固定走三步，缺一不可：
    ① 整片擦除 chip erase   （把旧镜像连尾巴一起清掉）
    ② 烧录 hex
    ③ 读回 flash 与 hex 逐字节比对，不一致就把区间打出来

用法
    双击【重新烧录固件.bat】；或
    python flash_board.py [--uid <探针UID>] [--keep] [hex路径]
    --keep : 不整片擦除（只在你确定板子上就是本工程时才用）
"""

import argparse
import glob
import io
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(HERE, "flash_board.log")

PATS = ["*直接烧录*.hex", "IrAvoid_Full.hex", "*.hex"]
EXTRA_DIRS = [
    HERE,
    os.path.dirname(HERE),
    os.path.dirname(os.path.dirname(HERE)),
    r"D:\STM32_Project\IrAvoid_Full\Project\Objects",
]
TARGET = "stm32f103ze"

_LOG = io.open(LOG_PATH, "w", encoding="utf-8", newline="\n")


def log(msg=""):
    print(msg, flush=True)
    _LOG.write(str(msg) + "\n")
    _LOG.flush()


def find_hex():
    # 先按"明显是本工程"的命名找，避免误烧别的 hex
    for d in EXTRA_DIRS:
        if not os.path.isdir(d):
            continue
        for pat in ("*直接烧录*.hex", "IrAvoid*.hex", "*红外避障*.hex"):
            for h in sorted(glob.glob(os.path.join(d, pat))):
                if os.path.getsize(h) > 1024:
                    return h
    # 最后才在脚本自己所在目录里宽泛找
    for h in sorted(glob.glob(os.path.join(HERE, "*.hex"))):
        if os.path.getsize(h) > 1024:
            return h
    return None


def tool(name):
    """在同一 venv 里找 pyocd.exe"""
    exe = os.path.join(os.path.dirname(sys.executable), name + ".exe")
    if os.path.isfile(exe):
        return exe
    for c in (r"D:\STM32_AI_Tools\venvs\emb\Scripts\%s.exe" % name, name):
        if c == name or os.path.isfile(c):
            return c
    return None


def run(cmd, timeout=240):
    log("  $ %s" % " ".join(cmd))
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        log("  ✘ 调用失败：%r" % (e,))
        return None, ""
    out = (p.stdout or "") + (p.stderr or "")
    for line in out.splitlines():
        log("    | " + line)
    return p.returncode, out


def hex_image(path):
    """解析 Intel HEX，返回 {相对地址: 字节值}"""
    mem = {}
    for line in io.open(path, encoding="ascii", errors="ignore"):
        line = line.strip()
        if not line.startswith(":") or len(line) < 11:
            continue
        n = int(line[1:3], 16)
        addr = int(line[3:7], 16)
        typ = int(line[7:9], 16)
        if typ != 0:
            continue
        for i in range(n):
            mem[addr + i] = int(line[9 + i * 2: 11 + i * 2], 16)
    return mem


def verify(hexf, uid):
    """读回 flash 逐字节比对"""
    from pyocd.core.helpers import ConnectHelper

    img = hex_image(hexf)
    if not img:
        return False, "hex 解析失败"
    lo, hi = min(img), max(img)
    n = hi - lo + 1

    kw = dict(target_override=TARGET, options={"connect_mode": "halt"})
    if uid:
        kw["unique_id"] = uid
    sess = ConnectHelper.session_with_chosen_probe(**kw)
    if sess is None:
        return False, "找不到探针"
    sess.open()
    try:
        t = sess.target
        t.halt()
        blk = bytes(t.read_memory_block8(0x08000000 + lo, n))
        # 镜像之后到扇区边界也看一遍，确认没有旧镜像残留
        pad_end = ((hi // 0x800) + 1) * 0x800
        pad = bytes(t.read_memory_block8(0x08000000 + hi + 1, pad_end - hi - 1)) \
            if pad_end > hi + 1 else b""
        t.resume()
    finally:
        try:
            sess.close()
        except Exception:
            pass

    diffs = [i for i in range(n) if blk[i] != img[lo + i]]
    log("  镜像范围 0x08000000~0x%08x（%d 字节）" % (0x08000000 + hi, n))
    log("  读回比对：不一致 %d 字节" % len(diffs))
    if diffs:
        groups, s, prev = [], diffs[0], diffs[0]
        for d in diffs[1:]:
            if d - prev > 0x800:
                groups.append((s, prev))
                s = d
            prev = d
        groups.append((s, prev))
        for a, b in groups[:8]:
            log("     0x%08x ~ 0x%08x (%d 字节)"
                % (0x08000000 + lo + a, 0x08000000 + lo + b, b - a + 1))
        return False, "读回与 hex 不一致 %d 字节" % len(diffs)
    if pad and any(b != 0xFF for b in pad):
        log("  ★ 镜像之后到扇区末尾有非 0xFF 残留：%d 字节" % sum(1 for b in pad if b != 0xFF))
        return False, "扇区末尾有旧镜像残留，建议整片擦除后重烧"
    return True, "读回与 hex 完全一致"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("hex", nargs="?", default=None, help="要烧录的 hex（可选）")
    ap.add_argument("--uid", default=None, help="调试探针 UID（只有多个探针时才需要）")
    ap.add_argument("--keep", action="store_true", help="不做整片擦除")
    args = ap.parse_args()

    log("=" * 68)
    log("  烧录 0920 红外避障固件（擦除 -> 烧录 -> 读回校验）")
    log("=" * 68)

    hexf = args.hex or find_hex()
    if not hexf or not os.path.isfile(hexf):
        log("  ✘ 没找到 hex。请把 hex 放到本目录，或手动指定：")
        log("      python flash_board.py  D:/路径/xxx.hex")
        return 3
    log("  固件：%s" % hexf)
    log("  大小：%d 字节" % os.path.getsize(hexf))

    pyocd = tool("pyocd")
    if not pyocd:
        log("  ✘ 没找到 pyocd，请确认 D:\\STM32_AI_Tools\\venvs\\emb 还在")
        return 3

    base = [pyocd]
    if args.uid:
        uid_opt = ["-u", args.uid]
    else:
        uid_opt = []

    # ---- ① 整片擦除 ----
    log()
    if args.keep:
        log("① 跳过整片擦除（--keep）")
    else:
        log("① 整片擦除（把板上可能残留的旧镜像一起清掉）")
        rc, out = run(base + ["erase", "--chip", "-t", TARGET] + uid_opt)
        if rc is None or "error" in out.lower():
            log("  ✘ 擦除失败，检查探针与供电")
            return 3

    # ---- ② 烧录 ----
    log()
    log("② 烧录")
    rc, out = run(base + ["load", hexf, "-t", TARGET] + uid_opt)
    if rc is None or "error" in out.lower():
        log("  ✘ 烧录失败")
        return 3

    # ---- ③ 读回校验 ----
    log()
    log("③ 读回 flash 与 hex 逐字节校验")
    try:
        ok, why = verify(hexf, args.uid)
    except Exception as e:
        log("  ✘ 校验出错：%r" % (e,))
        ok, why = False, "校验异常"

    log()
    log("=" * 68)
    if ok:
        log("  ★★ 烧录成功且校验通过：%s" % why)
        log()
        log("  下一步建议跑一次【换板自检】，确认按键与两路红外都正常。")
    else:
        log("  ✘ 烧录后校验未通过：%s" % why)
        log()
        log("  先试试去掉 --keep 重烧（整片擦除）；还是不行就把本日志发给我。")
    log("=" * 68)
    log()
    log("  日志已存：%s" % LOG_PATH)
    return 0 if ok else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("  已中断")
        sys.exit(3)
