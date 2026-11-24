# -*- coding: utf-8 -*-
"""生成 ir_drv.h / ir_drv.c（GBK + CRLF，与工程内其他源码保持一致），
并把 ir_drv.c 注册进 uvprojx 文件列表、把工程改名为 IrAvoid_Full。"""
import io
import os
import re

PROJ = r"D:\STM32_Project\IrAvoid_Full"
DRV = os.path.join(PROJ, "Drv_Common")

H = r'''/**
  ******************************************************************************
  * @file    Drv_Common/ir_drv.h
  * @brief   红外避障对管驱动（板载两路）
  *
  * 硬件说明：
  *   开发板左右两侧各有一对红外对管（D7/D8 接收管 + R17/R18 10K 偏置电阻，
  *   配合 Q1/Q2 SS8550 组成两路反射式检测电路），原理图网络名 P1~P4。
  *   两路输出分别接到 MCU 引脚，见下方宏定义。
  *
  * 电气特性（上板实测确认）：
  *   输出为【反相逻辑】——对管前方有障碍物、反射强时引脚为高电平；
  *   前方空旷、无反射时为低电平。
  *   因此判"有障碍"要看【高】而不是低，写成通用代码时最容易在这里搞反。
  *
  * 引脚确定方法：
  *   用脚本把全部空闲引脚临时配成上拉输入，连续采样 IDR，
  *   同时人为改变对管前方的遮挡状态，观察哪一位跟着变
  *   （脚本见 D:\STM32_Project\_ir_block_test.py）。
  ******************************************************************************
  */

#ifndef __IR_DRV_H
#define __IR_DRV_H

#include "stm32f10x.h"

/* ---------------- 两路对管对应的 MCU 引脚 ---------------- */
#define IR_LEFT_PORT      GPIOA
#define IR_LEFT_PIN       GPIO_Pin_0        /* PA0，同时是 ADC1_IN0 */
#define IR_RIGHT_PORT     GPIOA
#define IR_RIGHT_PIN      GPIO_Pin_1        /* PA1，同时是 ADC1_IN1 */

/* ---------------- 逻辑状态约定 ---------------- */
#define IR_CLEAR          0u                /* 前方无障碍 */
#define IR_BLOCKED        1u                /* 检测到障碍 */

/* ---------------- 对外接口 ---------------- */
void    Ir_Init(void);
uint8_t Ir_ReadRaw(uint8_t isLeft);         /* 读原始电平（1 = 高），调试用 */
uint8_t Ir_IsBlocked(uint8_t isLeft);       /* 1 = 有障碍，0 = 无障碍 */
uint8_t Ir_ReadBoth(void);                  /* bit0 = 左路，bit1 = 右路 */

#endif /* __IR_DRV_H */
'''

C = r'''/**
  ******************************************************************************
  * @file    Drv_Common/ir_drv.c
  * @brief   红外避障对管驱动实现
  ******************************************************************************
  */

#include "ir_drv.h"

/* 两个引脚在同一个端口上，合成一个掩码一起初始化 */
#define IR_ALL_PINS       (IR_LEFT_PIN | IR_RIGHT_PIN)

void Ir_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStructure;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA, ENABLE);

    /* 配成浮空输入：
       板上已经用 R17 / R18 做了外部偏置，这里再开内部上拉/下拉
       会和外部电阻分压，把静态电平拉偏，反而读不准。 */
    GPIO_InitStructure.GPIO_Pin   = IR_ALL_PINS;
    GPIO_InitStructure.GPIO_Mode  = GPIO_Mode_IN_FLOATING;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(IR_LEFT_PORT, &GPIO_InitStructure);
}

uint8_t Ir_ReadRaw(uint8_t isLeft)
{
    if (isLeft != 0u)
    {
        return (GPIO_ReadInputDataBit(IR_LEFT_PORT, IR_LEFT_PIN) != 0) ? 1u : 0u;
    }

    return (GPIO_ReadInputDataBit(IR_RIGHT_PORT, IR_RIGHT_PIN) != 0) ? 1u : 0u;
}

uint8_t Ir_IsBlocked(uint8_t isLeft)
{
    /* 反相逻辑：读到高电平代表有障碍物把红外反射回来了 */
    return (Ir_ReadRaw(isLeft) != 0u) ? IR_BLOCKED : IR_CLEAR;
}

uint8_t Ir_ReadBoth(void)
{
    uint8_t value = 0u;

    if (Ir_IsBlocked(1u) != IR_CLEAR)
    {
        value |= 0x01u;         /* bit0 = 左 */
    }

    if (Ir_IsBlocked(0u) != IR_CLEAR)
    {
        value |= 0x02u;         /* bit1 = 右 */
    }

    return value;
}
'''


def write_src(path, text):
    """工程源码统一 UTF-8；Drv_Common 下的文件用 LF 换行（与同目录其他 .c 一致）"""
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print("写入 %s (%d 字节)" % (os.path.basename(path), os.path.getsize(path)))


write_src(os.path.join(DRV, "ir_drv.h"), H)
write_src(os.path.join(DRV, "ir_drv.c"), C)

# ---------- 注册进 uvprojx ----------
old_proj = os.path.join(PROJ, "Project", "RadarFlash_Full.uvprojx")
new_proj = os.path.join(PROJ, "Project", "IrAvoid_Full.uvprojx")
old_opt = os.path.join(PROJ, "Project", "RadarFlash_Full.uvoptx")
new_opt = os.path.join(PROJ, "Project", "IrAvoid_Full.uvoptx")

if not os.path.isfile(old_proj):
    # 已经改过名了（重复执行），只重写驱动文件就好
    print("[跳过] 工程文件已经是 IrAvoid_Full.uvprojx，本次只重写驱动源码")
    chk = io.open(os.path.join(PROJ, "Project", "IrAvoid_Full.uvprojx"),
                  encoding="utf-8").read()
    print("  OutputName      :", re.search(r"<OutputName>(.*?)</OutputName>", chk).group(1))
    print("  ir_drv.c 已注册 :", "ir_drv.c" in chk)
    raise SystemExit(0)

raw = io.open(old_proj, encoding="utf-8").read()

# 1) 输出名
assert "<OutputName>RadarFlash_Full</OutputName>" in raw
raw = raw.replace("<OutputName>RadarFlash_Full</OutputName>",
                  "<OutputName>IrAvoid_Full</OutputName>")

# 2) 在 Drv_Common 组的最后追加 ir_drv.c（hcsr04_drv.c 之后）
anchor = ('<File><FileName>hcsr04_drv.c</FileName><FileType>1</FileType>'
          '<FilePath>..\\Drv_Common\\hcsr04_drv.c</FilePath></File>')
assert anchor in raw, "没找到 hcsr04_drv.c 的注册点"
add = anchor + ('<File><FileName>ir_drv.c</FileName><FileType>1</FileType>'
                '<FilePath>..\\Drv_Common\\ir_drv.c</FilePath></File>')
raw = raw.replace(anchor, add)

io.open(new_proj, "w", encoding="utf-8", newline="\r\n").write(raw)
print("写入 %s" % os.path.basename(new_proj))

# 3) uvoptx 改名
if os.path.isfile(old_opt):
    opt = io.open(old_opt, encoding="utf-8").read()
    opt = opt.replace("RadarFlash_Full", "IrAvoid_Full")
    io.open(new_opt, "w", encoding="utf-8", newline="\r\n").write(opt)
    os.remove(old_opt)
    print("写入 %s" % os.path.basename(new_opt))

os.remove(old_proj)
print("\n校验:")
chk = io.open(new_proj, encoding="utf-8").read()
print("  OutputName      :", re.search(r"<OutputName>(.*?)</OutputName>", chk).group(1))
print("  ir_drv.c 已注册 :", "ir_drv.c" in chk)
print("  残留旧名        :", chk.count("RadarFlash_Full"))
