/**
 * @file recovery.c
 * @brief Boot recovery window. See recovery.h. Runs before the UART swap, while the RS-232
 *        chip is still off, so nothing here reaches the device.
 */
#include "recovery.h"

#include <stdio.h>

#include "config.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_system.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "logfwd.h"
#include "settings.h"
#include "uartdev.h"

static const char *TAG = "recovery";

/** @brief Blink D4 fast for @p ms (confirmation that the FLASH reset was taken). */
static void blink(unsigned ms)
{
    gpio_config_t io = {.pin_bit_mask = 1UL << PIN_LOG_TX, .mode = GPIO_MODE_OUTPUT};
    logfwd_pause_uart(1); /* D4 is UART1 TX: stop logs so the blinking does not garble them */
    gpio_config(&io);
    for (unsigned t = 0; t < ms; t += 100) {
        gpio_set_level(PIN_LOG_TX, (t / 100) & 1);
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

/** @brief The menu, after `r`. Returns only for "continue". */
static void menu(void)
{
    char line[160];
    ap_cfg_t ap;

    for (;;) {
        uartdev_console_puts("\r\nwifiterm recovery\r\n"
                             "  1 show access point SSID and password\r\n"
                             "  2 reset WiFi settings to defaults\r\n"
                             "  3 reset all settings to defaults\r\n"
                             "  4 continue normal boot\r\n"
                             "choice: ");
        int c = uartdev_console_getc(60000);
        if (c < 0) {
            uartdev_console_puts("\r\nno choice in 60 s, continuing\r\n");
            return;
        }
        snprintf(line, sizeof line, "%c\r\n", c);
        uartdev_console_puts(line);
        switch (c) {
        case '1':
            settings_ap_load(&ap);
            snprintf(line, sizeof line, "SSID: %s\r\npassword: %s\r\nchannel: %u\r\n", ap.ssid, ap.pass,
                     ap.channel);
            uartdev_console_puts(line);
            break;
        case '2':
            settings_reset_wifi();
            uartdev_console_puts("WiFi settings reset (SSID " AP_SSID_DEFAULT "). Restarting.\r\n");
            esp_restart();
        case '3':
            settings_reset_all();
            uartdev_console_puts("All settings reset. Restarting.\r\n");
            esp_restart();
        case '4':
            return;
        default:
            break;
        }
    }
}

void recovery_window(void)
{
    gpio_config_t btn = {.pin_bit_mask = 1UL << PIN_FLASH_BUTTON, .mode = GPIO_MODE_INPUT,
                         .pull_up_en = GPIO_PULLUP_ENABLE};
    unsigned held = 0;

    gpio_config(&btn);
    uartdev_console_puts("\r\nwifiterm " FW_VERSION ": press r for recovery\r\n");
    for (unsigned t = 0; t < RECOVERY_WINDOW_MS || held; t += 50) {
        int c = uartdev_console_getc(50);
        if (c == 'r' || c == 'R') {
            ESP_LOGW(TAG, "recovery menu opened on USB");
            menu();
            return;
        }
        if (gpio_get_level(PIN_FLASH_BUTTON) == 0) {
            held += 50;
            if (held >= RECOVERY_HOLD_MS) {
                ESP_LOGW(TAG, "FLASH held %u ms: resetting all settings", held);
                settings_reset_all();
                uartdev_console_puts("FLASH held: all settings reset. Restarting.\r\n");
                blink(2000);
                esp_restart();
            }
        } else {
            held = 0;
        }
    }
}
