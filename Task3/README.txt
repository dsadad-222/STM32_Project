任务3：寄存器方式控制按键
提交人：陈相林   学号：202417010304   班级：智能2班
板子：YB-DSF01-V1.0（STM32F103ZET6）

【引脚】
  LED1 = PG14（高电平点亮）
  KEY1 = PG3（浮空输入，默认 KEY_INPUT_MODE=0x04）

【实验内容】
  主循环读取 KEY1（GPIOG_IDR bit3）电平：按下时置位 GPIOG_BSRR 让 LED1 亮，
  松开时置位 GPIOG_BRR 让 LED1 灭。读取按键封装在 GetKeyVal() 中，
  通过 KeyDown() 判断单个按键。全部为寄存器直接操作。

【若按键逻辑相反（未按就亮/按了不亮）】
  把 main.c 顶部 #define KEY_INPUT_MODE 0x04 改为 0x08（上拉输入），重编即可。

【编译 / 烧录】同任务2（产物 Objects/Task3.hex）

【现象】
  按住 KEY1 → LED1 亮；松开 → LED1 灭。
