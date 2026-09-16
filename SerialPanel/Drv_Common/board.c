/**
  ******************************************************************************
  * @file    Drv_Common/board.c
  * @brief   Port G actuator driver written at register level.
  *          CRL/CRH hold the configuration nibbles of pin 0..7 and 8..15,
  *          BSRR sets pins atomically, BRR resets them, ODR is used to flip.
  ******************************************************************************
  */

#include "board.h"

/* One nibble per pin: CNF = 00 (push-pull), MODE = 11 (50 MHz) -> 0x3 */
#define OUT_NIBBLE      0x3U

void board_gpio_init(void)
{
    uint32_t crh;

    /* Port G is clocked from APB2 */
    RCC->APB2ENR |= RCC_APB2ENR_IOPGEN;

    /* PG0 / PG1 / PG2 as push-pull outputs (configuration low register) */
    GPIOG->CRL &= ~0x00000FFFU;
    GPIOG->CRL |=  (OUT_NIBBLE << 0)  |
                   (OUT_NIBBLE << 4)  |
                   (OUT_NIBBLE << 8);

    /* PG12 buzzer, PG14/PG15 LEDs (configuration high register) */
    crh  = GPIOG->CRH;
    crh &= ~((0xFU << 16) | (0xFFU << 24));
    crh |=  (OUT_NIBBLE << 16) |                       /* PG12 */
            (OUT_NIBBLE << 24) | (OUT_NIBBLE << 28);   /* PG14, PG15 */
    GPIOG->CRH = crh;

    /* Everything off at power up */
    GPIOG->BRR = BOARD_LED_LEFT | BOARD_LED_RIGHT | BOARD_BEEP_PIN | BOARD_RGB_MASK;
}

void board_led_write(uint16_t mask, uint8_t on)
{
    if (on != 0U)
    {
        GPIOG->BSRR = (uint32_t)mask;
    }
    else
    {
        GPIOG->BRR = (uint32_t)mask;
    }
}

void board_led_toggle(uint16_t mask)
{
    GPIOG->ODR ^= (uint32_t)mask;
}

void board_beep_write(uint8_t on)
{
    if (on != 0U)
    {
        GPIOG->BSRR = BOARD_BEEP_PIN;
    }
    else
    {
        GPIOG->BRR = BOARD_BEEP_PIN;
    }
}

void board_rgb_write(uint16_t mask)
{
    uint16_t on = (uint16_t)(mask & BOARD_RGB_MASK);

    GPIOG->BRR = BOARD_RGB_MASK;        /* blank first, then light up */
    if (on != 0U)
    {
        GPIOG->BSRR = (uint32_t)on;
    }
}
