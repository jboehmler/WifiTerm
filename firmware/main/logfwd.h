/**
 * @file logfwd.h
 * @brief Log routing (ADR-0004): every ESP_LOG line goes to UART1 TX (D4) as before, and after
 *        `log on` also to the client as LOG frames.
 */
#ifndef LOGFWD_H
#define LOGFWD_H

#include <stddef.h>

/** @brief Hook into esp_log. Call once, early. */
void logfwd_init(void);

/** @brief Stop or restart UART1 output (paused while D4 blinks in the recovery window). */
void logfwd_pause_uart(int paused);

/**
 * @brief Choose which lines are copied for the client.
 * @param level 'E', 'W', 'I', 'D', or 0 to stop (log off).
 */
void logfwd_set_level(char level);

/**
 * @brief Take the next copied log line.
 * @param buf Destination (no trailing newline, not NUL-terminated).
 * @param n Size of @p buf.
 * @return Length, or 0 if none waiting.
 */
size_t logfwd_take(char *buf, size_t n);

#endif /* LOGFWD_H */
