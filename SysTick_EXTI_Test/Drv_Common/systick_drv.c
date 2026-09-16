/**
  ******************************************************************************
  * @file    Drv_Common/systick_drv.c
  * @author  陈相林 (智能3班)
  * @brief   SysTick 配置为 1ms 中断，全局运行时间计数
  ******************************************************************************
  */

#include "systick_drv.h"
#include "stm32f10x.h"

volatile uint64_t g_sysRunTime = 0;

void SysTick_Init(void)
{
    if (SysTick_Config(SystemCoreClock / 1000) != 0)
    {
        while (1); /* 配置失败 */
    }
}

uint64_t Get_SysRunTime(void)
{
    return g_sysRunTime;
}
