============================================================
STM32F103 标准库工程 - 任务2：按键控制 LED（含两组 RGB 灯扩展）
（基于 ST 官方 StdPeriph Lib V3.6.0，Keil uVision 工程）
============================================================

【功能】
- 任务2 原始功能：KEY1(PG3) 按住 -> LED1(PG14) 亮；松开 -> 灭
- RGB 扩展功能：两组 RGB LED 显示 8 种颜色
   （灭 / 红 / 绿 / 蓝 / 黄 / 品红 / 青 / 白）
   KEY2(PG4) 切换颜色组合（8 档循环）
   KEY3(PG5) 切换显示模式（0 静态 / 1 两组同步闪 / 2 两组交替闪）
   闪烁模式下 LED2(PG15) 作状态指示（与闪烁同相）

【引脚（依据 YB-DSF01-V1.0 原理图）】
第一组 RGB LED：PG0=R / PG1=G / PG2=B
第二组 RGB LED：PE2=R / PE3=G / PE4=B
基础 LED：LED1=PG14  LED2=PG15（高电平点亮）
按键：KEY1=PG3  KEY2=PG4  KEY3=PG5（浮空输入，外部上拉，按下为高）

【Keil 打开方式】
1) 双击 Project/Task2_KeyRGB.uvprojx 用 Keil 打开
2) 按 F7 编译 -> 生成 Objects/Task2_KeyRGB.hex
3) 烧录后操作：
   - 按住 KEY1 -> LED1 亮
   - 按 KEY2 -> 切换 RGB 颜色
   - 按 KEY3 -> 切换 RGB 显示模式

【要点】
- 标准库需先开 GPIOG + GPIOE 时钟
- RGB 为共阴极：IO 输出高电平点亮；若板子为共阳，把电平反接即可
- 按键若按下为低电平，把 KEY1/2/3 配成 GPIO_Mode_IPU，逻辑不变
- 改 RGB 引脚只需改 main.c 中 gpioInit() 的几处 GPIO_Pin
============================================================
