/**
  ******************************************************************************
  * @file    Drv_Common/oled_drv.h
  * @brief   0.86 寸 4PIN OLED 显示驱动（SSD1306 控制器 / 软件 I2C1）
  *
  *          板上接线（J12 插座）：
  *              OLED SCL -> PB6 (I2C1_SCL)
  *              OLED SDA -> PB7 (I2C1_SDA)
  *          I2C1 这两根线在板上已经有 R21 / R22 两个 4.7K 上拉到 3V3，
  *          所以 SCL / SDA 按 I2C 规范配成开漏输出即可，不需要再外接上拉。
  *
  *          屏是 128x32 像素，SSD1306 按"页(page)"组织：一页 8 行像素，
  *          所以整屏共 4 页，每页 128 个字节，一个字节表示同一列上的 8 个像素
  *          （bit0 在最上面）。
  ******************************************************************************
  */

#ifndef __OLED_DRV_H
#define __OLED_DRV_H

#include "stm32f10x.h"
#include "font8x8.h"

#define OLED_I2C_ADDR       0x78                        /* 7 位地址 0x3C 左移一位 */

#define OLED_WIDTH          128                         /* 屏宽（像素）*/
#define OLED_HEIGHT         32                          /* 屏高（像素）*/
#define OLED_PAGE_COUNT     (OLED_HEIGHT / 8)           /* 页数 = 4 */

#define OLED_CHAR_W         FONT8X8_WIDTH               /* 字符宽 8 像素 */
#define OLED_CHAR_H         FONT8X8_HEIGHT              /* 字符高 8 像素 */
#define OLED_COL_MAX        (OLED_WIDTH / OLED_CHAR_W)  /* 一行 16 个字符 */
#define OLED_ROW_MAX        OLED_PAGE_COUNT             /* 一屏 4 行 */

void OLED_Init(void);
void OLED_DisplayOn(void);
void OLED_DisplayOff(void);
void OLED_Clear(void);
void OLED_ClearLine(uint8_t row);
void OLED_Refresh(void);
void OLED_ShowChar(uint8_t col, uint8_t row, char ch);
void OLED_ShowString(uint8_t col, uint8_t row, const char *str);

#endif /* __OLED_DRV_H */
