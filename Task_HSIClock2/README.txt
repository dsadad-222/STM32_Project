STM32 System Clock via HSI
==========================

Lab task 1, chapter3.

Target : STM32F103ZET6
LED1   : PG14 (active high)

By default the standard library boots the chip with HSE*PLL = 72 MHz.
This project overrides that in main() by calling sysclk_from_hsi(), which
selects the internal HSI (8 MHz) as the PLL source, divides it by 2, then
multiplies it to build the system clock.

Clock path note:
  HSE path : 8 MHz x 9              = 72 MHz  (library default)
  HSI path : 8 MHz / 2 x N = 4 MHz x N, N <= 16 -> max 64 MHz
  So the HSI path cannot reach 72 MHz.

Default target is 48 MHz (RCC_PLLMul_12):
  RCC_PLLMul_8  -> 32 MHz
  RCC_PLLMul_12 -> 48 MHz (default)
  RCC_PLLMul_16 -> 64 MHz (HSI limit)

Check:
  LED1 toggles through a fixed CPU loop. Raise SYSCLK and the blink speeds
  up, confirming the clock switch took effect.

Build:
  Open Project/Task_HSIClock2.uvprojx in Keil uVision, press F7.
  Output hex: Objects/Task_HSIClock2.hex
