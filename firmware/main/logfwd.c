/**
 * @file logfwd.c
 * @brief Log routing. See logfwd.h. esp_log_write holds a lock for a whole line, so the
 *        hook below never sees two lines mixed together.
 */
#include "logfwd.h"

#include <string.h>

#include "config.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/message_buffer.h"

/** @brief Longest log line copied to the client (longer lines are cut). */
#define LINE_MAX 200

static putchar_like_t s_uart_putchar;   /**< The original output (UART1). */
static MessageBufferHandle_t s_lines;   /**< Copied lines for LOG frames. */
static volatile char s_level;           /**< Copy level, 0 = off. */
static volatile int s_paused;           /**< UART1 output paused. */
static char s_line[LINE_MAX];
static size_t s_len;

/** @brief Rank of a level letter; higher is more detailed. Unknown letters rank as info. */
static int rank(char c)
{
    switch (c) {
    case 'E': return 1;
    case 'W': return 2;
    case 'I': return 3;
    case 'D': return 4;
    case 'V': return 5;
    default: return 3;
    }
}

/** @brief Replacement putchar: UART1, plus line capture for the client. */
static int hook(int ch)
{
    if (!s_paused && s_uart_putchar) {
        s_uart_putchar(ch);
    }
    if (!s_level) {
        s_len = 0;
        return ch;
    }
    if (ch == '\n' || s_len == LINE_MAX) {
        if (s_len && rank(s_line[0]) <= rank(s_level)) {
            xMessageBufferSend(s_lines, s_line, s_len, 0); /* dropped if full */
        }
        s_len = 0;
        if (ch == '\n') {
            return ch;
        }
    }
    if (ch != '\r') {
        s_line[s_len++] = (char)ch;
    }
    return ch;
}

void logfwd_init(void)
{
    s_lines = xMessageBufferCreate(LOG_STREAM_BUF);
    s_uart_putchar = esp_log_set_putchar(hook);
}

void logfwd_pause_uart(int paused)
{
    s_paused = paused;
}

void logfwd_set_level(char level)
{
    s_level = level;
    /* Let the chosen detail through esp_log itself; INFO stays the floor for UART1. */
    esp_log_level_set("*", level == 'D' ? ESP_LOG_DEBUG : ESP_LOG_INFO);
    if (!level && s_lines) {
        xMessageBufferReset(s_lines);
    }
}

size_t logfwd_take(char *buf, size_t n)
{
    return s_lines ? xMessageBufferReceive(s_lines, buf, n, 0) : 0;
}
