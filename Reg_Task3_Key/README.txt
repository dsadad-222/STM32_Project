============================================================
STM32F103 工程 - 任务3：寄存器方式控制按键
（直接操作寄存器，不使用标准外设库函数；Keil uVision 工程）
============================================================

【功能】
按键控制 LED：KEY1 按下 -> LED1 亮，KEY2 按下 -> LED2 亮，
KEY3 按下 -> LED1+LED2 同时亮；松开按键对应 LED 熄灭。
全程直接写 RCC / GPIO 寄存器，不调用任何标准库 API。

【引脚】
LED1 = PG14，LED2 = PG15（推挽输出，高电平点亮）
KEY1 = PG3，KEY2 = PG4，KEY3 = PG5（浮空输入，开发板按下=低电平）

【寄存器操作要点】
1) 开时钟：RCC->APB2ENR |= (1<<8);          // IOPG 时钟使能
2) LED 配输出：GPIOG->CRH（PG14/PG15）CNF 00 / MODE 11 = 0x3
3) 按键配输入：GPIOG->CRL（PG3/4/5）CNF 01 / MODE 00 = 0x4（浮空输入）
4) 读按键：GPIOG->IDR 对应位为 0 表示按下（开发板接 GND）
5) 控灯：GPIOG->BSRR 置位（亮），GPIOG->BRR 清位（灭）
6) 主循环扫描三个按键，按下则点亮对应 LED，松开即灭

【Keil 打开方式】
1) 双击 Project/Reg_Task3_Key.uvprojx 用 Keil 打开
2) 芯片 STM32F103ZE，宏 Define：STM32F10X_HD,USE_STDPERIPH_DRIVER
   包含路径：..\Arm_Kernel ; ..\STM32_Library\inc ; ..\App_User
   已勾选 Create HEX File
3) 按 F7 编译 -> 生成 Objects/Reg_Task3_Key.hex
4) ST-Link / DAP-Link 烧录，按下 KEY1~KEY3 观察对应 LED 亮灭
============================================================
