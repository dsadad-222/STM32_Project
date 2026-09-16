/*-----------------------------------------------------------------------------
 * HSI-driven system clock setup for STM32F103ZET6
 * Lab task 1 of chapter3: build SYSCLK from the internal 8 MHz HSI
 * instead of the default HSE*PLL 72 MHz path.
 *
 * Verification: on-board LED1 (PG14, active-high) toggles inside a fixed
 * software loop. The loop runs on the CPU, so a higher SYSCLK makes the LED
 * blink faster - which visually proves the clock was reconfigured.
 *---------------------------------------------------------------------------*/
#include "stm32f10x.h"

/* busy-wait loop; its real duration scales with SYSCLK */
static void busy_wait(uint32_t ticks)
{
    while (ticks--) {
        __NOP();
    }
}

/* Build the system clock from HSI:
 *    HSI 8MHz -> /2 (PLL input = 4MHz) -> x mult -> SYSCLK
 *    mult is one of RCC_PLLMul_x (x in 2..16).
 *    Note: the HSI path tops out at 4MHz * 16 = 64MHz. It cannot reach
 *    72MHz the way the HSE (8MHz x 9) path does.
 */
static void sysclk_from_hsi(uint32_t mult)
{
    RCC_DeInit();

    RCC_HSICmd(ENABLE);
    while (RCC_GetFlagStatus(RCC_FLAG_HSIRDY) == RESET) {
    }

    FLASH_PrefetchBufferCmd(FLASH_PrefetchBuffer_Enable);
    FLASH_SetLatency(FLASH_Latency_2);

    RCC_HCLKConfig(RCC_SYSCLK_Div1);
    RCC_PCLK2Config(RCC_HCLK_Div1);
    RCC_PCLK1Config(RCC_HCLK_Div2);

    RCC_PLLConfig(RCC_PLLSource_HSI_Div2, mult);
    RCC_PLLCmd(ENABLE);
    while (RCC_GetFlagStatus(RCC_FLAG_PLLRDY) == RESET) {
    }

    RCC_SYSCLKConfig(RCC_SYSCLKSource_PLLCLK);
    while (RCC_GetSYSCLKSource() != 0x08) {
    }
}

static void led_pin_init(void)
{
    GPIO_InitTypeDef gpio;
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOG, ENABLE);
    gpio.GPIO_Pin = GPIO_Pin_14;
    gpio.GPIO_Mode = GPIO_Mode_Out_PP;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOG, &gpio);
}

int main(void)
{
    /* target frequency: _8 = 32M, _12 = 48M (default), _16 = 64M */
    sysclk_from_hsi(RCC_PLLMul_12);

    led_pin_init();

    for (;;) {
        /* read-modify-write toggle on the whole port */
        GPIO_Write(GPIOG, (uint16_t)(GPIO_ReadOutputData(GPIOG) ^ GPIO_Pin_14));
        busy_wait(2000000u);
    }
}
