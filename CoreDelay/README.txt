STM32F103 标准库工程 - 任务：配置实现 DWT 延时功能
（基于 ST 官方 StdPeriph Lib V3.6.0，Keil uVision 工程）

【功能】
使用 Cortex-M3 内核 DWT 单元的周期计数器（DWT_CYCCNT）实现微秒/毫秒级
精确延时，不依赖 SysTick。验证现象：LED1（PG14）以约 1Hz 频率闪烁。

【引脚】
LED1 = PG14（推挽输出 50MHz，高电平点亮）

【Keil 打开方式】
1) 双击 Project/CoreDelay.uvprojx 用 Keil 打开
2) 工程已配好：芯片 STM32F103ZE
   C/C++ 宏 Define：STM32F10X_HD,USE_STDPERIPH_DRIVER
   包含路径：..\Arm_Kernel ; ..\STM32_Library\inc ; ..\App_User
   已勾选 Create HEX File
3) 按 F7 编译 -> 生成 Objects/CoreDelay.hex
4) 烧录后观察 LED1 闪烁，说明 DWT 延时生效
