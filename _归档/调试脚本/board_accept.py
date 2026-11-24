# -*- coding: utf-8 -*-
"""
board_accept.py —— 0920 红外避障工程【换板验收自检】

用途
    换到另一块 YB-DSF01 板子（或重新烧录）之后，双击一次就得到机器判定的 PASS/FAIL，
    不需要逐条对照 OLED 或串口日志。

原理
    不另写测试代码，而是走【真实交付路径】：
      1) 用 SWD 把 PG3/PG4/PG5 临时配成推挽输出拉低 250ms，模拟一次真实按键单击
         （按键驱动是"轮询 + 20ms 消抖 + 按下沿触发"，所以这样等价于手按）
      2) 直接读 App 自己的变量，看它有没有按预期更新

    需要读的变量地址从 Keil 链接 map 里自动解析，所以换板子/重新编译后地址变了也能跟上；
    解析不到才回退到内置的实测地址。

输出
    控制台 + 同目录 board_accept.log

用法
    · 双击【换板自检.bat】
    · 或命令行： <venv>/python.exe board_accept.py [--map <map路径>] [--uid <探针UID>]
"""

import argparse
import io
import os
import re
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_PATH = os.path.join(HERE, "board_accept.log")

# ---------------------------------------------------------------- 日志
_LOG = io.open(LOG_PATH, "w", encoding="utf-8", newline="\n")


def log(msg=""):
    print(msg, flush=True)
    _LOG.write(str(msg) + "\n")
    _LOG.flush()


# ---------------------------------------------------------------- 寄存器
GPIOG_CRL = 0x40012000
GPIOG_CRH = 0x40012004
GPIOG_BSRR = 0x40012010
GPIOG_BRR = 0x40012014

KEY1_PIN, KEY2_PIN, KEY3_PIN = 3, 4, 5

# 内置回退地址（2026-09-20 实测 map，与源码 IrAvoid_Full 一致）
FALLBACK = {
    "s_line3Mode":   0x20000045,
    "s_irLeft":      0x20000046,
    "s_irRight":     0x20000047,
    "s_irLeftValid": 0x20000048,
    "s_irRightValid": 0x20000049,
    "s_msg":         0x200000E0,
    "s_irL":         0x20000130,
    "s_irR":         0x2000013A,
}
MSG_LEN = 17
IR_SIZE = 10

LEVEL_WORD = {0: "FAR ", 1: "MID ", 2: "NEAR"}

MAP_CANDIDATES = [
    r"D:\STM32_Project\IrAvoid_Full\Project\Listings\IrAvoid_Full.map",
    os.path.join(HERE, "IrAvoid_Full.map"),
]

# ---------------------------------------------------------------- map 解析


def parse_map(path):
    """从 Keil 链接 map 里取全局变量地址。
    符号行格式：
        s_irL                                    0x20000130   Data          10  main.o(.bss)
    """
    want = set(FALLBACK.keys())
    got = {}
    with io.open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = re.match(r"^\s+(\w+)\s+0x([0-9a-fA-F]{8})\s+Data\s+(\d+)\s", line)
            if m and m.group(1) in want:
                got[m.group(1)] = int(m.group(2), 16)
    return got


def resolve_addrs(map_path=None):
    cands = ([map_path] if map_path else []) + MAP_CANDIDATES
    for p in cands:
        if p and os.path.isfile(p):
            got = parse_map(p)
            if len(got) == len(FALLBACK):
                log("变量地址来源：%s" % p)
                return got, p
            log("map 解析不全（%s 只找到 %d/%d 个符号），跳过"
                % (p, len(got), len(FALLBACK)))
    log("变量地址来源：内置实测地址（未找到可用的 .map）")
    return dict(FALLBACK), None


# ---------------------------------------------------------------- SWD 会话


def open_session(uid=None):
    from pyocd.core.helpers import ConnectHelper

    kw = dict(target_override="stm32f103ze", options={"connect_mode": "halt"})
    if uid:
        kw["unique_id"] = uid
    try:
        sess = ConnectHelper.session_with_chosen_probe(**kw)
    except TypeError:
        sess = ConnectHelper.session_with_chosen_probe(
            unique_id=uid, target_override="stm32f103ze",
            options={"connect_mode": "halt"})
    if sess is None:
        raise RuntimeError("没找到调试探针（检查 DAPLink 是否插好、板子是否上电）")
    sess.open()
    return sess


def set_pin(target, port_base, pin, val):
    """把某个引脚的 CRL/CRH 四位模式字改成 val（0x3=推挽输出, 0x8=上拉输入）"""
    a = port_base + (0x04 if pin >= 8 else 0x00)
    sh = (pin - 8 if pin >= 8 else pin) * 4
    cur = target.read32(a)
    target.write32(a, (cur & ~(0xF << sh)) | ((val & 0xF) << sh))


def press_key(target, pin, hold=0.25, settle=0.45):
    """模拟一次真实按键单击：拉低 -> 保持 -> 放开 -> 还原上拉输入"""
    target.halt()
    set_pin(target, GPIOG_CRL, pin, 0x3)          # 推挽输出
    target.write32(GPIOG_BRR, 1 << pin)           # 输出低 = 按下
    target.resume()
    time.sleep(hold)
    target.halt()
    target.write32(GPIOG_BSRR, 1 << pin)          # 放开
    set_pin(target, GPIOG_CRL, pin, 0x8)          # 还原上拉输入
    target.resume()
    time.sleep(settle)


def read_state(target, addr):
    base = addr["s_line3Mode"]
    target.halt()
    try:
        flags = bytes(target.read_memory_block8(base, 5))
        msg = bytes(target.read_memory_block8(addr["s_msg"], MSG_LEN))
        blk = bytes(target.read_memory_block8(addr["s_irL"], 26))
    finally:
        target.resume()
    ir_l = struct.unpack_from("<HHHBBB", blk, 0)
    ir_r = struct.unpack_from("<HHHBBB", blk, addr["s_irR"] - addr["s_irL"])
    text = msg.split(b"\x00")[0].decode("ascii", "replace")
    return {
        "mode": flags[0], "L": ir_l, "R": ir_r, "msg": text,
        "blockedL": flags[1], "blockedR": flags[2],
        "validL": flags[3], "validR": flags[4],
    }


def show(tag, st):
    l, r = st["L"], st["R"]
    st["msg"] = st["msg"].strip()          # SetMessage 会用空格把缓冲区补齐，比对前先去掉
    log("  [%-14s] mode=%d  msg=\"%s\"" % (tag, st["mode"], st["msg"]))
    log("     左 PF9 : dark=%4d lit=%4d diff=%4d level=%s strength=%3d valid=%d"
        % (l[0], l[1], l[2], LEVEL_WORD.get(l[3], "?"), l[4], l[5]))
    log("     右 PF10: dark=%4d lit=%4d diff=%4d level=%s strength=%3d valid=%d"
        % (r[0], r[1], r[2], LEVEL_WORD.get(r[3], "?"), r[4], r[5]))


# ---------------------------------------------------------------- 主流程


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", default=None, help="Keil 链接 map 的路径（可选）")
    ap.add_argument("--uid", default=None, help="调试探针 UID（只有多个探针时才需要）")
    ap.add_argument("--nofront", action="store_true",
                    help="不提示放手在前面（只看按键链路通不通）")
    args = ap.parse_args()

    log("=" * 68)
    log("  0920 红外避障工程 —— 换板验收自检")
    log("=" * 68)
    addr, map_used = resolve_addrs(args.map)

    log()
    if not args.nofront:
        log("请先把一张卡片 / 名片【同时贴在两对对管正前方 1~2cm】（整条前缘都盖住最稳），")
        log("然后回到这个窗口按回车开始。")
        log("（不放手也能跑，只是左右都会显示 FAR，那样只能验按键链路，验不出收发。）")
        log()
        try:
            input(">>> 准备好后按回车开始... ")
        except EOFError:
            pass

    log()
    log("正在连接调试探针 ...")
    try:
        sess = open_session(args.uid)
    except Exception as e:
        log("  ✘ 连接失败：%r" % (e,))
        log()
        log("  请检查：① DAPLink/ST-Link 插好 ② 板子已上电（USB 插上）")
        log("          ③ 若电脑同时插了多个探针，用 --uid <UID> 指定")
        return 2

    t = sess.target
    log("  已连接：%s  状态=%s" % (t.part_number, t.get_state()))

    results = []
    ch_l = ch_r = None
    try:
        # ---------- 1) 复位，等它跑起来 ----------
        log()
        log("### 1. 复位 App，等启动完成 ###")
        t.reset_and_halt()
        time.sleep(0.15)
        t.resume()
        time.sleep(1.8)
        st = read_state(t, addr)
        show("复位基线", st)
        ok0 = (st["mode"] == 0) and (st["validL"] == 0) and (st["validR"] == 0)
        results.append(("上电启动 / 初始状态", ok0,
                        "mode=%d（应为 0）未测标志 validL/R=0" % st["mode"]))

        # ---------- 2) KEY1 -> 测左侧 ----------
        log()
        log("### 2. KEY1 = 测左侧距离 ###")
        press_key(t, KEY1_PIN)
        st1 = read_state(t, addr)
        show("KEY1", st1)
        ok1 = (st1["msg"] == "IR LEFT DONE") and (st1["validL"] == 1)
        results.append(("KEY1 按键 -> 左路测量", ok1,
                        "msg=\"%s\"（应为 IR LEFT DONE）validL=%d"
                        % (st1["msg"], st1["validL"])))

        # ---------- 3) KEY2 -> 测右侧 ----------
        log()
        log("### 3. KEY2 = 测右侧距离 ###")
        press_key(t, KEY2_PIN)
        st2 = read_state(t, addr)
        show("KEY2", st2)
        ok2 = (st2["msg"] == "IR RIGHT DONE") and (st2["validR"] == 1)
        results.append(("KEY2 按键 -> 右路测量", ok2,
                        "msg=\"%s\"（应为 IR RIGHT DONE）validR=%d"
                        % (st2["msg"], st2["validR"])))

        # ---------- 4) KEY3 -> 两路都测（需求5-2） ----------
        log()
        log("### 4. KEY3 = 左右都测（串口打印）###")
        press_key(t, KEY3_PIN)
        st3 = read_state(t, addr)
        show("KEY3", st3)
        ok3 = (st3["msg"] == "IR BOTH DONE") and \
              (st3["validL"] == 1) and (st3["validR"] == 1)
        results.append(("KEY3 按键 -> 两路测量", ok3,
                        "msg=\"%s\"（应为 IR BOTH DONE）valid L/R=%d/%d"
                        % (st3["msg"], st3["validL"], st3["validR"])))

        # ---------- 5) 收发通道判读 ----------
        log()
        log("### 5. 两路收发通道判读 ###")
        th = 600
        dL, dR = st3["L"][2], st3["R"][2]
        ch_l = dL >= th
        ch_r = dR >= th

        def retry_side(is_left):
            """某一路读数太小时，引导你把卡片贴住那一对再测一次，
            以区分"前方本来就没东西"和"确实是这一路硬件不行"。"""
            side = "左" if is_left else "右"
            log()
            log("  · %s路 diff 太小，需要复测才能定性（可能只是前方没东西）" % side)
            log("    请把卡片 / 名片【紧紧贴住%s侧那一对红外对管】，保持不动，然后按回车。" % side)
            log("    （两对对管在超声波那两颗银色圆柱的左右两侧；发射管是透明的，接收管是黑球）")
            try:
                input("    >>> 贴好后按回车继续... ")
            except EOFError:
                return None
            t.resume()
            press_key(t, KEY1_PIN if is_left else KEY2_PIN)
            st = read_state(t, addr)
            show("复测 " + side, st)
            return st["L" if is_left else "R"][2]

        if not args.nofront:
            if not ch_l:
                d2 = retry_side(True)
                if d2 is not None:
                    dL = max(dL, d2)
                    ch_l = dL >= th
            if not ch_r:
                d2 = retry_side(False)
                if d2 is not None:
                    dR = max(dR, d2)
                    ch_r = dR >= th

        if ch_l:
            log("  左路 diff=%d >= %d  ->  ✔ 左发射管 / 左接收管 正常" % (dL, th))
        elif dL <= 40:
            log("  左路 diff=%d ≈ 0     ->  ✘ 贴住了仍然收不到 -> 左发射支路硬件故障" % dL)
            log("       （右路同期 diff=%d，可作对照）" % dR)
        else:
            log("  左路 diff=%d           ->  ~ 有微弱反射（介于 40 与 %d 之间）" % (dL, th))
        if ch_r:
            log("  右路 diff=%d >= %d  ->  ✔ 右发射管 / 右接收管 正常" % (dR, th))
        elif dR <= 40:
            log("  右路 diff=%d ≈ 0     ->  ✘ 贴住了仍然收不到 -> 右发射支路硬件故障" % dR)
        else:
            log("  右路 diff=%d           ->  ~ 有微弱反射" % dR)

        results.append(("右路收发（PF10）", ch_r,
                        "diff=%d，前方有物时应 >= %d" % (dR, th)))
        if not args.nofront:
            results.append(("左路收发（PF9）", ch_l,
                            "diff=%d，前方有物时应 >= %d" % (dL, th)))
        else:
            log("  （--nofront 模式：不做「贴住复测」，两路收发都不判定）")

        # ---------- 收尾 ----------
        log()
        log("### 6. 复位，释放探针 ###")
        t.halt()
        t.write32(GPIOG_BSRR, (1 << KEY1_PIN) | (1 << KEY2_PIN) | (1 << KEY3_PIN))
        t.reset_and_halt()
        time.sleep(0.15)
        t.resume()
    finally:
        try:
            sess.close()
        except Exception:
            pass

    # ---------- 汇总 ----------
    log()
    log("=" * 68)
    log("  验收汇总")
    log("=" * 68)
    npass = 0
    for name, ok, detail in results:
        log("  [%s] %-26s %s" % ("PASS" if ok else "FAIL", name, detail))
        if ok:
            npass += 1
    log()
    log("  通过 %d / %d 项" % (npass, len(results)))
    if npass == len(results):
        log()
        log("  ★★ 这块板子验收通过，可以按计划演示 / 录视频。")
    else:
        log()
        if ch_l is False and ch_r is False:
            log("  ★ 左右两路【都】收不到反射 —— 这不是某一颗发射管的问题：")
            log("    ① 先确认卡片真的同时盖住了两对对管（正前方 1~2cm）")
            log("    ② 若贴住了还是两路都为 0，很可能是这块板子的硬件版本与原理图不同")
            log("       （引脚 PE5/PE6/PF9/PF10 对不上），把本日志发我，我按新板子重查引脚。")
        log("  ★ 其它未通过项：把上面整段（以及 %s）发给我，我来定位。"
            % os.path.basename(LOG_PATH))
    log()
    log("  日志已存：%s" % LOG_PATH)
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log()
        log("  已中断")
        sys.exit(3)
