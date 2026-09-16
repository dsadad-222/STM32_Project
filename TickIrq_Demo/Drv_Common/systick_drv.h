/*
 * systick_drv.h
 * 1 ms tick for system runtime
 */

#ifndef SYSTICK_DRV_H
#define SYSTICK_DRV_H

#include <stdint.h>

extern volatile uint64_t sys_ms;

void systick_init(void);
uint64_t sys_runtime_ms(void);

#endif
