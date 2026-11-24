/**
  ******************************************************************************
  * @file    App_User/stm32f10x_it.c
  * @brief   中断服务函数：SysTick 1ms 累加
  ******************************************************************************
  */

#include "stm32f10x_it.h"

/* 与 Drv_Common/systick_drv.c 里的定义保持一致，必须是 uint32_t */
extern volatile uint32_t g_sysRunTime;

void SysTick_Handler(void)
{
    g_sysRunTime++;
}
