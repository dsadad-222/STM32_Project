### 串口通信模块及接口说明

串口使用 USART1，PA9 为 TX、PA10 为 RX。板上自带 CH340 USB 转串口电路接在这两个脚上，插上 USB 线即可在 PC 上看到虚拟串口。串口参数固定如下，串口助手按同样参数打开：

| 项目 | 取值 |
| --- | --- |
| 波特率 | 115200 |
| 数据位 | 8 |
| 停止位 | 1 |
| 校验 | 无 |
| 流控 | 无 |

接收采用中断加环形缓冲的结构。USART1_IRQHandler 每收到一个字节就写进 64 字节的环形缓冲并立即返回，主循环再通过 Usart_ReadByte 把字节取走。缓冲深度取 2 的幂，用位与运算代替取模，中断里不会因为除法而变慢。

| 函数原型 | void Usart_Init(uint32_t baud) |
| --- | --- |
| 描述 | 配置 PA9 为复用推挽输出、PA10 为浮空输入，设置波特率，使能接收中断并配置 NVIC 优先级 |
| 参数 | baud：波特率，工程默认传入 USART_BAUD_DEFAULT，即 115200 |
| 返回值 | void |

| 函数原型 | void Usart_SendByte(uint8_t byte) |
| --- | --- |
| 描述 | 阻塞方式发送一个字节，等发送数据寄存器空才返回 |
| 参数 | byte：待发送的字节 |
| 返回值 | void |

| 函数原型 | void Usart_SendString(const char \*str) |
| --- | --- |
| 描述 | 连续发送一个字符串，内部循环调用 Usart_SendByte |
| 参数 | str：以 0 结尾的字符串，可含回车换行 |
| 返回值 | void |

| 函数原型 | uint8_t Usart_ReadByte(uint8_t \*pByte) |
| --- | --- |
| 描述 | 从环形缓冲取出一个字节，供主循环轮询使用，不会阻塞 |
| 参数 | pByte：用于返回取到的字节 |
| 返回值 | 1 表示取到一字节，0 表示缓冲为空 |

### 存储模块及接口说明

存储使用片内 Flash 的最后一页。STM32F103ZE 属于大容量产品，主存储区 512KB、页大小 2KB、共 256 页；程序只占最前面 8KB 左右，所以把最后一页 0x0807F800 当作数据页。

保存时先擦除整页再写入记录。记录里带魔数和累加和校验：从没写过的页读出来是全 0xFF，魔数不匹配；上次写到一半掉电，校验和不匹配。这两种情况都会被判为无效记录，开机时不会把垃圾数据当参数使用。

文本字段是定长字段而不是 C 字符串，固定占 32 字节，不足部分用空格补齐，有效字符个数由 textLen 给出。这样存储和显示都不必关心结尾有没有结束符。

#### 3.4.1 内部 Flash 存储接口

| 函数原型 | uint8_t Store_Load(StoreRecord_t \*rec) |
| --- | --- |
| 描述 | 从数据页读出一条记录，校验魔数与累加和后返回是否有效 |
| 参数 | rec：用于返回读到的记录 |
| 返回值 | 1 表示读到有效记录，0 表示 Flash 里没有有效数据 |

| 函数原型 | uint8_t Store_Save(StoreRecord_t \*rec) |
| --- | --- |
| 描述 | 擦除数据页后写入一条记录，写入前自动计算并填充累加和 |
| 参数 | rec：待写入的记录 |
| 返回值 | 1 表示写入成功，0 表示写入失败 |

| 函数原型 | void Store_Clear(void) |
| --- | --- |
| 描述 | 擦除数据页，等效于清除已保存的记录 |
| 参数 | void |
| 返回值 | void |

| 函数原型 | uint8_t Store_IsSame(const StoreRecord_t \*a, const StoreRecord_t \*b) |
| --- | --- |
| 描述 | 比较两条记录的内容是否完全相同，用于判断是否需要重复写 Flash，避免无谓消耗擦写寿命 |
| 参数 | a、b：指向两条待比较的记录 |
| 返回值 | 1 表示两条记录内容一致，0 表示不一致 |

用到的常量定义如下：

| 宏名 | 取值 | 说明 |
| --- | --- | --- |
| STORE_PAGE_ADDR | 0x0807F800 | 数据页起始地址，即内部 Flash 最后一页 |
| STORE_MAGIC | 0x5A5AA5A5 | 记录有效标志，魔数不匹配即判为无效 |
| STORE_TEXT_MAX | 32 | 文本字段的固定长度，单位字节 |
| STORE_BIT_LEFT | 1 左移 0 位 | 左转向灯状态位 |
| STORE_BIT_RIGHT | 1 左移 1 位 | 右转向灯状态位 |
| STORE_BIT_BEEP | 1 左移 2 位 | 蜂鸣器状态位 |
| STORE_BIT_LED | 1 左移 3 位 | LED 灯状态位 |

#### 3.4.2 存储记录结构

存储记录的结构体定义如下：

typedef struct

{

uint32_t magic;

uint32_t flags;

uint32_t textLen;

char text[STORE_TEXT_MAX];

uint16_t checksum;

uint16_t reserved;

} StoreRecord_t;

各字段含义如下：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| magic | uint32_t | 魔数，等于 STORE_MAGIC 才认为记录有效 |
| flags | uint32_t | 设备状态位，按 STORE_BIT_ 开头的四个宏组合 |
| textLen | uint32_t | text 中有效字符个数，取值 0 到 32 |
| text | char 数组，32 字节 | 串口下发的文本，不足部分用空格补齐 |
| checksum | uint16_t | 前面所有字节的累加和 |
| reserved | uint16_t | 占位，用于凑齐 4 字节对齐 |

字段按 4 字节对齐排列，结构体不会有隐式填充，总长度 48 字节；校验范围是结构体长度减去末尾 4 字节，即 checksum 与 reserved 之前的所有内容。

### 系统时基模块及接口说明

SysTick 被配置成 1ms 周期中断，中断服务程序里对一个全局变量做递增，应用层与驱动层都靠它计算时间差。转向灯 500ms 闪烁、协议解析 200ms 半截帧超时都是基于这个时基实现的。

#### 3.5.1 SysTick 接口

| 函数原型 | void SysTick_Init(void) |
| --- | --- |
| 描述 | 按 SystemCoreClock 配置 SysTick 重装值，使能中断，得到一个 1ms 的系统节拍 |
| 参数 | void |
| 返回值 | void |

| 函数原型 | uint32_t Get_SysRunTime(void) |
| --- | --- |
| 描述 | 读取系统上电以来的运行时间，用于计算时间差而非阻塞等待 |
| 参数 | void |
| 返回值 | 系统运行时间，单位毫秒 |

| 函数原型 | void DelayMs(uint16_t ms) |
| --- | --- |
| 描述 | 基于 SysTick 计数实现毫秒级延时，阻塞等待指定时间 |
| 参数 | ms：延时长度，单位毫秒 |
| 返回值 | void |
