============================================================
STM32F103 标准库工程 - chapter5 任务：实现 systick 的编程
（基于 ST 官方 StdPeriph Lib V3.6.0，Keil uVision 工程）
============================================================

【功能】
使用内核 SysTick 定时器产生 1ms 时基，在中断服务函数中累加
系统运行时间计数 g_sysRunTime；应用层用该计数实现毫秒级
延时 DelayMs()，驱动 LED1（PG14，高电平点亮）以 1Hz 周期
闪烁。证明 SysTick 配置生效（相比纯软件空循环延时，精度
不受主频校准影响）。

【引脚】
LED1 = PG14（推挽输出 GPIO_Mode_Out_PP，50MHz）

【SysTick 配置要点】
1. 设置重装载寄存器 LOAD = SystemCoreClock / 1000（72M 时 72000）
2. 清除当前值寄存器 VAL（SysTick_Config 内部完成）
3. 配置控制寄存器 CTRL（SysTick_Config 内部完成：使能、内核时钟、
   使能中断）
中断服务函数：void SysTick_Handler(void) 每 1ms 让 g_sysRunTime++

【Keil 打开方式】
1) 双击 Project/SysTick_Tick.uvprojx 用 Keil 打开
2) 工程已配好：芯片 STM32F103ZE
   C/C++ 宏 Define：STM32F10X_HD,USE_STDPERIPH_DRIVER
   包含路径：..\Arm_Kernel ; ..\STM32_Library\inc ; ..\App_User
   已勾选 Create HEX File
3) 按 F7 编译 -> 生成 Objects/SysTick_Tick.hex
4) 用 ST-Link / DAP-Link 烧录，观察 LED1 以 1Hz 闪烁
============================================================
