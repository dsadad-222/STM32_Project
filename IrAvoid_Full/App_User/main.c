/**
  ******************************************************************************
  * @file    App_User/main.c
  * @brief   ADC 内部温度采集 + 串口控制 + OLED 显示 + 呼吸灯（chapter8 综合）
  *
  *          【本次实训（任务实训11 · 需求5）新增 —— 左右红外避障传感器采集】
 *          1. KEY1(PG3) 单击：测左侧红外避障，结果显示到 OLED 第 3 行并打串口。
 *          2. KEY2(PG4) 单击：测右侧红外避障，同上。
 *          3. KEY3(PG5) 单击：左右两路一起测，结果通过串口打印到 PC。
 *          4. 板上两路对管是【发射管 + 接收管】两组分立元件，不是三线一体模块：
 *             发射管必须 MCU 自己驱动 —— 基极回路接在 5V 上（PNP SS8550），
 *             所以驱动脚配【开漏输出】：写低 = 基极被拉低 = 发射管亮，
 *             写高 = 引脚高阻 = 发射管灭（推挽写高是关不断的，Vbe 还有 1.7V）。
 *             接收管集电极被 10K 上拉到 3V3，见光才导通，于是
 *                 ★ 有障碍（有反射）= 低电平，前方空旷 = 高电平 —— 最容易写反。
 *             测量不用单纯的高低电平，而是接 ADC3 做"灭灯/亮灯差分"，
 *             既能分远/中/近三档，又自动扣掉环境光的影响。
 *          5. 因为 KEY1/KEY2/KEY3 已全被本需求占用，需求4 的原 KEY1（测距并存入
 *             外部 FLASH）改到串口命令 'O'，需求3 的原 KEY3（读外部 FLASH 文本）
 *             改到 'E'，功能一个不少；串口另加 Q/J/V 做同样的红外测量。
 *          6. PIN（依据原理图 YB-DSF01-V1.0 第 2 页 / U1B 页）：
 *                 左发射管 P1 = PE5    右发射管 P3 = PE6   （开漏，低 = 亮）
 *                 左接收管 P2 = PF9    右接收管 P4 = PF10  （ADC3_IN7 / IN8，
 *                                                       3V3 上拉，有障碍 = 低）
 *
 *          【本次实训（任务实训10 · 需求4）新增 —— 超声波测距 + 片外 FLASH 存储 + 距离联动】
  *          1. KEY1(PG3) 单击：HC-SR04 测一次距离（连测 3 次取中值），
  *             把距离值存进片外 W25Q64 的"距离记录区"（扇区 1，0x001000）。
  *             每条记录 2 字节（小端 mm），0xFFFF = 空，开机自动扫描出已存条数。
  *          2. KEY2(PG4) 单击：从距离记录区按顺序读出一条（第 1 次读第 1 条，
  *             第 2 次读第 2 条……读完自动回到第 1 条），把距离显示到 OLED，
  *             并按任务书要求做声光联动：
  *                 < 10cm        蜂鸣器鸣叫 1 秒
  *                 10cm ~ 50cm   左转向灯闪 2 次
  *                 50cm ~ 1m     右转向灯闪 2 次
  *                 > 1m          左右转向灯双闪 5 次
  *          3. KEY3(PG5) 单击：保留需求3 的功能 —— 读片外 FLASH 的文本记录（扇区 0）。
  *          4. 呼吸灯原来挂在 KEY2 上，本任务把 KEY2 让给距离读取，
  *             呼吸灯改到 ASCII 快捷命令 'W'（串口敲一个 W 回车即可）。
  *
  *          【存储分区（两片 FLASH 各管各的，互不干扰）】
  *              内部 FLASH  0x0807F000  24 字节文本记录（需求3）
  *              内部 FLASH  0x0807F800  设备状态 + 标定值（需求3）
  *              外部 W25Q64 0x000000    24 字节文本记录（需求3，扇区 0）
  *              外部 W25Q64 0x001000    2 字节距离记录（需求4，扇区 1）
  *
  *          【本任务（chapter8）新增】
 *          1. 芯片内部温度采集：ADC1 的通道 16，每 2 秒采一次；
 *             温度(℃) = {(V25 - Vsense) / Avg_Slope} + 25
 *             V25 = 1.43V，Avg_Slope = 4.3mV/℃
 *             ★ 这里读的是芯片自己的温度（die 温度），不是环境/室内温度。
 *               传感器就集成在芯片内部，天然跟着芯片自身发热走，所以读数
 *               会比房间空气高几度（72MHz 全速运行大约高 5~9℃），这是它的
 *               正常物理特性，不是故障。任务书只要求"采集内部温度并按公式
 *               换算显示"，并没有要求测室温，所以本项目的定位就是
 *               "芯片温度监测"，屏上和串口报的都是芯片温度。
  *          2. KEY2（PG4）按下：左转向灯（红色 LED1 / PG14）进入呼吸灯效果
  *          3. 每次采集完成：把 ADC 原始值、换算后的模拟量、温度值
  *             显示到 OLED，并通过串口发到 PC：
  *                 Current ADC_Value is XXXX
  *                 Current Voltage is XXXX
  *                 Current Temperature is XXXX
  *
  *          【沿用 chapter7 的功能】
  *          - 串口协议帧控制左/右转向灯、蜂鸣器、LED 灯条
  *          - 串口下发文本显示到 OLED
  *          - 状态与文本写内部 Flash，掉电不丢，开机自动恢复
  *
 *  一、OLED 有两个显示页（0.86 寸，128x32 像素，一行 16 个字符）
 *      温度数据页（默认页，每次采样后都会回到这一页）——按任务书规定的三行格式：
 *          +------------------+
 *          | ADCvalue:  1738  |  <- ADC 原始值 0~4095
 *          | Voltage:  1.390V |  <- 换算后的模拟量（VDDA 反推，3 位小数）
 *          | Temp:     35.9C  |  <- 芯片结温（1 位小数；读数无效显示 --.-）
 *          | L0 R0 B0 D0  CAL |  <- 设备状态（L左转 R右转 B蜂鸣器 D灯条）+ 尾部标记
 *          +------------------+
 *          标签定长、数值在固定 5 格内右对齐，位数变化时数字不会左右抖。
 *          第 4 行状态行是任务书之外加的（方便演示时看设备开关状态），不影响验收格式。
 *      文本页（串口下发文本后自动切过来，或按 KEY1 切换）：
 *          第 1、2 行 = 串口发来的 32 个字符，第 3 行 = 提示信息
 *      尾部标记：CAL = 已标定 / BRTH = 呼吸灯在跑 / RST = 开机从 Flash 恢复 / NEW = 首次上电
 *      屏的从机地址上电自动识别（0x78 / 0x7A 都试一遍），开机横幅会打印
 *      "OLED : ack ok ..." 或 "OLED : NO ACK ..."，屏不亮时可据此判断是
 *      接线问题还是驱动问题。
  *
  *  二、按键（按下为低电平）
  *      KEY1(PG3) 单击：超声波测一次距离，存进片外 FLASH 距离记录区（需求4-1）
  *      KEY2(PG4) 单击：从距离记录区顺序读一条，显示 + 声光联动（需求4-2）
  *      KEY3(PG5) 单击：读片外 FLASH 的文本记录（需求3 功能保留）
  *
  *  三、协议帧格式（与任务书一致）
  *      ┌────────┬────────┬──────────────┬────────────┬──────────────────┐
  *      │ 帧头 0 │ 帧头 1 │  数据域长度  │   功能字   │       数据       │
  *      │  0x55  │  0xFF  │      N       │    见下    │      见下        │
  *      └────────┴────────┴──────────────┴────────────┴──────────────────┘
  *      N = 功能字 + 数据 的字节数。数据后面可以再跟校验字节，
  *          解析器收满自己需要的参数就立刻执行，多出来的字节会被忽略。
  *
  *      0x06  控制设备，数据 = 控制单元 + 开关状态
  *              控制单元：0x00 左转向灯 LED1(PG14)   0x01 右转向灯 LED2(PG15)
  *                        0x02 蜂鸣器   (PG12)       0x03 LED 灯 RGB 灯条(PG0/PG1/PG2)
  *              开关状态：0x00 关，0x01 开（只带 1 个字节的旧格式按"翻转"处理）
  *      0x07  下发文本，数据 = ASCII 文本（最多 32 个字符）
  *            文本显示到 OLED 文本页并写入 Flash
  *      0x08  存储操作，数据 = 操作码（0x00 保存 / 0x01 清除 / 0x02 重新读回）
  *
  *      例子：
  *          55 FF 03 06 02 01     蜂鸣器 开      （...02 00 即关）
  *          55 FF 03 06 00 01     左转向灯 开
  *          55 FF 06 07 HELLO     OLED 显示 "HELLO" 并写入 Flash
  *          55 FF 02 08 01        清除 Flash 记录
  *
 *  四、ASCII 快捷命令（调试用，空闲状态下直接敲，不影响协议帧）
 *      L/R/B/D + 1|0   左转/右转/蜂鸣器/LED 灯 开或关，省略数字 = 翻转
 *      T + 文本        显示到 OLED 并保存（回车结束）
 *      S / C / P       保存 Flash / 清除 Flash / 重新读回
 *      A               立即采集一次温度并上报
 *      K + 温度 + 回车 一键标定：把当前温度当作指定温度（不填数字 = 25℃），
 *                      得到的偏移量写进 Flash，掉电不丢
 *      Z               清除标定，恢复成手册公式的原始结果
 *      M               立即测一次距离并显示（不存储，演示时看当前距离用）
 *      N               等价于按一下 KEY2：顺序读下一条距离记录 + 联动
 *      X               清空距离记录区（擦掉扇区 1），演示前归零用
 *      W               呼吸灯 开 / 关（原 KEY2 的功能，改到这里）
 *      I               读内部 FLASH 的数据记录并显示到 OLED 第 1 行
 *                      （原 KEY1 的功能，被需求4 的测距占用后挪到这里）
 *
 *  五、温度为什么偏高、以及怎么改（重点，汇报时讲这段）
 *
 *      【现象】室温下读数 ~98℃，看着像芯片在发烧。
 *
 *      【第一步先分清：是"真高温"还是"固定偏差"】
 *          看开机瞬间的第一次读数 —— 实测上电一小会儿就已经 96.4℃。
 *          芯片热质量很小但也不可能 1 秒内从室温冲到 96℃，所以这 96℃ 里
 *          绝大部分是**固定零点偏差**，不是真实温度。
 *          之后读数从 96.4 缓慢爬到 98.9℃、噪声只有 ±0.3℃，那 2~3℃ 才是
 *          真实的芯片自热。两个成分要分开看。
 *
 *      【第二步找偏差出在哪】
 *          公式 T = (V25 - Vsense)/Avg_Slope + 25 本身没问题，
 *          偏差只能出在 V25 / Vsense / Avg_Slope 三个量上：
 *            · Vsense = AD值 × VDDA / 4096 —— VDDA 已经用通道 17 的 Vrefint
 *              反推过（实测约 3.13V，落在合理区间内，这一路是准的）；
 *            · 剩下的就是 V25：手册给的是 1.43V「典型值」，芯片之间本来就有
 *              离散性，非原厂的兼容片偏差更大。V25 实测偏低 0.3V，按
 *              4.3mV/℃ 折合就是 70℃ 左右的整体平移 —— 正好对上现象。
 *
 *      【第三步：单点标定把它拉回来】
 *          偏差是**加性**的（整体平移，不改变斜率），所以一个偏移量就能修正：
 *              偏移量 = 参考温度 - 公式算出的温度
 *          在一个已知温度下（比如室温 29℃）敲一次 K，偏移量存进内部 Flash，
 *          以后每次算温度都加上它，掉电不丢。
 *          标定后关机再开的自热趋势依然保留（相对测量一直是准的），
 *          这才是这颗片子真正能给的精度。
 *
 *      【顺带加的两层健壮性】
 *          · 丢首次转换 + 去极值平均：切换通道后第一次转换不可信，丢掉；
 *            连读 8 次再扣掉最大最小各一次，避免野点把结果拉偏。
 *          · VDDA 合理区间放宽到 1800~4600mV：原来卡在 2800~3600mV，
 *            万一供电真的偏离（电池供电、两路电源倒灌抬高），反推值会被
 *            当成坏点退回 3.300V 默认值，温度就会整体算错几十度。
 *            区间放宽后，实测 VDDA 一律参与换算。
 ******************************************************************************
 */

#include "led_drv.h"
#include "beep_drv.h"
#include "systick_drv.h"
#include "usart_drv.h"
#include "oled_drv.h"
#include "flash_drv.h"
#include "adc_drv.h"
#include "key_drv.h"
#include "pwm_drv.h"
#include "w25q64_drv.h"
#include "hcsr04_drv.h"
#include "ir_drv.h"
#include "cn_msg.h"

/* ========================= 协议字段 ========================= */

#define FRAME_HEAD0         0x55
#define FRAME_HEAD1         0xFF

#define FUNC_CTRL           0x06        /* 控制设备 */
#define FUNC_STORE_DATA     0x07        /* 数据存储（本任务：写内部 / 外部 FLASH）*/
#define FUNC_STORE          0x08        /* 状态存储操作 */
#define FUNC_TEXT           0x09        /* 下发文本（原 0x07，为数据存储让位）*/

/* ---- 数据存储（功能字 0x07）的控制单元 ---- */
#define DATA_UNIT_INTERNAL  0x01        /* 存到片内 FLASH */
#define DATA_UNIT_EXTERNAL  0x02        /* 存到片外 W25Q64 */
#define DATA_MAX_LEN        20u         /* 数据域最大 20 字节（任务书规定）*/

#define CTRL_LEFT_TURN      0x00
#define CTRL_RIGHT_TURN     0x01
#define CTRL_BEEP           0x02
#define CTRL_LED            0x03

#define STORE_OP_SAVE       0x00
#define STORE_OP_CLEAR      0x01
#define STORE_OP_RELOAD     0x02

#define FRAME_DATA_MAX      40          /* 单帧数据域最多 40 字节 */
#define PARSE_TIMEOUT_MS    200         /* 帧内字节间隔超时，丢弃半截帧 */
#define ASCII_TIMEOUT_MS    3000        /* ASCII 快捷命令的超时（人手敲，给宽一点）*/
#define TURN_BLINK_PERIOD   500         /* 转向灯闪烁半周期（ms）*/

/* ========================= 本任务参数 ========================= */

#define SAMPLE_PERIOD_MS    2000u       /* 温度采集周期：2 秒 */

/* ========================= 数据存储记录 =========================
 * 内部 / 外部 FLASH 存的是同一种记录，按字节流排布（不用结构体，避开编译器
 * 对齐填充的坑）：
 *      [0]  0x46 'F'     魔数 0
 *      [1]  0x53 'S'     魔数 1
 *      [2]  数据长度      0 ~ 20
 *      [3..22]  数据     最多 20 字节，不足部分为 0xFF
 *      [23] 校验         前 23 字节的累加和（低 8 位）
 * 一共 24 字节，内部 FLASH 按半字（2 字节）编程正好 12 次。
 */
#define DATA_REC_SIZE       24u
#define DATA_REC_MAGIC0     0x46u
#define DATA_REC_MAGIC1     0x53u
#define DATA_REC_OFF_LEN    2u
#define DATA_REC_OFF_DATA   3u
#define DATA_REC_OFF_CHECK  (DATA_REC_OFF_DATA + DATA_MAX_LEN)      /* = 23 */

/* 内部 FLASH 的数据页：倒数第二页（2KB 一页），和存设备状态的最后一页
 * 0x0807F800 分开，各擦各的，互不影响。
 * 注意：Keil 下载范围要设成 -FL07F000 才能保护这两页不被整片擦掉。*/
#define DATA_PAGE_ADDR      0x0807F000u

/* 外部 W25Q64 里放记录的地址（扇区 0 起始）*/
#define DATA_EXT_ADDR       0x000000u

/* ========================= 需求4：片外 FLASH 距离记录 =========================
 * 距离记录单独占一个扇区，和需求3 的 24 字节文本记录彻底分开：
 *     需求3 文本记录区：W25Q64 扇区 0，0x000000，24 字节/条
 *     需求4 距离记录区：W25Q64 扇区 1，0x001000，2 字节/条
 * 距离区内部布局：
 *     [0x001000 .. 0x001003]  4 字节区头 = 'D' 'R' + 版本号 + 预留
 *     [0x001004 起]           2 字节/条，小端 mm，0xFFFF = 空（擦除后的默认值）
 * 区头只在初始化时写一次（擦除后全 0xFF，写 0x44/0x52 是 1->0，合法），
 * 之后每条记录追加到新地址上，永远不重复写同一个位置，所以不用反复擦扇区。
 * 4KB 扇区扣掉 4 字节区头，最多 (4096-4)/2 = 2046 条。
 * 量程 4m = 4000mm，永远取不到 65535，所以拿 0xFFFF 当"空"是安全的。
 */
#define DIST_SECTOR_ADDR    0x001000u
#define DIST_HEAD_SIZE      4u
#define DIST_DATA_ADDR      (DIST_SECTOR_ADDR + DIST_HEAD_SIZE)
#define DIST_REC_SIZE       2u
#define DIST_MAX_REC        ((uint16_t)((W25Q64_SECTOR_SIZE - DIST_HEAD_SIZE) / DIST_REC_SIZE))
#define DIST_EMPTY          0xFFFFu
#define DIST_MAGIC0         0x44u           /* 'D' */
#define DIST_MAGIC1         0x52u           /* 'R' */
#define DIST_HEAD_VER       0x01u

/* 距离联动的四个区间（任务书原文，单位 mm）*/
#define DIST_NEAR_MM        100u            /* < 10cm          -> 蜂鸣器 */
#define DIST_LEFT_MM        500u            /* 10cm ~ 50cm     -> 左转向灯闪 2 次 */
#define DIST_RIGHT_MM       1000u           /* 50cm ~ 1m       -> 右转向灯闪 2 次 */
                                            /* > 1m            -> 左右双闪 5 次 */

#define ALERT_BLINK_PERIOD  250u            /* 提示闪烁半周期（ms），比转向灯快一倍 */
#define ALERT_BEEP_MS       1000u           /* <10cm 蜂鸣时长（ms）*/

/* ========================= 运行状态 ========================= */

static uint8_t      s_leftTurnOn   = 0;
static uint8_t      s_rightTurnOn  = 0;
static uint8_t      s_beepOn       = 0;
static uint8_t      s_ledOn        = 0;
static uint8_t      s_blinkPhase   = 0;
static uint32_t     s_blinkTick    = 0;

/* 右转向灯的彩虹色序：每闪一次换一色 */
#define RAINBOW_STEP_MAX    6u
static const RGB_TypeDef s_rainbow[RAINBOW_STEP_MAX] =
{
    RGB_R, RGB_YELLOW, RGB_G, RGB_CYAN, RGB_B, RGB_MAGENTA
};
static uint8_t      s_rainbowIdx   = 0;

static char         s_text[STORE_TEXT_MAX];     /* 当前文本，定长 32，空格补齐 */
static uint32_t     s_textLen      = 0;         /* 有效字符个数 */
static char         s_msg[OLED_COL_MAX + 1];    /* OLED 第 4 行的状态/提示 */

static uint32_t     s_lastSampleMs = 0;         /* 上次采样时刻 */
static uint32_t     s_lastKeyMs    = 0;         /* 上次按键扫描时刻 */
static uint32_t     s_sampleCount  = 0;         /* 开机以来的采样次数 */
static AdcTempSample_t s_sample;                /* 最近一次采样结果 */

/* ---- 两片 FLASH 里存的数据（分别显示在 OLED 第 1 / 第 3 行）---- */
static uint8_t      s_inData[DATA_MAX_LEN];     /* 内部 FLASH 读出的数据 */
static uint8_t      s_inLen        = 0;
static uint8_t      s_inValid      = 0;         /* 1 = 读到了有效记录 */

static uint8_t      s_exData[DATA_MAX_LEN];     /* 外部 FLASH 读出的数据 */
static uint8_t      s_exLen        = 0;
static uint8_t      s_exValid      = 0;         /* 1 = 读到了有效记录 */

static uint8_t      s_extOk        = 0;         /* W25Q64 是否检测到（1=在）*/

/* ---- 需求4：距离测量 / 记录 / 联动 ---- */
static uint16_t     s_distCount    = 0;         /* 距离记录区已存条数（开机扫描得出）*/
static uint16_t     s_distCursor   = 0;         /* KEY2 下一条要读的下标（0 基）*/
static uint16_t     s_distLastMm   = DIST_EMPTY;/* 最近一次测量/读出的距离（mm）*/
static uint8_t      s_distValid    = 0;         /* 1 = 上面的距离值有效 */
static uint16_t     s_distShownNo  = 0;         /* 当前显示的距离值对应的记录号；0 = 现场测量的值，不在记录里 */
static uint8_t      s_distAreaOk   = 0;         /* 1 = 距离扇区区头已就绪 */
static uint8_t      s_line3Mode    = 0;         /* OLED 第 3 行：0=外部文本(需求3)，1=距离(需求4)，2=红外避障(需求5) */

/* ---- 需求5：红外避障对管（左发 PE5 / 右发 PE6；左收 PF9 / 右收 PF10）----
   接收管被 10K 上拉，见光导通，所以【有障碍 = 低电平】。
   这里存的是完整测量结果（本底 / 反射 / 差值 / 分档），测量过程在 ir_drv.c 里。*/
static IrResult_t   s_irL;                      /* 左路最近一次完整测量结果 */
static IrResult_t   s_irR;                      /* 右路最近一次完整测量结果 */
static uint8_t      s_irLeft       = 0;         /* 左路最近一次读数：1 = 有障碍 */
static uint8_t      s_irRight      = 0;         /* 右路最近一次读数：1 = 有障碍 */
static uint8_t      s_irLeftValid  = 0;         /* 1 = 这一路已经测过（没测过屏上显示 '-'）*/
static uint8_t      s_irRightValid = 0;

/* 距离联动的提示动作（有限次闪烁 / 定时蜂鸣，跑完自动收手）*/
typedef enum
{
    ALERT_NONE = 0,     /* 无提示 */
    ALERT_BEEP,         /* < 10cm      : 蜂鸣器鸣叫 */
    ALERT_LEFT2,        /* 10cm ~ 50cm : 左转向灯闪 2 次 */
    ALERT_RIGHT2,       /* 50cm ~ 1m   : 右转向灯闪 2 次 */
    ALERT_BOTH5         /* > 1m        : 左右转向灯双闪 5 次 */
} AlertKind_t;

static AlertKind_t  s_alertKind    = ALERT_NONE;
static uint8_t      s_alertTotal   = 0;         /* 本次要闪几次 */
static uint8_t      s_alertDone    = 0;         /* 已经闪完几次 */
static uint8_t      s_alertPhase   = 0;         /* 0 = 灭，1 = 亮 */
static uint32_t     s_alertTick    = 0;         /* 上次翻转时刻 */
static uint32_t     s_alertEndMs   = 0;         /* 蜂鸣结束时刻 */
static uint8_t      s_alertBreath  = 0;         /* 提示前呼吸灯是否在跑，提示结束后恢复 */

/* ========================= 前置声明 =========================
 * ASCII 快捷命令 'N' 在 ParseByte（定义在前面）里要调 Key2ReadNext，
 * 而 Key2ReadNext 在按键处理段（定义在后面），所以先声明一下。*/
static void Key1MeasureAndStore(void);
static void Key2ReadNext(void);
static void Key3ReadExternal(void);
static void AppendDigits4(char *line, uint8_t *pos, uint16_t v);
static void KeyIrLeft(void);
static void KeyIrRight(void);
static void KeyIrBoth(void);
static void DumpIrPins(void);

/* 协议解析状态机 */
typedef enum
{
    RX_HEAD0 = 0,       /* 等帧头 0x55（空闲态同时识别 ASCII 快捷命令）*/
    RX_HEAD1,           /* 等帧头 0xFF */
    RX_LEN,             /* 等数据域长度 */
    RX_FUNC,            /* 等功能字 */
    RX_DATA,            /* 收数据 */
    RX_ASCII_ARG,       /* 快捷命令：等 '0'/'1'（等不到就翻转一次）*/
    RX_ASCII_TEXT,      /* 快捷命令：收文本，回车/换行或满 32 字符结束 */
    RX_ASCII_CAL        /* 快捷命令 K：收标定参考温度，回车/换行结束 */
} RxState_t;

static RxState_t    s_rxState    = RX_HEAD0;
static uint8_t      s_rxLen      = 0;           /* 长度域声明的值 */
static uint8_t      s_rxFunc     = 0;           /* 本次帧的功能字 */
static uint8_t      s_rxNeed     = 0;           /* 还差几个数据字节 */
static uint8_t      s_rxCount    = 0;           /* 已收数据字节数 */
static uint8_t      s_rxData[FRAME_DATA_MAX];
static uint32_t     s_lastRxMs   = 0;
static uint8_t      s_asciiCmd   = 0;           /* 快捷命令首字母 L/R/B/D */
static uint32_t     s_calRefC    = 0;           /* K 命令收到的参考温度整数部分（℃）*/

static StoreRecord_t s_saved;                   /* 最近一次写入 / 读出的记录 */

/* ========================= 数字格式化 ========================= */

/* 无符号整数转十进制字符串，返回写入的字符个数 */
static uint8_t WriteU32(char *out, uint32_t value)
{
    char    tmp[10];
    uint8_t n = 0;
    uint8_t i;

    if (value == 0u)
    {
        out[0] = '0';
        out[1] = '\0';
        return 1u;
    }

    while ((value > 0u) && (n < 10u))
    {
        tmp[n] = (char)('0' + (value % 10u));
        value /= 10u;
        n++;
    }

    for (i = 0; i < n; i++)
    {
        out[i] = tmp[n - 1u - i];
    }

    /* 必须补结束符：调用方是 WriteU32(num,..) 连着 Usart_SendString(num) 用的，
       而 num 是未初始化的局部数组。不补的话短数字盖不掉上一轮的长数字尾巴，
       例如先写 286 再写 29，会打印出 "296"。 */
    out[n] = '\0';
    return n;
}

/* 把放大 10^decimals 倍的整数写成小数文本，例如 (1626, 3) -> "1.626" */
static void FormatFixed(char *out, int32_t scaled, uint8_t decimals)
{
    uint32_t div = 1u;
    uint32_t frac;
    int32_t  intPart;
    uint8_t  i;

    for (i = 0; i < decimals; i++)
    {
        div *= 10u;
    }

    if (scaled < 0)
    {
        *out = '-';
        out++;
        scaled = -scaled;
    }

    intPart = scaled / (int32_t)div;
    frac    = (uint32_t)(scaled % (int32_t)div);

    out += WriteU32(out, (uint32_t)intPart);

    if (decimals > 0u)
    {
        uint32_t p = div / 10u;

        *out = '.';
        out++;
        while (p > 0u)
        {
            *out = (char)('0' + ((frac / p) % 10u));
            out++;
            p /= 10u;
        }
    }

    *out = '\0';
}

static void AppendTextX(char *line, uint8_t *pos, const char *text)
{
    uint8_t i = 0;

    while (text[i] != '\0')
    {
        line[*pos] = text[i];
        (*pos)++;
        i++;
    }
}

static void PadLine(char *line, uint8_t *pos)
{
    while (*pos < OLED_COL_MAX)
    {
        line[*pos] = ' ';
        (*pos)++;
    }
    line[*pos] = '\0';
}

/* ========================= 显示 ========================= */

static void SetMessage(const char *text)
{
    uint8_t i = 0;

    /* 屏上用 8x8 ASCII 字库，只覆盖 0x20~0x7E。这里统一把超出范围的字节
       过滤成 '.'：万一有人再把 GBK 中文串传进来，屏上只会是一串点，
       而不是 OLED_ShowChar 逐个替换出来的问号 —— 一眼能看出是"内容不对"，
       不会误判成屏坏了。 */
    while ((i < OLED_COL_MAX) && (text[i] != '\0'))
    {
        uint8_t c = (uint8_t)text[i];
        s_msg[i] = ((c >= 0x20u) && (c <= 0x7Eu)) ? (char)c : '.';
        i++;
    }
    while (i < OLED_COL_MAX)
    {
        s_msg[i] = ' ';
        i++;
    }
    s_msg[OLED_COL_MAX] = '\0';
}

static void TextFillSpace(void)
{
    uint32_t i;

    for (i = 0; i < STORE_TEXT_MAX; i++)
    {
        s_text[i] = ' ';
    }
    s_textLen = 0;
}

/* ==================== OLED 固定三行版式 ====================
 * 本任务（chapter9）要求：
 *     第 1 行  内部 FLASH 读出的数据（十六进制）
 *     第 2 行  温度 Temp
 *     第 3 行  外部 FLASH（W25Q64）读出的数据（十六进制）
 *     第 4 行  状态提示（W25Q64 是否在线 / 最近一次操作结果）
 * 不再分页；按任务书要求也不再显示 ADCvalue / Voltage。
 */

/* 第 1 / 3 行：把 FLASH 数据拼成 "IN:0102030405" 这样的十六进制串。
 * 一行 16 个字符，扣掉 "IN:" 3 格还剩 13 格，最多放 6 个字节；
 * 超过 6 字节就只显示前 5 个再补 ".."，保证永远不顶出屏幕。 */
static void BuildFlashLine(char *line, const char *tag,
                           const uint8_t *data, uint8_t len, uint8_t valid)
{
    static const char hex[] = "0123456789ABCDEF";
    uint8_t pos = 0;
    uint8_t shown;
    uint8_t i;

    AppendTextX(line, &pos, tag);

    if ((valid == 0u) || (len == 0u))
    {
        AppendTextX(line, &pos, "--");
        PadLine(line, &pos);
        return;
    }

    shown = (len > 6u) ? 5u : len;

    for (i = 0u; i < shown; i++)
    {
        line[pos++] = hex[(data[i] >> 4) & 0x0Fu];
        line[pos++] = hex[data[i] & 0x0Fu];
    }

    if (len > 6u)
    {
        line[pos++] = '.';
        line[pos++] = '.';
    }

    PadLine(line, &pos);
}

/* 第 2 行：温度。任务书要求这一行只显示 Temp（ADCvalue / Voltage 已取消）*/
static void BuildTempLine(char *line)
{
    char    num[16];
    uint8_t pos = 0;

    AppendTextX(line, &pos, "TEMP ");
    if (s_sample.valid != 0u)
    {
        /* tempX100 是温度×100（36.86℃ = 3686）。FormatFixed 的位数参数指的是
         * "小数位数"，直接传 1 会把 3686 打成 368.6 —— 先四舍五入到温度×10，
         * 再按 1 位小数格式化，才是 "36.9"。 */
        int32_t tempX10 = (s_sample.tempX100 >= 0)
                        ? ((s_sample.tempX100 + 5) / 10)
                        : ((s_sample.tempX100 - 5) / 10);
        FormatFixed(num, tempX10, 1);
        AppendTextX(line, &pos, num);
        AppendTextX(line, &pos, " C");
    }
    else
    {
        AppendTextX(line, &pos, "--.- C");
    }
    PadLine(line, &pos);
}

/* 第 3 行（需求5 模式）：红外避障距离分级。一行 16 字符，格式：
 *     IR L:NEAR R:FAR
 * 每个单词固定 4 列：NEAR（近）/ MID （中）/ FAR （远）/ ----（这一路还没测过）
 * 分级依据是"反射强度差值"，差分测量 + 门限见 ir_drv.c。 */
static void BuildIrLine(char *line)
{
    uint8_t pos = 0;

    AppendTextX(line, &pos, "IR L:");
    if (s_irLeftValid != 0)
    {
        AppendTextX(line, &pos, Ir_LevelWord(s_irL.level));
    }
    else
    {
        AppendTextX(line, &pos, "----");
    }

    AppendTextX(line, &pos, " R:");
    if (s_irRightValid != 0)
    {
        AppendTextX(line, &pos, Ir_LevelWord(s_irR.level));
    }
    else
    {
        AppendTextX(line, &pos, "----");
    }

    PadLine(line, &pos);
}

/* 第 4 行（需求5 模式）：两路反射强度原始差值。一行 16 字符，格式：
 *     dL:0120 dR:0000
 * 差值 = 灭灯读数 - 亮灯读数（ADC3 原始值），越大说明反射越强、障碍越近。
 * 现场标定门限（IR_DIFF_MID / IR_DIFF_NEAR）时就照这一行读数改。 */
static void BuildIrDiffLine(char *line)
{
    uint8_t pos = 0;

    AppendTextX(line, &pos, "dL:");
    AppendDigits4(line, &pos, (s_irLeftValid  != 0) ? s_irL.diff : 0u);
    AppendTextX(line, &pos, " dR:");
    AppendDigits4(line, &pos, (s_irRightValid != 0) ? s_irR.diff : 0u);

    PadLine(line, &pos);
}

/* 第 3 行（需求4 模式）：距离记录。
 * 一行 16 字符，格式：  DIST 123CM #03
 *     无有效读数   ->   "DIST --"
 * 距离按 cm 显示（mm 四舍五入到 cm，屏上一格只放得下这么多）。
 * 尾部 #NN 是这条记录在片外 FLASH 里的序号，方便演示时对着串口日志核对。*/
static void BuildDistLine(char *line)
{
    char    num[16];
    uint8_t pos = 0;

    AppendTextX(line, &pos, "DIST ");

    if (s_distValid == 0u)
    {
        AppendTextX(line, &pos, "--");
        PadLine(line, &pos);
        return;
    }

    WriteU32(num, (uint32_t)(((uint32_t)s_distLastMm + 5u) / 10u));   /* mm -> cm */
    AppendTextX(line, &pos, num);
    AppendTextX(line, &pos, "CM");

    if (s_distShownNo > 0u)
    {
        AppendTextX(line, &pos, " #");
        WriteU32(num, (uint32_t)s_distShownNo);
        AppendTextX(line, &pos, num);
    }

    PadLine(line, &pos);
}

static void UpdateDisplay(void)
{
    char line[OLED_COL_MAX + 1];

    /* 第 1 行：内部 FLASH 数据 */
    BuildFlashLine(line, "IN:", s_inData, s_inLen, s_inValid);
    OLED_ShowString(0, 0, line);

    /* 第 2 行：温度 */
    BuildTempLine(line);
    OLED_ShowString(0, 1, line);

    /* 第 3 行：外部 FLASH 数据(需求3) / 距离记录(需求4) / 红外避障(需求5)，谁操作就显示谁 */
    if (s_line3Mode == 2u)
    {
        BuildIrLine(line);
    }
    else if (s_line3Mode != 0u)
    {
        BuildDistLine(line);
    }
    else
    {
        BuildFlashLine(line, "EX:", s_exData, s_exLen, s_exValid);
    }
    OLED_ShowString(0, 2, line);

    /* 第 4 行：红外模式下摆两路反射强度原始差值，其余情况是状态 / 提示 */
    if (s_line3Mode == 2u)
    {
        BuildIrDiffLine(line);
        OLED_ShowString(0, 3, line);
    }
    else
    {
        OLED_ShowString(0, 3, s_msg);
    }

    OLED_Refresh();
}

/* ========================= 温度采集与上报 ========================= */

/* 串口上报格式（本任务 chapter9）：
 *     Current Temperature is XXXX
 * ADC 原始值 / 电压按任务书要求取消 —— 屏上同样只留 Temp，
 * 串口与屏显示的内容各自独立（屏上另有 FLASH 数据两行）。
 */
static void ReportSample(void)
{
    char num[16];

    Usart_SendString("Current Temperature is ");
    if (s_sample.valid != 0u)
    {
        FormatFixed(num, s_sample.tempX100, 2);
        Usart_SendString(num);
    }
    else
    {
        /* -40~125℃ 之外认为读数不可信（例如 TSVREFE 没打开、通道读回 0），
           不把离谱数字当真值报出去 */
        Usart_SendString("--");
    }
    Usart_SendString("\r\n");
}

/* 采一次 -> 串口上报 -> 刷新当前页（不强制跳页，用户在看哪页就留在哪页）*/
static void DoSample(void)
{
    Adc_SampleTemp(&s_sample);
    s_sampleCount++;
    ReportSample();
    UpdateDisplay();
}

/* ========================= 设备控制 ========================= */

static void ReportState(void)
{
    Usart_SendString("STATUS  LEFT_TURN=");
    Usart_SendString((s_leftTurnOn  != 0) ? "ON" : "OFF");
    Usart_SendString("  RIGHT_TURN=");
    Usart_SendString((s_rightTurnOn != 0) ? "ON" : "OFF");
    Usart_SendString("  BEEP=");
    Usart_SendString((s_beepOn      != 0) ? "ON" : "OFF");
    Usart_SendString("  LED=");
    Usart_SendString((s_ledOn       != 0) ? "ON" : "OFF");
    Usart_SendString("  BREATH=");
    Usart_SendString((Breath_IsActive() != 0) ? "ON" : "OFF");
    Usart_SendString("\r\n");
}

static void ApplyHardware(void)
{
    uint32_t now = Get_SysRunTime();

    /* 呼吸模式下 PG14 与左灯珠由 TIM2 中断独占，这里绝不能碰，否则会把 PWM 盖成常亮 */
    if (Breath_IsActive() == 0u)
    {
        if (s_leftTurnOn != 0)
        {
            s_blinkPhase = 1;               /* 开启后立刻点亮，不等第一个闪烁周期 */
            s_blinkTick  = now;
            LED_On(LED1);
            RGB_Set(RGB_R);                 /* 左转向灯 = 板载左灯珠红（PG1，150R）*/
        }
        else
        {
            LED_Off(LED1);
            /* 左转向灯没开：左灯珠交回 s_ledOn 的灯条状态（LED=ON 时全亮）*/
            RGB_Set((s_ledOn != 0) ? RGB_ALL : RGB_NONE);
        }
    }

    if (s_rightTurnOn != 0)
    {
        s_blinkPhase = 1;
        s_blinkTick  = now;
        LED_On(LED2);
        RGB2_Set(RGB_R);                /* 右灯珠（PE2/3/4）先点亮红色，随后由闪烁服务变色 */
    }
    else
    {
        LED_Off(LED2);
        RGB2_Set(RGB_NONE);
    }

    if (s_beepOn != 0)
    {
        Beep_On();
    }
    else
    {
        Beep_Off();
    }
}

/* 转向灯闪烁。注意：左转向灯正在呼吸时由呼吸灯模块独占 PG14，这里不碰它 */
static void TurnSignalService(void)
{
    uint32_t now = Get_SysRunTime();
    uint8_t  phase;
    uint8_t  breath = Breath_IsActive();

    /* 距离联动提示（需求4）期间独占 LED1/LED2，转向灯闪烁先让路，
       否则两边同时改同一个 IO，闪出来的次数就乱了 */
    if (s_alertKind != ALERT_NONE)
    {
        return;
    }

    if ((s_leftTurnOn == 0) && (s_rightTurnOn == 0))
    {
        s_blinkTick = now;
        return;
    }

    if ((uint32_t)(now - s_blinkTick) < TURN_BLINK_PERIOD)
    {
        return;
    }

    s_blinkTick  = now;
    s_blinkPhase = (uint8_t)(!s_blinkPhase);
    phase        = s_blinkPhase;

    if (breath == 0u)
    {
        if (s_leftTurnOn != 0)
        {
            /* 左转向灯 = 板载左灯珠红（PG1，150R）+ 指示灯 LED1，
               与右侧（LED2 + 右灯珠 RGB2）对称 */
            if (phase != 0) { LED_On(LED1); RGB_Set(RGB_R); }
            else            { LED_Off(LED1); RGB_Set(RGB_NONE); }
        }
        else
        {
            LED_Off(LED1);
            /* ⚠ 这里绝不能写 RGB_Set(RGB_NONE)：左灯珠的"常亮"状态由 s_ledOn 管
               （LED=ON 时 RGB_Set(RGB_ALL)），在左转向灯没开时灭它会顺手把
               灯条状态也灭掉。交回 ApplyHardware() 处理即可。 */
        }
    }

    if (s_rightTurnOn != 0)
    {
        if (phase != 0)
        {
            LED_On(LED2);
            /* 右灯珠彩虹闪烁：每亮一次换一种颜色，红→黄→绿→青→蓝→紫轮转 */
            RGB2_Set(s_rainbow[s_rainbowIdx]);
            s_rainbowIdx = (uint8_t)((s_rainbowIdx + 1u) % RAINBOW_STEP_MAX);
        }
        else
        {
            LED_Off(LED2);
            RGB2_Set(RGB_NONE);
        }
    }
    else
    {
        LED_Off(LED2);
        RGB2_Set(RGB_NONE);
    }
}

/* ========================= 呼吸灯 ========================= */

static void ToggleBreath(void)
{
    if (Breath_IsActive() != 0)
    {
        Breath_Stop();
        ApplyHardware();                /* 灯条交回状态控制 */
        SetMessage("BREATH OFF");
        Usart_SendString("BREATH: off\r\n");
    }
    else
    {
        Breath_Start();
        SetMessage("BREATH ON");
        /* 需求2：左转向灯（红色）呼吸 —— 只走左灯珠的红色通道 PG1 */
        Usart_SendString("BREATH: on (LED1 PG14 + left lamp RED)\r\n");
    }

    ReportState();
    UpdateDisplay();
}

/* ========================= 掉电保存 ========================= */

static void BuildRecord(StoreRecord_t *rec)
{
    uint32_t flags = 0u;
    uint32_t i;

    if (s_leftTurnOn  != 0) { flags |= STORE_BIT_LEFT;  }
    if (s_rightTurnOn != 0) { flags |= STORE_BIT_RIGHT; }
    if (s_beepOn      != 0) { flags |= STORE_BIT_BEEP;  }
    if (s_ledOn       != 0) { flags |= STORE_BIT_LED;   }

    rec->magic         = STORE_MAGIC;
    rec->flags         = flags;
    rec->textLen       = s_textLen;
    rec->calOffsetX100 = (int16_t)Adc_GetCalOffsetX100();   /* 温度标定值一起存 */
    rec->checksum      = 0u;

    for (i = 0; i < STORE_TEXT_MAX; i++)
    {
        rec->text[i] = s_text[i];
    }
}

static void ApplyRecord(const StoreRecord_t *rec)
{
    uint32_t i;

    s_leftTurnOn  = (uint8_t)(((rec->flags & STORE_BIT_LEFT)  != 0u) ? 1 : 0);
    s_rightTurnOn = (uint8_t)(((rec->flags & STORE_BIT_RIGHT) != 0u) ? 1 : 0);
    s_beepOn      = (uint8_t)(((rec->flags & STORE_BIT_BEEP)  != 0u) ? 1 : 0);
    s_ledOn       = (uint8_t)(((rec->flags & STORE_BIT_LED)   != 0u) ? 1 : 0);

    for (i = 0; i < STORE_TEXT_MAX; i++)
    {
        s_text[i] = rec->text[i];
    }
    s_textLen = (rec->textLen <= STORE_TEXT_MAX) ? rec->textLen : STORE_TEXT_MAX;

    Adc_SetCalOffsetX100(rec->calOffsetX100);               /* 恢复上次的标定值 */

    ApplyHardware();
}

/* 内容没变就不重复擦写，省 Flash 寿命。返回 1 = Flash 里已经是当前内容 */
static uint8_t SaveCurrent(void)
{
    StoreRecord_t rec;

    BuildRecord(&rec);

    if ((s_saved.magic == STORE_MAGIC) && (Store_IsSame(&rec, &s_saved) != 0))
    {
        return 1;                   /* 已经存过了，不用再擦写一次 */
    }

    if (Store_Save(&rec) != 0)
    {
        s_saved = rec;
        Usart_SendString("FLASH: saved\r\n");
        return 1;
    }

    Usart_SendString("FLASH: write failed\r\n");
    return 0;
}

/* ========================= 命令处理 ========================= */

static void ExecuteControl(uint8_t code, uint8_t on)
{
    on = (on != 0u) ? 1u : 0u;

    switch (code)
    {
        case CTRL_LEFT_TURN:
            if (Breath_IsActive() != 0)
            {
                Breath_Stop();      /* 手动控制左转向灯时先退出呼吸模式 */
            }
            s_leftTurnOn = on;
            if (on != 0)
            {
                s_blinkPhase = 1;
                s_blinkTick  = Get_SysRunTime();
                LED_On(LED1);
                RGB_Set(RGB_R);     /* 左转向灯 = 板载左灯珠红（PG1，150R），与右侧对称 */
            }
            else
            {
                LED_Off(LED1);
                /* 关掉左转向灯：左灯珠交回 s_ledOn 的灯条状态 */
                RGB_Set((s_ledOn != 0) ? RGB_ALL : RGB_NONE);
            }
            break;

        case CTRL_RIGHT_TURN:
            s_rightTurnOn = on;
            if (on != 0) { s_blinkPhase = 1; s_blinkTick = Get_SysRunTime(); LED_On(LED2); }
            else         { LED_Off(LED2); }
            break;

        case CTRL_BEEP:
            s_beepOn = on;
            if (on != 0) { Beep_On(); } else { Beep_Off(); }
            break;

        case CTRL_LED:
            s_ledOn = on;
            /* 左转向灯正在闪的时候，左灯珠归闪烁服务管，这里不抢 */
            if (s_leftTurnOn == 0)
            {
                RGB_Set((on != 0) ? RGB_ALL : RGB_NONE);
            }
            break;

        default:
            SetMessage("BAD CODE");
            Usart_SendString("ERROR: unknown control code\r\n");
            UpdateDisplay();
            return;
    }

    if (SaveCurrent() != 0)     /* 状态变了就写进 Flash，下次开机自动恢复 */
    {
        SetMessage("CTRL OK");
    }
    else
    {
        SetMessage("FLASH ERR");
    }
    ReportState();
    UpdateDisplay();
}

static void HandleText(const uint8_t *data, uint8_t len)
{
    char    log[STORE_TEXT_MAX + 1];
    uint8_t n = len;
    uint8_t i;

    if (n > STORE_TEXT_MAX)
    {
        n = (uint8_t)STORE_TEXT_MAX;
    }

    for (i = 0; i < n; i++)
    {
        char c = (char)data[i];
        /* 不可显示的字符（回车、换行等）用点代替，避免屏上出现乱码 */
        s_text[i] = ((c >= 0x20) && (c <= 0x7E)) ? c : '.';
        log[i]    = s_text[i];
    }
    log[n] = '\0';

    for (i = n; i < STORE_TEXT_MAX; i++)
    {
        s_text[i] = ' ';
    }
    s_textLen = n;

    Usart_SendString("TEXT : ");
    Usart_SendString(log);
    Usart_SendString("\r\n");

    if (SaveCurrent() != 0)     /* 串口下发的文本立刻存进 Flash */
    {
        SetMessage(log);        /* 新版式没有文本页了，收到的文本直接回显在第 4 行 */
    }
    else
    {
        SetMessage("FLASH ERR");
    }

    UpdateDisplay();
}

static void HandleStore(uint8_t op)
{
    StoreRecord_t rec;

    switch (op)
    {
        case STORE_OP_SAVE:
            BuildRecord(&rec);
            if (Store_Save(&rec) != 0)
            {
                s_saved = rec;
                SetMessage("SAVED");
                Usart_SendString("FLASH: saved\r\n");
            }
            else
            {
                SetMessage("FLASH ERR");
                Usart_SendString("FLASH: write failed\r\n");
            }
            break;

        case STORE_OP_CLEAR:
            Store_Clear();
            s_saved.magic = 0u;     /* 清掉缓存，让下一次保存一定会真正写 */
            SetMessage("CLEARED");
            Usart_SendString("FLASH: cleared\r\n");
            break;

        case STORE_OP_RELOAD:
            if (Store_Load(&rec) != 0)
            {
                ApplyRecord(&rec);
                s_saved = rec;
                SetMessage("READ FLASH");
                Usart_SendString("FLASH: reloaded\r\n");
            }
            else
            {
                SetMessage("NO FLASH DATA");
                Usart_SendString("FLASH: no valid record\r\n");
            }
            break;

        default:
            SetMessage("BAD CODE");
            Usart_SendString("ERROR: unknown store code\r\n");
            break;
    }

    ReportState();
    UpdateDisplay();
}

/* ======================= 温度单点标定 ======================= */

/* 把"当前实测温度"标定成参考温度，得到的偏移量存进 Flash
 * refC = 0 表示用户没填数字，按默认参考温度（25℃）处理 */
static void DoCalibrate(uint32_t refC)
{
    int32_t rawTempX100;
    int32_t offsetX100;
    char    num[16];

    if ((refC == 0u) || (refC > 99u))
    {
        refC = (uint32_t)(ADC_CAL_REF_X100 / 100);      /* 默认 25℃ */
    }

    Adc_SampleTemp(&s_sample);                          /* 先取一组最新读数 */

    /* 本次读数本身就不在传感器量程内（通道读回 0 / 满量程），标定没有意义，
       拒绝标定，免得把一个坏读数固化进 Flash */
    if (s_sample.valid == 0u)
    {
        Usart_SendString("CAL  : skipped, current sample is invalid\r\n");
        SetMessage("CAL SKIP");
        UpdateDisplay();
        return;
    }

    /* 注意：这里必须用"不含标定偏移"的公式结果，否则重复按 K 会越标越歪 */
    rawTempX100 = Adc_RawToTempX100(s_sample.rawValue, s_sample.vddaMv);
    offsetX100  = ((int32_t)refC * 100) - rawTempX100;

    /* 偏移量要存进 int16 字段，这里夹一下，防止异常读数把值撑爆
       （Adc_SetCalOffsetX100 内部也会再夹一次，双保险）*/
    if (offsetX100 >  ADC_CAL_OFFSET_X100_LIMIT) { offsetX100 =  ADC_CAL_OFFSET_X100_LIMIT; }
    if (offsetX100 < -ADC_CAL_OFFSET_X100_LIMIT) { offsetX100 = -ADC_CAL_OFFSET_X100_LIMIT; }

    Adc_SetCalOffsetX100(offsetX100);

    Usart_SendString("CAL  : reference ");
    FormatFixed(num, (int32_t)refC * 100, 2);
    Usart_SendString(num);
    Usart_SendString(" C, formula gave ");
    FormatFixed(num, rawTempX100, 2);
    Usart_SendString(num);
    Usart_SendString(" C, offset ");
    FormatFixed(num, offsetX100, 2);
    Usart_SendString(num);
    Usart_SendString(" C\r\n");
    Usart_SendString("       " CN_CAL_OK "\r\n");

    if (SaveCurrent() != 0)
    {
        SetMessage("CAL OK");
    }
    else
    {
        SetMessage("FLASH ERR");
    }

    DoSample();                                         /* 立刻按标定后的结果重采并上报 */
}

/* 清除标定，回到手册公式的原始结果 */
static void DoClearCal(void)
{
    Adc_SetCalOffsetX100(0);

    Usart_SendString("CAL  : cleared\r\n");
    Usart_SendString("       " CN_CAL_CLEAR "\r\n");

    if (SaveCurrent() != 0)
    {
        SetMessage("CAL CLEAR");
    }
    else
    {
        SetMessage("FLASH ERR");
    }

    DoSample();
}

/* 查询某控制单元当前状态（供旧格式"翻转"语义换算目标状态用） */
static uint8_t CurrentOf(uint8_t code)
{
    switch (code)
    {
        case CTRL_LEFT_TURN:  return s_leftTurnOn;
        case CTRL_RIGHT_TURN: return s_rightTurnOn;
        case CTRL_BEEP:       return s_beepOn;
        case CTRL_LED:        return s_ledOn;
        default:              return 0u;
    }
}

/* ========================= FLASH 数据存储 =========================
 * 内部 FLASH 和外部 W25Q64 存的是同一种 24 字节记录，校验方式也一样，
 * 所以两边的打包/校验代码共用。
 */

/* 按记录格式打包：魔数 + 长度 + 数据(不足补 0xFF) + 累加和 */
static void DataRec_Build(uint8_t *rec, const uint8_t *data, uint8_t len)
{
    uint8_t i;
    uint8_t sum = 0u;

    rec[0]                 = DATA_REC_MAGIC0;
    rec[1]                 = DATA_REC_MAGIC1;
    rec[DATA_REC_OFF_LEN]  = len;

    for (i = 0u; i < DATA_MAX_LEN; i++)
    {
        rec[DATA_REC_OFF_DATA + i] = (i < len) ? data[i] : 0xFFu;
    }

    for (i = 0u; i < DATA_REC_OFF_CHECK; i++)
    {
        sum = (uint8_t)(sum + rec[i]);
    }
    rec[DATA_REC_OFF_CHECK] = sum;
}

/* 校验记录。通过返回数据长度（1~20），失败返回 0 */
static uint8_t DataRec_Check(const uint8_t *rec)
{
    uint8_t i;
    uint8_t sum = 0u;
    uint8_t len;

    if ((rec[0] != DATA_REC_MAGIC0) || (rec[1] != DATA_REC_MAGIC1))
    {
        return 0u;
    }

    len = rec[DATA_REC_OFF_LEN];
    if ((len == 0u) || (len > DATA_MAX_LEN))
    {
        return 0u;
    }

    for (i = 0u; i < DATA_REC_OFF_CHECK; i++)
    {
        sum = (uint8_t)(sum + rec[i]);
    }
    if (sum != rec[DATA_REC_OFF_CHECK])
    {
        return 0u;
    }

    return len;
}

/* 写内部 FLASH：解锁 -> 擦数据页 -> 按半字逐次编程 -> 上锁 */
static uint8_t Data_SaveInternal(const uint8_t *data, uint8_t len)
{
    uint8_t  rec[DATA_REC_SIZE];
    uint32_t addr = DATA_PAGE_ADDR;
    uint16_t i;
    uint16_t halfWord;

    DataRec_Build(rec, data, len);

    FLASH_Unlock();

    if (FLASH_ErasePage(DATA_PAGE_ADDR) != FLASH_COMPLETE)
    {
        FLASH_Lock();
        return 0u;
    }

    for (i = 0u; i < DATA_REC_SIZE; i += 2u)
    {
        halfWord = (uint16_t)((uint16_t)rec[i] | ((uint16_t)rec[i + 1u] << 8));
        if (FLASH_ProgramHalfWord(addr, halfWord) != FLASH_COMPLETE)
        {
            FLASH_Lock();
            return 0u;
        }
        addr += 2u;
    }

    FLASH_Lock();

    return 1u;
}

/* 读内部 FLASH 记录，校验通过则把数据拷进 out */
static uint8_t Data_LoadInternal(uint8_t *out, uint8_t *outLen)
{
    const uint8_t *rec = (const uint8_t *)DATA_PAGE_ADDR;
    uint8_t len;
    uint8_t i;

    len = DataRec_Check(rec);
    if (len == 0u)
    {
        return 0u;
    }

    for (i = 0u; i < len; i++)
    {
        out[i] = rec[DATA_REC_OFF_DATA + i];
    }
    *outLen = len;

    return 1u;
}

/* 写外部 FLASH（W25Q64）：擦扇区 + 逐页写 */
static uint8_t Data_SaveExternal(const uint8_t *data, uint8_t len)
{
    uint8_t rec[DATA_REC_SIZE];

    if (s_extOk == 0u)
    {
        return 0u;
    }

    DataRec_Build(rec, data, len);

    return W25Q64_WriteData(DATA_EXT_ADDR, rec, (uint16_t)DATA_REC_SIZE);
}

/* 读外部 FLASH 记录 */
static uint8_t Data_LoadExternal(uint8_t *out, uint8_t *outLen)
{
    uint8_t rec[DATA_REC_SIZE];
    uint8_t len;
    uint8_t i;

    if (s_extOk == 0u)
    {
        return 0u;
    }

    W25Q64_Read(DATA_EXT_ADDR, rec, (uint16_t)DATA_REC_SIZE);
    len = DataRec_Check(rec);
    if (len == 0u)
    {
        return 0u;
    }

    for (i = 0u; i < len; i++)
    {
        out[i] = rec[DATA_REC_OFF_DATA + i];
    }
    *outLen = len;

    return 1u;
}

/* 重新读内部 FLASH 并刷新全局缓存。返回 1 = 有有效数据 */
static uint8_t RefreshInternal(void)
{
    s_inLen   = 0u;
    s_inValid = Data_LoadInternal(s_inData, &s_inLen);

    return s_inValid;
}

/* 重新读外部 FLASH 并刷新全局缓存。返回 1 = 有有效数据 */
static uint8_t RefreshExternal(void)
{
    s_exLen   = 0u;
    s_exValid = Data_LoadExternal(s_exData, &s_exLen);

    return s_exValid;
}

/* ============================================================================
 *              需求4：片外 FLASH 距离记录（扇区 1，0x001000）
 * ==========================================================================*/

/* 擦掉距离扇区并写入 4 字节区头，等于把距离记录区归零。返回 1 = 成功 */
static uint8_t Dist_AreaFormat(void)
{
    uint8_t head[DIST_HEAD_SIZE];

    if (s_extOk == 0u)
    {
        return 0u;
    }

    if (W25Q64_EraseSector(DIST_SECTOR_ADDR) == 0u)
    {
        return 0u;
    }

    head[0] = DIST_MAGIC0;
    head[1] = DIST_MAGIC1;
    head[2] = DIST_HEAD_VER;
    head[3] = 0xFFu;                        /* 预留 */

    if (W25Q64_PageProgram(DIST_SECTOR_ADDR, head, (uint16_t)DIST_HEAD_SIZE) == 0u)
    {
        return 0u;
    }

    s_distAreaOk  = 1u;
    s_distCount   = 0u;
    s_distCursor  = 0u;
    s_distShownNo = 0u;
    s_distValid   = 0u;

    return 1u;
}

/* 开机扫描距离区：
 *   1) 先读区头，magic 不对说明这块扇区还没按本任务的格式初始化过
 *      （全新芯片，或上一次实验留下的数据）——这时不擅自擦除，只标记"未就绪"，
 *      等用户按 KEY1（会先格式化再写）或敲 X 清空。
 *   2) magic 对了就从 0x001004 起按 2 字节一条往后读，读到 0xFFFF 就停，
 *      数出已存条数，顺便把 KEY2 的读取游标归零。
 * 一次读 64 条（128 字节）而不是逐条读，2046 条的扫描量也就 32 次 SPI 读，
 * 开机耗时可以忽略。返回 1 = 距离区可用 */
static uint8_t Dist_AreaScan(void)
{
    uint8_t  head[DIST_HEAD_SIZE];
    uint8_t  buf[128];
    uint16_t cnt = 0u;
    uint16_t base;
    uint8_t  stop = 0u;

    if (s_extOk == 0u)
    {
        s_distAreaOk = 0u;
        s_distCount  = 0u;
        s_distCursor = 0u;
        return 0u;
    }

    W25Q64_Read(DIST_SECTOR_ADDR, head, (uint16_t)DIST_HEAD_SIZE);
    if ((head[0] != DIST_MAGIC0) || (head[1] != DIST_MAGIC1))
    {
        s_distAreaOk = 0u;
        s_distCount  = 0u;
        s_distCursor = 0u;
        return 0u;
    }

    for (base = 0u; (base < DIST_MAX_REC) && (stop == 0u); base += 64u)
    {
        uint16_t n = (uint16_t)(((DIST_MAX_REC - base) > 64u) ? 64u : (DIST_MAX_REC - base));
        uint16_t k;

        W25Q64_Read(DIST_DATA_ADDR + ((uint32_t)base * DIST_REC_SIZE),
                    buf, (uint16_t)(n * DIST_REC_SIZE));

        for (k = 0u; k < n; k++)
        {
            uint16_t v = (uint16_t)((uint16_t)buf[k * 2u] |
                                    ((uint16_t)buf[k * 2u + 1u] << 8));

            if (v == DIST_EMPTY)
            {
                stop = 1u;
                break;
            }
            cnt++;
        }
    }

    s_distAreaOk  = 1u;
    s_distCount   = cnt;
    s_distCursor  = 0u;
    s_distShownNo = 0u;

    return 1u;
}

/* 追加一条距离记录到扇区 1。返回 1 = 成功
 * 追加写只在"没写过的地址"上编程，不重复写同一位置，所以不用每次擦扇区。
 * 只有距离区还没初始化时（首次使用 / 刚被 X 清空）才格式化一次。*/
static uint8_t Dist_Append(uint16_t mm)
{
    uint8_t  buf[DIST_REC_SIZE];
    uint32_t addr;

    if (s_extOk == 0u)
    {
        return 0u;
    }

    if (s_distAreaOk == 0u)
    {
        if (Dist_AreaFormat() == 0u)
        {
            return 0u;
        }
    }

    if (s_distCount >= DIST_MAX_REC)
    {
        return 0u;                          /* 扇区写满了 */
    }

    addr   = DIST_DATA_ADDR + ((uint32_t)s_distCount * DIST_REC_SIZE);
    buf[0] = (uint8_t)(mm & 0x00FFu);       /* 小端：低字节在前 */
    buf[1] = (uint8_t)((mm >> 8) & 0x00FFu);

    if (W25Q64_PageProgram(addr, buf, (uint16_t)DIST_REC_SIZE) == 0u)
    {
        return 0u;
    }

    s_distCount++;

    return 1u;
}

/* 按下标读一条距离记录。返回 1 = 读到了有效值 */
static uint8_t Dist_Read(uint16_t idx, uint16_t *mm)
{
    uint8_t  buf[DIST_REC_SIZE];
    uint16_t v;

    if ((s_extOk == 0u) || (idx >= s_distCount))
    {
        return 0u;
    }

    W25Q64_Read(DIST_DATA_ADDR + ((uint32_t)idx * DIST_REC_SIZE),
                buf, (uint16_t)DIST_REC_SIZE);

    v = (uint16_t)((uint16_t)buf[0] | ((uint16_t)buf[1] << 8));
    if (v == DIST_EMPTY)
    {
        return 0u;
    }

    *mm = v;

    return 1u;
}

/* ============================================================================
 *              需求4：距离 -> 声光联动
 * ==========================================================================*/

static const char *AlertName(AlertKind_t kind)
{
    switch (kind)
    {
        case ALERT_BEEP:   return "BEEP 1s (<10cm)";
        case ALERT_LEFT2:  return "LEFT TURN x2 (10-50cm)";
        case ALERT_RIGHT2: return "RIGHT TURN x2 (50cm-1m)";
        case ALERT_BOTH5:  return "HAZARD x5 (>1m)";
        default:           return "NONE";
    }
}

static const char *AlertMsg(AlertKind_t kind)
{
    switch (kind)
    {
        case ALERT_BEEP:   return "DIST BEEP";
        case ALERT_LEFT2:  return "DIST L x2";
        case ALERT_RIGHT2: return "DIST R x2";
        case ALERT_BOTH5:  return "DIST D x5";
        default:           return "DIST OK";
    }
}

/* 按距离值启动对应的提示动作。四段区间就是任务书原文的四个档 */
static void Alert_Start(uint16_t mm)
{
    /* 提示要独占 LED1/LED2：左转向灯如果正在呼吸，先把呼吸停掉，
       结束后再按原样恢复（不悄悄改掉用户设过的状态）*/
    s_alertBreath = Breath_IsActive();
    if (s_alertBreath != 0u)
    {
        Breath_Stop();
    }

    s_alertDone  = 0u;
    s_alertPhase = 0u;
    s_alertTick  = Get_SysRunTime();

    if (mm < DIST_NEAR_MM)
    {
        s_alertKind  = ALERT_BEEP;
        s_alertTotal = 0u;
        s_alertEndMs = Get_SysRunTime() + ALERT_BEEP_MS;
        Beep_On();
    }
    else if (mm < DIST_LEFT_MM)
    {
        s_alertKind  = ALERT_LEFT2;
        s_alertTotal = 2u;
    }
    else if (mm < DIST_RIGHT_MM)
    {
        s_alertKind  = ALERT_RIGHT2;
        s_alertTotal = 2u;
    }
    else
    {
        s_alertKind  = ALERT_BOTH5;
        s_alertTotal = 5u;
    }
}

/* 提示结束：灯和蜂鸣器交回按键/串口设定的状态 */
static void Alert_Stop(void)
{
    LED_Off(LED1);
    LED_Off(LED2);
    RGB2_Set(RGB_NONE);
    Beep_Off();

    s_alertKind = ALERT_NONE;

    ApplyHardware();                        /* 回到 s_leftTurnOn / s_beepOn 等设定的状态 */

    if (s_alertBreath != 0u)
    {
        Breath_Start();                     /* 提示前呼吸灯是开着的，还给它 */
        s_alertBreath = 0u;
    }
}

/* 主循环每轮调用：驱动"闪 N 次"或"响一段时间" */
static void AlertService(void)
{
    uint32_t now;

    if (s_alertKind == ALERT_NONE)
    {
        return;
    }

    now = Get_SysRunTime();

    /* 蜂鸣档：只等时间到 */
    if (s_alertKind == ALERT_BEEP)
    {
        if ((int32_t)(now - s_alertEndMs) >= 0)
        {
            Alert_Stop();
        }
        return;
    }

    if ((uint32_t)(now - s_alertTick) < ALERT_BLINK_PERIOD)
    {
        return;
    }
    s_alertTick  = now;
    s_alertPhase = (uint8_t)(!s_alertPhase);

    if (s_alertPhase != 0u)
    {
        /* 亮 */
        if ((s_alertKind == ALERT_LEFT2) || (s_alertKind == ALERT_BOTH5))
        {
            LED_On(LED1);
            /* 左转向灯 = 板载左灯珠 TLED 的红色通道（PG1，经 150R，亮）。
               不驱动它的话，左侧只剩 PG14 那颗 10K 的暗指示灯，
               "左右双闪"看起来就只有右边在闪。 */
            RGB_Set(RGB_R);
        }
        if ((s_alertKind == ALERT_RIGHT2) || (s_alertKind == ALERT_BOTH5))
        {
            LED_On(LED2);
            RGB2_Set(RGB_R);
        }
    }
    else
    {
        /* 灭：一轮"亮 + 灭"算闪 1 次 */
        LED_Off(LED1);
        LED_Off(LED2);
        RGB_Set(RGB_NONE);
        RGB2_Set(RGB_NONE);

        s_alertDone++;
        if (s_alertDone >= s_alertTotal)
        {
            Alert_Stop();
        }
    }
}

/* 串口按十六进制打印一段数据 */
static void ReportDataHex(const uint8_t *data, uint8_t len)
{
    static const char hex[] = "0123456789ABCDEF";
    char    buf[3];
    uint8_t i;

    if ((data == 0) || (len == 0u))
    {
        Usart_SendString("(empty)\r\n");
        return;
    }

    buf[2] = '\0';
    for (i = 0u; i < len; i++)
    {
        buf[0] = hex[(data[i] >> 4) & 0x0Fu];
        buf[1] = hex[data[i] & 0x0Fu];
        Usart_SendString(buf);
        if ((i + 1u) < len)
        {
            Usart_SendString(" ");
        }
    }
    Usart_SendString("\r\n");
}

/* 功能字 0x07（数据存储）：s_rxData = [控制单元][数据...]
 *   控制单元 0x01 -> 写内部 FLASH
 *   控制单元 0x02 -> 写外部 FLASH（W25Q64）*/
static void HandleStoreData(const uint8_t *data, uint8_t len)
{
    uint8_t unit;
    uint8_t dlen;

    if (len < 1u)
    {
        SetMessage("NO UNIT");
        Usart_SendString("ERROR: missing control unit\r\n");
        UpdateDisplay();
        return;
    }

    unit = data[0];
    dlen = (uint8_t)(len - 1u);

    if ((dlen == 0u) || (dlen > DATA_MAX_LEN))
    {
        SetMessage("BAD LEN");
        Usart_SendString("ERROR: data length must be 1~20\r\n");
        UpdateDisplay();
        return;
    }

    if (unit == DATA_UNIT_INTERNAL)
    {
        if (Data_SaveInternal(&data[1], dlen) != 0u)
        {
            (void)RefreshInternal();
            SetMessage("IN SAVED");
            Usart_SendString("STORE: internal flash saved -> ");
            ReportDataHex(s_inData, s_inLen);
        }
        else
        {
            SetMessage("IN FAIL");
            Usart_SendString("STORE: internal flash write failed\r\n");
        }
    }
    else if (unit == DATA_UNIT_EXTERNAL)
    {
        if (s_extOk == 0u)
        {
            SetMessage("NO W25Q64");
            Usart_SendString("STORE: W25Q64 not found\r\n");
            UpdateDisplay();
            return;
        }
        if (Data_SaveExternal(&data[1], dlen) != 0u)
        {
            (void)RefreshExternal();
            SetMessage("EX SAVED");
            Usart_SendString("STORE: external flash saved -> ");
            ReportDataHex(s_exData, s_exLen);
        }
        else
        {
            SetMessage("EX FAIL");
            Usart_SendString("STORE: external flash write failed\r\n");
        }
    }
    else
    {
        SetMessage("BAD UNIT");
        Usart_SendString("ERROR: unknown unit (01=internal 02=external)\r\n");
    }

    UpdateDisplay();
}

/* ASCII 'M'：立即测一次距离并显示（不存储）。
 * 演示时先敲 M 看当前距离，确认模块工作正常，再按 KEY1 存。*/
static void DoMeasureOnly(void)
{
    uint16_t mm;
    char     num[16];

    s_line3Mode = 1u;

    mm = Hcsr04_GetDistanceMm();

    if (mm == DIST_EMPTY)
    {
        s_distValid = 0u;
        SetMessage("NO ECHO");
        Usart_SendString("MEASURE: no echo, err=");
        WriteU32(num, (uint32_t)Hcsr04_GetLastErr());
        Usart_SendString(num);
        Usart_SendString(" raw=");
        WriteU32(num, (uint32_t)Hcsr04_GetLastRawUs());
        Usart_SendString(num);
        Usart_SendString(" us\r\n");
        UpdateDisplay();
        return;
    }

    s_distLastMm  = mm;
    s_distValid   = 1u;
    s_distShownNo = 0u;                     /* 现场测量的值，不属于任何一条记录 */

    SetMessage("MEASURED");
    Usart_SendString("MEASURE: ");
    WriteU32(num, (uint32_t)mm);
    Usart_SendString(num);
    Usart_SendString(" mm (");
    WriteU32(num, (uint32_t)(((uint32_t)mm + 5u) / 10u));
    Usart_SendString(num);
    Usart_SendString(" cm)\r\n");

    UpdateDisplay();
}

/* ASCII 'X'：清空距离记录区（擦掉扇区 1 重新写区头），演示前归零用 */
static void DoDistClear(void)
{
    s_line3Mode = 1u;

    if (s_extOk == 0u)
    {
        SetMessage("NO W25Q64");
        Usart_SendString("DIST : W25Q64 not found\r\n");
        UpdateDisplay();
        return;
    }

    if (Dist_AreaFormat() != 0u)
    {
        s_distValid = 0u;
        SetMessage("DIST CLEAR");
        Usart_SendString("DIST : sector 1 erased, 0 record now\r\n");
    }
    else
    {
        SetMessage("CLEAR FAIL");
        Usart_SendString("DIST : erase failed\r\n");
    }

    UpdateDisplay();
}

/* 一帧收齐，按功能字分发 */
static void DispatchFrame(void)
{
    switch (s_rxFunc)
    {
        case FUNC_CTRL:
            if (s_rxCount >= 2u)
            {
                /* 课件协议表格式：控制单元 + 开关状态(0x00 关 / 0x01 开) */
                ExecuteControl(s_rxData[0], s_rxData[1]);
            }
            else if (s_rxCount == 1u)
            {
                /* 旧格式（单数据字节）：按"翻转一次"处理 */
                ExecuteControl(s_rxData[0], (uint8_t)(!CurrentOf(s_rxData[0])));
            }
            else
            {
                SetMessage("BAD CODE");
                Usart_SendString("ERROR: missing control unit\r\n");
                UpdateDisplay();
            }
            break;

        case FUNC_STORE_DATA:
            HandleStoreData(s_rxData, s_rxCount);
            break;

        case FUNC_TEXT:
            HandleText(s_rxData, s_rxCount);
            break;

        case FUNC_STORE:
            HandleStore(s_rxData[0]);
            break;

        default:
            SetMessage("BAD CODE");
            Usart_SendString("ERROR: unknown func code\r\n");
            UpdateDisplay();
            break;
    }
}

/* ========================= 协议解析 ========================= */

static void ParserReset(void)
{
    s_rxState = RX_HEAD0;
    s_rxLen   = 0;
    s_rxFunc  = 0;
    s_rxNeed  = 0;
    s_rxCount = 0;
}

/* 快捷命令首字母 -> 控制单元 */
static uint8_t AsciiCodeOf(uint8_t letter)
{
    switch (letter)
    {
        case 'L': return CTRL_LEFT_TURN;
        case 'R': return CTRL_RIGHT_TURN;
        case 'B': return CTRL_BEEP;
        case 'D': return CTRL_LED;
        default:  return 0xFFu;
    }
}

/* 逐字节喂入解析状态机 */
static void ParseByte(uint8_t byte)
{
    uint32_t now = Get_SysRunTime();
    uint32_t timeout;

    /* 帧内字节间隔超时 -> 半截帧作废，重新找帧头。
       ASCII 快捷命令是人手敲的，两个字符之间可能隔上好几秒（比如先敲 K 再按回车），
       所以这几个状态用更宽松的超时，免得命令还没敲完就被判成半截帧丢掉。*/
    if ((s_rxState == RX_ASCII_ARG) || (s_rxState == RX_ASCII_TEXT) || (s_rxState == RX_ASCII_CAL))
    {
        timeout = ASCII_TIMEOUT_MS;
    }
    else
    {
        timeout = PARSE_TIMEOUT_MS;
    }

    if ((s_rxState != RX_HEAD0) && ((uint32_t)(now - s_lastRxMs) > timeout))
    {
        ParserReset();
    }
    s_lastRxMs = now;

    switch (s_rxState)
    {
        case RX_HEAD0:
            if (byte == FRAME_HEAD0)
            {
                s_rxState = RX_HEAD1;
                break;
            }

            /* ---- ASCII 快捷命令（空闲态才识别，不影响协议帧）----
             * L/R/B/D + 0/1 : 直接设置左转/右转/蜂鸣器/LED，省略数字 = 翻转
             * T + 文本      : OLED 显示并保存，回车/换行结束
             * S / C / P     : 保存 Flash / 清除 Flash / 重新读回
             * A             : 立即采集一次温度并上报
             * K + 数字      : 按室温标定，回车结束
             * Z             : 清除标定
             * M / N / X / W : 测距 / 读下一条距离记录 / 清空距离区 / 呼吸灯开关
             * I             : 读内部 FLASH 数据
             * O / E         : 测距并存入外部 FLASH / 读外部 FLASH 文本（原 KEY1、KEY3 移过来）
             * Q / J / V     : 需求5 —— 测左侧 / 测右侧 / 左右都测并打印
             * #             : 打印两路红外的原始值与引脚分配（现场排查接线用）
             */
            if ((byte == 'L') || (byte == 'R') || (byte == 'B') || (byte == 'D'))
            {
                s_asciiCmd = byte;
                s_rxState  = RX_ASCII_ARG;
            }
            else if (byte == 'T')
            {
                s_rxCount = 0;
                s_rxState = RX_ASCII_TEXT;
            }
            else if (byte == 'A')
            {
                DoSample();
            }
            else if (byte == 'S')
            {
                HandleStore(STORE_OP_SAVE);
            }
            else if (byte == 'C')
            {
                HandleStore(STORE_OP_CLEAR);
            }
            else if (byte == 'P')
            {
                HandleStore(STORE_OP_RELOAD);
            }
            else if (byte == 'K')
            {
                s_calRefC = 0u;                 /* 后面跟的数字才是参考温度 */
                s_rxState = RX_ASCII_CAL;
            }
            else if (byte == 'Z')
            {
                DoClearCal();                   /* 清除标定 */
            }
            else if (byte == 'M')
            {
                DoMeasureOnly();                /* 立即测一次距离（不存储）*/
            }
            else if (byte == 'N')
            {
                Key2ReadNext();                 /* 等价于按 KEY2：读下一条距离记录 + 联动 */
            }
            else if (byte == 'X')
            {
                DoDistClear();                  /* 清空距离记录区 */
            }
            else if (byte == 'W')
            {
                ToggleBreath();                 /* 呼吸灯开关（原 KEY2 的功能挪到这里）*/
            }
            else if (byte == 'I')
            {
                /* 需求3 的 KEY1（读内部 FLASH 数据）被需求4 的"测距+存储"占用了，
                   原功能挪到这里的 'I'，保证需求3 的验收项一个不少。*/
                if (RefreshInternal() != 0)
                {
                    SetMessage("IN OK");
                    Usart_SendString("IN   : internal flash -> ");
                    ReportDataHex(s_inData, s_inLen);
                }
                else
                {
                    SetMessage("IN EMPTY");
                    Usart_SendString("IN   : internal flash empty\r\n");
                }
                UpdateDisplay();
            }
            else if (byte == 'O')
            {
                /* 需求5 把 KEY1 让给了红外避障，原来"测距并存入外部 FLASH"的
                   功能挪到这个命令上，保证需求4 的验收项一个不少。*/
                Key1MeasureAndStore();
            }
            else if (byte == 'E')
            {
                /* 同理：原 KEY3（读外部 FLASH 文本记录）挪到 'E' */
                Key3ReadExternal();
            }
            else if (byte == 'Q')
            {
                KeyIrLeft();                    /* 需求5-1：测左侧 */
            }
            else if (byte == 'J')
            {
                KeyIrRight();                   /* 需求5-1：测右侧 */
            }
            else if (byte == 'V')
            {
                KeyIrBoth();                    /* 需求5-2：左右都测并打串口 */
            }
            else if (byte == '#')
            {
                DumpIrPins();                   /* 调试：打印两个端口的输入电平 */
            }
            break;

        case RX_ASCII_CAL:
            if ((byte >= '0') && (byte <= '9'))
            {
                s_calRefC = (s_calRefC * 10u) + (uint32_t)(byte - '0');
                if (s_calRefC > 99u)
                {
                    s_calRefC = 99u;
                }
            }
            else
            {
                /* 回车/换行（或任何非数字字符）当作结束，按当前值标定 */
                DoCalibrate(s_calRefC);
                s_rxState = RX_HEAD0;
            }
            break;

        case RX_ASCII_ARG:
            if (byte == '1')
            {
                ExecuteControl(AsciiCodeOf(s_asciiCmd), 1u);
                s_rxState = RX_HEAD0;
            }
            else if (byte == '0')
            {
                ExecuteControl(AsciiCodeOf(s_asciiCmd), 0u);
                s_rxState = RX_HEAD0;
            }
            else
            {
                /* 后面不是数字：按"翻转一次"执行，再把当前字节重新喂回去 */
                ExecuteControl(AsciiCodeOf(s_asciiCmd),
                               (uint8_t)(!CurrentOf(AsciiCodeOf(s_asciiCmd))));
                s_rxState = RX_HEAD0;
                ParseByte(byte);
            }
            break;

        case RX_ASCII_TEXT:
            if ((byte == '\r') || (byte == '\n'))
            {
                if (s_rxCount > 0u)
                {
                    HandleText(s_rxData, s_rxCount);
                }
                s_rxState = RX_HEAD0;
            }
            else
            {
                s_rxData[s_rxCount] = byte;
                s_rxCount++;
                if (s_rxCount >= STORE_TEXT_MAX)
                {
                    HandleText(s_rxData, s_rxCount);    /* 满 32 字符直接显示 */
                    s_rxState = RX_HEAD0;
                }
            }
            break;

        case RX_HEAD1:
            if (byte == FRAME_HEAD1)
            {
                s_rxState = RX_LEN;
            }
            else if (byte == FRAME_HEAD0)
            {
                s_rxState = RX_HEAD1;       /* 连着来几个 0x55 也不断帧 */
            }
            else
            {
                ParserReset();
            }
            break;

        case RX_LEN:
            if (byte == 0u)
            {
                ParserReset();              /* 长度域至少得装下功能字本身 */
            }
            else
            {
                s_rxLen   = byte;
                s_rxState = RX_FUNC;
            }
            break;

        case RX_FUNC:
            s_rxFunc  = byte;
            s_rxCount = 0;

            /* 数据字节数统一由长度域给出：N = 功能字 + 数据 的字节数
             * （控制功能 N=3 → 数据 2 字节：控制单元 + 开关状态） */
            s_rxNeed = (uint8_t)((s_rxLen > 1u) ? (s_rxLen - 1u) : 0u);

            if (s_rxNeed == 0u)
            {
                DispatchFrame();
                ParserReset();
            }
            else if (s_rxNeed > FRAME_DATA_MAX)
            {
                SetMessage("BAD CODE");
                UpdateDisplay();
                ParserReset();
            }
            else
            {
                s_rxState = RX_DATA;
            }
            break;

        case RX_DATA:
            s_rxData[s_rxCount] = byte;
            s_rxCount++;
            s_rxNeed--;
            if (s_rxNeed == 0u)
            {
                DispatchFrame();
                ParserReset();
            }
            break;

        default:
            ParserReset();
            break;
    }
}

/* ========================= 按键处理 ========================= */

/* KEY1（需求4-1）：超声波测一次距离 -> 存进片外 FLASH 距离记录区 */
static void Key1MeasureAndStore(void)
{
    uint16_t mm;
    char     num[16];

    s_line3Mode = 1u;                       /* OLED 第 3 行切到距离显示 */

    if (s_extOk == 0u)
    {
        s_distValid = 0u;
        SetMessage("NO W25Q64");
        Usart_SendString("KEY1 : W25Q64 not found, cannot store\r\n");
        UpdateDisplay();
        return;
    }

    /* 连测 3 次取中值：单次超声测量容易被余波/串扰带偏，中值能直接挤掉毛刺 */
    mm = Hcsr04_GetDistanceMid3();

    if (mm == DIST_EMPTY)
    {
        s_distValid = 0u;
        SetMessage("NO ECHO");
        Usart_SendString("KEY1 : ultrasonic no echo, err=");
        WriteU32(num, (uint32_t)Hcsr04_GetLastErr());
        Usart_SendString(num);
        Usart_SendString(" raw=");
        WriteU32(num, (uint32_t)Hcsr04_GetLastRawUs());
        Usart_SendString(num);
        Usart_SendString(" us  (1=no rising 2=stuck high 3=out of range 4=too close)\r\n");
        UpdateDisplay();
        return;
    }

    s_distLastMm = mm;
    s_distValid  = 1u;

    if (Dist_Append(mm) == 0u)
    {
        SetMessage("DIST FAIL");
        Usart_SendString("KEY1 : external flash write failed (sector full?)\r\n");
        UpdateDisplay();
        return;
    }

    s_distShownNo = s_distCount;            /* 屏上标出这是第几条记录 */

    SetMessage("DIST SAVED");
    Usart_SendString("KEY1 : distance ");
    WriteU32(num, (uint32_t)mm);
    Usart_SendString(num);
    Usart_SendString(" mm, saved as record #");
    WriteU32(num, (uint32_t)s_distCount);
    Usart_SendString(num);
    Usart_SendString(" in ext flash sector 1\r\n");

    UpdateDisplay();
}

/* KEY2（需求4-2）：从片外 FLASH 顺序读一条距离记录 -> 显示 + 声光联动 */
static void Key2ReadNext(void)
{
    uint16_t mm;
    char     num[16];

    s_line3Mode = 1u;

    if (s_extOk == 0u)
    {
        s_distValid = 0u;
        SetMessage("NO W25Q64");
        Usart_SendString("KEY2 : W25Q64 not found\r\n");
        UpdateDisplay();
        return;
    }

    if (s_distCount == 0u)
    {
        s_distValid = 0u;
        SetMessage("DIST EMPTY");
        Usart_SendString("KEY2 : no distance record yet, press KEY1 first\r\n");
        UpdateDisplay();
        return;
    }

    /* 读完一遍自动回到第 1 条：演示时可以反复按，不用先敲 X 归零 */
    if (s_distCursor >= s_distCount)
    {
        s_distCursor = 0u;
        Usart_SendString("KEY2 : end reached, restart from record #1\r\n");
    }

    if (Dist_Read(s_distCursor, &mm) == 0u)
    {
        s_distValid = 0u;
        SetMessage("READ FAIL");
        Usart_SendString("KEY2 : read record failed\r\n");
        UpdateDisplay();
        return;
    }

    s_distCursor++;                         /* 下一次读下一条 */
    s_distLastMm  = mm;
    s_distValid   = 1u;
    s_distShownNo = s_distCursor;           /* 屏上标出这是第几条记录 */

    Alert_Start(mm);                        /* 按距离区间启动声光提示 */

    Usart_SendString("KEY2 : record #");
    WriteU32(num, (uint32_t)s_distCursor);
    Usart_SendString(num);
    Usart_SendString(" = ");
    WriteU32(num, (uint32_t)mm);
    Usart_SendString(num);
    Usart_SendString(" mm (");
    WriteU32(num, (uint32_t)(((uint32_t)mm + 5u) / 10u));
    Usart_SendString(num);
    Usart_SendString(" cm) -> ");
    Usart_SendString(AlertName(s_alertKind));
    Usart_SendString("\r\n");

    SetMessage(AlertMsg(s_alertKind));
    UpdateDisplay();
}

/* KEY3（需求3 保留）：读片外 FLASH 的文本记录 -> OLED 第 3 行 */
static void Key3ReadExternal(void)
{
    s_line3Mode = 0u;                       /* 第 3 行切回外部文本记录 */

    if (s_extOk == 0u)
    {
        SetMessage("NO W25Q64");
        Usart_SendString("KEY3 : W25Q64 not found\r\n");
    }
    else if (RefreshExternal() != 0)
    {
        SetMessage("EX OK");
        Usart_SendString("KEY3 : external flash -> ");
        ReportDataHex(s_exData, s_exLen);
    }
    else
    {
        SetMessage("EX EMPTY");
        Usart_SendString("KEY3 : external flash empty\r\n");
    }
    UpdateDisplay();
}

/* ========================= 需求5：红外避障采集 =========================
 *
 * 板上是两组【分立对管】（发射管 + 接收管），不是三线一体模块，所以每测一次
 * 都要"先给发射管通电，再读接收管"，而且两个发射管不能同时亮（会互相照到）：
 *      左发射 P1 = PE5  开漏输出，低 = 亮      左接收 P2 = PF9  = ADC3_IN7
 *      右发射 P3 = PE6  开漏输出，低 = 亮      右接收 P4 = PF10 = ADC3_IN8
 * 接收管集电极被 10K 上拉到 3V3，见光导通 —— 有障碍 = 低电平。
 * 测量用"灭灯本底 - 亮灯读数"的差值当反射强度，既分远/中/近，又扣掉环境光。
 * 具体采集与分档在 Drv_Common/ir_drv.c，这里只负责按键 / 显示 / 串口上报。
 */

/* 往一行里追加一个 4 位定宽十进制数（不足补 0），屏上两列才对得齐 */
static void AppendDigits4(char *line, uint8_t *pos, uint16_t v)
{
    if (v > 9999u)
    {
        v = 9999u;
    }

    line[(*pos)++] = (char)('0' + ((v / 1000u) % 10u));
    line[(*pos)++] = (char)('0' + ((v / 100u) % 10u));
    line[(*pos)++] = (char)('0' + ((v / 10u) % 10u));
    line[(*pos)++] = (char)('0' + (v % 10u));
}

/* 把一路的完整读数报到串口。原始值一起打出来 —— 现场标定门限、核对接线都靠它：
 *     IR   : left  diff=0120  dark=4080  lit=3960  level=NEAR
 * diff = 灭灯读数 - 亮灯读数（反射强度），dark / lit 是 ADC3 原始值。 */
static void ReportIr(const char *tag, const IrResult_t *r)
{
    char    buf[80];
    uint8_t pos = 0;

    AppendTextX(buf, &pos, "IR   : ");
    AppendTextX(buf, &pos, tag);
    AppendTextX(buf, &pos, "  diff=");
    AppendDigits4(buf, &pos, r->diff);
    AppendTextX(buf, &pos, "  dark=");
    AppendDigits4(buf, &pos, r->dark);
    AppendTextX(buf, &pos, "  lit=");
    AppendDigits4(buf, &pos, r->lit);
    AppendTextX(buf, &pos, "  level=");
    AppendTextX(buf, &pos, Ir_LevelWord(r->level));
    AppendTextX(buf, &pos, "\r\n");
    buf[pos] = '\0';

    Usart_SendString(buf);
}

/* 需求5-1：KEY1 单击 —— 完成【左侧】红外的距离测量并显示 */
static void KeyIrLeft(void)
{
    Ir_Measure(1u, &s_irL);             /* 完整测一次：灭灯本底 -> 亮灯反射 */
    s_irLeft       = Ir_IsBlocked(1u);
    s_irLeftValid  = 1u;
    s_line3Mode    = 2u;                /* 第 3、4 行切到红外版式 */
    SetMessage("IR LEFT DONE");
    ReportIr("left ", &s_irL);
    UpdateDisplay();
}

/* 需求5-1：KEY2 单击 —— 完成【右侧】红外的距离测量并显示 */
static void KeyIrRight(void)
{
    Ir_Measure(0u, &s_irR);
    s_irRight      = Ir_IsBlocked(0u);
    s_irRightValid = 1u;
    s_line3Mode    = 2u;
    SetMessage("IR RIGHT DONE");
    ReportIr("right", &s_irR);
    UpdateDisplay();
}

/* 需求5-2：KEY3 单击 —— 左右两路都测一遍，结果通过串口打印到 PC */
static void KeyIrBoth(void)
{
    Ir_MeasureBoth(&s_irL, &s_irR);     /* 串行测，两路发射管不同时亮 */
    s_irLeft       = Ir_IsBlocked(1u);
    s_irRight      = Ir_IsBlocked(0u);
    s_irLeftValid  = 1u;
    s_irRightValid = 1u;
    s_line3Mode    = 2u;
    SetMessage("IR BOTH DONE");

    Usart_SendString("IR   : ----- both sensors measured -----\r\n");
    ReportIr("left ", &s_irL);
    ReportIr("right", &s_irR);
    Usart_SendString("IR   : RESULT  L=");
    Usart_SendString(Ir_LevelWord(s_irL.level));
    Usart_SendString("  R=");
    Usart_SendString(Ir_LevelWord(s_irR.level));
    Usart_SendString("   (FAR=CLEAR  MID/NEAR=BLOCKED)\r\n");

    /* 再单独给一行"检测到位"的布尔结论，方便上位机直接抓 0/1 */
    Usart_SendString("IR   : DETECT  L=");
    Usart_SendString((s_irLeft != 0u) ? "1" : "0");
    Usart_SendString("  R=");
    Usart_SendString((s_irRight != 0u) ? "1" : "0");
    Usart_SendString("   (1=blocked  0=clear)\r\n");

    UpdateDisplay();
}

/* 调试辅助（串口命令 '#'）：把两路接收管的 ADC3 原始值整个打出来，连打两次测量。
 * 用途：
 *   ① 现场标定门限 —— 拿尺子在不同距离各敲一次，看 diff 落在哪一档；
 *   ② 核对接线 —— 遮住哪一路，只有哪一路的 diff 明显变大。 */
static void DumpIrPins(void)
{
    IrResult_t l;
    IrResult_t r;

    SetMessage("IR ADC SCAN");
    UpdateDisplay();

    Ir_MeasureBoth(&l, &r);

    Usart_SendString("IR   : scan  (dark = LED off / lit = LED on / diff = dark - lit)\r\n");
    ReportIr("left ", &l);
    ReportIr("right", &r);
    Usart_SendString("IR   : pins  LED_L=PE5 LED_R=PE6  RX_L=PF9(ADC3_IN7) RX_R=PF10(ADC3_IN8)\r\n");
}


static void HandleKey(KeyEvent ev)
{
    switch (ev)
    {
        case KEY_EVT_KEY1_CLICK:        /* 需求5-1：测左侧红外避障 */
            KeyIrLeft();
            break;

        case KEY_EVT_KEY2_CLICK:        /* 需求5-1：测右侧红外避障 */
            KeyIrRight();
            break;

        case KEY_EVT_KEY3_CLICK:        /* 需求5-2：左右都测并通过串口打印 */
            KeyIrBoth();
            break;

        default:
            break;
    }
}

/* ========================= 主函数 ========================= */

int main(void)
{
    uint8_t       rxByte;
    uint8_t       oledAck;
    uint32_t      now;
    StoreRecord_t rec;
    char          num[16];

    LED_Init();
    RGB_Init();
    RGB2_Init();
    Beep_Init();
    SysTick_Init();
    OLED_Init();
    Usart_Init(USART_BAUD_DEFAULT);
    Adc_Init();
    Key_Init();
    Breath_Init();
    Hcsr04_Init();                  /* 超声波 HC-SR04：TRIG=PF11 ECHO=PF12，计时用 TIM4 */
    Ir_Init();                      /* 需求5：红外避障（左发PE5 右发PE6 开漏；
                                       左收PF9 右收PF10 -> ADC3_IN7/IN8）*/
    s_extOk = W25Q64_Init();        /* 片外 SPI Flash：读 JEDEC ID 判断芯片在不在 */

    /* 扫描片外 FLASH 的距离记录区（扇区 1），得出已存条数并把读取游标归零 */
    (void)Dist_AreaScan();

    TextFillSpace();
    SetMessage("BOOTING");
    UpdateDisplay();

    Usart_SendString("=== IrAvoid Full (\xBA\xEC\xCD\xE2\xB1\xDC\xD5\xCF + \xB3\xAC\xC9\xF9\xB2\xA8\xB2\xE2\xBE\xE0 + FLASH \xB4\xE6\xB4\xA2)   115200-8-N-1 ===\x0D\x0A");
    Usart_SendString("\xD6\xD0\xCE\xC4: \xB1\xBE\xB9\xA4\xB3\xCC = \xB3\xAC\xC9\xF9\xB2\xA8\xB2\xE2\xBE\xE0 + \xCD\xE2\xB2\xBF" "W25Q64 \xB4\xE6\xB4\xA2 + \xBE\xE0\xC0\xEB\xC1\xAA\xB6\xAF(\xC8\xCE\xCE\xF1\xCA\xB5\xD1\xB5" "10/\xD0\xE8\xC7\xF3" "4)\r\n");
    Usart_SendString("\xCE\xC2\xB6\xC8: ADC1 \xCD\xA8\xB5\xC0" "16 \xC6\xAC\xC4\xDA\xCE\xC2\xB6\xC8\xB4\xAB\xB8\xD0\xC6\xF7\xA3\xAC\xC3\xBF 2 \xC3\xEB\xB2\xC9\xBC\xAF\xD2\xBB\xB4\xCE\xA3\xBB\xB4\xAE\xBF\xDA\xD6\xBB\xB1\xA8\xCE\xC2\xB6\xC8\r\n");
    Usart_SendString("\xB2\xE2\xBE\xE0: HC-SR04  TRIG=PF11  ECHO=PF12  \xBC\xC6\xCA\xB1 TIM4(1MHz)\r\n");
    Usart_SendString("OLED: 0.86 \xB4\xE7 128x32\xA3\xAC\xC8\xED\xBC\xFE I2C1  PB6=SCL  PB7=SDA\r\n");
    Usart_SendString("      \xB5\xDA" "1\xD0\xD0=\xC4\xDA\xB2\xBF" "FLASH" "\xCA\xFD\xBE\xDD  \xB5\xDA" "2\xD0\xD0=\xCE\xC2\xB6\xC8" "Temp  \xB5\xDA" "3\xD0\xD0=\xBE\xE0\xC0\xEB/\xCD\xE2\xB2\xBF" "FLASH" "  \xB5\xDA" "4\xD0\xD0=\xD7\xB4\xCC\xAC/\xBA\xEC\xCD\xE2\xC7\xBF\xB6\xC8\r\n");
    Usart_SendString("IR  : \xB0\xE5\xD4\xD8\xC1\xBD\xC2\xB7\xBA\xEC\xCD\xE2\xB1\xDC\xD5\xCF\xB6\xD4\xB9\xDC(\xB7\xD6\xC1\xA2\xB6\xD4\xB9\xDC): \xD7\xF3\xB7\xA2PE5 \xD3\xD2\xB7\xA2PE6 \xBF\xAA\xC2\xA9\xC7\xFD\xB6\xAF(\xB5\xCD=\xC1\xC1); \xD7\xF3\xCA\xD5PF9 \xD3\xD2\xCA\xD5PF10 \xBE\xAD" "10K\xC9\xCF\xC0\xAD\xB5\xBD" "3V3, \xD3\xD0\xD5\xCF\xB0\xAD=\xB5\xCD\xB5\xE7\xC6\xBD, \xD7\xDF" "ADC3\xB2\xEE\xB7\xD6\xB2\xE2\xBE\xE0\x0D\x0A");
    Usart_SendString("KEY : KEY1=\xB2\xE2\xD7\xF3  KEY2=\xB2\xE2\xD3\xD2  KEY3=\xD7\xF3\xD3\xD2\xB6\xBC\xB2\xE2\xB2\xA2\xB4\xF2\xD3\xA1\xA3\xA8\xD4\xAD KEY1 \xB2\xE2\xBE\xE0\xB4\xE6\xB4\xA2\xB8\xC4\xC7\xC3 O\xA3\xAC\xD4\xAD KEY3 \xB6\xC1\xCD\xE2\xB2\xBF FLASH \xB8\xC4\xC7\xC3 E\xA3\xA9\x0D\x0A");
    Usart_SendString("FLASH: \xC4\xDA\xB2\xBF 0x0807F000(\xCA\xFD\xBE\xDD\xD2\xB3) / 0x0807F800(\xD7\xB4\xCC\xAC\xD2\xB3)\r\n");
    Usart_SendString("       \xCD\xE2\xB2\xBF W25Q64 8MB @SPI2  PB12=CS PB13=SCK PB14=MISO PB15=MOSI\r\n");
    Usart_SendString("      \xC9\xC8\xC7\xF8" "0(0x000000)=\xC4\xDA\xB4\xE6\xCE\xC4\xB1\xBE\xBC\xC7\xC2\xBC  \xC9\xC8\xC7\xF8" "1(0x001000)=\xBE\xE0\xC0\xEB\xBC\xC7\xC2\xBC" "(2\xD7\xD6\xBD\xDA/\xCC\xF5)\r\n");
    Usart_SendString("\xB4\xE6\xB4\xA2: 55 FF <len> 07 <01\xC4\xDA\xB2\xBF 02\xCD\xE2\xB2\xBF> <\xCA\xFD\xBE\xDD> <\xD2\xEC\xBB\xF2>    len = 1+1+N\xA3\xACN\xD7\xEE\xB4\xF3" "20\r\n");
    Usart_SendString("      \xC0\xFD: 55 FF 07 07 01 01 02 03 04 05 <\xD2\xEC\xBB\xF2>  -> 01 02 03 04 05 \xB4\xE6\xC4\xDA\xB2\xBF\r\n");
    Usart_SendString("\xBF\xD8\xD6\xC6: 55 FF 03 06 <00\xD7\xF3\xD7\xAA 01\xD3\xD2\xD7\xAA 02\xB7\xE4\xC3\xF9\xC6\xF7 03\xB5\xC6\xCC\xF5> <00\xB9\xD8 01\xBF\xAA>\r\n");
    Usart_SendString("\xCE\xC4\xB1\xBE: 55 FF <len> 09 <\xCE\xC4\xB1\xBE>    len = 1 + \xD7\xD6\xB7\xFB\xCA\xFD\r\n");
    Usart_SendString("\xD7\xB4\xCC\xAC: 55 FF 02 08 <00\xB1\xA3\xB4\xE6 01\xC7\xE5\xB3\xFD 02\xB6\xC1\xBB\xD8>\r\n");
    Usart_SendString("\xBF\xEC\xBD\xDD: L/R/B/D <1\xBB\xF2" "0> \xBF\xAA/\xB9\xD8   T<\xCE\xC4\xB1\xBE>   S\xB1\xA3\xB4\xE6 C\xC7\xE5\xB3\xFD P\xB6\xC1\xBB\xD8   A\xC1\xA2\xBC\xB4\xB2\xC9\xD1\xF9\r\n");
    Usart_SendString("      M=\xB2\xE2\xBE\xE0  N=\xB6\xC1\xCF\xC2\xD2\xBB\xCC\xF5\xBE\xE0\xC0\xEB  X=\xC7\xE5\xBF\xD5\xBE\xE0\xC0\xEB\xC7\xF8  W=\xBA\xF4\xCE\xFC\xB5\xC6\xBF\xAA\xB9\xD8  I=\xB6\xC1\xC4\xDA\xB2\xBF" "FLASH\r\n");
    Usart_SendString("\xB1\xEA\xB6\xA8: K<\xCA\xD2\xCE\xC2> \xBB\xD8\xB3\xB5 = \xB1\xEA\xB6\xA8     Z = \xC7\xE5\xB3\xFD\xB1\xEA\xB6\xA8\r\n");
    Usart_SendString("\xB0\xB4\xBC\xFC: KEY1/2/3 \xD2\xD1\xC8\xC3\xB8\xF8\xBA\xEC\xCD\xE2(\xBC\xFB\xC9\xCF)  \xD4\xAD KEY1 \xB2\xE2\xBE\xE0+\xB4\xE6" "FLASH -> O  \xD4\xAD KEY2 \xB6\xC1\xCF\xC2\xD2\xBB\xCC\xF5 -> N  \xD4\xAD KEY3 \xB6\xC1\xCD\xE2\xB2\xBF\xCE\xC4\xB1\xBE -> E" "\r\n");
    Usart_SendString("Info : " CN_BOOT_OK "\r\n");

    /* 顺手把 OLED 的自检结果打出来：屏不亮时一眼看出是接线问题还是驱动问题 */
    oledAck = OLED_Probe();
    if (oledAck == 1u)
    {
        Usart_SendString("OLED : ack ok, slave addr 0x78, 128x32 SSD1306\r\n");
    }
    else if (oledAck == 2u)
    {
        Usart_SendString("OLED : ack ok, slave addr 0x7A (SA0 = high)\r\n");
    }
    else
    {
        Usart_SendString("OLED : NO ACK - check SCL=PB6 / SDA=PB7 / 3V3 / GND\r\n");
    }

    /* 片外 W25Q64 自检结果 */
    if (s_extOk != 0u)
    {
        Usart_SendString("W25Q64: found, JEDEC ID = EF 40 17 (8MB)\r\n");
    }
    else
    {
        Usart_SendString("W25Q64: NOT FOUND - check SPI2 (PB12/13/14/15) or chip mounted\r\n");
    }

    /* 开机把两片 FLASH 里已有的数据读出来：屏上第 1 / 第 3 行立刻就有内容 */
    if (RefreshInternal() != 0)
    {
        Usart_SendString("BOOT : internal flash data -> ");
        ReportDataHex(s_inData, s_inLen);
    }
    else
    {
        Usart_SendString("BOOT : internal flash data empty\r\n");
    }

    if (s_extOk != 0u)
    {
        if (RefreshExternal() != 0)
        {
            Usart_SendString("BOOT : external flash data -> ");
            ReportDataHex(s_exData, s_exLen);
        }
        else
        {
            Usart_SendString("BOOT : external flash data empty\r\n");
        }
    }

    /* 再看内部 Flash 里有没有上次存下的设备状态 */
    if (Store_Load(&rec) != 0)
    {
        ApplyRecord(&rec);
        s_saved = rec;
        Usart_SendString("BOOT : restored device state from internal flash\r\n");
    }
    else
    {
        Usart_SendString("BOOT : internal flash state empty, using default\r\n");
    }

    /* 片外 FLASH 距离记录区（需求4）：把开机扫描的结果报出来 */
    if (s_extOk != 0u)
    {
        if (s_distAreaOk != 0u)
        {
            Usart_SendString("DIST : ext flash sector 1 ready, ");
            WriteU32(num, (uint32_t)s_distCount);
            Usart_SendString(num);
            Usart_SendString(" record(s) stored, press KEY2 to read them one by one\r\n");
        }
        else
        {
            Usart_SendString("DIST : sector 1 not formatted yet, press KEY1 to store the first record (or 'X' to erase)\r\n");
        }
    }

    ReportState();

    /* 第 4 行状态栏优先显示 W25Q64 在不在 —— 这颗芯片有没有焊，是这台板子上
       最要紧的一条信息，先摆在明面上 */
    SetMessage((s_extOk != 0u) ? "W25Q64 OK" : "NO W25Q64");

    /* 标定状态提示：标定值跟文本、设备状态一起存在 Flash 的最后一页里。
       如果烧录固件时勾了"Erase Full Chip"（整片擦除），这一页也会被擦掉，
       于是温度回到手册公式的原始结果（这颗片子会偏高几度）。
       开机明确说一句，省得看到温度不对再猜原因。*/
    if (Adc_GetCalOffsetX100() != 0)
    {
        Usart_SendString("CAL  : " CN_CAL_USE "  offset ");
        FormatFixed(num, Adc_GetCalOffsetX100(), 2);
        Usart_SendString(num);
        Usart_SendString(" C (restored from flash)\r\n");
    }
    else
    {
        Usart_SendString("CAL  : " CN_CAL_NONE " - raw formula value\r\n");
        Usart_SendString("CAL  : " CN_CAL_HINT "\r\n");
    }

    /* 先采样一次，开机就有数据 */
    Adc_SampleTemp(&s_sample);
    s_sampleCount++;
    ReportSample();
    s_lastSampleMs = Get_SysRunTime();
    UpdateDisplay();

    while (1)
    {
        /* 1. 串口：收字节喂协议解析器 */
        while (Usart_ReadByte(&rxByte) != 0)
        {
            ParseByte(rxByte);
        }

        now = Get_SysRunTime();

        /* 2. 按键：每 10ms 扫一次 */
        if ((uint32_t)(now - s_lastKeyMs) >= KEY_SCAN_PERIOD_MS)
        {
            s_lastKeyMs = now;
            HandleKey(Key_Scan());
        }

        /* 3. 温度：每 2 秒采集一次，刷屏 + 串口上报 */
        if ((uint32_t)(now - s_lastSampleMs) >= SAMPLE_PERIOD_MS)
        {
            s_lastSampleMs = now;
            DoSample();
        }

        /* 4. 转向灯闪烁 + 呼吸灯调占空比 + 距离联动提示 */
        TurnSignalService();
        Breath_Service();
        AlertService();
    }
}
