/**
 * @file uartdev.h
 * @brief The RS-232 device link: UART0 on swapped pins (D7 RX, D8 TX), chip power, break,
 *        and receive errors turned into EVENT text (ADR-0004, I-12).
 */
#ifndef UARTDEV_H
#define UARTDEV_H

#include <stddef.h>
#include <stdint.h>

#include "cmd.h"

/**
 * @brief Install the UART0 driver on its default pins (USB) at 74880 baud for the
 *        recovery window. The RS-232 chip stays powered off.
 * @return 0 on success.
 */
int uartdev_init_console(void);

/** @brief Read one key from the USB console. @param ms Wait up to this long. @return Key, or -1. */
int uartdev_console_getc(unsigned ms);

/** @brief Write text to the USB console. @param s NUL-terminated text. */
void uartdev_console_puts(const char *s);

/**
 * @brief Switch UART0 to the device: apply settings, swap pins, then power the chip on.
 * @param c Serial settings.
 * @return 0 on success.
 */
int uartdev_start(const uart_cfg_t *c);

/** @brief Apply serial settings now. @param c Settings. @return 0 on success. */
int uartdev_apply(const uart_cfg_t *c);

/** @brief Read whatever the device has sent, without waiting. @return Bytes read (0 if none). */
int uartdev_read(uint8_t *buf, size_t n);

/**
 * @brief Send bytes to the device, waiting while the transmit buffer is full.
 * @return Bytes queued (normally @p n).
 */
int uartdev_write(const uint8_t *buf, size_t n);

/** @brief Bytes waiting in the receive buffer. */
size_t uartdev_rx_pending(void);

/** @brief Hold the line in break (space) for @p ms milliseconds. @return 0 on success. */
int uartdev_break(unsigned ms);

/** @brief Switch the RS-232 chip on or off. @param on Nonzero for on. @return 0 on success. */
int uartdev_power(int on);

/**
 * @brief Next receive problem as EVENT text ("uart overflow", "uart frame-error",
 *        "uart parity-error"), at most one of each kind per second.
 * @param text Destination.
 * @param n Size of @p text.
 * @return 1 if @p text was filled.
 */
int uartdev_event(char *text, size_t n);

#endif /* UARTDEV_H */
