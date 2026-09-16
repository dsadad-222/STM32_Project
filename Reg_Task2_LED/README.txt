============================================================
STM32F103 工程 - 任务2：寄存器方式控制 IO 点亮 LED
（直接操作寄存器，不使用标准外设库函数；Keil uVision 工程）
============================================================

【功能】
LED1(PG14) 与 LED2(PG15) 交替闪烁，全程直接写 RCC / GPIO 寄存器，
不调用任何标准库 API。

【引脚】
LED1 = PG14，LED2 = PG15（推挽输出 50MHz，高电平点亮，共阴接法）

【寄存器操作要点】
1) 开时钟：RCC->APB2ENR |= (1<<8);          // IOPG 时钟使能
2) 配输出：GPIOG->CRH 每 4 位控一个引脚
           推挽输出 50MHz = CNF 00 / MODE 11 = 0x3
           PG14 -> CRH[27:24]，PG15 -> CRH[31:28]
3) 输出：GPIOG->BSRR 写 1 置高（亮），GPIOG->BRR 写 1 清低（灭）
4) 软件延时：固定循环次数，系统时钟越高闪得越快（本工程 72M）

【Keil 打开方式】
1) 双击 Project/Reg_Task2_LED.uvprojx 用 Keil 打开
2) 芯片 STM32F103ZE，宏 Define：STM32F10X_HD,USE_STDPERIPH_DRIVER
   包含路径：..\Arm_Kernel ; ..\STM32_Library\inc ; ..\App_User
   已勾选 Create HEX File
3) 按 F7 编译 -> 生成 Objects/Reg_Task2_LED.hex
4) ST-Link / DAP-Link 烧录，观察两灯交替闪烁
============================================================
