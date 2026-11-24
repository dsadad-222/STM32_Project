# -*- coding: utf-8 -*-
"""匿名版 SerialAdv_Demo 的接收器 + 存储逻辑移植验证。

对照源码：App_User/main.c (rx_feed / dispatch / on_actuator / on_text / on_nvram)
          Drv_Common/nvstore.c (nv_block_t 布局 / sum / read / write)
匿名版是独立实现（整数阶段号 + 查表分发 + 单一 g_state 位域），不能套用含信息版的结论。
"""
import struct

PASS, FAIL = [], []


def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}{('  ' + extra) if extra else ''}")


# ---------------- nv_block_t ----------------
NV_TAG = 0x5A5AA5A5
NV_TEXT_LEN = 32
B_LEFT, B_RIGHT, B_BEEP, B_STRIP = 1, 2, 4, 8
FMT = "<III32sHH"
REC_SIZE = struct.calcsize(FMT)
assert REC_SIZE == 48, REC_SIZE
SUM_LEN = REC_SIZE - 4


def nv_sum(buf):
    return sum(buf[:SUM_LEN]) & 0xFFFF


class Flash:
    def __init__(self):
        self.page = bytearray([0xFF] * 2048)
        self.erase_count = 0

    def erase(self):
        self.page = bytearray([0xFF] * 2048)
        self.erase_count += 1

    def program(self, off, data):
        for i, b in enumerate(data):
            self.page[off + i] &= b

    def read(self, n):
        return bytes(self.page[:n])


def nv_write(flash, state, nchars, text_b):
    if nchars > NV_TEXT_LEN:
        nchars = NV_TEXT_LEN
    body = struct.pack(FMT, NV_TAG, state, nchars, text_b, 0, 0)
    blob = struct.pack(FMT, NV_TAG, state, nchars, text_b, nv_sum(body), 0)
    flash.erase()
    flash.program(0, blob)
    return blob


def nv_read(flash):
    raw = flash.read(REC_SIZE)
    tag, state, nchars, text, s, spare = struct.unpack(FMT, raw)
    if tag != NV_TAG or nchars > NV_TEXT_LEN or s != nv_sum(raw):
        return None
    return dict(tag=tag, state=state, nchars=nchars, text=text, sum=s, spare=spare)


# ---------------- 接收器 ----------------
ACTS = [(0x00, B_LEFT, "LEFT"), (0x01, B_RIGHT, "RIGHT"),
        (0x02, B_BEEP, "BEEP"), (0x03, B_STRIP, "STRIP")]
RX_CAP, RX_GAP = 40, 200


class Node:
    def __init__(self, flash):
        self.flash = flash
        self.state = 0
        self.text = [" "] * NV_TEXT_LEN
        self.nchars = 0
        self.note = ""
        self.from_nv = 0
        self.shadow = None
        self.serial = []
        self.events = []
        self.stage = 0
        self.declared = 0
        self.fid = 0
        self.need = 0
        self.got = 0
        self.payload = []
        self.last_rx = 0

    def say(self, s):
        self.serial.append(s)

    def note_set(self, s):
        self.note = (s + " " * 16)[:16]

    # ---- nv ----
    def shadow_build(self):
        return dict(state=self.state, nchars=self.nchars,
                    text="".join(self.text).encode("ascii"))

    def persist(self):
        b = self.shadow_build()
        if self.shadow is not None and self.shadow["tag"] == NV_TAG:
            if (self.shadow["state"] == b["state"] and
                    self.shadow["nchars"] == b["nchars"] and
                    self.shadow["text"][:b["nchars"]] == b["text"][:b["nchars"]]):
                return 1
        blob = nv_write(self.flash, b["state"], b["nchars"], b["text"])
        self.shadow = nv_read(self.flash)
        self.say("NV  : committed")
        return 1

    def apply_block(self, blk):
        self.state = blk["state"]
        self.text = list((blk["text"].decode("ascii", "replace") + " " * 32)[:32])
        self.nchars = min(blk["nchars"], NV_TEXT_LEN)

    def boot(self):
        blk = nv_read(self.flash)
        if blk is not None:
            self.apply_block(blk)
            self.shadow = blk
            self.from_nv = 1
            self.note_set("NV DATA LOADED")
            self.say("BOOT: flash block applied")
            return True
        self.shadow = None
        self.from_nv = 0
        self.note_set("NV EMPTY")
        self.say("BOOT: flash empty, defaults in use")
        return False

    # ---- handlers ----
    def on_actuator(self, code):
        hit = None
        for c, bit, label in ACTS:
            if c == code:
                hit = (bit, label)
                break
        if hit is None:
            self.note_set("BAD ACT CODE")
            self.say("ERR : unknown actuator code")
            return
        self.state ^= hit[0]
        self.events.append(("act", code))
        if self.persist():
            self.note_set("ACT OK")
        else:
            self.note_set("NV WRITE ERR")

    def on_text(self):
        n = min(self.got, NV_TEXT_LEN)
        chars = []
        for i in range(n):
            raw = self.payload[i]
            chars.append(chr(raw) if 0x20 <= raw <= 0x7E else ".")
        self.text = chars + [" "] * (NV_TEXT_LEN - n)
        self.nchars = n
        self.say("TEXT: " + "".join(chars))
        self.events.append(("text", "".join(chars)))
        if self.persist():
            self.note_set("TEXT SAVED")
        else:
            self.note_set("NV WRITE ERR")

    def on_nvram(self, op):
        if op == 0x00:
            b = self.shadow_build()
            blob = nv_write(self.flash, b["state"], b["nchars"], b["text"])
            self.shadow = nv_read(self.flash)
            self.note_set("NV COMMITTED")
            self.say("NV  : committed")
        elif op == 0x01:
            self.flash.erase()
            self.shadow = None
            self.note_set("NV WIPED")
            self.say("NV  : wiped")
        elif op == 0x02:
            blk = nv_read(self.flash)
            if blk is not None:
                self.apply_block(blk)
                self.shadow = blk
                self.note_set("NV RELOADED")
                self.say("NV  : reloaded")
            else:
                self.note_set("NV EMPTY")
                self.say("NV  : no valid block")
        else:
            self.note_set("BAD NV CODE")
            self.say("ERR : unknown store code")
        self.events.append(("nv", op))

    def dispatch(self):
        if self.fid == 0x06:
            self.on_actuator(self.payload[0])
        elif self.fid == 0x07:
            self.on_text()
        elif self.fid == 0x08:
            self.on_nvram(self.payload[0])
        else:
            self.note_set("BAD FUNC ID")
            self.say("ERR : unknown function id")
            self.events.append(("badfunc", self.fid))

    def rx_reset(self):
        self.stage = self.declared = self.fid = 0
        self.need = self.got = 0
        self.payload = []

    def feed(self, b, now):
        if self.stage != 0 and (now - self.last_rx) > RX_GAP:
            self.rx_reset()
        self.last_rx = now

        if self.stage == 0:
            if b == 0x55:
                self.stage = 1
        elif self.stage == 1:
            if b == 0xFF:
                self.stage = 2
            elif b == 0x55:
                self.stage = 1
            else:
                self.rx_reset()
        elif self.stage == 2:
            if b == 0:
                self.rx_reset()
            else:
                self.declared = b
                self.stage = 3
        elif self.stage == 3:
            self.fid = b
            self.got = 0
            self.need = (self.declared - 1 if self.declared > 1 else 0) if b == 0x07 else 1
            if self.need == 0:
                self.dispatch(); self.rx_reset()
            elif self.need > RX_CAP:
                self.note_set("FRAME TOO LONG"); self.rx_reset()
            else:
                self.payload = []
                self.stage = 4
        elif self.stage == 4:
            self.payload.append(b)
            self.got += 1
            self.need -= 1
            if self.need == 0:
                self.dispatch(); self.rx_reset()

    def stream(self, data, t0=0, step=1):
        t = t0
        for b in data:
            self.feed(b, t)
            t += step
        return t


print("=" * 66)
print("[A] nv_block_t 布局")
print("=" * 66)
check("sizeof(nv_block_t) == 48", REC_SIZE == 48)
check("sum 覆盖 44 字节", SUM_LEN == 44)

print()
print("=" * 66)
print("[B] 控制帧（查表分发）")
print("=" * 66)
f = Flash()
n = Node(f)
n.boot()
n.serial.clear()

n.stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x00]))
check("55 FF 03 06 00 -> LEFT ON", n.state & B_LEFT, f"state={n.state:#x}")

n.stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x00, 0xAA]))
check("带校验字节也能执行 -> LEFT OFF", (n.state & B_LEFT) == 0, f"state={n.state:#x}")

n.stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x01]))
check("01 -> RIGHT ON", n.state & B_RIGHT)

n.stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x02]))
check("02 -> BEEP ON", n.state & B_BEEP)

n.stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x03]))
check("03 -> STRIP ON", n.state & B_STRIP)

n.stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x09]))
check("未知控制单元 -> BAD ACT CODE，状态不变",
      n.note.strip() == "BAD ACT CODE" and (n.state & B_STRIP))

print()
print("=" * 66)
print("[C] 重同步 / 畸形帧")
print("=" * 66)
n2 = Node(Flash())
n2.boot()
n2.stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x00, 0x55,
                 0x55, 0xFF, 0x03, 0x06, 0x02]))
check("校验字节是 0x55 时不丢帧（两个动作都执行）",
      (n2.state & B_BEEP) and len(n2.events) == 2, f"events={n2.events}")

n3 = Node(Flash())
n3.boot()
t = n3.stream(bytes([0x55, 0xFF, 0x03, 0x06]), 0, 1)
n3.feed(0x00, t + 300)
check("半截帧超时作废", n3.events == [], f"events={n3.events}")

n3.stream(bytes([0x55, 0xFF, 0x00, 0x06, 0x00]), t + 400)
check("长度域为 0 被丢弃", n3.events == [], f"events={n3.events}")

n3.stream(bytes([0x55, 0xFF, 0x02, 0x09, 0x00]), t + 800)
check("未知功能字 -> BAD FUNC ID", n3.events[-1][0] == "badfunc")

print()
print("=" * 66)
print("[D] 文本 -> 面板")
print("=" * 66)
n4 = Node(Flash())
n4.boot()
n4.stream(b"\x55\xFF\x06\x07HELLO")
check('"HELLO" 收到', "".join(n4.text[:5]) == "HELLO", repr("".join(n4.text)))
check("补齐到 32 字节", "".join(n4.text) == "HELLO" + " " * 27)
check("nchars == 5", n4.nchars == 5)

n4.stream(b"\x55\xFF\x12\x07HELLO STM32 WORLD")
check("17 字符完整收到", "".join(n4.text[:17]) == "HELLO STM32 WORLD" and n4.nchars == 17)

n5 = Node(Flash())
n5.boot()
n5.stream(b"\x55\xFF\x04\x07A\x0DB")
check("控制字符替换成点", "".join(n5.text[:3]) == "A.B", repr("".join(n5.text[:5])))

n6 = Node(Flash())
n6.boot()
n6.stream(bytes([0x55, 0xFF, 41, 0x07]) + bytes(range(0x41, 0x41 + 40)))
check("超长文本截到 32", n6.nchars == 32, f"nchars={n6.nchars}")

print()
print("=" * 66)
print("[E] 掉电保存 / 开机自读")
print("=" * 66)
f7 = Flash()
n7 = Node(f7)
check("首次上电无记录", n7.boot() is False and n7.note.strip() == "NV EMPTY")

n7.stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x00]))
n7.stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x02]))
n7.stream(b"\x55\xFF\x12\x07HELLO STM32 WORLD")
print(f"  掉电前: state={n7.state:#x} text={''.join(n7.text[:17])!r}")

n8 = Node(f7)
check("重启读到记录", n8.boot() is True)
check("LEFT 恢复", n8.state & B_LEFT)
check("BEEP 恢复", n8.state & B_BEEP)
check("文本恢复", "".join(n8.text[:17]) == "HELLO STM32 WORLD",
      repr("".join(n8.text[:17])))
check("未开的设备保持关闭", (n8.state & B_RIGHT) == 0 and (n8.state & B_STRIP) == 0)
check("开机提示 NV DATA LOADED", n8.note.strip() == "NV DATA LOADED")

before = f7.erase_count
n8.stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x01]))
check("状态变化时确实擦写了 Flash", f7.erase_count == before + 1,
      f"{before} -> {f7.erase_count}")

n9 = Node(f7)
n9.boot()
n9.stream(bytes([0x55, 0xFF, 0x02, 0x08, 0x02]))
check("nv 0x02 读回成功", n9.note.strip() == "NV RELOADED")

n10 = Node(f7)
n10.boot()
n10.stream(bytes([0x55, 0xFF, 0x02, 0x08, 0x01]))
n11 = Node(f7)
check("nv 0x01 擦除后重启读不到", n11.boot() is False)

# 校验和破坏
f12 = Flash()
nv_write(f12, 0, 5, b"HELLO")
check("正常写入可读", nv_read(f12) is not None)
f12.page[20] ^= 0xFF
check("数据被写坏 -> 判无效", nv_read(f12) is None)
f12.page[0] = 0x00
check("tag 不对 -> 判无效", nv_read(f12) is None)

print()
print("=" * 66)
print(f"结果：PASS {len(PASS)} / FAIL {len(FAIL)}")
if FAIL:
    for x in FAIL:
        print("   -", x)
else:
    print("全部通过")
print("=" * 66)
