/**
  ******************************************************************************
  * @file    App_User/stm32f10x_it.c
  * @brief   中断服务函数：SysTick 1ms 累加
  ******************************************************************************
  */

#include "stm32f10x_it.h"

extern volatile uint64_t g_sysRunTime;

void SysTick_Handler(void)
{
    g_sysRunTime++;
}
