#ifndef DWT_TIMER_H
#define DWT_TIMER_H

#include <stdint.h>

/* turn on the Cortex-M3 DWT cycle counter */
void dwt_timer_start(void);

/* busy-wait for a given number of microseconds (uses CYCCNT) */
void dwt_udelay(uint32_t us);

/* busy-wait for a given number of milliseconds */
void dwt_mdelay(uint32_t ms);

#endif
