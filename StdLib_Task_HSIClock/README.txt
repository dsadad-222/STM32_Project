使用 HSI 配置系统时钟
====================

对应课件 chapter3 第四节 任务测试 任务1。

硬件平台
--------
- 芯片: STM32F103ZET6
- LED1: PG14 (高电平点亮)
- MCO:  PA8 (复用推挽, 输出 SYSCLK 供测量)

功能说明
--------
片上电后标准库默认会用 HSE×PLL 把系统时钟配成 72MHz。
本工程在 main() 中主动调用 HSI_SetSysClock()，改用片内高速时钟 HSI(8MHz)
作为 PLL 输入源，经 /2 后倍频，再切换为系统时钟。

时钟路径差异 (重点):
- HSE 路径: 8MHz × 9 = 72MHz (课件推荐的官方稳定值)
- HSI 路径: 8MHz / 2 × N = 4MHz × N, 倍频上限 16 -> 最高 64MHz
  因此 HSI 方案拿不到 72MHz，这是与 HSE 方案的关键区别。

本工程默认配置为 48MHz (RCC_PLLMul_12):
- RCC_PLLMul_8  -> 32MHz
- RCC_PLLMul_12 -> 48MHz
- RCC_PLLMul_16 -> 64MHz (HSI 路径上限)

验证方法
--------
1) LED1 闪烁: softDelay 循环次数固定，SYSCLK 越高 LED 闪得越快，
   可直观对比默认 8MHz 与配置后 48MHz 的差异。
2) PA8(MCO) 输出 SYSCLK，用示波器或逻辑分析仪可直接测得 48MHz 波形。

编译
----
Keil uVision 打开 Project/StdLib_Task_HSIClock.uvprojx，F7 编译，
生成的 hex 位于 Objects/StdLib_Task_HSIClock.hex。
