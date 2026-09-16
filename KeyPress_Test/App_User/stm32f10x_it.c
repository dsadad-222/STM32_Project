/**
  ******************************************************************************
  * @file    App_User/stm32f10x_it.c
  * @brief   Interrupt handlers (SysTick only).
  ******************************************************************************
  */

#include "stm32f10x_it.h"

extern volatile uint32_t tick_ms;

void SysTick_Handler(void)
{
    tick_ms++;
}
