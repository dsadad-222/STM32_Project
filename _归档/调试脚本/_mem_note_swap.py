# -*- coding: utf-8 -*-
"""把"换板保证"这一轮的工作写入记忆（双份）"""
import io
import os

NOTE = u"""

---

## 13:05 换板保证：抓到【半新半旧拼接固件】+ 交付两个自检工具

### 0. 用户诉求
原话：「只要测试的时候我换个板子 没问题就好了 这点你要保证」
=> 任务转为：证明工程与板子无关（可移植），并把"换板"这件事的验证动作自动化。

### 1. ★★ 板级兼容性审计结论：工程与具体板子无关
| 检查项 | 结论 |
|---|---|
| 引脚 | 全部来自原理图（发射 PE5/PE6 开漏、接收 PF9/PF10 走 ADC3_IN7/8），无实测凑出来的值 |
| 门限 | 600 / 2000 / 4000 来自物理规律，非按某块板的个体差异标定 |
| 板级硬编码 | grep 无 `本板/临时/hack/TODO/DEBUG`；无 PA0/PA1 旧残留 |
| 空片启动 | 内部数据页 `0x0807F000` 走 checksum、状态页 `0x0807F800` 走 `STORE_MAGIC`，
读不到即按默认值 → **新板空片不会挂、不会误用垃圾数据** |
| W25Q64 缺失 | 打印 `NOT FOUND` 后继续跑，**需求 5（红外）不受影响** |
| 变量地址 | 从 Keil `Listings/IrAvoid_Full.map` 核对：`s_line3Mode=0x20000045`、
`s_irLeft/Right=0x46/0x47`、`s_irLeftValid/RightValid=0x48/0x49`、`s_msg=0x200000E0`、
`s_irL/s_irR=0x20000130/0x13A`（与固化在脚本里的地址逐个对得上） |

### 2. ★★ 抓到真凶：板子上是"半新半旧"的拼接固件（重大发现）
用自检工具模拟按键，回读到的却是：`KEY1→" SAVED"`、`KEY2→" BEEP"`、`KEY3→"MPTY"`、`mode=1/1/0`
—— 这是**需求 4 时代的老按键映射**，不是红外避障固件。但开机横幅又是新工程的。

逐层查下去：
```
① 扫板载 flash 字符串：既有新工程的 "=== IrAvoid Full (" (0x08005A3C) 和修好的
   "按键: KEY1/2/3 ..." (0x08005A8C)，**又有** 0918 老工程的
   "=== RadarFlash Full (" (0x0800516C) → 同一个 flash 里存在两套横幅！
② 板载 flash 与我们构建的镜像逐字节 diff：0x08000000~0x080057FF 全不一样（20620/22528 字节），
   而 0x08005800~0x08005ED3 **完全一致**。
③ 查各工程 hex 范围（决定性证据）：
       RadarFlash_Full.hex  0x00000 ~ 0x054DB   (21724 字节) → 只占满前 11 个扇区 = 0x0000~0x57FF
       IrAvoid_Full.hex     0x00000 ~ 0x05ED3   (24276 字节) → 占 12 个扇区
   0x57FF = 22528 字节 —— 与 diff 出来的"不一致边界"以及历史日志里的
   "identical 22528 bytes" **三个数字完全吻合**。
```
**成因（100% 确认）**：把 `RadarFlash_Full`（0918 那份，镜像较短）下载到板子时，
下载器只擦写它覆盖到的前 11 个扇区，**新工程多出来的第 12 个扇区（0x5800~0x5FFF）没人碰**，
于是板子变成：老代码 + 新字符串尾巴。表现就是"横幅是新的、按键逻辑是旧的"。

### 3. 修复与固化流程
```
pyocd erase --chip -t stm32f103ze                    # ① 整片擦除（连尾巴一起清）
pyocd load IrAvoid_Full.hex -t stm32f103ze           # ② 烧录
读回 flash 与 hex 逐字节比对                          # ③ 校验
```
修复后：`Erased 24576 bytes (12 sectors), programmed 24576 bytes (24 pages), identical 0 bytes`
→ 读回**不一致 0 字节**、镜像之后全 `0xFF`、flash 里再无 `RadarFlash` 残留。
（整片擦除只会清掉数据页/状态页的历史数据，程序开机自动按默认值初始化，无副作用。）

### 4. 交付的新工具（`桌面\\嵌入式\\0920_红外避障传感器采集\\换板自检工具\\`）
| 文件 | 作用 |
|---|---|
| `重新烧录固件.bat` + `flash_board.py` | **整片擦除 → 烧录 → 读回逐字节校验**，打印「读回与 hex 完全一致」才算过；
自动按 `*直接烧录*.hex / IrAvoid*.hex / *红外避障*.hex` 找固件（避免误烧别工程） |
| `换板自检.bat` + `board_accept.py` | SWD 模拟 KEY1/KEY2/KEY3 单击（拉低 PG3/4/5 250ms），读 App 变量出 PASS/FAIL；
含"某路读数太小 → 引导贴住那一对再复测"的分支，区分"前方没东西"与"硬件不行" |

★ `board_accept.py` 的地址**从 map 自动解析**（`^\s+(\w+)\s+0x([0-9a-f]{8})\s+Data\s+(\d+)`），
重新编译后地址漂移也能跟上；解析不到才回退内置实测地址。
实测：修好固件后 **5/5 PASS**。

### 5. 本轮踩到的三个新坑（记牢）
1. **`pyocd load` 只烧"有变化"的扇区**（日志里的 `identical N bytes` 就是在跳过），
   所以任何"板上已有别的工程"的场景都必须先 `erase --chip`，否则必然拼接。
2. **`SetMessage()` 会用空格把缓冲区补齐** → 读回的消息是 `"IR LEFT DONE    "`，
   字符串比对前必须 `.strip()`。（第一次跑自检 3 个 FAIL 全是这个原因，不是固件问题。）
3. 脚本里写中文提示时，**别在双引号字符串里用 ASCII 双引号做强调**（`"贴住复测"`）→
   SyntaxError；用 `「」`。
"""

NOTE2 = u"""

---

## 板级交付铁律（2026-09-20 起生效）

**烧录三步不可省**：`erase --chip` → `load` → **读回 flash 与 hex 逐字节比对**。
理由：keil/pyocd 都是"只擦要改的扇区"，板上残留别的工程时会产生**半新半旧的拼接固件**
（实测案例：0918 `RadarFlash_Full` 镜像 21724 字节只占前 11 扇区 = 0x0000~0x57FF，
下载它之后新工程只更新了第 12 扇区 → 横幅是新的、按键逻辑是旧的）。

- 一键脚本：`D:\\STM32_Project\\flash_board.py`（副本在交付目录 `换板自检工具\\`，
  双击 `重新烧录固件.bat`）。
- **换板/换机验收工具**：`D:\\STM32_Project\\board_accept.py`（双击 `换板自检.bat`）——
  SWD 模拟 KEY1/2/3 单击 + 读 App 变量，出 PASS/FAIL；地址从 `Listings/*.map` 自动解析。
- **哪些板子行为可以判"半新半旧"**：按键回 `SAVED`/`BEEP`/`EMPTY`、`s_line3Mode` 不是 2、
  横幅是新工程名 → 立刻怀疑拼接固件，先 `erase --chip` 再来一遍。
- 板级兼容性已审计通过：引脚全部来自原理图、门限来自物理规律、空片/无 W25Q64 都能正常启动。
"""

for base in (r'C:\\Users\\y7000\\WorkBuddy\\2026-08-05-21-53-54\\.workbuddy',
             r'C:\\Users\\y7000\\WorkBuddy\\2026-08-05-21-53-54\\.workbuddy-ai'):
    d = os.path.join(base, 'memory')
    os.makedirs(d, exist_ok=True)
    p1 = os.path.join(d, '2026-09-20.md')
    with io.open(p1, 'a', encoding='utf-8', newline='') as f:
        f.write(NOTE)
    print('appended ->', p1, os.path.getsize(p1))
    p2 = os.path.join(d, 'MEMORY.md')
    with io.open(p2, 'a', encoding='utf-8', newline='') as f:
        f.write(NOTE2)
    print('appended ->', p2, os.path.getsize(p2))
