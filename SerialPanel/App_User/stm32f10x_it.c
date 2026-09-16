/**
  ******************************************************************************
  * @file    App_User/stm32f10x_it.c
  * @brief   Interrupt service routines: the 1 ms tick only bumps a counter.
  ******************************************************************************
  */

#include "stm32f10x_it.h"
#include "tick.h"

void SysTick_Handler(void)
{
    g_ms_tick++;
}
