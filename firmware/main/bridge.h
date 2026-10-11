/**
 * @file bridge.h
 * @brief The bridge task: TLS session <-> frames <-> device UART, commands, keepalive,
 *        software watchdog (R1 to R9).
 */
#ifndef BRIDGE_H
#define BRIDGE_H

#include "cmd.h"

/** @brief Longest EVENT text from the UART. */
#define LINE_MAX_EVENT 40

/**
 * @brief Start the bridge task. Call after the access point, TLS and device UART are up.
 * @param active Serial settings in use.
 */
void bridge_start(const uart_cfg_t *active);

#endif /* BRIDGE_H */
