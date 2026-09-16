/* 任务3: 配置实现 DWT 延时功能
 * 目标芯片: STM32F103ZET6 (Cortex-M3, 默认 SYSCLK = 72M)
 * 验证: LED1 (PG14) 以 1Hz 频率闪烁 (亮 500ms / 灭 500ms)
 *       使用 DWT_CYCCNT 精确计时，不依赖 SysTick
 */
#include "stm32f10x.h"
#include "dwt.h"

static void Led1_GpioInit(void)
{
    /* 1) 打开 GPIOG 时钟 (RCC_APB2ENR.IOPGEN = bit8) */
    RCC->APB2ENR |= (uint32_t)1u << 8;

    /* 2) 配置 PG14 为推挽输出 50MHz (CRH[27:24] = 0x3) */
    GPIOG->CRH &= ~((uint32_t)0x0Fu << 24);
    GPIOG->CRH |=  ((uint32_t)0x03u << 24);
}

int main(void)
{
    Led1_GpioInit();
    DelayInit();

    while (1) {
        GPIOG->BSRR = (uint32_t)1u << 14;  /* LED1 亮 */
        DelayNms(500);

        GPIOG->BRR  = (uint32_t)1u << 14;  /* LED1 灭 */
        DelayNms(500);
    }
}
