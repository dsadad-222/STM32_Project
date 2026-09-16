================================================================
STM32F103 标准库工程 - 任务2：按键控制 LED（含 RGB 灯组扩展）
学号：202417010304   班级：智能3班   姓名：陈相林
（基于 StdLib_Template 标准库模板，结构相同，仅 main.c 不同）
================================================================

本工程在《chapter2.pdf》第7节"任务测试"的【任务2：基于标准库实现按键控制
LED】基础上进行扩展 —— 保留按键控制 LED 的原始功能，并额外点亮两组 RGB LED，
支持任意颜色组合显示与闪烁。扩展不再单独成工程，直接合在本任务内。

【引脚分配（依据 YB-DSF01-V1.0 原理图）】
  第一组 RGB LED(L1)：LRGB-R=PG0 / LRGB-G=PG1 / LRGB-B=PG2
  第二组 RGB LED(L2)：R=PE2 / G=PE3 / B=PE4
  基础 LED1=PG14  LED2=PG15   （高电平点亮）
  按键  KEY1=PG3  KEY2=PG4  KEY3=PG5   （浮空输入，外接上拉按下为高）

【功能】
  —— 任务2 原始功能 ——
  KEY1(PG3) 按下 -> LED1(PG14) 点亮；松开 -> 熄灭

  —— RGB 扩展功能 ——
  两组 RGB LED 可显示 8 种颜色组合：全灭 / 红 / 绿 / 蓝 / 黄 / 紫 / 青 / 白
  KEY2(PG4)：切换 RGB 颜色组合（8 档循环）
  KEY3(PG5)：切换 RGB 显示模式（0=静态 / 1=整体闪烁 / 2=两组交替闪）
  任意颜色组合可显示；可单独控制哪些颜色亮、哪些不亮
  闪烁模式下 LED2(PG15) 参与指示（与 LED1 反相）

【标准库写法要点】
  1) 开时钟：RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOG | RCC_APB2Periph_GPIOE, ENABLE);
  2) RGB/LED 配 GPIO_Mode_Out_PP（推挽输出）
  3) KEY1/2/3 配 GPIO_Mode_IN_FLOATING（浮空输入）
  4) 按键实时读：GPIO_ReadInputDataBit(GPIOG, GPIO_Pin_3) == Bit_SET
     切档用边沿检测（按下+释放）避免长按连发

【与寄存器版对照】
  寄存器： if (GPIOG_IDR & (1u<<3)) GPIOG_ODR |= (1u<<14);
  标准库： if (GPIO_ReadInputDataBit(GPIOG, GPIO_Pin_3))
               GPIO_SetBits(GPIOG, GPIO_Pin_14);

【使用】
  双击 Project/StdLib_Task3.uvprojx 用 Keil 打开，F7 编译 -> Objects/StdLib_Task3.hex
  或直接烧录 Outputs/StdLib_Task3.hex（已用 GNU 工具链验证，向量表合法：
  SP=0x20001000, Reset_Handler=0x08000041）

【踩坑提示】
  - 按键若按下为低电平，把 KEY1/2/3 改为 GPIO_Mode_IPU 即可，逻辑无需改
  - RGB 若为共阳，把所有 SetBits/ResetBits 对调
  - 若板子 RGB 引脚不是 PG0/1/2 与 PE2/3/4，改 main.c 中 GPIO_Config() 的 3 处 Pin
================================================================
