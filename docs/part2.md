### 人机交互模块及接口说明

本模块包含板载 LED、RGB 灯条、有源蜂鸣器和 OLED 显示屏四类外设，向上提供开关、翻转、显示等接口，应用层不接触任何 GPIO 或 I2C 寄存器。

#### 3.2.1 LED 与 RGB 灯条驱动接口

LED1（PG14）与 LED2（PG15）是板载指示灯，RGB 灯条接在 PG0、PG1、PG2 上，三路均为高电平点亮。

| 函数原型 | void LED_Init(void) |
| --- | --- |
| 描述 | 把 LED1、LED2 所用引脚配置为推挽输出，上电后两灯均为熄灭状态 |
| 参数 | void |
| 返回值 | void |

| 函数原型 | void LED_On(LED_TypeDef led) |
| --- | --- |
| 描述 | 点亮指定的板载指示灯 |
| 参数 | led：LED1、LED2 或 LED_ALL（同时点亮两灯） |
| 返回值 | void |

| 函数原型 | void LED_Off(LED_TypeDef led) |
| --- | --- |
| 描述 | 熄灭指定的板载指示灯 |
| 参数 | led：LED1、LED2 或 LED_ALL |
| 返回值 | void |

| 函数原型 | void LED_Toggle(LED_TypeDef led) |
| --- | --- |
| 描述 | 翻转指定指示灯的状态，亮变灭、灭变亮。转向灯闪烁就是靠它实现的 |
| 参数 | led：LED1、LED2 或 LED_ALL |
| 返回值 | void |

| 函数原型 | void RGB_Init(void) |
| --- | --- |
| 描述 | 把 RGB 灯条的三个引脚配置为推挽输出，上电后全灭 |
| 参数 | void |
| 返回值 | void |

| 函数原型 | void RGB_Set(RGB_TypeDef color) |
| --- | --- |
| 描述 | 设置 RGB 灯条的显示颜色，一次调用同时决定三路的亮灭 |
| 参数 | color：RGB_NONE（全灭）、RGB_R、RGB_G、RGB_B、RGB_YELLOW（红加绿）、RGB_ALL（三色全亮） |
| 返回值 | void |

用到的枚举定义如下：

typedef enum { LED1 = 0, LED2, LED_ALL } LED_TypeDef;

typedef enum { RGB_NONE = 0, RGB_R, RGB_G, RGB_B, RGB_YELLOW, RGB_ALL } RGB_TypeDef;

#### 3.2.2 蜂鸣器驱动接口

板上是 5V 有源蜂鸣器，经 SS8050 三极管驱动，接在 PG12 上，引脚输出高电平即鸣叫。

| 函数原型 | void Beep_Init(void) |
| --- | --- |
| 描述 | 把 PG12 配置为推挽输出，上电后蜂鸣器不响 |
| 参数 | void |
| 返回值 | void |

| 函数原型 | void Beep_On(void) |
| --- | --- |
| 描述 | 让蜂鸣器持续鸣叫，直到调用 Beep_Off |
| 参数 | void |
| 返回值 | void |

| 函数原型 | void Beep_Off(void) |
| --- | --- |
| 描述 | 关闭蜂鸣器 |
| 参数 | void |
| 返回值 | void |

| 函数原型 | void Beep_Beep(uint16_t ms) |
| --- | --- |
| 描述 | 鸣叫指定毫秒数后自动关闭，内部使用 DelayMs 阻塞等待 |
| 参数 | ms：鸣叫时长，单位毫秒 |
| 返回值 | void |

#### 3.2.3 OLED 显示驱动接口

屏为 0.86 寸 4PIN OLED，控制器 SSD1306，通过软件 I2C1 驱动，SCL 接 PB6、SDA 接 PB7。I2C1 这两根线在板上已有 R21、R22 两个 4.7K 电阻上拉到 3V3，因此按开漏输出配置即可，不需要外接上拉。

屏参数如下：

| 项目 | 取值 | 说明 |
| --- | --- | --- |
| 分辨率 | 128 x 32 | 宽 128 像素、高 32 像素 |
| 组织方式 | 4 页 | 每页 8 行像素，每页 128 字节 |
| 字符尺寸 | 8 x 8 像素 | 直接使用 8x8 ASCII 字库 |
| 单行字符数 | 16 | 128 除以 8 |
| 总行数 | 4 | 与页数一致 |
| 从机地址 | 0x78 | 7 位地址 0x3C 左移一位后的 8 位写地址 |

显存操作采用先写缓存、再统一刷新的方式：所有显示函数只修改内存中的显存数组，真正发送到屏上的动作由 OLED_Refresh 完成。这样一屏内容可以一次性推给屏，不会出现写一半就被看到的现象。

| 函数原型 | void OLED_Init(void) |
| --- | --- |
| 描述 | 初始化 I2C 引脚并下发 SSD1306 上电配置序列，清空显存后刷新一次 |
| 参数 | void |
| 返回值 | void |

| 函数原型 | void OLED_DisplayOn(void) |
| --- | --- |
| 描述 | 打开屏显，用于从熄屏状态恢复 |
| 参数 | void |
| 返回值 | void |

| 函数原型 | void OLED_DisplayOff(void) |
| --- | --- |
| 描述 | 关闭屏显，屏上内容保留在显存里 |
| 参数 | void |
| 返回值 | void |

| 函数原型 | void OLED_Clear(void) |
| --- | --- |
| 描述 | 清空整屏显存，需要调用 OLED_Refresh 才能看到效果 |
| 参数 | void |
| 返回值 | void |

| 函数原型 | void OLED_ClearLine(uint8_t row) |
| --- | --- |
| 描述 | 清空指定的一行，用于局部刷新时避免残影 |
| 参数 | row：行号，取值 0 到 3 |
| 返回值 | void |

| 函数原型 | void OLED_Refresh(void) |
| --- | --- |
| 描述 | 把显存整屏写入 SSD1306，是唯一真正产生 I2C 通信的显示接口 |
| 参数 | void |
| 返回值 | void |

| 函数原型 | void OLED_ShowChar(uint8_t col, uint8_t row, char ch) |
| --- | --- |
| 描述 | 在指定位置显示一个 ASCII 字符，只改显存不刷新 |
| 参数 | col：列号，取值 0 到 15；row：行号，取值 0 到 3；ch：待显示字符，范围 0x20 到 0x7E |
| 返回值 | void |

| 函数原型 | void OLED_ShowString(uint8_t col, uint8_t row, const char *str) |
| --- | --- |
| 描述 | 从指定位置起连续显示一个字符串，超出右边界自动截断 |
| 参数 | col：起始列号；row：行号；str：以 0 结尾的字符串 |
| 返回值 | void |

本工程的屏显排版固定为 4 行：

| 行号 | 内容 | 说明 |
| --- | --- | --- |
| 第 0 行 | NEW L0 R0 B0 D0 或 RST L1 R0 B0 D0 | NEW 表示全新开机，RST 表示从 Flash 恢复；L、R、B、D 分别是左转向灯、右转向灯、蜂鸣器、LED 灯的状态 |
| 第 1 行 | 文本前半 | 串口下发的文本第 1 到 16 个字符 |
| 第 2 行 | 文本后半 | 串口下发的文本第 17 到 32 个字符 |
| 第 3 行 | 提示信息 | 例如 BOOTING...、CTRL OK、TEXT SAVED、FLASH CLEARED |

#### 3.2.4 8x8 点阵 ASCII 字库

字库为独立的数据文件，只提供字模数组和几个尺寸宏，不含任何函数。

| 名称 | 类型 | 说明 |
| --- | --- | --- |
| g_font8x8 | const uint8_t 二维数组 | 每个字符占 8 个字节，一个字节表示一行，最高位为该行最左边的像素 |
| FONT8X8_FIRST_CHAR | 宏，0x20 | 字库中第一个字符，空格 |
| FONT8X8_LAST_CHAR | 宏，0x7E | 字库中最后一个字符，波浪号 |
| FONT8X8_WIDTH | 宏，8 | 字符点阵宽度，含 1 列字符间隔 |
| FONT8X8_HEIGHT | 宏，8 | 字符点阵高度 |

数组下标按字符码减去 FONT8X8_FIRST_CHAR 计算，例如字符 A 的字模位于 g_font8x8[0x41 - 0x20]。
