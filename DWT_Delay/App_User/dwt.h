#ifndef __DWT_DELAY_H__
#define __DWT_DELAY_H__

#include <stdint.h>

/* DWT 硬件延时初始化
 * 1) DEMCR.TRACENA 置位 (bit24)
 * 2) DWT_CTRL.CYCCNTENA 置位 (bit0)
 * 3) DWT_CYCCNT 清零
 */
void DelayInit(void);

/* 微秒级精确延时 (基于 CYCCNT) */
void DelayNus(uint32_t nUs);

/* 毫秒级精确延时 (循环调用 DelayNus(1000)) */
void DelayNms(uint32_t nMs);

#endif
