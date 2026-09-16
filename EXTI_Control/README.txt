================================================================
STM32F103 StdPeriph Demo: External Interrupt Control
================================================================

【Task】
Chapter 5 "Interrupt and External Interrupt" -> External Interrupt Control Test

【Behavior】
Falling edge on keys toggles LEDs:
  - KEY1 (PG3) -> EXTI3 -> toggle LED1 (PG14)
  - KEY2 (PG4) -> EXTI4 -> toggle LED2 (PG15)
  - KEY3 (PG5) -> EXTI5 -> toggle both LED1 and LED2
Keys use internal pull-up; LEDs are active high.

【Key points】
  1) Enable GPIOG and AFIO clocks.
  2) Configure PG3/4/5 as IPU (input pull-up).
  3) Map PG3/4/5 to EXTI3/4/5 via GPIO_EXTILineConfig().
  4) Set EXTI trigger to falling edge and enable line.
  5) Configure NVIC (EXTI3_IRQn, EXTI4_IRQn, EXTI9_5_IRQn).
  6) In ISRs, check pending bit, toggle LED, clear pending bit.

【Build in Keil】
  1) Open Project/EXTI_Control.uvprojx
  2) Target: STM32F103ZE; Defines: STM32F10X_HD,USE_STDPERIPH_DRIVER
  3) Press F7 to generate Objects/EXTI_Control.hex
  4) Burn and press keys to see LED toggling

【Verification】
Compiled with ARM GNU toolchain. Outputs/EXTI_Control.hex has a valid
vector table: SP=0x20001000, Reset_Handler=0x08000041.
================================================================
