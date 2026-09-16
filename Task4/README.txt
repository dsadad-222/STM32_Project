任务4：寄存器方式控制按键扩展
提交人：陈相林   学号：202417010304   班级：智能2班
板子：YB-DSF01-V1.0（STM32F103ZET6）

【引脚】
  LED1 = PG14，LED2 = PG15（高电平点亮）
  KEY1 = PG3，KEY2 = PG4，KEY3 = PG5（浮空输入，默认 KEY_INPUT_MODE=0x04）

【实验内容】
  主循环读取 3 个按键状态（GetKeyVal() 返回 bit0/1/2 对应 KEY1/2/3）：
    - KEY1 按下 → LED1 亮，否则灭
    - KEY2 按下 → LED2 亮，否则灭
    - KEY3 按下 → LED1+LED2 同时亮，否则同时灭
  通过 BSRR/BRR 直接驱动两个 LED，全部为寄存器操作。

【若按键逻辑相反】同任务3，把 main.c 顶部 KEY_INPUT_MODE 改为 0x08 重编。

【编译 / 烧录】同任务2（产物 Objects/Task4.hex）

【现象】
  独立控制：KEY1→LED1，KEY2→LED2，KEY3→双 LED 同时亮灭。
