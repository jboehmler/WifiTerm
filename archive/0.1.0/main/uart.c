// Copyright 2018-2025 Espressif Systems (Shanghai) PTE LTD
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

/**
 * This example shows how to use the UART driver to handle special UART events.
 *
 * It also reads data from UART0 directly, and echoes it to uart0out_.
 *
 * - Port: UART0
 * - Receive (Rx) buffer: on
 * - Transmit (Tx) buffer: on
 * - Flow control: off
 * - Event queue: on
 * - Pin assignment: TxD (default), RxD (default)
 */
#include "uart.h"

#define EX_UART_NUM UART_NUM_0

#define BUF_SIZE 128
#define RD_BUF_SIZE BUF_SIZE

static QueueHandle_t uart0in_queue; // for standard uart queue

// needed to transfer data from uart read q to msgbuf
static uint8_t uartread_buf[RD_BUF_SIZE];
static const int uartread_buf_size = sizeof(uartread_buf);
static const int uartread_msgbuf_size = 1024;
//    4 * (uartread_buf_size + 4 * sizeof(size_t));

MSGBUF_DATA uartread_msgdata;

// needed to transfer data from uartwrite msgbuf to uart
static char uartwrite_buf[RD_BUF_SIZE];
static const int uartwrite_buf_size = sizeof(uartwrite_buf);
static const int uartwrite_msgbuf_size = 1024;
//    4 * (uartwrite_buf_size + 4 * sizeof(size_t));

MSGBUF_DATA uartwrite_msgdata;

static void uartread_task(void *pvParameters) {
    const char *TAG = "uartread_task";

    uart_event_t event;

    while (1) {
        // Waiting for UART event.
        ESP_LOGD(TAG, "[UART WAIT]...");
        if (xQueueReceive(uart0in_queue, (void *)&event,
                          (portTickType)portMAX_DELAY)) {
            memset(uartread_buf, '\0', uartread_buf_size);
            ESP_LOGD(TAG, "uart[%d] event:", EX_UART_NUM);

            switch (event.type) {
            // Event of UART receving data
            // We'd better handler data event fast, there would be much more
            // data events than other types of events. If we take too much
            // time on data event, the queue might be full.
            case UART_DATA:
                ESP_LOGD(TAG, "[UART DATA]: %d", event.size);
                uart_read_bytes(EX_UART_NUM, uartread_buf, event.size,
                                portMAX_DELAY);
                ESP_LOGI(TAG, "[DATA EVT]:  <%s>", uartread_buf);
                msgbuf_write(TAG, &uartread_msgdata, uartread_buf, event.size,
                             0);
                break;

            // Event of HW FIFO overflow detected
            case UART_FIFO_OVF:
                ESP_LOGE(TAG, "hw fifo overflow");
                // If fifo overflow happened, you should consider adding
                // flow control for your application. The ISR has already
                // reset the rx FIFO, As an example, we directly flush the
                // rx buffer here in order to read more data.
                uart_flush_input(EX_UART_NUM);
                xQueueReset(uart0in_queue);
                break;

            // Event of UART ring buffer full
            case UART_BUFFER_FULL:
                ESP_LOGE(TAG, "ring buffer full");
                // If buffer full happened, you should consider encreasing
                // your buffer size As an example, we directly flush the rx
                // buffer here in order to read more data.
                uart_flush_input(EX_UART_NUM);
                xQueueReset(uart0in_queue);
                break;

            case UART_PARITY_ERR:
                ESP_LOGE(TAG, "uart parity error");
                break;

            // Event of UART frame error
            case UART_FRAME_ERR:
                ESP_LOGE(TAG, "uart frame error");
                break;

            // Others
            default:
                ESP_LOGE(TAG, "uart event type: %d", event.type);
                break;
            }
        }
    }
}

/*
 * Wait for a message in the message buffer and send it to the uart_out
 */
static void uartwrite_task(void *pvParameters) {
    const char *TAG = "uartwrite_task";

    // const TickType_t xBlockTime = pdMS_TO_TICKS(20);
    const TickType_t xBlockTime = (portTickType)portMAX_DELAY;

    while (1) {

        ESP_LOGD(TAG, "[UART0 Receive WAIT]...");
        /* Receive the next message from the message buffer. Wait in the Blocked
           state (so not using any CPU processing time) for a maximum of 100ms
           for a message to become available. */
        if (msgbuf_read_str(TAG, &uartwrite_msgdata, uartwrite_buf,
                            uartwrite_buf_size, xBlockTime)) {
            /* A uartwrite_buf contains a message that is xReceivedBytes long.
               Process the message here.... */
            ESP_LOGI(TAG, "[MSGBUF EVT]:  <%s>", uartwrite_buf);
            ESP_LOGD(TAG, "[UART WRITE START]:");
            uart_write_bytes(EX_UART_NUM, uartwrite_buf,
                             uartwrite_msgdata.msglen);
            ESP_LOGD(TAG, "[UART WRITE END]:");
        }
    }
}

TaskHandle_t uartread_task_handle;
TaskHandle_t uartwrite_task_handle;

void uart_init(void) {
    const char *TAG = "uart_init";

    ESP_LOGD(TAG, "Initializing UART...");
    // Configure parameters of an UART driver,
    // communication pins and install the driver
    uart_config_t uart_config = {.baud_rate = 74880,
                                 .data_bits = UART_DATA_8_BITS,
                                 .parity = UART_PARITY_DISABLE,
                                 .stop_bits = UART_STOP_BITS_1,
                                 .flow_ctrl = UART_HW_FLOWCTRL_DISABLE};
    uart_param_config(EX_UART_NUM, &uart_config);

    // Install UART driver, and get the queue.
    uart_driver_install(EX_UART_NUM, BUF_SIZE * 2, BUF_SIZE * 2, 100,
                        &uart0in_queue,
                        0); // must run xQueueCreate inside so none
                            // done explicitly in code

    ESP_LOGD(TAG, "Creating uartread message buffer data...");
    if (msgbuf_create(TAG, &uartread_msgdata, uartread_msgbuf_size) == 0) {
        ESP_LOGE(TAG, "Create uartread message buffer failed.\n");
    }
    ESP_LOGD(TAG, "Creating uartwrite message buffer data...");
    if (msgbuf_create(TAG, &uartwrite_msgdata, uartwrite_msgbuf_size) == 0) {
        ESP_LOGE(TAG, "Create uartwrite message buffer failed.\n");
    }

    // Create a task to handler UART event from ISR
    xTaskCreate(uartread_task, "uartread_task", 2048, NULL, 12,
                uartread_task_handle);
    xTaskCreate(uartwrite_task, "uartwrite_task", 2048, NULL, 12,
                uartwrite_task_handle);
}
