/**
  ******************************************************************************
  * @file    Drv_Common/font8x8.h
  * @brief   8x8 点阵 ASCII 字库 (0x20~0x7E)，用于 OLED 字符显示
  ******************************************************************************
  */

#ifndef __FONT8X8_H
#define __FONT8X8_H

#include "stm32f10x.h"

#define FONT8X8_FIRST_CHAR   0x20        /* 字库里第一个字符: 空格 */
#define FONT8X8_LAST_CHAR    0x7E        /* 字库里最后一个字符: '~' */
#define FONT8X8_WIDTH        8           /* 字符点阵宽度（含 1 列间隔）*/
#define FONT8X8_HEIGHT       8           /* 字符点阵高度 */

/* 每字符 8 字节：一个字节代表一行，bit7 为该行最左边的像素 */
extern const uint8_t g_font8x8[FONT8X8_LAST_CHAR - FONT8X8_FIRST_CHAR + 1][FONT8X8_HEIGHT];

#endif /* __FONT8X8_H */
