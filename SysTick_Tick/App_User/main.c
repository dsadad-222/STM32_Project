// chapter5 任务测试：实现 systick 的编程
// 目标板：STM32F103ZET6，板载 LED1 = PG14（高电平点亮）
#include "stm32f10x.h"

// 系统运行时间计数，单位 1ms，由 SysTick 中断累加（在 stm32f10x_it.c 中自增）
volatile uint64_t g_sysRunTime = 0;

/**
 * @brief  SysTick 初始化，配置为 1ms 产生一次中断
 * @note   重装载值 = SystemCoreClock / 1000（72M 时即 72000 次/ms）
 */
static void SysTickInit(void)
{
    // SysTick_Config 位于 core_cm3.h，内部会设置 LOAD、清零 VAL、配置 CTRL 并使能中断
    if (SysTick_Config(SystemCoreClock / 1000)) {
        // 配置失败则停在这里
        while (1);
    }
}

/**
 * @brief  获取系统运行时间（单位 ms）
 */
uint64_t GetSysRunTime(void)
{
    return g_sysRunTime;
}

/**
 * @brief  基于 SysTick 的毫秒级延时
 */
static void DelayMs(uint32_t ms)
{
    uint64_t start = g_sysRunTime;
    while ((g_sysRunTime - start) < ms);
}

/**
 * @brief  LED GPIO 初始化（PG14 推挽输出）
 */
static void LedGpioInit(void)
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
    LedGpioInit();
    SysTickInit();

    while (1) {
        GPIO_WriteBit(GPIOG, GPIO_Pin_14, Bit_SET);
        DelayMs(500);

        GPIO_WriteBit(GPIOG, GPIO_Pin_14, Bit_RESET);
        DelayMs(500);
    }
}
