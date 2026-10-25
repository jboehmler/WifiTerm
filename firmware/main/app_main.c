/**
 * @file app_main.c
 * @brief Boot order for the WiFi Terminal ESP8266 firmware.
 * @details
 *  1. Logs go to UART1 TX (D4) from the start (sdkconfig: console UART 1).
 *  2. Settings from NVS; UART0 on its USB pins at 74880 for the 3 s recovery window
 *     (RS-232 chip still off, so the device sees nothing).
 *  3. UART0 switched to the device: settings applied, pins swapped (D7 RX, D8 TX).
 *  4. Access point, TLS, then the bridge task, which switches the chip on as the saved power
 *     mode says (`auto` on the rs232-shield: only once a console is detected, NOTES I-21).
 *  The green state LED (NOTES I-22) starts first: battery blinks, then steady while booting;
 *  a failed step N blinks N times before the restart.
 */
#include "batmon.h"
#include "battery.h"
#include "bridge.h"
#include "config.h"
#include "esp_log.h"
#include "esp_system.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "logfwd.h"
#include "recovery.h"
#include "settings.h"
#include "statusled.h"
#include "tls.h"
#include "uartdev.h"
#include "wifi_ap.h"

static const char *TAG = "main";

void app_main(void)
{
    uart_cfg_t uart;
    ap_cfg_t ap;

    logfwd_init();
    esp_log_level_set("*", ESP_LOG_INFO);
    ESP_LOGI(TAG, "wifiterm %s starting", FW_VERSION);

    int mv = batmon_init() == 0 ? batmon_read_mv() : 0;
    statusled_init(battery_quarters(mv));
    if (battery_percent(mv) >= 0) {
        ESP_LOGI(TAG, "battery %d mV, about %d%%", mv, battery_percent(mv));
    }

    if (settings_init()) {
        ESP_LOGE(TAG, "settings unavailable; using defaults");
        statusled_fail(1, 10000);
    }
    uartdev_power(0); /* make sure the RS-232 chip is off until the swap */
    if (uartdev_init_console() == 0) {
        recovery_window();
    }

    if (settings_uart_load(&uart)) {
        ESP_LOGI(TAG, "no saved serial settings; using defaults");
    }
    if (uartdev_start(&uart)) {
        ESP_LOGE(TAG, "device UART setup failed");
    }

    settings_ap_load(&ap);
    int failed = wifi_ap_start(&ap) ? 2 : tls_init() ? 3 : 0;
    if (failed) {
        ESP_LOGE(TAG, "startup failed at step %d (%s); restarting in 8 s", failed,
                 failed == 2 ? "access point" : "TLS: certificates");
        statusled_fail(failed, 0);
        vTaskDelay(pdMS_TO_TICKS(8000));
        esp_restart();
    }
    statusled_booted();
    bridge_start(&uart);
}
