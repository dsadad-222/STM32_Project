/**
  ******************************************************************************
  * @file    Drv_Common/panel.h
  * @brief   0.86 inch 128x32 OLED module, SSD1306 controller.
  *
  *          The module hangs on I2C1 of the board: PB6 drives SCL and PB7
  *          drives SDA.  R21 / R22 (4.7k) already pull both lines up to 3V3,
  *          so the pins are configured as open drain outputs and the bus is
  *          bit banged in software.
  *
  *          Nothing is sent to the panel while drawing.  Characters are
  *          written into a 4 x 128 byte shadow buffer and pushed out in one
  *          go by panel_flush().
  ******************************************************************************
  */

#ifndef PANEL_DRV_H
#define PANEL_DRV_H

#include <stdint.h>
#include "stm32f10x.h"
#include "glyphs.h"

#define PANEL_I2C_ADDR      0x78U                       /* 0x3C shifted left */
#define PANEL_W             128U
#define PANEL_H             32U
#define PANEL_PAGES         (PANEL_H / 8U)              /* 4   */

#define PANEL_CELL_W        GLYPH_W                     /* 8   */
#define PANEL_CELL_H        GLYPH_H                     /* 8   */
#define PANEL_COLS          (PANEL_W / PANEL_CELL_W)    /* 16  */
#define PANEL_ROWS          PANEL_PAGES                 /* 4   */

void panel_init(void);
void panel_blank(void);
void panel_blank_row(uint8_t row);
void panel_flush(void);
void panel_putc(uint8_t col, uint8_t row, char c);
void panel_puts(uint8_t col, uint8_t row, const char *s);

#endif /* PANEL_DRV_H */
