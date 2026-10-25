/**
 * @file batmon.c
 * @brief Battery voltage from A0. See batmon.h.
 */
#include "batmon.h"

#include "battery.h"
#include "driver/adc.h"

int batmon_init(void)
{
    adc_config_t c = {.mode = ADC_READ_TOUT_MODE, .clk_div = 8};
    return adc_init(&c) == ESP_OK ? 0 : -1;
}

int batmon_read_mv(void)
{
    unsigned sum = 0;
    for (int i = 0; i < 4; i++) {
        uint16_t v = 0;
        if (adc_read(&v) != ESP_OK) {
            return 0;
        }
        sum += v;
    }
    return battery_mv(sum / 4);
}
