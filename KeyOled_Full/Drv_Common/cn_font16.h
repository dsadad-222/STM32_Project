/**
  ******************************************************************************
  * @file    Drv_Common/cn_font16.h
  * @brief   16x16 汉字点阵字库（只含本工程用到的字，按需生成）
  *
  *          字形由 PC 端 gen_cn_font.py 用 Windows 宋体取模生成。
  *          每个字 32 字节：16 行 x 每行 2 字节，高位在左，1 = 亮点。
  *
  *          屏上显示时按“请求的 GBK 双字节 -> 查表”取字模，找不到就画方块。
  ******************************************************************************
  */

#ifndef __CN_FONT16_H
#define __CN_FONT16_H

#include "stm32f10x.h"

#define CN_FONT16_W         16                  /* 汉字宽（像素）*/
#define CN_FONT16_H         16                  /* 汉字高（像素）*/

typedef struct
{
    uint16_t gbk;                               /* GBK 双字节编码（高字节在前）*/
    uint8_t  data[32];                          /* 16 行 x 2 字节点阵 */
} CnGlyph16_t;

extern const CnGlyph16_t g_cnFont16[];
extern const uint16_t    g_cnFont16Count;

/* 按 GBK 双字节查字模，找不到返回 0 */
const CnGlyph16_t *CnFont16_Lookup(uint16_t gbk);

#endif /* __CN_FONT16_H */
