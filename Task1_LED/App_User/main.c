// Task 1 - LED toggle using STM32 standard peripheral library
// Target: STM32F103ZET6, on-board LED1 tied to PG14 (active high)
#include "stm32f10x.h"

static void delay(uint32_t n)
{
    for (volatile uint32_t i = 0; i < n; i++);
}

static void ledGpioInit(void)
{
    GPIO_InitTypeDef gpio;
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOG, ENABLE);

    gpio.GPIO_Pin   = GPIO_Pin_14;
    gpio.GPIO_Mode  = GPIO_Mode_Out_PP;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOG, &gpio);
}

int main(void)
{
    ledGpioInit();

    while (1) {
        GPIO_WriteBit(GPIOG, GPIO_Pin_14, Bit_SET);
        delay(600000);

        GPIO_WriteBit(GPIOG, GPIO_Pin_14, Bit_RESET);
        delay(600000);
    }
}
