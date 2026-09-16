================================================================
STM32F103 标准库工程模板 (StdPeriph Lib V3.6.0)
学号：202417010304   班级：智能3班   姓名：陈相林
================================================================

【这是什么】
本工程是按培训资料《STM32F103标准库基础.md》第 2.4 节搭建的
“标准库工程模板”——用 ST 官方标准外设库（而非寄存器直写）写代码。
已用 ARM GNU 工具链编译验证，Outputs/StdLib_Template.hex 可直接烧录。

【目录结构（与教程 2.4.1 一致）】
  StdLib_Template/
   ├ App_Common/     应用层通用文件（预留）
   ├ App_User/       main.c / stm32f10x_conf.h / stm32f10x_it.c / .h
   ├ Arm_Kernel/     core_cm3.c/.h + stm32f10x.h + system_stm32f10x.c/.h
   ├ Os/             任务调度/队列（预留，FreeRTOS 等）
   ├ Mid_Common/    中间层通用文件（预留，LVGL/fatfs）
   ├ Drv_Common/    底层驱动通用文件（预留）
   ├ STM32_Library/ 标准外设库 inc/(头) + src/(23个 .c 驱动)
   ├ Startup/        startup_stm32f10x_hd.s（ZET6 大容量启动文件）
   ├ Project/        StdLib_Template.uvprojx（Keil 工程）+ GNU 启动/链接脚本
   ├ Listings/       编译列表
   ├ Outputs/        StdLib_Template.hex（已验证可烧录）
   └ Doc/            说明

【标准库 vs 寄存器写法对比】
  寄存器版(原 Task2)：  GPIOG_BSRR = (1u<<14);
  标准库版(本工程)：    GPIO_SetBits(GPIOG, GPIO_Pin_14);
                       + 必须先 RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOG, ENABLE);

【在 Keil 里怎么用】
  1) 双击 Project/StdLib_Template.uvprojx 打开
  2) 工程已配好：
       - 芯片：STM32F103ZE（需先装 Keil.STM32F1xx_DFP 芯片包）
       - C/C++ 宏 Define：STM32F10X_HD,USE_STDPERIPH_DRIVER
            （HD=大容量 ZET6；USE_STDPERIPH_DRIVER=让 stm32f10x.h 包含 conf）
       - 包含路径：.\Arm_Kernel ; .\STM32_Library\inc ; .\App_User
       - Output 已勾 Create HEX File
  3) 按 F7 编译 → 生成 Objects/StdLib_Template.hex
  4) 用 ST-Link / DAP-Link 烧录，LED1(PG14) 闪烁

【关键点（最容易漏）】
  - 必须开对应外设时钟：RCC_APB2PeriphClockCmd(...)
  - 宏 STM32F10X_HD：ZET6 是大容量，填 HD；若是 C8T6 中容量填 MD
  - USE_STDPERIPH_DRIVER：不定义则 stm32f10x.h 不会包含外设库头文件

【如何用本模板写自己的任务】
  直接在 App_User/main.c 里改逻辑，或新增 App_User/xxx.c，
  在 Keil 的 App_User 组里 Add 进来即可。
  例：按键控制 LED 只需在 main.c 里加 RCC_APB2Periph_GPIOx 时钟 +
      GPIO_Init 配置输入 + 循环读取 GPIO_ReadInputDataBit()。
================================================================
