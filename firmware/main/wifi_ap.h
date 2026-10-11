/**
 * @file wifi_ap.h
 * @brief The ESP8266's own WiFi access point (the PC joins it). Settings come from NVS
 *        (settings.c); the WiFi driver keeps nothing in flash itself.
 */
#ifndef WIFI_AP_H
#define WIFI_AP_H

#include "settings.h"

/** @brief Start the access point. @param ap Name, password, channel. @return 0 on success. */
int wifi_ap_start(const ap_cfg_t *ap);

/** @brief The running access point's settings (for `wifi get`). */
const ap_cfg_t *wifi_ap_current(void);

#endif /* WIFI_AP_H */
