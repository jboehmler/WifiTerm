#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "task.h"
#include "ticks.h"

static const char *TAG_ticks = "ticks";

TickType_t ticks_ms(int ms) {
    TickType_t mtick = 0;

    mtick = pdMS_TO_TICKS(ms);
    if (mtick == 0) {
        ESP_LOGE(TAG_ticks, "mtick too small ms <%d>, porttick <%d>", ms,
                 mtick);
        mtick = 1;
    }
    return (mtick);
}

/*
int ticks_ms(int ms) {
    int mint = ms / portTICK_PERIOD_MS;
    if (mint == 0) {
        ESP_LOGD(TAG_ticks,
                 "mint too small ms <%d>, porttick <%d>", ms,
                 portTICK_PERIOD_MS);
        mint = 1;
    }
    return (mint);
}
*/

void task_wait_ms(int ms) {
    int mint = ticks_ms(ms);
    vTaskDelay(mint);
}

void task_wait_s(float s) { task_wait_ms((int)(s * 1000)); }

void endless_wait(char *opt_msg) {
    while (1) {
        if (opt_msg != NULL) {
            ESP_LOGD(TAG_ticks, "endless_wait:  <%s>", opt_msg);
        }
        task_wait_s(10);
    }
}
