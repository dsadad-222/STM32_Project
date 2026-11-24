# -*- coding: utf-8 -*-
"""
chapter9 协议与记录格式的等价验证（用 Python 复刻 main.c 的解析逻辑）。

验证两件事：
  1. 帧解析：55 FF <len> 07 <unit> <data...> <xor> 能否按任务书语义正确切分；
     特别是「数据域长度 = 功能字 + 控制单元 + 数据」这条定义，
     以及任务书示例里写的 03 到底该怎么解读。
  2. 记录打包/校验：DataRec_Build / DataRec_Check 的等价实现，
     含边界（1 字节 / 20 字节 / 校验错 / 魔数错）。
"""

FRAME_HEAD0 = 0x55
FRAME_HEAD1 = 0xFF
FUNC_STORE_DATA = 0x07
DATA_UNIT_INTERNAL = 0x01
DATA_UNIT_EXTERNAL = 0x02
DATA_MAX_LEN = 20
FRAME_DATA_MAX = 40

DATA_REC_SIZE = 24
MAGIC0, MAGIC1 = 0x46, 0x53
OFF_LEN, OFF_DATA = 2, 3
OFF_CHECK = OFF_DATA + DATA_MAX_LEN


# ---------------- 复刻 main.c 的解析状态机 ----------------
def parse_frame(bytes_in):
    """返回 (func, data_list) 或 None（解析失败）"""
    state = "HEAD0"
    rx_len = rx_func = rx_need = 0
    rx_data = []

    for b in bytes_in:
        if state == "HEAD0":
            if b == FRAME_HEAD0:
                state = "HEAD1"
        elif state == "HEAD1":
            if b == FRAME_HEAD1:
                state = "LEN"
            elif b == FRAME_HEAD0:
                pass
            else:
                state = "HEAD0"
        elif state == "LEN":
            if b == 0:
                state = "HEAD0"
            else:
                rx_len = b
                state = "FUNC"
        elif state == "FUNC":
            rx_func = b
            rx_data = []
            rx_need = (rx_len - 1) if rx_len > 1 else 0
            if rx_need == 0:
                return rx_func, rx_data
            if rx_need > FRAME_DATA_MAX:
                state = "HEAD0"
            else:
                state = "DATA"
        elif state == "DATA":
            rx_data.append(b)
            rx_need -= 1
            if rx_need == 0:
                return rx_func, rx_data
    return None


# ---------------- 复刻 DataRec_* ----------------
def rec_build(data):
    rec = [0] * DATA_REC_SIZE
    rec[0], rec[1] = MAGIC0, MAGIC1
    rec[OFF_LEN] = len(data)
    for i in range(DATA_MAX_LEN):
        rec[OFF_DATA + i] = data[i] if i < len(data) else 0xFF
    rec[OFF_CHECK] = sum(rec[:OFF_CHECK]) & 0xFF
    return rec


def rec_check(rec):
    if rec[0] != MAGIC0 or rec[1] != MAGIC1:
        return 0
    ln = rec[OFF_LEN]
    if ln == 0 or ln > DATA_MAX_LEN:
        return 0
    if (sum(rec[:OFF_CHECK]) & 0xFF) != rec[OFF_CHECK]:
        return 0
    return ln


def show(title):
    print("\n" + "=" * 68)
    print(title)
    print("=" * 68)


# ============ 1. 帧解析 ============
show("1. 帧解析验证")

payload = [0x01, 0x02, 0x03, 0x04, 0x05]
# 正确帧：数据域长度 = 功能字(1) + 控制单元(1) + 数据(5) = 7
body = [FUNC_STORE_DATA, DATA_UNIT_INTERNAL] + payload
len_ok = len(body)
xor_ok = 0
for b in [FRAME_HEAD0, FRAME_HEAD1, len_ok] + body:
    xor_ok ^= b
frame_ok = [FRAME_HEAD0, FRAME_HEAD1, len_ok] + body + [xor_ok]
print("内部 FLASH 帧: " + " ".join("%02X" % b for b in frame_ok))
r = parse_frame(frame_ok)
if r:
    func, data = r
    unit, d = data[0], data[1:]
    print("  解析 -> func=0x%02X unit=0x%02X data=%s" % (func, unit, " ".join("%02X" % x for x in d)))
    assert func == FUNC_STORE_DATA and unit == DATA_UNIT_INTERNAL and d == payload
    print("  [OK] 与任务书例子 55 FF 03 07 01 01 02 03 04 05 的数据部分一致")
else:
    print("  [FAIL] 解析失败")

# 任务书示例里的长度字节写的是 03 —— 按那个值切会得到什么？
frame_task = [0x55, 0xFF, 0x03, 0x07, 0x01, 0x01, 0x02, 0x03, 0x04, 0x05, 0x00]
r2 = parse_frame(frame_task)
print("\n任务书原样示例: " + " ".join("%02X" % b for b in frame_task))
if r2:
    func, data = r2
    print("  按 len=03 解析 -> func=0x%02X data=%s  (只有 %d 字节)" % (func, " ".join("%02X" % x for x in data), len(data)))
    print("  [注意] 这样切出来的数据只有 1 个字节 0x01，和任务书文字『将 01 02 03 04 05 存到内部FLASH』对不上")
print("  -> 结论：任务书示例里的长度字节 03 是笔误，按文字定义应为 07")

# 外部 FLASH 帧
body2 = [FUNC_STORE_DATA, DATA_UNIT_EXTERNAL] + payload
xor2 = 0
for b in [FRAME_HEAD0, FRAME_HEAD1, len(body2)] + body2:
    xor2 ^= b
frame_ex = [FRAME_HEAD0, FRAME_HEAD1, len(body2)] + body2 + [xor2]
print("\n外部 FLASH 帧: " + " ".join("%02X" % b for b in frame_ex))
r3 = parse_frame(frame_ex)
func, data = r3
print("  解析 -> unit=0x%02X data=%s" % (data[0], " ".join("%02X" % x for x in data[1:])))
assert data[0] == DATA_UNIT_EXTERNAL
print("  [OK]")

# 20 字节最大数据
payload20 = list(range(1, 21))
body3 = [FUNC_STORE_DATA, DATA_UNIT_INTERNAL] + payload20
xor3 = 0
for b in [FRAME_HEAD0, FRAME_HEAD1, len(body3)] + body3:
    xor3 ^= b
frame20 = [FRAME_HEAD0, FRAME_HEAD1, len(body3)] + body3 + [xor3]
r4 = parse_frame(frame20)
func, data = r4
print("\n20 字节数据帧: len=%d, 解析出 %d 字节数据 -> %s" % (len(body3), len(data) - 1,
      "OK" if data[1:] == payload20 else "FAIL"))

# 1 字节最小数据
payload1 = [0xAB]
body4 = [FUNC_STORE_DATA, DATA_UNIT_INTERNAL] + payload1
xor4 = 0
for b in [FRAME_HEAD0, FRAME_HEAD1, len(body4)] + body4:
    xor4 ^= b
frame1 = [FRAME_HEAD0, FRAME_HEAD1, len(body4)] + body4 + [xor4]
r5 = parse_frame(frame1)
func, data = r5
print("1 字节数据帧 : len=%d, 解析出 %d 字节 -> %s" % (len(body4), len(data) - 1,
      "OK" if data[1:] == payload1 else "FAIL"))

# ============ 2. 记录打包/校验 ============
show("2. 记录打包 / 校验验证")
for d in ([0x01, 0x02, 0x03, 0x04, 0x05], [0xAB], list(range(1, 21))):
    rec = rec_build(d)
    ln = rec_check(rec)
    ok = (ln == len(d)) and (rec[OFF_DATA:OFF_DATA + ln] == d)
    print("数据 %2d 字节 -> 记录 %s ... 校验读回 len=%2d  %s" % (
        len(d), " ".join("%02X" % b for b in rec[:8]), ln, "[OK]" if ok else "[FAIL]"))

# 篡改校验
rec = rec_build([0x11, 0x22, 0x33])
rec[OFF_CHECK] ^= 0xFF
print("校验字节被篡改 -> rec_check=%d  %s" % (rec_check(rec), "[OK] 正确拒绝" if rec_check(rec) == 0 else "[FAIL]"))

# 篡改魔数
rec = rec_build([0x11, 0x22, 0x33])
rec[0] = 0x00
print("魔数被篡改     -> rec_check=%d  %s" % (rec_check(rec), "[OK] 正确拒绝" if rec_check(rec) == 0 else "[FAIL]"))

# 空 FLASH（全 0xFF）
rec = [0xFF] * DATA_REC_SIZE
print("空白 FLASH     -> rec_check=%d  %s" % (rec_check(rec), "[OK] 正确拒绝" if rec_check(rec) == 0 else "[FAIL]"))

# 长度越界
rec = rec_build([0x11])
rec[OFF_LEN] = 21
rec[OFF_CHECK] = sum(rec[:OFF_CHECK]) & 0xFF
print("长度写成 21    -> rec_check=%d  %s" % (rec_check(rec), "[OK] 正确拒绝" if rec_check(rec) == 0 else "[FAIL]"))

show("全部验证结束")
