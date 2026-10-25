/**
 * @file ota.h
 * @brief ESP8266 side of the signed firmware update (NOTES I-25): flash slots, SHA-256,
 *        signature check against the built-in key, and the trial-boot fallback. The protocol
 *        itself is in fwup.c.
 * @details Needs the two-slot flash layout (sdkconfig: CONFIG_PARTITION_TABLE_TWO_OTA). The
 *          signing key's public half, fw-sign.pub (tools/make-signing-key.sh), is built into
 *          the firmware; only images signed with its private half are accepted.
 */
#ifndef OTA_H
#define OTA_H

#include "fwup.h"

/** @brief Platform operations for fwup_cmd() / fwup_data(). */
extern const fwup_ops_t ota_ops;

/**
 * @brief Boot check, as early as possible after settings_init(): on trial, count the boot,
 *        or switch back to the previous firmware and restart if the trial is used up.
 */
void ota_boot_check(void);

/** @brief A client session started: the running firmware works, so end any trial. */
void ota_mark_good(void);

/** @brief Nonzero if the flash has two firmware slots (OTA layout). */
int ota_available(void);

#endif /* OTA_H */
