/**
  ******************************************************************************
  * @file    Drv_Common/ir_drv.c
  * @brief   板载两路红外避障对管驱动实现
  *
  *          测量流程（一路）：
  *            1. 发射管灭灯 -> 等 1ms -> ADC3 采 8 次去极值平均 = dark（环境本底）
  *            2. 发射管亮灯 -> 等 1ms -> ADC3 采 8 次去极值平均 = lit （含反射）
  *            3. diff = dark - lit
  *                 前方空旷：接收管基本截止，两次读数几乎一样 -> diff ≈ 0
  *                 前方有障碍：亮灯时反射回来把接收管打低 -> diff 明显变大
  *            4. 按 diff 分档：FAR / MID / NEAR
  *            5. 测完立刻灭灯（省电，也避免照亮隔壁那一路造成串扰）
  *
  *          ADC3 的选择理由：
  *              内部温度传感器占的是 ADC1 的通道 16/17，ADC3 完全空闲；
  *              而 PF9/PF10 硬件上正好是 ADC3_IN7 / ADC3_IN8，不需要改板子。
  *              两路共用 ADC3，用软件切换规则通道（单次转换、不用 DMA）。
  ******************************************************************************
  */

#include "ir_drv.h"
#include "systick_drv.h"

/* 最近一次测量结果：索引 0 = 右路，1 = 左路（沿用"左 = 1"的习惯，和 main.c 一致）*/
static IrResult_t s_last[2];

/* 左 = 1，右 = 0 */
#define IR_IDX(isLeft)      (((isLeft) != 0u) ? 1u : 0u)

/* ============================ 发射管开关 ============================ */

/* 开漏输出：写 0 -> 引脚拉低 -> PNP 基极被拉低 -> 发射管亮
 *           写 1 -> 引脚高阻 -> 基极无直流通路 -> 发射管灭 */
static void Ir_LedWrite(uint8_t isLeft, uint8_t on)
{
    GPIO_TypeDef *port = ((isLeft) != 0u) ? IR_LED_L_PORT : IR_LED_R_PORT;
    uint16_t      pin  = ((isLeft) != 0u) ? IR_LED_L_PIN  : IR_LED_R_PIN;

    if (on != 0u)
    {
        GPIO_ResetBits(port, pin);
    }
    else
    {
        GPIO_SetBits(port, pin);
    }
}

void Ir_Emit(uint8_t isLeft, uint8_t on)
{
    Ir_LedWrite(isLeft, on);
}

/* ============================ ADC3 采样 ============================ */

/* 单次转换：软件启动 -> 等 EOC -> 读数据寄存器（右对齐）*/
static uint16_t Adc3ConvertOnce(void)
{
    ADC_SoftwareStartConvCmd(ADC3, ENABLE);
    while (ADC_GetFlagStatus(ADC3, ADC_FLAG_EOC) == RESET)
    {
        /* 12MHz、239.5 周期下约 20us 一次 */
    }
    return (uint16_t)ADC_GetConversionValue(ADC3);
}

/* 读一个通道：丢首次 + 去极值平均
 * 丢首次是因为刚切通道，采样保持电容还没充到新通道的电位；
 * 去极值平均是为了干掉偶发野点（光敏管对纹波、闪灯都敏感）。*/
static uint16_t Adc3ReadAvg(uint8_t channel)
{
    uint32_t sum  = 0u;
    uint16_t v;
    uint16_t vMin = 0xFFFFu;
    uint16_t vMax = 0u;
    uint8_t  i;

    ADC_RegularChannelConfig(ADC3, channel, 1, ADC_SampleTime_239Cycles5);

    (void)Adc3ConvertOnce();            /* 丢掉切换通道后的第一次 */

    for (i = 0u; i < IR_ADC_AVG; i++)
    {
        v = Adc3ConvertOnce();
        if (v < vMin) { vMin = v; }
        if (v > vMax) { vMax = v; }
        sum += (uint32_t)v;
    }

    sum -= (uint32_t)vMin;
    sum -= (uint32_t)vMax;

    return (uint16_t)(sum / (uint32_t)(IR_ADC_AVG - 2u));
}

/* ============================ 初始化 ============================ */

void Ir_Init(void)
{
    GPIO_InitTypeDef gpio;
    ADC_InitTypeDef  adc;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOE | RCC_APB2Periph_GPIOF |
                           RCC_APB2Periph_ADC3, ENABLE);

    /* ---- 两个发射管驱动脚（PE5 / PE6）：开漏输出，先置"灭"（高阻）----
       必须是开漏：发射管基极回路接的是 5V，推挽输出 3.3V 高电平关不断它。 */
    gpio.GPIO_Pin   = IR_LED_L_PIN | IR_LED_R_PIN;
    gpio.GPIO_Mode  = GPIO_Mode_Out_OD;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(IR_LED_L_PORT, &gpio);            /* PE5 / PE6 同在 GPIOE */
    GPIO_SetBits(IR_LED_L_PORT, IR_LED_L_PIN | IR_LED_R_PIN);

    /* ---- 两个接收脚（PF9 / PF10）：模拟输入，交给 ADC3 ----
       配成 AIN 后数字输入缓冲关闭，读 IDR 恒为 0，要拿数字电平得改回输入模式；
       本工程一律走 ADC，所以直接配 AIN。*/
    gpio.GPIO_Pin  = IR_RX_L_PIN | IR_RX_R_PIN;
    gpio.GPIO_Mode = GPIO_Mode_AIN;
    GPIO_Init(IR_RX_L_PORT, &gpio);             /* PF9 / PF10 同在 GPIOF */

    /* ---- ADC3 ---- */
    RCC_ADCCLKConfig(RCC_PCLK2_Div6);           /* ADCCLK = 72MHz / 6 = 12MHz < 14MHz */

    ADC_DeInit(ADC3);

    adc.ADC_Mode               = ADC_Mode_Independent;
    adc.ADC_ScanConvMode       = DISABLE;       /* 单通道，软件切通道 */
    adc.ADC_ContinuousConvMode = DISABLE;
    adc.ADC_ExternalTrigConv   = ADC_ExternalTrigConv_None;
    adc.ADC_DataAlign          = ADC_DataAlign_Right;
    adc.ADC_NbrOfChannel       = 1;
    ADC_Init(ADC3, &adc);

    /* 注意：这里不能调 ADC_TempSensorVrefintCmd —— 那是 ADC1 才有的内部通道 */
    ADC_Cmd(ADC3, ENABLE);

    ADC_ResetCalibration(ADC3);
    while (ADC_GetResetCalibrationStatus(ADC3) == SET)
    {
    }
    ADC_StartCalibration(ADC3);
    while (ADC_GetCalibrationStatus(ADC3) == SET)
    {
    }

    s_last[0].valid = 0u;
    s_last[1].valid = 0u;
}

/* ============================ 测量 ============================ */

void Ir_Measure(uint8_t isLeft, IrResult_t *r)
{
    uint8_t  channel = ((isLeft) != 0u) ? IR_ADC_L_CHANNEL : IR_ADC_R_CHANNEL;
    uint16_t dark;
    uint16_t lit;
    uint32_t diff;

    if (r == 0)
    {
        return;
    }

    /* ① 灭灯：环境本底 */
    Ir_LedWrite(isLeft, 0u);
    DelayMs(IR_SETTLE_MS);
    dark = Adc3ReadAvg(channel);

    /* ② 亮灯：反射回来会让接收管导通、把电压拉低 */
    Ir_LedWrite(isLeft, 1u);
    DelayMs(IR_SETTLE_MS);
    lit = Adc3ReadAvg(channel);

    /* ③ 测完立刻灭灯 */
    Ir_LedWrite(isLeft, 0u);

    diff = (dark > lit) ? (uint32_t)(dark - lit) : 0u;

    r->dark = dark;
    r->lit  = lit;
    r->diff = (uint16_t)diff;

    if (diff >= (uint32_t)IR_DIFF_NEAR)
    {
        r->level = IR_LEVEL_NEAR;
    }
    else if (diff >= (uint32_t)IR_DIFF_MID)
    {
        r->level = IR_LEVEL_MID;
    }
    else
    {
        r->level = IR_LEVEL_FAR;
    }

    r->strength = (uint8_t)((diff >= (uint32_t)IR_DIFF_FULL)
                            ? 100u
                            : ((diff * 100u) / (uint32_t)IR_DIFF_FULL));
    r->valid    = 1u;

    s_last[IR_IDX(isLeft)] = *r;
}

void Ir_MeasureBoth(IrResult_t *left, IrResult_t *right)
{
    /* 串行测：先测左再测右，中间两路发射管不同时亮，避免互相照到 */
    Ir_Measure(1u, left);
    Ir_Measure(0u, right);
}

const IrResult_t *Ir_Last(uint8_t isLeft)
{
    return &s_last[IR_IDX(isLeft)];
}

uint8_t Ir_IsBlocked(uint8_t isLeft)
{
    const IrResult_t *r = &s_last[IR_IDX(isLeft)];

    if (r->valid == 0u)
    {
        return 0u;              /* 还没测过，不能凭空说有障碍 */
    }

    return (r->diff >= (uint16_t)IR_DIFF_MID) ? 1u : 0u;
}

const char *Ir_LevelWord(uint8_t level)
{
    if (level == IR_LEVEL_NEAR)
    {
        return "NEAR";
    }
    if (level == IR_LEVEL_MID)
    {
        return "MID ";
    }
    return "FAR ";
}
