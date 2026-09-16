STM32F103 标准库工程 - 任务：实现流水灯架构
（基于 ST 官方 StdPeriph Lib V3.6.0，Keil uVision 工程）

【功能】
分层实现流水灯：drv_led.c/h 为驱动层，提供 led_driver_init / led_turn_on /
led_turn_off / led_toggle 统一接口（内部直接配置 GPIO 寄存器）；main.c 为
应用层，只负责编排流水/呼吸花式。

【引脚】
LED1/LED2    = PG14 / PG15
左侧 RGB      = PG0 / PG1 / PG2 （R/G/B）
右侧 RGB      = PE2 / PE3 / PE4 （R/G/B）
（共阴，高电平点亮）

【Keil 打开方式】
1) 双击 Project/LedPattern.uvprojx 用 Keil 打开
2) 工程已配好：芯片 STM32F103ZE
   C/C++ 宏 Define：STM32F10X_HD,USE_STDPERIPH_DRIVER
   包含路径：..\Arm_Kernel ; ..\STM32_Library\inc ; ..\App_User
   已勾选 Create HEX File
3) 按 F7 编译 -> 生成 Objects/LedPattern.hex
4) 烧录后观察 8 个 LED 流水 / 整体闪烁
