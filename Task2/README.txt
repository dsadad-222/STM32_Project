任务2：寄存器方式控制 IO 点亮 LED
提交人：陈相林   学号：202417010304   班级：智能2班
板子：YB-DSF01-V1.0（STM32F103ZET6，512KB Flash / 64KB SRAM）

【引脚】
  LED1 = PG14，LED2 = PG15（高电平点亮）
  按键 KEY1=PG3，KEY2=PG4，KEY3=PG5（本任务未用按键）

【实验内容】
  LED1 以约 1Hz 频率闪烁：置位 GPIOG_BSRR 点亮，置位 GPIOG_BRR 熄灭，中间用软件延时循环。
  所有寄存器用内存映射宏直接操作（无库函数），体现“寄存器方式”本质。

【编译】
  - Keil MDK5：打开 Task2.uvprojx → 魔术棒 Output 选项卡勾选 Create HEX File → F7 编译，
    产物在 Objects/Task2.hex
  - 或用 arm-none-eabi-gcc（参考同目录 gnu_startup.s + stm32f103ze.ld）

【烧录】
  - ST-LINK：Keil 里 Flash → Download（F8）
  - 串口：FlyMcu 载入 Objects/Task2.hex，选“DTR低电平复位, RTS高电平进BootLoader”

【现象】
  复位后 LED1 周期性亮/灭闪烁。
