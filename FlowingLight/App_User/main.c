/* 任务4: 实现流水灯架构
 * 应用层 — 只负责"花式配置 LED 指示效果", 不直接操作寄存器
 * 驱动层 — drv_led.c/h 提供 Led_On/Off/Toggle/Drv_Init 统一接口
 */
#include "stm32f10x.h"
#include "drv_led.h"

/* 简单毫秒延时 (SysTick 已被标准库初始化) */
static void delay_ms(uint32_t ms)
{
    for (volatile uint32_t i = 0; i < ms * 8000u; ++i) {
        /* busy-wait, 72M 下约 1ms */
    }
}

/* 流水序列: 8 个 LED 依次点亮 */
static const LED_NO_t flow_seq[] = {
    LED1, LED2, LRGB_R, LRGB_G, LRGB_B, RRGB_R, RRGB_G, RRGB_B
};

int main(void)
{
    Led_Drv_Init();

    while (1) {
        /* 单灯流水: 一个一个点过去 */
        for (uint32_t i = 0; i < sizeof(flow_seq)/sizeof(flow_seq[0]); ++i) {
            Led_On(flow_seq[i]);
            delay_ms(150);
            Led_Off(flow_seq[i]);
        }

        /* 全部点亮保持 200ms 后一起灭 (回旋) */
        for (uint32_t i = 0; i < sizeof(flow_seq)/sizeof(flow_seq[0]); ++i) {
            Led_On(flow_seq[i]);
        }
        delay_ms(200);
        for (uint32_t i = 0; i < sizeof(flow_seq)/sizeof(flow_seq[0]); ++i) {
            Led_Off(flow_seq[i]);
        }
        delay_ms(200);
    }
}
