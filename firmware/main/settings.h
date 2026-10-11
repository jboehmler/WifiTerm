/**
 * @file settings.h
 * @brief Settings kept in NVS (namespace "wifiterm"): serial settings, access point,
 *        reboot-on-disconnect. Missing or invalid values fall back to the factory defaults.
 */
#ifndef SETTINGS_H
#define SETTINGS_H

#include <stddef.h>

#include "cmd.h"

/** @brief Access point settings. */
typedef struct {
    char ssid[SSID_MAX + 1];  /**< Network name. */
    char pass[PASS_MAX + 1];  /**< WPA2 passphrase. */
    unsigned channel;         /**< 1..13. */
} ap_cfg_t;

/** @brief Open NVS (erasing it if its layout is from another SDK version). @return 0 on success. */
int settings_init(void);

/** @brief Saved serial settings, or defaults. @param c Filled in. @return 0 if saved ones were found. */
int settings_uart_load(uart_cfg_t *c);

/** @brief Save serial settings. @param c Settings. @return 0 on success. */
int settings_uart_save(const uart_cfg_t *c);

/** @brief Access point settings, or defaults. @param a Filled in. */
void settings_ap_load(ap_cfg_t *a);

/**
 * @brief Save access point settings (used at the next boot).
 * @param ssid Name. @param pass Passphrase. @param channel 1..13, or 0 to keep the current one.
 * @return 0 on success.
 */
int settings_ap_save(const char *ssid, const char *pass, unsigned channel);

/** @brief The R3 setting. @return Nonzero if the ESP restarts when the client disconnects. */
int settings_reboot_on_disconnect(void);

/** @brief Save the R3 setting. @param on Nonzero for on. @return 0 on success. */
int settings_set_reboot_on_disconnect(int on);

/** @brief Recovery: forget the access point settings (factory SSID/password at next boot). */
void settings_reset_wifi(void);

/** @brief Recovery: forget every setting. */
void settings_reset_all(void);

#endif /* SETTINGS_H */
