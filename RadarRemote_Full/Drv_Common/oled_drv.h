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

#define OLED_I2C_ADDR       0x78                        /* 默认从机地址：7 位 0x3C 左移一位 */
#define OLED_I2C_ADDR_A     0x78                        /* 多数 0.86/0.96 寸模块用这个地址 */
#define OLED_I2C_ADDR_B     0x7A                        /* 少数模块 SA0 焊成高电平，用这个 */

#define OLED_WIDTH          128                         /* 屏宽（像素）*/
#define OLED_HEIGHT         32                          /* 屏高（像素）*/
#define OLED_PAGE_COUNT     (OLED_HEIGHT / 8)           /* 页数 = 4 */

#define OLED_CHAR_W         FONT8X8_WIDTH               /* 字符宽 8 像素 */
#define OLED_CHAR_H         FONT8X8_HEIGHT              /* 字符高 8 像素 */
#define OLED_COL_MAX        (OLED_WIDTH / OLED_CHAR_W)  /* 一行 16 个字符 */
#define OLED_ROW_MAX        OLED_PAGE_COUNT             /* 一屏 4 行 */

/* ---- 放大字（2 倍宽 2 倍高，16x16 像素，跨相邻两页）----
 * 0.86 寸屏只有 128x32 像素，8x8 字排 4 行会把 32 像素顶满、行间毫无空隙，
 * 看着很挤。文字用 8x8 字模按“每行像素复制一遍、每列像素复制一遍”放大
 * 2 倍，占两页高度，字号立刻翻倍，一眼就能看清。 */
#define OLED_BIG_CHAR_W     (OLED_CHAR_W * 2u)              /* 放大字：宽 16 像素 */
#define OLED_BIG_CHAR_H     (OLED_CHAR_H * 2u)              /* 放大字：高 16 像素 */
#define OLED_BIG_COL_MAX    (OLED_WIDTH / OLED_BIG_CHAR_W)  /* 一行 8 个放大字 */
#define OLED_BIG_ROW_MAX    (OLED_PAGE_COUNT / 2u)          /* 一屏 2 行放大字 */

/* 放大字的小数点：8x8 字模里 '.' 只有 2x2 个像素，放大后 4x4，在 0.86 寸屏上
 * 很不显眼。这里不用字模，直接画一个 6x6 的实心方块（贴着底线、水平居中），
 * 一眼就能看出是小数点。 */
#define OLED_BIG_DOT_W      6                               /* 方块边长（像素）*/
#define OLED_BIG_DOT_MASK   0xFC                            /* 在 page+1 里占第 2~7 位（第 10~15 行）*/

/* 探测屏在不在，顺便自动选对从机地址：
 *   返回 1 = 0x78 有应答，2 = 0x7A 有应答，0 = 两个地址都没应答（查接线/供电）*/
uint8_t OLED_Probe(void);

void OLED_Init(void);
void OLED_DisplayOn(void);
void OLED_DisplayOff(void);
void OLED_Clear(void);
void OLED_ClearLine(uint8_t row);
void OLED_Refresh(void);
void OLED_ShowChar(uint8_t col, uint8_t row, char ch);
void OLED_ShowString(uint8_t col, uint8_t row, const char *str);

/* 放大字：col 单位是一个放大字宽（16 像素），page 是起始页（0 或 2），
 * 一个字符会同时占用 page 和 page+1 两页 */
void OLED_ShowCharBig(uint8_t col, uint8_t page, char ch);
void OLED_ShowStringBig(uint8_t col, uint8_t page, const char *str);

/* 中文显示：col 单位是一个汉字宽（16 像素），page 是起始页（0 或 2），
 * 一个汉字同样占 page 和 page+1 两页。
 * 输入是 GBK 双字节字节串，按 16x16 字库（cn_font16.c）查字模渲染；
 * 查不到的字画成空心方块，一眼就能发现字库缺字。
 * 注意屏上一行最多 8 个汉字，传入的字符串不要超过 8 个字。 */
void OLED_ShowCNChar(uint8_t col, uint8_t page, uint16_t gbk);
void OLED_ShowCNString(uint8_t col, uint8_t page, const char *gbkStr);

#endif /* __OLED_DRV_H */
