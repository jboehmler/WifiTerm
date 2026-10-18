/*
 *  SSL server demonstration program
 *
 *  Copyright The Mbed TLS Contributors
 *  SPDX-License-Identifier: Apache-2.0 OR GPL-2.0-or-later
 */

#include <stdlib.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "esp_err.h"
#include "esp_log.h"
#include "esp_system.h"

#include "msgbuf.h"
#include "ssl.h"
#include "ticks.h"
#include "uart.h"
#include "wifi.h"

static const int WIFIWAIT_SECS = 90;

const int tskPRIORITY = tskIDLE_PRIORITY + 2;
TaskHandle_t ssltask_handle;
extern void sslmain_task(void *pvParameters);

/*
static void sslresponse_create(char *dststr, char *msgstr) {
    strcpy(dststr, "Successful read:  <");
    strcat(dststr, msgstr);
    strcat(dststr, ">\n>");
}
*/

static const int Blockms = 10;

#define SSL_TMPBUF_SIZE 64
static char sslread_tmpbuf[SSL_TMPBUF_SIZE];
static int sslread_tmpbuf_size = sizeof(sslread_tmpbuf);

// static char sslwrite_tmpbuf[SSL_TMPBUF_SIZE];
//  static int sslwrite_tmpbuf_size = sizeof(sslwrite_tmpbuf);

#define UART_TMPBUF_SIZE 128
static char uartread_tmpbuf[UART_TMPBUF_SIZE];
static int uartread_tmpbuf_size = sizeof(uartread_tmpbuf);

static char uartwrite_tmpbuf[UART_TMPBUF_SIZE];
// static int uartwrite_tmpbuf_size = sizeof(uartwrite_tmpbuf);

int app_main(void) {
    static const char *TAG = "app_main";
    // int ret, len;
    int wifiwait_cnt = 0;

    ESP_LOGD(TAG, "wifi_init ESP_WIFI_MODE_AP");
    wifi_init();
    ESP_LOGW(TAG, "Waiting for station connection...");
    while (sta_connected() == 0) {
        if (wifiwait_cnt > WIFIWAIT_SECS) {
            esp_restart();
        }
        wifiwait_cnt++;
        ESP_LOGD(TAG, "wifi station wait cnt %d", wifiwait_cnt);
        task_wait_s(1);
    }
    ESP_LOGW(TAG, "Station connected...");
    uart_init();
    ESP_LOGD(TAG, "Creating sslmain_task...");
    xTaskCreate(sslmain_task, "sslmain_task", 4096, NULL, tskPRIORITY,
                &ssltask_handle);
    while (1) {
        if (ssl_ready()) {
            // SSL read -> read msgbuf -> SSL response -> write msgbuf -> SSL
            // write
            ESP_LOGD(TAG, "Read message from SSL read message buffer...");
            if (msgbuf_read_str(TAG, &sslread_msgdata, sslread_tmpbuf,
                                sslread_tmpbuf_size, Blockms)) {
                ESP_LOGI(TAG, "Write message <%s> to UART msgbuf", sslread_tmpbuf);
                if (msgbuf_write_str(TAG, &uartwrite_msgdata, sslread_tmpbuf,
                                     Blockms) == 0) {
                    ESP_LOGD(TAG, "Read message buffer zero bytes...");
                }
            }

            ESP_LOGD(TAG, "Read message from UART read message buffer...");
            if (msgbuf_read_str(TAG, &uartread_msgdata, uartread_tmpbuf,
                                uartread_tmpbuf_size, Blockms)) {
                ESP_LOGI(TAG, "Write message <%s> to SSL", uartread_tmpbuf);
                if (msgbuf_write_str(TAG, &sslwrite_msgdata, uartread_tmpbuf,
                                     Blockms) == 0) {
                    ESP_LOGD(TAG, "Read message buffer zero bytes...");
                }
            }
        } else {
            ESP_LOGD(TAG, "app_main is alive. Waiting for SSL...");
            task_wait_s(1);
        }
    }
    ESP_LOGD(TAG, "Exiting...");
    exit(0);
}
