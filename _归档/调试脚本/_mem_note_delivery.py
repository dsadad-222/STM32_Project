# -*- coding: utf-8 -*-
import io
import os

NOTE = u"""

---

## 12:20~12:45 交付阶段：工程包 + 接口文档 + 演示脚本（用户已喊停硬件测试）

### 1. 用户明确叫停反复测试
原话「你到底要测多少次？」——之后**不再做任何硬件判决实验**。
软件侧结论已足够：需求5-1/5-2 全流程（KEY1/2/3 → OLED 行切换 + 串口打印）经模拟按键验证全部正确。

### 2. 交付目录（结构照 0918 模板）
```
C:\\Users\\y7000\\Desktop\\嵌入式\\0920_红外避障传感器采集\\
├── 202417010304智能3班陈相林实现红外避障传感器采集\\
│   ├── STM32_Project\\IrAvoid_Full\\        (2.06 MB，已剔 Objects/Listings/.uvguix*)
│   ├── 红外避障传感器采集_接口文档.docx
│   └── 红外避障传感器采集_演示视频.mp4     ← 等用户录
├── 红外避障传感器采集_直接烧录.hex
└── 红外避障传感器采集_现场演示脚本.md
```
★ 对照发现 **0918 的工程副本里其实留了 Objects/Listings/.uvguix.y7000**（当时没剔干净），这次按规矩剔了。
剔除用 `shutil.copytree(ignore=...)` 一步到位（不要"先全拷再删"，本机删除会进回收站且可能被 safe-delete 拦）。

### 3. 交付副本全量重建验证通过
`UV4.exe -j0 -r IrAvoid_Full.uvprojx`（在交付目录里跑）→ **0 Error(s), 0 Warning(s)**，
`Code=21528 RO-data=2516 RW-data=192 ZI-data=2448`（与源工程一致）。

### 4. ★ 接口文档：在 0918 成品上增量生成（新脚本 `make_ir_doc.py`）
**结论先行：这套 lxml 增量法已经完全成熟，以后每章照抄这个脚本即可。**

0918 文档结构（索引会随文档版本变，脚本里务必按内容校验，别裸用索引）：
- 样式 ID：章标题 = `1`(Normal)、二级 = `3`、三级 = `4`；`ac` = 修订记录那个特殊样式
- 目录是**静态纯文本**（不是域），条目靠 `w:ind left` 缩进：一级 0 / 二级 210 / 三级 420
- 表格规格分布：2 列 ×21 张（全是接口表）、3 列 ×20 张、4 列 ×9 张
- 模板选取（本次实测可用）：
  | 用途 | 索引 | 规格 |
  |---|---|---|
  | 硬件连接表 | body[279] | 4 列（信号/模块/引脚/说明） |
  | 接口表 | body[282] | 2 列，**tr[0..3] = 函数原型/描述/参数/返回值 四种行模板** |
  | 字段表 | body[165] | 3 列 |
  | 门限表 | body[189] | 3 列（宏名/取值/说明） |
  | 区间表 | body[255] | 3 列 |
  | 按键表 | body[296] | 4 列 |
  | 二级标题 | body[288] | 三级标题 body[290] | 正文段 body[289] |
  | 目录锚点 body[73]（3.12.4 行）| 目录条目模板 body[70] |
- **插入位置**：`body` 末尾是**独立 `<w:sectPr>`**（不是嵌在段落 pPr 里），
  所以 `SECT.addprevious(el)` 依次追加即可，顺序天然正确。
- **接口表构造**：不要用通用 build_table，要写 `build_api_table`——4 种行的左列样式不同，
  必须分别 deepcopy 模板的 tr[0..3]。
- **表内单元格默认「两端对齐」**：长中文串塞进窄列会被拉成"字距忽大忽小"的难看样子。
  新增 `force_left(tbl)` 把所有单元格设成 `jc=left`。
  注意 `jc` 在 `pPr` 里有**固定顺序**（在 `ind` 之后、`rPr` 之前），插错位置 Word 会报文档损坏
  ——脚本里用 `_PPR_ORDER` 列表按 schema 顺序定位插入点。

### 5. 自检（必须保留，踩过坑）
- 改前记录：标题样本文集合 / `body` 段落数 / 表格数
- 改后断言：**原有标题一个不丢**（封面标题是刻意替换的，进 `ALLOW_REPLACED` 白名单）、
  标题 +6（1 个 H2 + 5 个 H3）、表格 +6
- 本次数字：标题 56→62、body 段 254→298、表 50→56
- **自检第一次就拦住了**：报"原有标题丢失：超声波测距与外部FLASH存储方案文档（接口）"
  ——正是被我有意改掉的封面标题。**这正说明这套自检有效，别嫌它烦。**

### 6. 目检链路（本机已验证可用）
Word COM 导 PDF，中文路径先 cp 成 ASCII；再 `pymupdf` 渲染指定页。
调用要点：`$w = New-Object -ComObject Word.Application`，`Visible=$false`、`DisplayAlerts=0`，
`Documents.Open($tmp, $false, $true)`（第 3 参 ReadOnly=$true 更安全），
`ExportAsFixedFormat($pdf, 17)`（17 = wdExportFormatPDF）。
本次成品 **44 页**，3.13 章节在第 40~44 页，页脚页码正确。

### 7. 交付校验结果
- 交付 docx md5 = 源 md5（`61b6c1a1d670de25ba4d7411e09b4b46`）
- 回读 `w:tbl = 56`、`w:p = 1828`、含 "3.13" 与 "红外避障"
- 源文件：`D:\\STM32_Project\\docs\\红外避障传感器采集_接口文档.docx`（81986 bytes）

### 8. 剩余
- **演示视频**（用户自己录，唯一待办）→ 见 `<任务>_现场演示脚本.md`
- 录完 → 打同名 zip（`202417010304智能3班陈相林实现红外避障传感器采集.zip`，内容 = 内层文件夹）
"""

for p in (r'C:\Users\y7000\WorkBuddy\2026-08-05-21-53-54\.workbuddy\memory\2026-09-20.md',
          r'C:\Users\y7000\WorkBuddy\2026-08-05-21-53-54\.workbuddy-ai\memory\2026-09-20.md'):
    d = os.path.dirname(p)
    if not os.path.isdir(d):
        os.makedirs(d)
    with io.open(p, 'a', encoding='utf-8', newline='') as f:
        f.write(NOTE)
    print('appended ->', p, os.path.getsize(p))
