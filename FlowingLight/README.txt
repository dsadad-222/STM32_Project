============================================================
STM32F103 标准库工程 - 任务1：LED 灯控制
（基于 ST 官方 StdPeriph Lib V3.6.0，Keil uVision 工程）
============================================================

【功能】
LED1（PG14，高电平点亮）以约 1Hz 周期闪烁，使用标准外设库 GPIO
接口实现，未直接操作寄存器。

【引脚】
LED1 = PG14（推挽输出 GPIO_Mode_Out_PP，50MHz）

【Keil 打开方式】
1) 双击 Project/Task1_LED.uvprojx 用 Keil 打开
2) 工程已配好：芯片 STM32F103ZE
   C/C++ 宏 Define：STM32F10X_HD,USE_STDPERIPH_DRIVER
   包含路径：..\Arm_Kernel ; ..\STM32_Library\inc ; ..\App_User
   已勾选 Create HEX File
3) 按 F7 编译 -> 生成 Objects/Task1_LED.hex
4) 用 ST-Link / DAP-Link 烧录，观察 LED1 闪烁

【要点】
- 标准库必须先开对应外设时钟：
  RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOG, ENABLE);
- 宏 STM32F10X_HD 对应 ZET6 大容量；USE_STDPERIPH_DRIVER 让
  stm32f10x.h 包含外设库头文件
- 要换别的 LED 引脚，改 main.c 里 GPIO_Pin_14 即可
============================================================
