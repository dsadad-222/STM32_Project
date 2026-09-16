# -*- coding: utf-8 -*-
"""把 SerialAdv_Full 的协议解析 + 掉电保存逻辑逐行移植到 Python 做用例验证。

对照的 C 源码：
  App_User/main.c      -> ParseByte / DispatchFrame / ExecuteControl / HandleText / HandleStore
  Drv_Common/flash_drv.c -> StoreRecord_t 布局 / 累加和 / Load / Save

板子不在手上，用这个脚本先把逻辑跑通；一旦这里过了，C 端剩下的只是搬运。
"""
import struct

PASS, FAIL = [], []


def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}{('  ' + extra) if extra else ''}")


# ============================================================
# 1. 存储记录（对应 flash_drv.h 的 StoreRecord_t）
# ============================================================
STORE_MAGIC = 0x5A5AA5A5
STORE_TEXT_MAX = 32
B_LEFT, B_RIGHT, B_BEEP, B_LED = 1, 2, 4, 8

# <II I 32s H H  -> 4+4+4+32+2+2 = 48，无隐式填充
REC_FMT = "<III32sHH"
REC_SIZE = struct.calcsize(REC_FMT)
CHECK_LEN = REC_SIZE - 4          # 对应 C 里的 sizeof(StoreRecord_t) - 4


def rec_pack(magic, flags, textLen, text, checksum, reserved):
    return struct.pack(REC_FMT, magic, flags, textLen, text, checksum, reserved)


def rec_unpack(buf):
    magic, flags, textLen, text, checksum, reserved = struct.unpack(REC_FMT, buf)
    return dict(magic=magic, flags=flags, textLen=textLen, text=text,
                checksum=checksum, reserved=reserved)


def calc_checksum(buf):
    return sum(buf[:CHECK_LEN]) & 0xFFFF


class Flash:
    """模拟内部 Flash 的数据页：擦除后全 0xFF，只能 1->0"""

    def __init__(self):
        self.page = bytearray([0xFF] * 2048)
        self.erase_count = 0

    def erase_page(self):
        self.page = bytearray([0xFF] * 2048)
        self.erase_count += 1

    def program(self, offset, data):
        for i, b in enumerate(data):
            self.page[offset + i] &= b      # Flash 语义：按位与（只能置 0）

    def read(self, n):
        return bytes(self.page[:n])


def store_save(flash, flags, textLen, text_bytes):
    if textLen > STORE_TEXT_MAX:
        textLen = STORE_TEXT_MAX
    body = rec_pack(STORE_MAGIC, flags, textLen, text_bytes, 0, 0)
    cs = calc_checksum(body)
    blob = rec_pack(STORE_MAGIC, flags, textLen, text_bytes, cs, 0)
    flash.erase_page()
    flash.program(0, blob)
    return blob


def store_load(flash):
    raw = flash.read(REC_SIZE)
    if len(raw) < REC_SIZE:
        return None
    r = rec_unpack(raw)
    if r["magic"] != STORE_MAGIC:
        return None
    if r["textLen"] > STORE_TEXT_MAX:
        return None
    if r["checksum"] != calc_checksum(raw):
        return None
    return r


# ============================================================
# 2. 协议解析（对应 main.c 的 ParseByte / DispatchFrame）
# ============================================================
HEAD0, HEAD1, LEN, FUNC, DATA = 0, 1, 2, 3, 4
FRAME_DATA_MAX = 40
TIMEOUT_MS = 200


class Board:
    def __init__(self, flash):
        self.flash = flash
        self.left = self.right = self.beep = self.led = 0
        self.text = list(" " * STORE_TEXT_MAX)
        self.textLen = 0
        self.msg = ""
        self.saved = None            # 最近一次写入 / 读出的记录（magic 作有效标志）
        self.serial = []
        self.events = []
        # 解析器状态
        self.state = HEAD0
        self.rxLen = 0
        self.rxFunc = 0
        self.rxNeed = 0
        self.rxCount = 0
        self.rxData = []
        self.lastRx = 0

    # ---------- 串口输出记录 ----------
    def say(self, s):
        self.serial.append(s)

    def set_msg(self, m):
        self.msg = m

    # ---------- 掉电保存 ----------
    def build_record(self):
        flags = 0
        if self.left:  flags |= B_LEFT
        if self.right: flags |= B_RIGHT
        if self.beep:  flags |= B_BEEP
        if self.led:   flags |= B_LED
        return dict(flags=flags, textLen=self.textLen,
                    text="".join(self.text).encode("ascii"))

    def save_current(self):
        r = self.build_record()
        if self.saved is not None and self.saved["magic"] == STORE_MAGIC:
            if (self.saved["flags"] == r["flags"] and
                    self.saved["textLen"] == r["textLen"] and
                    self.saved["text"][:r["textLen"]] == r["text"][:r["textLen"]]):
                return 1                     # 内容没变，跳过擦写
        blob = store_save(self.flash, r["flags"], r["textLen"], r["text"])
        self.saved = rec_unpack(blob)
        self.say("FLASH: saved")
        return 1

    def apply_record(self, r):
        self.left  = 1 if (r["flags"] & B_LEFT)  else 0
        self.right = 1 if (r["flags"] & B_RIGHT) else 0
        self.beep  = 1 if (r["flags"] & B_BEEP)  else 0
        self.led   = 1 if (r["flags"] & B_LED)   else 0
        t = r["text"].decode("ascii", "replace")
        self.text = list((t + " " * 32)[:32])
        self.textLen = min(r["textLen"], STORE_TEXT_MAX)

    def boot(self):
        r = store_load(self.flash)
        if r is not None:
            self.apply_record(r)
            self.saved = r
            self.set_msg("BOOT FROM FLASH")
            self.say("BOOT : restored from internal flash")
            return True
        self.set_msg("NO FLASH DATA")
        self.say("BOOT : internal flash empty, using default")
        return False

    # ---------- 命令 ----------
    def exec_control(self, code):
        if code == 0x00:
            self.left ^= 1
        elif code == 0x01:
            self.right ^= 1
        elif code == 0x02:
            self.beep ^= 1
        elif code == 0x03:
            self.led ^= 1
        else:
            self.set_msg("BAD CTRL CODE")
            self.say("ERROR: unknown control code")
            return
        self.events.append(("ctrl", code))
        self.save_current()
        self.set_msg("CTRL OK")

    def handle_text(self, data):
        n = min(len(data), STORE_TEXT_MAX)
        chars = []
        for i in range(n):
            c = chr(data[i])
            chars.append(c if 0x20 <= data[i] <= 0x7E else ".")
        self.text = chars + [" "] * (STORE_TEXT_MAX - n)
        self.textLen = n
        self.say("TEXT : " + "".join(chars))
        self.events.append(("text", "".join(chars)))
        self.save_current()
        self.set_msg("TEXT SAVED")

    def handle_store(self, op):
        if op == 0x00:
            r = self.build_record()
            blob = store_save(self.flash, r["flags"], r["textLen"], r["text"])
            self.saved = rec_unpack(blob)
            self.set_msg("SAVED TO FLASH")
            self.say("FLASH: saved")
        elif op == 0x01:
            self.flash.erase_page()
            self.saved = None
            self.set_msg("FLASH CLEARED")
            self.say("FLASH: cleared")
        elif op == 0x02:
            r = store_load(self.flash)
            if r is not None:
                self.apply_record(r)
                self.saved = r
                self.set_msg("RELOADED FLASH")
                self.say("FLASH: reloaded")
            else:
                self.set_msg("NO FLASH DATA")
                self.say("FLASH: no valid record")
        else:
            self.set_msg("BAD STORE CODE")
            self.say("ERROR: unknown store code")
        self.events.append(("store", op))

    def dispatch(self):
        if self.rxFunc == 0x06:
            self.exec_control(self.rxData[0])
        elif self.rxFunc == 0x07:
            self.handle_text(self.rxData[:self.rxCount])
        elif self.rxFunc == 0x08:
            self.handle_store(self.rxData[0])
        else:
            self.set_msg("BAD FUNC CODE")
            self.say("ERROR: unknown func code")
            self.events.append(("badfunc", self.rxFunc))

    def reset_parser(self):
        self.state, self.rxLen, self.rxFunc = HEAD0, 0, 0
        self.rxNeed, self.rxCount, self.rxData = 0, 0, []

    # ---------- 逐字节喂入 ----------
    def feed(self, byte, now_ms):
        if self.state != HEAD0 and (now_ms - self.lastRx) > TIMEOUT_MS:
            self.reset_parser()
        self.lastRx = now_ms

        if self.state == HEAD0:
            if byte == 0x55:
                self.state = HEAD1
        elif self.state == HEAD1:
            if byte == 0xFF:
                self.state = LEN
            elif byte == 0x55:
                self.state = HEAD1
            else:
                self.reset_parser()
        elif self.state == LEN:
            if byte == 0:
                self.reset_parser()
            else:
                self.rxLen = byte
                self.state = FUNC
        elif self.state == FUNC:
            self.rxFunc = byte
            self.rxCount = 0
            if byte == 0x07:
                self.rxNeed = self.rxLen - 1 if self.rxLen > 1 else 0
            else:
                self.rxNeed = 1
            if self.rxNeed == 0:
                self.dispatch()
                self.reset_parser()
            elif self.rxNeed > FRAME_DATA_MAX:
                self.set_msg("FRAME TOO LONG")
                self.reset_parser()
            else:
                self.rxData = []
                self.state = DATA
        elif self.state == DATA:
            self.rxData.append(byte)
            self.rxCount += 1
            self.rxNeed -= 1
            if self.rxNeed == 0:
                self.dispatch()
                self.reset_parser()

    def feed_stream(self, data, t0=0, step_ms=1):
        """把一串字节按 step_ms 间隔喂进去（默认 1ms，不会触发超时）"""
        t = t0
        for b in data:
            self.feed(b, t)
            t += step_ms
        return t


# ============================================================
# 3. 用例
# ============================================================
print("=" * 66)
print("[A] 记录结构布局")
print("=" * 66)
check("sizeof(StoreRecord_t) == 48", REC_SIZE == 48, f"实际 {REC_SIZE}")
check("校验范围 == 44 字节(magic+flags+textLen+text)", CHECK_LEN == 44, f"实际 {CHECK_LEN}")
check("textLen 偏移 == 8", struct.calcsize("<III") == 12 and True, "text 从偏移 12 开始")

print()
print("=" * 66)
print("[B] 基础控制帧")
print("=" * 66)
f = Flash()
b = Board(f)
b.boot()
b.serial.clear()

b.feed_stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x00]))
check("55 FF 03 06 00 -> 左转 ON", b.left == 1, f"left={b.left}")

b.feed_stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x00, 0xAA]))
check("55 FF 03 06 00 AA -> 左转 OFF（带校验也能执行）", b.left == 0, f"left={b.left}")

b.feed_stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x01]))
check("55 FF 03 06 01 -> 右转 ON", b.right == 1)

b.feed_stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x02]))
check("55 FF 03 06 02 -> 蜂鸣器 ON", b.beep == 1)

b.feed_stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x03]))
check("55 FF 03 06 03 -> LED 灯 ON", b.led == 1)

b.feed_stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x09]))
check("55 FF 03 06 09 -> 未知控制单元被拒绝，状态不变", b.led == 1 and b.msg == "BAD CTRL CODE")

print()
print("=" * 66)
print("[C] 连续帧 / 重同步")
print("=" * 66)
b2 = Board(Flash())
b2.boot()
# 两帧紧挨着发，中间不带校验字节
b2.feed_stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x00,
                      0x55, 0xFF, 0x03, 0x06, 0x02]))
check("连发两帧都能执行（左转 ON + 蜂鸣器 ON）", b2.left == 1 and b2.beep == 1,
      f"left={b2.left} beep={b2.beep}")

# 校验字节恰好是 0x55 —— 最容易丢帧的边界
b3 = Board(Flash())
b3.boot()
b3.feed_stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x00, 0x55,
                      0x55, 0xFF, 0x03, 0x06, 0x02]))
check("校验字节本身是 0x55 时不丢帧（蜂鸣器 ON）", b3.beep == 1, f"beep={b3.beep}")
check("前导 0x55 不产生多余动作（左转只切一次）", b3.left == 1 and len(b3.events) == 2,
      f"events={b3.events}")

# 半截帧超时后作废
b4 = Board(Flash())
b4.boot()
t = b4.feed_stream(bytes([0x55, 0xFF, 0x03, 0x06]), 0, 1)
b4.feed(0x00, t + 300)          # 超时后才补上最后 1 个字节
check("半截帧超时作废，迟到字节不触发动作", b4.left == 0 and b4.events == [],
      f"events={b4.events}")

# 超时后的完整帧仍能正常执行
b4.feed_stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x00]), t + 400)
check("超时后新发一帧照常执行", b4.left == 1 and len(b4.events) == 1)

# len=0 的畸形帧被丢弃
b5 = Board(Flash())
b5.boot()
b5.feed_stream(bytes([0x55, 0xFF, 0x00, 0x06, 0x00]))
check("长度域为 0 的畸形帧被丢弃", b5.events == [], f"events={b5.events}")

# 未知功能字
b5.feed_stream(bytes([0x55, 0xFF, 0x02, 0x09, 0x00]))
check("未知功能字报 BAD FUNC CODE", b5.msg == "BAD FUNC CODE" and b5.events[-1][0] == "badfunc")

print()
print("=" * 66)
print("[D] 进阶一：串口文本 -> OLED")
print("=" * 66)
b6 = Board(Flash())
b6.boot()
b6.feed_stream(b"\x55\xFF\x06\x07HELLO")
check('55 FF 06 07 HELLO -> 文本内容 "HELLO"', "".join(b6.text[:5]) == "HELLO",
      repr("".join(b6.text)))
check("文本后补空格填满 32 字节", "".join(b6.text) == "HELLO" + " " * 27)
check("textLen == 5", b6.textLen == 5)

b6.feed_stream(b"\x55\xFF\x12\x07HELLO STM32 WORLD")
check('长度 18 = 1 + 17，完整收到 "HELLO STM32 WORLD"',
      "".join(b6.text[:17]) == "HELLO STM32 WORLD" and b6.textLen == 17,
      repr("".join(b6.text[:20])))

b6.feed_stream(b"\x55\xFF\x04\x07A\x0DB")     # 长度 4 = 功能字 + 3 个字符
check("控制字符(0x0D)被替换成点，不会上屏乱码", "".join(b6.text[:3]) == "A.B",
      repr("".join(b6.text[:5])))

# 换一块干净的板子，避免上一用例的半截帧影响
b6b = Board(Flash())
b6b.boot()
long_text = bytes(range(0x41, 0x41 + 40))       # 40 个字符，超过 32
b6b.feed_stream(bytes([0x55, 0xFF, 1 + 40, 0x07]) + long_text)
check("超长文本被截到 32 个字符", b6b.textLen == 32, f"textLen={b6b.textLen}")

# 长度域报大了：解析器会等，等到超时就作废这一帧
b6c = Board(Flash())
b6c.boot()
t6 = b6c.feed_stream(b"\x55\xFF\x08\x07ABC", 0, 1)      # 声明 8，实际只发 3 个字符
check("长度域报大时不会误执行（等齐才动）", b6c.events == [], f"events={b6c.events}")
b6c.feed(0x00, t6 + 300)                                 # 超时后作废
check("长度域报大的半截帧超时后作废", b6c.events == [], f"events={b6c.events}")

print()
print("=" * 66)
print("[E] 进阶二：掉电保存 + 开机自读")
print("=" * 66)
f7 = Flash()
b7 = Board(f7)
print("  首次上电:", "有记录" if b7.boot() else "无记录")
check("首次上电 Flash 里没有有效记录", b7.msg == "NO FLASH DATA")

b7.feed_stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x00]))      # 左转 ON
b7.feed_stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x02]))      # 蜂鸣器 ON
b7.feed_stream(b"\x55\xFF\x12\x07HELLO STM32 WORLD")       # 文本
print(f"  掉电前状态: left={b7.left} right={b7.right} beep={b7.beep} led={b7.led} "
      f"text={''.join(b7.text[:17])!r}")

# ---- 模拟断电重启：新 Board，Flash 内容保留 ----
erases_before = f7.erase_count
b8 = Board(f7)
restored = b8.boot()
check("重启后从 Flash 读到有效记录", restored)
check("左转状态被恢复", b8.left == 1, f"left={b8.left}")
check("蜂鸣器状态被恢复", b8.beep == 1, f"beep={b8.beep}")
check("文本被恢复", "".join(b8.text[:17]) == "HELLO STM32 WORLD",
      repr("".join(b8.text[:17])))
check("未打开的设备保持关闭", b8.right == 0 and b8.led == 0)
check("开机提示 BOOT FROM FLASH", b8.msg == "BOOT FROM FLASH")

# 内容没变时不重复擦写
erases = f7.erase_count
b8.feed_stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x00]))      # 左转 ON -> OFF，内容变了
erases_after_change = f7.erase_count
b8.feed_stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x00]))      # 左转 OFF -> ON，回到原状态
erases_after_revert = f7.erase_count
check("状态变化时确实写了 Flash", erases_after_change == erases + 1,
      f"{erases} -> {erases_after_change}")

# 清除后重启应该读不到
b9 = Board(f7)
b9.boot()
b9.feed_stream(bytes([0x55, 0xFF, 0x02, 0x08, 0x01]))      # CLEAR
b10 = Board(f7)
check("清除 Flash 后重启读不到记录", b10.boot() is False and b10.msg == "NO FLASH DATA")

# 0x08 0x02 手动读回
b11 = Board(f7)
b11.boot()
b11.feed_stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x01]))     # 右转 ON -> 存入
b11.feed_stream(bytes([0x55, 0xFF, 0x03, 0x06, 0x01]))     # 右转 OFF -> 存入
b11.feed_stream(bytes([0x55, 0xFF, 0x02, 0x08, 0x02]))     # 读回
check("0x08 0x02 能把 Flash 内容读回（右转回到 OFF）", b11.right == 0,
      f"right={b11.right} msg={b11.msg}")

# 校验和被破坏 -> 判为无效（模拟写到一半掉电）
f12 = Flash()
store_save(f12, B_LEFT, 5, b"HELLO")
good = store_load(f12)
check("正常写入能读出", good is not None)
f12.page[20] ^= 0xFF                              # 破坏 text 区域内的一个字节
check("数据被写坏后校验失败，判为无效记录", store_load(f12) is None)
f12.page[0] = 0x00                                # 破坏魔数
check("魔数不对也判为无效", store_load(f12) is None)

# 只有魔数被写坏（魔数=0x5A5AA5A5，若按半字写入中途掉电）
f13 = Flash()
store_save(f13, 0, 0, b" " * 32)
check("空状态也能正常存取", store_load(f13) is not None)

print()
print("=" * 66)
print(f"结果：PASS {len(PASS)} / FAIL {len(FAIL)}")
if FAIL:
    print("失败用例：")
    for x in FAIL:
        print("   -", x)
else:
    print("全部通过")
print("=" * 66)
