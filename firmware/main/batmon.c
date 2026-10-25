/**
 * @file batmon.c
 * @brief Battery voltage from A0. See batmon.h.
 */
#include "batmon.h"

#include "battery.h"
#include "driver/adc.h"

static int s_cal = BAT_CAL_DEFAULT; /**< Calibration, per mille. */

void batmon_set_cal(int cal)
{
    s_cal = cal >= BAT_CAL_MIN && cal <= BAT_CAL_MAX ? cal : BAT_CAL_DEFAULT;
}

int batmon_cal(void) { return s_cal; }

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
    return battery_apply_cal(battery_mv(sum / 4), s_cal);
}
