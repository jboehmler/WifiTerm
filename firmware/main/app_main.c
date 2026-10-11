/**
 * @file app_main.c
 * @brief Boot order for the WiFi Terminal ESP8266 firmware.
 * @details
 *  1. Logs go to UART1 TX (D4) from the start (sdkconfig: console UART 1).
 *  2. Settings from NVS; UART0 on its USB pins at 74880 for the 3 s recovery window
 *     (RS-232 chip still off, so the device sees nothing).
 *  3. UART0 switched to the device: settings applied, pins swapped (D7 RX, D8 TX), chip on.
 *  4. Access point, TLS, then the bridge task.
 */
#include "bridge.h"
#include "config.h"
#include "esp_log.h"
#include "esp_system.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "logfwd.h"
#include "recovery.h"
#include "settings.h"
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

    if (settings_init()) {
        ESP_LOGE(TAG, "settings unavailable; using defaults");
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
    if (wifi_ap_start(&ap) || tls_init()) {
        ESP_LOGE(TAG, "startup failed; restarting in 5 s");
        vTaskDelay(pdMS_TO_TICKS(5000));
        esp_restart();
    }
    bridge_start(&uart);
}
