// 使用 HSI 配置系统时钟 (STM32 标准库)
// 对应课件 chapter3 第四节 任务测试 任务1
// 目标芯片: STM32F103ZET6
// 板载 LED1 接 PG14 (高电平点亮)
//
// 说明:
//   上电后库默认会把系统时钟配成 HSE×PLL = 72MHz。本任务要求改用
//   片内 HSI (8MHz) 作为时钟源，经 /2 后送 PLL 倍频，再切换为系统时钟。
//   由于 HSI 路径最高只能到 64MHz (4MHz × 16)，无法像 HSE 那样跑到 72MHz，
//   这是两种方案的关键差异，写代码时需特别注意。
#include "stm32f10x.h"

// 软件延时: 循环次数固定，实际延时随 SYSCLK 上升而缩短。
// 因此 LED 闪烁频率可直接反映系统时钟是否配置成功 (频率越高闪得越快)。
static void softDelay(uint32_t cnt)
{
    for (volatile uint32_t i = 0; i < cnt; i++);
}

// 通过 HSI 路径配置系统时钟
// pllmul: RCC_PLLMul_x, x 可取 [2,16]
//   HSI = 8MHz -> /2 = 4MHz -> ×pllmul = PLLCLK = SYSCLK
//   常用取值: RCC_PLLMul_8 (32M) / _12 (48M) / _16 (64M)
void HSI_SetSysClock(uint32_t pllmul)
{
    __IO uint32_t startUp = 0;

    // 1. 把 RCC 复位到初始状态 (关闭 HSE/PLL, 回到 HSI 默认)
    RCC_DeInit();

    // 2. 开启 HSI 并等待稳定
    RCC_HSICmd(ENABLE);
    while (RCC_GetFlagStatus(RCC_FLAG_HSIRDY) == RESET) {
        if (++startUp > 0x50000) break; // 简单超时保护
    }

    // 3. FLASH 预取缓冲 + 等待周期 ( SYSCLK > 24M 时必须配置 )
    FLASH_PrefetchBufferCmd(FLASH_PrefetchBuffer_Enable);
    FLASH_SetLatency(FLASH_Latency_2);

    // 4. 总线分频: HCLK = SYSCLK, PCLK2 = HCLK, PCLK1 = HCLK / 2 (<= 36M)
    RCC_HCLKConfig(RCC_SYSCLK_Div1);
    RCC_PCLK2Config(RCC_HCLK_Div1);
    RCC_PCLK1Config(RCC_HCLK_Div2);

    // 5. PLL 来源选 HSI/2, 倍频因子 pllmul -> PLLCLK = 4MHz × pllmul
    RCC_PLLConfig(RCC_PLLSource_HSI_Div2, pllmul);

    // 6. 开启 PLL 并等待锁定
    RCC_PLLCmd(ENABLE);
    while (RCC_GetFlagStatus(RCC_FLAG_PLLRDY) == RESET) {
    }

    // 7. 切换 PLL 为系统时钟并确认切换完成
    RCC_SYSCLKConfig(RCC_SYSCLKSource_PLLCLK);
    while (RCC_GetSYSCLKSource() != 0x08) {
    }
}

// 配置 PA8 为 MCO 输出当前 SYSCLK, 可用示波器/逻辑分析仪直接测量时钟频率
static void mcoInit(void)
{
    GPIO_InitTypeDef gpio;
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA, ENABLE);
    gpio.GPIO_Pin   = GPIO_Pin_8;
    gpio.GPIO_Mode  = GPIO_Mode_AF_PP;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOA, &gpio);
    RCC_MCOConfig(RCC_MCO_SYSCLK);
}

static void ledInit(void)
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
    // 将系统时钟从默认方案改为 HSI 经 PLL 倍频到 48MHz
    // 想体验其它频率可换成 RCC_PLLMul_8 (32M) 或 RCC_PLLMul_16 (64M)
    HSI_SetSysClock(RCC_PLLMul_12);

    ledInit();
    mcoInit();

    while (1) {
        GPIO_WriteBit(GPIOG, GPIO_Pin_14, Bit_SET);
        softDelay(2000000);
        GPIO_WriteBit(GPIOG, GPIO_Pin_14, Bit_RESET);
        softDelay(2000000);
    }
}
