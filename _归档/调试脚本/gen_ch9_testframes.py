# -*- coding: utf-8 -*-
"""
生成 chapter9 上板调试用的测试帧清单，并复刻固件解析逻辑逐条验证。
固件规则（main.c）：
    帧：55 FF <len> <func> <data...> [xor]
    len = 功能字(1) + 数据字节数
    功能字 0x07 的数据 = [控制单元][数据...]，控制单元 01=片内 02=片外，数据 1~20 字节
    解析器收满本帧所需参数立刻执行，多出来的字节（含校验字节）被忽略
"""


def xor_frame(bs):
    v = 0
    for b in bs:
        v ^= b
    return v


def build(func, data):
    """按固件定义拼帧，返回 (帧字节, 长度域, 异或校验)"""
    ln = 1 + len(data)
    body = [0x55, 0xFF, ln, func] + list(data)
    return body, ln, xor_frame(body)


def hexs(bs):
    return ' '.join('%02X' % b for b in bs)


# ---------------------------------------------------------- 固件解析器复刻
RX_HEAD0, RX_HEAD1, RX_LEN, RX_FUNC, RX_DATA = range(5)
FRAME_DATA_MAX = 40
DATA_MAX_LEN = 20
DATA_UNIT_INTERNAL = 0x01
DATA_UNIT_EXTERNAL = 0x02


def parse(stream):
    """返回 (功能字, 数据字节列表, 提示)；未收满返回 None"""
    st, ln, func, need, buf = RX_HEAD0, 0, 0, 0, []
    for b in stream:
        if st == RX_HEAD0:
            if b == 0x55:
                st = RX_HEAD1
        elif st == RX_HEAD1:
            st = RX_LEN if b == 0xFF else RX_HEAD0
        elif st == RX_LEN:
            ln = b
            if ln == 0:
                st = RX_HEAD0
            else:
                st = RX_FUNC
        elif st == RX_FUNC:
            func = b
            need = ln - 1
            buf = []
            if need == 0:
                return func, [], '帧收齐（无数据）'
            if need > FRAME_DATA_MAX:
                return None, None, '长度超上限，丢弃'
            st = RX_DATA
        elif st == RX_DATA:
            buf.append(b)
            need -= 1
            if need == 0:
                return func, buf, '帧收齐'
    return None, None, '未收满'


def judge_0707(data):
    """复刻 HandleStoreData 的判断"""
    if len(data) < 1:
        return 'NO UNIT'
    unit, d = data[0], data[1:]
    if len(d) == 0 or len(d) > DATA_MAX_LEN:
        return 'BAD LEN'
    if unit == DATA_UNIT_INTERNAL:
        return '片内 SAVE -> ' + hexs(d)
    if unit == DATA_UNIT_EXTERNAL:
        return '片外 SAVE -> ' + hexs(d)
    return 'BAD UNIT'


STORE_OP = {0x00: '状态保存', 0x01: '状态清除', 0x02: '状态读回'}


def dispatch(func, data):
    """复刻 DispatchFrame 按功能字分发"""
    if func == 0x06:                        # FUNC_CTRL
        if len(data) >= 2:
            return 'CTRL unit=0x%02X state=0x%02X' % (data[0], data[1])
        if len(data) == 1:
            return 'CTRL unit=0x%02X（翻转一次）' % data[0]
        return 'BAD CODE（缺控制单元）'
    if func == 0x07:                        # FUNC_STORE_DATA
        return judge_0707(data)
    if func == 0x08:                        # FUNC_STORE
        if not data:
            return 'BAD CODE（缺操作码）'
        return STORE_OP.get(data[0], 'BAD CODE（未知操作码）')
    if func == 0x09:                        # FUNC_TEXT
        return '文本 -> ' + ''.join(chr(c) if 32 <= c < 127 else '.' for c in data)
    return 'BAD CODE（未知功能字 0x%02X）' % func


# ---------------------------------------------------------- 用例表
CASES = [
    ('任务书原始示例（内部，长度字节按任务书写 03）', 0x07, [0x01, 0x01, 0x02, 0x03, 0x04, 0x05], 'orig'),
    ('内部存储 5 字节（正确帧）', 0x07, [0x01, 0x01, 0x02, 0x03, 0x04, 0x05], None),
    ('外部存储 5 字节（正确帧）', 0x07, [0x02, 0x01, 0x02, 0x03, 0x04, 0x05], None),
    ('内部存储 1 字节（最小）', 0x07, [0x01, 0xAA], None),
    ('外部存储 1 字节（最小）', 0x07, [0x02, 0xAA], None),
    ('内部存储 20 字节（最大）', 0x07, [0x01] + list(range(0x11, 0x25)), None),
    ('外部存储 20 字节（最大）', 0x07, [0x02] + list(range(0x11, 0x25)), None),
    ('内部存储 21 字节（超限，应拒绝）', 0x07, [0x01] + list(range(0x11, 0x26)), None),
    ('未知控制单元 0x03（应拒绝）', 0x07, [0x03, 0x01, 0x02], None),
    ('只有控制单元没有数据（应拒绝）', 0x07, [0x01], None),
    ('控制：右转开（0x06）', 0x06, [0x01, 0x01], None),
    ('控制：右转关（0x06）', 0x06, [0x01, 0x00], None),
    ('状态：读回（0x08）', 0x08, [0x02], None),
    ('未知功能字 0x0A（应拒绝）', 0x0A, [0x01], None),
]

print('=' * 96)
print('chapter9 上板调试帧清单（55 FF <len> <func> <data...> [xor]）')
print('=' * 96)

for name, func, data, tag in CASES:
    body, ln, x = build(func, data)
    if tag == 'orig':
        # 任务书原样：长度字节写 03
        body = [0x55, 0xFF, 0x03, func] + list(data)
        x = xor_frame(body)
    f, d, msg = parse(body + [x])
    verdict = dispatch(f, d) if d is not None else msg
    print()
    print('■ %s' % name)
    print('  发 送 : %s' % hexs(body + [x]))
    print('  长度域: 0x%02X   异或: 0x%02X' % (body[2], x))
    print('  固件  : %s' % verdict)
    if tag == 'orig':
        print('  ⚠ 任务书这行长度字节写 0x03，按固件定义（len=功能字+数据）应为 0x%02X；'
              % (1 + len(data)))
        print('     按 0x03 解析只能吃到 1 个数据字节，所以用下面那条正确帧。')

# ---------------------------------------------------------- 不带校验字节也能跑
print()
print('=' * 96)
print('校验字节可省（固件收满即执行，多余字节忽略）：')
body, ln, x = build(0x07, [0x01, 0x01, 0x02, 0x03, 0x04, 0x05])
f, d, msg = parse(body)
print('  只发 : %s   -> %s' % (hexs(body), judge_0707(d)))
print('  带校验: %s -> %s' % (hexs(body + [x]), judge_0707(parse(body + [x])[1])))
