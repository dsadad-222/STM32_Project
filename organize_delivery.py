# -*- coding: utf-8 -*-
"""把散落在桌面/嵌入式里的交付物，按「每天一个项目文件夹」归位。

原则：
  * 只做 MOVE（搬移）和 COPY（复制），绝不删除任何文件；
  * 被新版本取代的中间稿统一进 _历史草稿\，不丢；
  * 每一步打印出来，便于核对。
用法：先 --dry-run 看清单，再正式跑。
"""
import argparse
import shutil
import zipfile
from pathlib import Path

DESK = Path(r"C:\Users\y7000\Desktop")
BASE = DESK / "嵌入式"
SRC = Path(r"D:\STM32_Project")

HIST = BASE / "_历史草稿"
TOOL = BASE / "_工具包"
ENV = BASE / "00_环境准备"

P0909_LED = BASE / "0909_LED灯控制"
P0909_HSI = BASE / "0909_HSI配置系统时钟"
P0910_FLOW = BASE / "0910_流水灯架构"
P0910_DWT = BASE / "0910_DWT延时功能"
P0911_SYST = BASE / "0911_SysTick与外部中断"
P0914_KEY = BASE / "0914_按键扫描"
P0915_SER = BASE / "0915_串口数据控制测试"
P0915_ADV = BASE / "0915_串口数据控制测试进阶版"
P0916_ADC = BASE / "0916_ADC内部温度采集"

ALREADY_MAIN = "已有同名文件，跳过"

moves = []       # (src_path, dst_dir, new_name_or_None)
extracts = []    # (zip_path, member, dst_dir)
copies = []      # (src_path, dst_dir, new_name)


def mv(src, dst_dir, name=None):
    moves.append((src, dst_dir, name))


def ex(zp, member, dst_dir):
    extracts.append((zp, member, dst_dir))


def cp(src, dst_dir, name):
    copies.append((src, dst_dir, name))


# ---------------- ① 容器 zip 拆包（都是「一人一天多个任务」的打包） ----------------
ROOT_CONTAINER = BASE / "202417010304智能3班陈相林.zip"
ex(ROOT_CONTAINER, "202417010304智能3班陈相林基于标准库实现LED灯的控制.zip", P0909_LED)
ex(ROOT_CONTAINER, "202417010304智能3班陈相林基于标准库实现按键控制LED.zip", P0909_LED)
ex(ROOT_CONTAINER, "202417010304智能3班陈相林使用HSI配置系统时钟.zip", P0909_HSI)

D0910_CONTAINER = BASE / "9.10" / "202417010304智能3班陈相林.zip"
ex(D0910_CONTAINER, "202417010304智能3班陈相林实现流水灯架构.zip", P0910_FLOW)
ex(D0910_CONTAINER, "202417010304智能3班陈相林配置实现DWT延时功能.zip", P0910_DWT)

# 9.10 文件夹里已经解出来的两份（直接搬）
for f in (BASE / "9.10" / "202417010304智能3班陈相林").glob("*.zip"):
    tgt = P0910_FLOW if "流水灯" in f.name else P0910_DWT
    mv(f, tgt)

# ---------------- ② 各项目 zip ----------------
mv(BASE / "基于标准库实现LED灯的控制.zip", P0909_LED)
mv(BASE / "基于标准库实现按键控制LED.zip", P0909_LED)
mv(BASE / "基于标准库使用HSI配置系统时钟.zip", P0909_HSI)
mv(BASE / "实现流水灯架构.zip", P0910_FLOW)
mv(BASE / "配置实现DWT延时功能.zip", P0910_DWT)

mv(BASE / "基于标准库实现systick的编程和外部中断控制测试.zip", P0911_SYST)
mv(BASE / "202417010304智能3班陈相林实现systick的编程和外部中断控制测试.zip", P0911_SYST)

mv(BASE / "基于标准库实现按键扫描短按长按和单击双击测试.zip", P0914_KEY)
mv(BASE / "202417010304智能3班陈相林实现按键扫描短按长按和单击双击测试.zip", P0914_KEY)

# 串口基础版
mv(BASE / "202417010304智能3班陈相林实现串口数据控制测试.zip", P0915_SER)
# 串口进阶版（含信息版 + 匿名版）
mv(BASE / "202417010304智能3班陈相林实现串口数据控制测试进阶版.zip", P0915_ADV)
mv(BASE / "基于标准库实现串口数据控制测试进阶版.zip", P0915_ADV)
# 这个文件名叫「基础版」，实测内容含 OLED + Flash，实为进阶版 —— 归到进阶版并改名说明
mv(BASE / "基于标准库实现串口数据控制测试.zip", P0915_ADV,
   "基于标准库实现串口数据控制测试_实测为进阶版内容.zip")

# ---------------- ③ 文档与交付物 ----------------
# chapter7 串口
mv(BASE / "串口数据控制测试_接口文档_v5.docx", P0915_SER, "串口数据控制测试_接口文档.docx")
mv(DESK / "串口数据控制测试_上台汇报稿.md", P0915_SER)
mv(DESK / "串口数据控制测试_完成进度汇报.md", P0915_SER)
mv(BASE / "202417010304智能3班陈相林实现串口数据控制测试", P0915_SER, "源码目录_SerialCtrl_Full")

# chapter8 ADC（文档为新生成，用 copy 以免动到工程里的源文件）
cp(SRC / "docs" / "ADC内部温度采集_接口文档_v2.docx", P0916_ADC, "ADC内部温度采集_接口文档.docx")
cp(SRC / "docs" / "ADC内部温度采集_上台汇报稿.md", P0916_ADC, "ADC内部温度采集_上台汇报稿.md")
mv(BASE / "ADC温度修复版_直接烧录.hex", P0916_ADC)
mv(BASE / "Diag_Min_最小固件.hex", P0916_ADC)
mv(BASE / "chapter8_使用手册.md", P0916_ADC, "ADC内部温度采集_使用手册.md")

# 预览图
PREV = P0916_ADC / "预览图"
for f in BASE.glob("*.png"):
    mv(f, PREV)

# ---------------- ④ 环境准备 / 工具包 ----------------
mv(BASE / "幼专培训_Keil5安装步骤.txt", ENV)
mv(BASE / "stm32-stdlib-coursework.zip", TOOL)

# ---------------- ⑤ 历史草稿（被新版本取代的中间稿） ----------------
for n in ("串口数据控制测试_接口文档_v3.docx", "串口数据控制测试_接口文档_v4.docx",
          "串口数据控制测试_接口文档_完整版.docx", "ADC内部温度采集_接口文档.docx"):
    mv(BASE / n, HIST)
mv(DESK / "串口数据控制测试_接口文档_v3.docx", HIST)
mv(DESK / "ADC内部温度采集_上台汇报稿.md", HIST,
   "ADC内部温度采集_上台汇报稿_旧版（98℃归因已作废）.md")
# 容器 zip 与空壳文件夹进历史（两个容器同名，第二个改名避免撞车）
mv(ROOT_CONTAINER, HIST)
mv(D0910_CONTAINER, HIST, "202417010304智能3班陈相林_9.10提交包.zip")
mv(BASE / "9.10", HIST, "9.10_旧目录_已拆分")


# ============================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    for d in (P0909_LED, P0909_HSI, P0910_FLOW, P0910_DWT, P0911_SYST, P0914_KEY,
              P0915_SER, P0915_ADV, P0916_ADC, PREV, HIST, TOOL, ENV):
        d.mkdir(parents=True, exist_ok=True)

    print("=" * 78)
    print("① 从容器 zip 里解出当日各任务包")
    for zp, member, dst in extracts:
        # 容器里的成员带一层根目录前缀（如 202417010304智能3班陈相林/xxx.zip），
        # 这里按文件名匹配，避免写死前缀。
        base = Path(member).name
        out = dst / base
        if not zp.exists():
            print(f"  {'SKIP(容器已归档)':12s} {base}")
            continue
        with zipfile.ZipFile(zp) as src:          # 用完必须关，否则后面搬不动容器 zip
            hit = [n for n in src.namelist() if Path(n).name == base and not n.endswith("/")]
            if not hit:
                print(f"  NOTFOUND     {base}")
                continue
            real = hit[0]
            mark = "SKIP(已存在)" if out.exists() else "EXTRACT"
            print(f"  {mark:12s} {base}")
            if a.dry_run or out.exists():
                continue
            with src.open(real) as fin, open(out, "wb") as fout:
                shutil.copyfileobj(fin, fout)

    print()
    print("② 搬移 zip / 文档 / 交付物")
    for src, dst, name in moves:
        if not src.exists():
            print(f"  MISSING      {src}")
            continue
        out = dst / (name or src.name)
        if out.exists():
            print(f"  SKIP(已存在) {src.name}  ->  {dst.name}/{out.name}")
            continue
        print(f"  MOVE         {src.name}  ->  {dst.name}/{out.name}")
        if not a.dry_run:
            shutil.move(str(src), str(out))

    print()
    print("③ 复制新生成的文档")
    for src, dst, name in copies:
        out = dst / name
        if not src.exists():
            print(f"  MISSING      {src}")
            continue
        print(f"  COPY         {src.name}  ->  {dst.name}/{name}  ({src.stat().st_size} B)")
        if not a.dry_run:
            shutil.copy2(str(src), str(out))

    print()
    print("dry-run 结束，未改动任何文件。" if a.dry_run else "全部完成。")


if __name__ == "__main__":
    main()
