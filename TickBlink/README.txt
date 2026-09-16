============================================================
STM32F103 工程 - 实现 systick 的编程（无个人信息版）
（基于 ST 官方 StdPeriph Lib V3.6.0，Keil uVision 工程）
============================================================

【功能】
利用 Cortex-M3 内核 SysTick 产生 1ms 时基，中断里累加
ms_counter；应用层用 wait_ms() 做毫秒级延时，驱动 LED1
（PG14，高电平点亮）以 1Hz 闪烁。

【引脚】
LED1 = PG14（直接写寄存器配置为推挽输出）

【SysTick 配置要点】
- 调用 SysTick_Config(SystemCoreClock / 1000) 即完成
  LOAD 装载、VAL 清零、CTRL 使能（内核时钟 + 中断）
- 中断函数 SysTick_Handler 每 1ms 让 ms_counter 自增
- 延时基于 ms_counter 差值，精度不随主频校准变化

【Keil 打开方式】
1) 双击 Project/TickBlink.uvprojx 用 Keil 打开
2) 芯片 STM32F103ZE
   宏 Define：STM32F10X_HD,USE_STDPERIPH_DRIVER
   包含路径：..\Arm_Kernel ; ..\STM32_Library\inc ; ..\App_User
3) 按 F7 编译 -> 生成 Objects/TickBlink.hex
============================================================
