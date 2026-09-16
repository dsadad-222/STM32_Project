================================================================
STM32F103 标准库工程：外部中断控制测试
学号：202417010304   班级：智能3班   姓名：陈相林
================================================================

【任务来源】
培训课件 chapter5「中断及外部中断」-> 4、外部中断控制测试

【功能说明】
使用 STM32F10x 标准外设库配置外部中断 EXTI：
  - KEY1(PG3) 下降沿触发 EXTI3 -> 翻转 LED1(PG14)
  - KEY2(PG4) 下降沿触发 EXTI4 -> 翻转 LED2(PG15)
  - KEY3(PG5) 下降沿触发 EXTI5 -> 同时翻转 LED1、LED2
按键默认接内部上拉，按下时产生下降沿；LED 共阴，高电平点亮。

【关键 API 与步骤】
  1) RCC_APB2PeriphClockCmd(GPIOG + AFIO, ENABLE)  // 开 GPIO 与 AFIO 时钟
  2) GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IPU; // 上拉输入
  3) GPIO_EXTILineConfig(GPIO_PortSourceGPIOG, GPIO_PinSource3); // 映射引脚到 EXTI 线
  4) EXTI_InitStructure.EXTI_Trigger = EXTI_Trigger_Falling;     // 下降沿触发
  5) NVIC_PriorityGroupConfig(NVIC_PriorityGroup_1);
     NVIC_InitStructure.NVIC_IRQChannel = EXTI3_IRQn;            // 使能 NVIC 通道
  6) 编写 EXTI3_IRQHandler / EXTI4_IRQHandler / EXTI5_IRQHandler，
     进入后 EXTI_GetITStatus 判断 + 翻转 LED + EXTI_ClearITPendingBit 清标志

【在 Keil 里怎么用】
  1) 双击 Project/EXTI_Key.uvprojx 打开
  2) 工程已配好：芯片 STM32F103ZE；宏 STM32F10X_HD,USE_STDPERIPH_DRIVER
  3) 按 F7 编译 -> 生成 Objects/EXTI_Key.hex
  4) 烧录后按下 KEY1/2/3，对应 LED 翻转

【校验】
已用 ARM GNU 工具链编译验证，Outputs/EXTI_Key.hex 向量表合法：
  SP=0x20001000，Reset_Handler=0x08000041，可直接烧录。
================================================================
