/**
  ******************************************************************************
  * @file    Drv_Common/systick_drv.c
  * @brief   SysTick 配置为 1ms 中断，全局运行时间计数
  ******************************************************************************
  */

#include "systick_drv.h"
#include "stm32f10x.h"

volatile uint32_t g_sysRunTime = 0;   /* 单位 ms，中断中自增 */

void SysTick_Init(void)
{
    if (SysTick_Config(SystemCoreClock / 1000) != 0)
    {
        while (1); /* 配置失败 */
    }
}

uint32_t Get_SysRunTime(void)
{
    return g_sysRunTime;
}

/* 基于 1ms 时基的毫秒级延时（阻塞） */
void DelayMs(uint16_t ms)
{
    uint32_t start = g_sysRunTime;
    while ((uint32_t)(g_sysRunTime - start) < (uint32_t)ms)
    {
        __NOP();
    }
}
