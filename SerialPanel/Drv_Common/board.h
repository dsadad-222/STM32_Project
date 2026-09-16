/**
  ******************************************************************************
  * @file    Drv_Common/board.h
  * @brief   On board actuators, all of them sit on port G:
  *            PG14 / PG15  -> indicator LED 1 / LED 2 (active high)
  *            PG12         -> 5 V active buzzer   (active high, NPN driver)
  *            PG0/1/2      -> R / G / B channels of the LED strip
  ******************************************************************************
  */

#ifndef BOARD_H
#define BOARD_H

#include "stm32f10x.h"

#define BOARD_LED_LEFT      (1U << 14)      /* PG14 */
#define BOARD_LED_RIGHT     (1U << 15)      /* PG15 */
#define BOARD_BEEP_PIN      (1U << 12)      /* PG12 */

#define BOARD_RGB_R         (1U << 0)       /* PG0  */
#define BOARD_RGB_G         (1U << 1)       /* PG1  */
#define BOARD_RGB_B         (1U << 2)       /* PG2  */
#define BOARD_RGB_MASK      (BOARD_RGB_R | BOARD_RGB_G | BOARD_RGB_B)

void board_gpio_init(void);
void board_led_write(uint16_t mask, uint8_t on);
void board_led_toggle(uint16_t mask);
void board_beep_write(uint8_t on);
void board_rgb_write(uint16_t mask);

#endif /* BOARD_H */
