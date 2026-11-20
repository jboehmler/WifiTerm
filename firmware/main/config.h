/**
 * @file config.h
 * @brief Build-time constants: version, pins, ports, buffer sizes. One place to look (ADR-0004).
 */
#ifndef CONFIG_H
#define CONFIG_H

/** @brief Firmware version, reported in HELLO and `info`. */
#define FW_VERSION "0.0.3"

/* ---------------------------------------------------------------- pins (NodeMCU / Wemos D1 mini)
 * Device UART is UART0 with swapped pins, so ROM boot text on GPIO1/3 (USB) never reaches it.
 * GPIO15 must be low at reset (10k pull-down on both boards).
 */
#define DEVICE_UART        UART_NUM_0 /**< UART for the RS-232 device (swapped pins). */
#define PIN_DEVICE_RX      13         /**< D7: device data into the ESP (chip R1OUT). */
#define PIN_DEVICE_TX      15         /**< D8: device data out of the ESP (chip T1IN). */
#define PIN_LOG_TX         2          /**< D4: UART1 TX, logs at LOG_BAUD; on-board LED. */
#define PIN_CHIP_POWER     5          /**< D1: RS-232 chip power (MOSFET gate or FORCEOFF). */
#define PIN_CABLE_DETECT   4          /**< D2: TRS3243E INVALID, high while RS-232 levels are seen (I-21). */
#define PIN_FLASH_BUTTON   0          /**< D3: FLASH button, low when pressed. */
#define PIN_STATE_LED      16         /**< D0: green state LED, high = on (NOTES I-22). */
#define BAT_CHECK_MS       1000       /**< Battery check interval while running (NOTES I-24). */
#define BAT_CHECK_OFF_MS   5000       /**< Battery check interval after an empty shutdown. */

/**
 * @brief Board the firmware is built for (`make BOARD=bench|proto|shield`, component.mk).
 * @details 0 = bench: HiLetgo MAX3232 module powered through a P-MOSFET or PNP, no cable detect.
 *          1 = rs232-shield: TRS3243E, FORCEON+FORCEOFF on D1 (high = on), INVALID on D2.
 *          2 = prototype (hardware/prototype): bench power switch plus the discrete
 *              cable detector on D2 (low = console seen), so it behaves like the shield.
 */
#ifndef BOARD
#define BOARD 0
#endif
#define BOARD_RS232_SHIELD (BOARD == 1) /**< rs232-shield build. */
#define BOARD_PROTOTYPE    (BOARD == 2) /**< hardware/prototype build. */

/** @brief Chip power polarity: 0 = low turns the chip on (P-MOSFET/PNP, I-12), 1 = high (FORCEOFF, I-13). */
#define CHIP_POWER_ON_LEVEL BOARD_RS232_SHIELD

/** @brief Nonzero if the chip power pin is fitted (enables `uart power` and its capability). */
#define HAVE_CHIP_POWER 1

/** @brief Nonzero if the chip's INVALID output is wired to PIN_CABLE_DETECT (enables `uart power auto`). */
#define HAVE_CABLE_DETECT (BOARD_RS232_SHIELD || BOARD_PROTOTYPE)

/** @brief PIN_CABLE_DETECT level meaning "console seen": 1 = TRS3243E INVALID, 0 = prototype Q2. */
#define CABLE_VALID_LEVEL BOARD_RS232_SHIELD

/** @brief Nonzero if RTS/CTS pins are fitted (not in 0.2.0). */
#define HAVE_RTSCTS 0

/** @brief UART1 log baud rate (same as the ROM, so one terminal setting shows everything). */
#define LOG_BAUD 74880

/* ---------------------------------------------------------------- network */
#define TLS_PORT           8443   /**< TLS server port. */
#define AP_SSID_DEFAULT    "WIFITERM" /**< Factory access point name. */
#define AP_PASS_DEFAULT    "WifiTerm" /**< Factory access point password. */
#define AP_CHANNEL_DEFAULT 1      /**< Factory channel. */
#define AP_MAX_STA         2      /**< Stations allowed to join the access point. */

/* ---------------------------------------------------------------- timing */
#define RECOVERY_WINDOW_MS  3000  /**< Boot window for the USB recovery menu / FLASH button. */
#define RECOVERY_HOLD_MS    5000  /**< FLASH held this long resets all settings. */
#define CLIENT_TIMEOUT_MS   30000 /**< Session dropped after this long with nothing received. */
#define WATCHDOG_MS         30000 /**< Bridge loop must check in within this time or the ESP restarts. */
#define ACCEPT_FAIL_REBOOT  10    /**< Restart after this many failed listen/accept attempts in a row (R3). */
#define REBOOT_DELAY_MS     500   /**< Delay between `reboot` reply and restart. */

/* ---------------------------------------------------------------- buffers */
#define UART_RX_BUF   2048  /**< UART driver receive ring buffer. */
#define UART_TX_BUF   1024  /**< UART driver transmit ring buffer. */
#define LOG_STREAM_BUF 1024 /**< Log lines waiting to go out as LOG frames. */

#endif /* CONFIG_H */
