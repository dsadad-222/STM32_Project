/**
  ******************************************************************************
  * @file    Drv_Common/adc_drv.c
  * @brief   ADC1 + 内部温度传感器（通道 16）驱动实现
  *
  *          时钟：ADC1 挂在 APB2，ADCCLK 由 PCLK2(72MHz) 分频得到，最高 14MHz，
  *                这里用 6 分频 = 12MHz。
  *          采样时间：内部温度传感器手册要求采样时间 >= 17.1us。
  *                Tconv = 采样时间 + 12.5 个周期，12MHz 下 239.5 个周期约 20us，
  *                留足余量，保证转换结果稳定。
  *          触发方式：软件触发（SWSTART），需要就读一次，不用 DMA、不用中断。
  *
  *          为了提高读数可信度，一共做了三层处理（都是"为什么这么写"的答案）：
  *            1. 丢首次：切换通道后的第一次转换，采样保持电容还没充到新通道的电位，
  *               结果不可信，直接扔掉不算。
  *            2. 去极值平均：连读 8 次，扣掉最大和最小各一次再平均，避免偶发野点
  *               把结果整体拉偏。
  *            3. Vrefint 反推 VDDA：板上 3V3 未必是 3.300V，用内部 1.20V 基准
  *               算出真实 VDDA 再换算电压和温度。
  *          （第 4 层"单点标定"在 main.c 里，用串口 K 命令触发。）
  ******************************************************************************
  */

#include "adc_drv.h"

/* 单点标定偏移量（×100℃），默认 0 表示不标定 */
static int32_t  s_calOffsetX100 = 0;

/* 最近一次 Vrefint 通道的原始值，放到采样结构体里给上位机诊断用 */
static uint16_t s_lastVrefRaw = 0u;

/* 单次转换：启动 -> 等 EOC -> 读数据寄存器（右对齐，低 12 位有效）*/
static uint16_t AdcConvertOnce(void)
{
    ADC_SoftwareStartConvCmd(ADC1, ENABLE);
    while (ADC_GetFlagStatus(ADC1, ADC_FLAG_EOC) == RESET)
    {
        /* 等转换结束，12MHz、239.5 周期下大约 20us */
    }
    return (uint16_t)ADC_GetConversionValue(ADC1);
}

void Adc_Init(void)
{
    ADC_InitTypeDef adc;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_ADC1, ENABLE);
    RCC_ADCCLKConfig(RCC_PCLK2_Div6);       /* ADCCLK = 72MHz / 6 = 12MHz（< 14MHz 上限）*/

    ADC_DeInit(ADC1);

    adc.ADC_Mode               = ADC_Mode_Independent;      /* 只用 ADC1，独立模式 */
    adc.ADC_ScanConvMode       = DISABLE;                   /* 单通道，不用扫描 */
    adc.ADC_ContinuousConvMode = DISABLE;                   /* 读一次转一次，软件触发 */
    adc.ADC_ExternalTrigConv   = ADC_ExternalTrigConv_None; /* 不用外部触发 */
    adc.ADC_DataAlign          = ADC_DataAlign_Right;       /* 右对齐，低 12 位有效 */
    adc.ADC_NbrOfChannel       = 1;
    ADC_Init(ADC1, &adc);

    /* 关键一步：打开 TSVREFE 位，把内部温度传感器(通道16)和 Vrefint(通道17)接到 ADC 上，
       不打开的话这两个通道读出来恒为 0 */
    ADC_TempSensorVrefintCmd(ENABLE);

    ADC_Cmd(ADC1, ENABLE);

    /* 上电后做一次复位校准 + 校准，校准值会一直生效 */
    ADC_ResetCalibration(ADC1);
    while (ADC_GetResetCalibrationStatus(ADC1) == SET)
    {
    }
    ADC_StartCalibration(ADC1);
    while (ADC_GetCalibrationStatus(ADC1) == SET)
    {
    }

    s_calOffsetX100 = 0;                    /* 上电默认不标定，稍后由 Flash 里的值覆盖 */
    s_lastVrefRaw   = 0u;
}

/* 读某个通道：丢首次 + 去极值平均
 * 内部通道本体噪声比外部通道大，连读 times 次，扣掉最大最小各一次再平均更稳 */
uint16_t Adc_ReadChannelAvg(uint8_t channel, uint8_t times)
{
    uint32_t sum = 0u;
    uint16_t v;
    uint16_t vMin = 0xFFFFu;
    uint16_t vMax = 0u;
    uint8_t  i;
    uint8_t  n;

    if (times == 0u)
    {
        times = 1u;
    }

    /* 通道 16/17 的采样时间由 ADC_SMPR1 控制，统一给 239.5 个周期 */
    ADC_RegularChannelConfig(ADC1, channel, 1, ADC_SampleTime_239Cycles5);

    /* 刚切换通道，第一次转换的采样保持电容还没稳定，丢掉不要 */
    (void)AdcConvertOnce();

    for (i = 0; i < times; i++)
    {
        v = AdcConvertOnce();
        if (v < vMin) { vMin = v; }
        if (v > vMax) { vMax = v; }
        sum += v;
    }

    if (times >= 4u)
    {
        sum -= (uint32_t)vMin;
        sum -= (uint32_t)vMax;
        n = (uint8_t)(times - 2u);          /* 去掉最大最小之后剩几个 */
    }
    else
    {
        n = times;
    }

    return (uint16_t)(sum / n);
}

/* 用内部 1.20V 基准反推实际 VDDA（mV）
 * 只有在"原始值明显是坏点（读回 0 / 读回满量程）"时才退回默认 3300mV；
 * 反推值只要落在一个很宽的正常区间内就采信，避免把 4.2V 这种真实但不常见
 * 的供电当成坏点，从而把温度算飞（见头文件里的说明）*/
uint16_t Adc_GetVddaMv(void)
{
    uint16_t raw = Adc_ReadChannelAvg(ADC_VREFINT_CHANNEL, ADC_AVG_TIMES);
    uint32_t mv;

    s_lastVrefRaw = raw;

    if ((raw < ADC_VREFINT_RAW_MIN) || (raw > ADC_VREFINT_RAW_MAX))
    {
        return ADC_VDDA_MV_DEFAULT;
    }

    mv = ((uint32_t)ADC_VREFINT_MV * ADC_FULL_SCALE) / raw;

    if ((mv < ADC_VDDA_MV_MIN) || (mv > ADC_VDDA_MV_MAX))
    {
        return ADC_VDDA_MV_DEFAULT;
    }

    return (uint16_t)mv;
}

/* AD 值 -> 模拟量(mV)：Vsense = AD值 / 4096 * VDDA */
uint32_t Adc_RawToVoltageMv(uint16_t raw, uint16_t vddaMv)
{
    return (((uint32_t)raw * vddaMv) / ADC_FULL_SCALE);
}

/* AD 值 -> 温度 ×100（℃），只按手册公式算，不含标定偏移
 * 温度(℃) = (V25 - Vsense) / Avg_Slope + 25
 * 全部用整数算：ΔmV * 1000 / 43 得到的就是"温度差的 100 倍"（43 表示 4.3mV/℃ ×10）*/
int32_t Adc_RawToTempX100(uint16_t raw, uint16_t vddaMv)
{
    int32_t vsenseMv  = (int32_t)Adc_RawToVoltageMv(raw, vddaMv);
    int32_t deltaX100 = (((int32_t)ADC_V25_MV - vsenseMv) * 1000) / ADC_SLOPE_X10_UV_PER_C;

    return (2500 + deltaX100);
}

/* 设置 / 读取标定偏移量（×100℃）
 * 这里统一夹到 ±120℃（传感器量程本身就是 -40~125℃，再大没有物理意义），
 * 这样无论偏移量来自串口标定还是从 Flash 读回，都不会把温度顶到离谱的值 */
void Adc_SetCalOffsetX100(int32_t offsetX100)
{
    if (offsetX100 >  ADC_CAL_OFFSET_X100_LIMIT) { offsetX100 =  ADC_CAL_OFFSET_X100_LIMIT; }
    if (offsetX100 < -ADC_CAL_OFFSET_X100_LIMIT) { offsetX100 = -ADC_CAL_OFFSET_X100_LIMIT; }

    s_calOffsetX100 = offsetX100;
}

int32_t Adc_GetCalOffsetX100(void)
{
    return s_calOffsetX100;
}

/* 一次完整采样：取 VDDA -> 读温度通道原始值 -> 换算模拟量与温度
 * 量程判断用"未标定的温度"，避免标定值把有效采样误判成无效 */
void Adc_SampleTemp(AdcTempSample_t *sample)
{
    int32_t rawTempX100;

    if (sample == 0)
    {
        return;
    }

    sample->vddaMv    = Adc_GetVddaMv();
    sample->vrefRaw   = s_lastVrefRaw;
    sample->rawValue  = Adc_ReadChannelAvg(ADC_TEMP_CHANNEL, ADC_AVG_TIMES);
    sample->voltageMv = Adc_RawToVoltageMv(sample->rawValue, sample->vddaMv);
    rawTempX100       = Adc_RawToTempX100(sample->rawValue, sample->vddaMv);

    if ((sample->rawValue == 0u) || (sample->rawValue >= (uint16_t)(ADC_FULL_SCALE - 1u)) ||
        (rawTempX100 < ADC_TEMP_X100_MIN) || (rawTempX100 > ADC_TEMP_X100_MAX))
    {
        sample->valid = 0u;
    }
    else
    {
        sample->valid = 1u;
    }

    /* 真正报出去的温度 = 手册公式算出的值 + 单点标定偏移 */
    sample->tempX100 = rawTempX100 + s_calOffsetX100;
}
