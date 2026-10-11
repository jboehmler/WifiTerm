/**
 * @file recovery.h
 * @brief Boot-time recovery over USB (docs/protocol.md, "Recovery"): for RECOVERY_WINDOW_MS
 *        after reset, `r` on the USB console opens a menu; holding FLASH (D3) resets all settings.
 */
#ifndef RECOVERY_H
#define RECOVERY_H

/**
 * @brief Run the recovery window. Needs uartdev_init_console() and settings_init() first.
 * @details Returns when the window passes or the user picks "continue"; a reset choice
 *          restarts the ESP and does not return.
 */
void recovery_window(void);

#endif /* RECOVERY_H */
