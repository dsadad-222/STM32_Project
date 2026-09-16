/*
 * led_drv.c
 * LED driver: PG14 / PG15 push-pull output
 */

#include "led_drv.h"

#define LED1_PIN  GPIO_Pin_14
#define LED2_PIN  GPIO_Pin_15
#define LED_PORT  GPIOG

static uint16_t led_pin_map(uint8_t id)
{
    uint16_t pins = 0;
    if (id & LED_1) pins |= LED1_PIN;
    if (id & LED_2) pins |= LED2_PIN;
    return pins;
}

void led_init(void)
{
    GPIO_InitTypeDef gpio;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOG, ENABLE);

    gpio.GPIO_Pin   = LED1_PIN | LED2_PIN;
    gpio.GPIO_Mode  = GPIO_Mode_Out_PP;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(LED_PORT, &gpio);

    GPIO_ResetBits(LED_PORT, LED1_PIN | LED2_PIN);
}

void led_on(uint8_t id)
{
    GPIO_SetBits(LED_PORT, led_pin_map(id));
}

void led_off(uint8_t id)
{
    GPIO_ResetBits(LED_PORT, led_pin_map(id));
}

void led_toggle(uint8_t id)
{
    uint16_t pins = led_pin_map(id);
    GPIO_Write(LED_PORT, (uint16_t)(GPIO_ReadOutputData(LED_PORT) ^ pins));
}
