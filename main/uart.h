#ifndef UART_H
#define UART_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/message_buffer.h"
#include "freertos/queue.h"
#include "freertos/task.h"

#include "driver/uart.h"

#include "esp_log.h"
#include "msgbuf.h"

extern MSGBUF_DATA uartread_msgdata;
extern MSGBUF_DATA uartwrite_msgdata;

extern void uart_init(void);
#endif // UART_H
