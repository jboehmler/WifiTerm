/**
 * @file statusled.h
 * @brief The green state LED on D0 (GPIO16): which state the unit is in (led.h patterns),
 *        updated from boot, the access point, the bridge and the battery monitor.
 * @details State is derived: booting until statusled_booted(); then terminal connected if a
 *          session is up, else station joined if any station is on the access point, else
 *          waiting for WiFi. A 10 ms timer drives the pin. Safe to call from any task.
 */
#ifndef STATUSLED_H
#define STATUSLED_H

#include <stdint.h>

/** @brief Start the LED in state 1. @param bat_quarters 1-4 battery blinks first, 0 = none. */
void statusled_init(int bat_quarters);

/** @brief Boot is over (access point up): leave state 1. */
void statusled_booted(void);

/** @brief A station joined (+1) or left (-1) the access point. */
void statusled_station(int delta);

/** @brief The terminal session came up (1) or ended (0). */
void statusled_session(int up);

/** @brief Show "failed at step N" for @p hold_ms (0 = until restart). */
void statusled_fail(int step, uint32_t hold_ms);

/** @brief Data moved over the session. */
void statusled_traffic(void);

/** @brief Switch the LED off for good (battery shutdown). */
void statusled_off(void);

#endif /* STATUSLED_H */
