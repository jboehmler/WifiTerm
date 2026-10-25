/**
 * @file cmd.h
 * @brief ESP command handler (docs/protocol.md, "Commands"): parses CMD text, calls the
 *        hardware through an ops table, and writes the RESP text.
 * @details Portable C99 with no ESP headers, so it is unit-tested on the PC with gcc and
 *          checked against the same vectors as the Python mock (tests/vectors/commands.txt).
 */
#ifndef CMD_H
#define CMD_H

#include <stddef.h>
#include <stdint.h>

#include "cabledet.h"

/** @brief Device flow control modes. */
typedef enum {
    FLOW_NONE = 0, /**< No flow control. */
    FLOW_RTSCTS,   /**< RTS/CTS on GPIOs (needs pins; not in 0.2.0). */
    FLOW_XONXOFF,  /**< XON/XOFF in the data stream. */
} flow_t;

/** @brief Device serial settings. */
typedef struct {
    uint32_t baud;  /**< Bits per second, UART_BAUD_MIN..UART_BAUD_MAX. */
    uint8_t bits;   /**< Data bits 5..8. */
    char parity;    /**< 'N', 'E' or 'O'. */
    uint8_t stop2;  /**< Stop bits times two: 2, 3 or 4 (1, 1.5, 2). */
    uint8_t flow;   /**< flow_t. */
} uart_cfg_t;

/** @brief Lowest baud rate accepted. */
#define UART_BAUD_MIN 300
/** @brief Highest baud rate accepted. */
#define UART_BAUD_MAX 921600
/** @brief Longest `uart break`, ms. */
#define BREAK_MS_MAX 5000
/** @brief Default `uart break`, ms. */
#define BREAK_MS_DEFAULT 250
/** @brief Longest SSID (802.11 limit). */
#define SSID_MAX 32
/** @brief Shortest WPA2 passphrase. */
#define PASS_MIN 8
/** @brief Longest WPA2 passphrase. */
#define PASS_MAX 63

/** @brief Factory serial settings: 9600,8,N,1,none (FortiGate console default). */
extern const uart_cfg_t UART_CFG_DEFAULT;

/**
 * @brief Format settings as "9600,8,N,1,none".
 * @param c Settings.
 * @param buf Destination.
 * @param n Size of @p buf.
 * @return @p buf.
 */
const char *uart_cfg_text(const uart_cfg_t *c, char *buf, size_t n);

/**
 * @brief Check that stored settings are sane (e.g. after reading NVS).
 * @param c Settings.
 * @return 1 if valid.
 */
int uart_cfg_valid(const uart_cfg_t *c);

/**
 * @brief Hardware and storage operations the commands need. The firmware fills this with
 *        real functions; the host test fills it with fakes that record calls.
 * @details Functions return 0 on success, nonzero on failure, unless noted.
 */
typedef struct {
    void *ctx;                                                  /**< Passed to every call. */
    int (*uart_apply)(void *ctx, const uart_cfg_t *c);          /**< Use settings now. */
    int (*uart_save)(void *ctx, const uart_cfg_t *c);           /**< Store as boot settings. */
    int (*uart_saved)(void *ctx, uart_cfg_t *c);                /**< Read boot settings. */
    int (*uart_break)(void *ctx, unsigned ms);                  /**< Send a line break. */
    int (*uart_power)(void *ctx, int mode);                     /**< Set power_mode_t (off/on/auto). */
    int (*power_save)(void *ctx, int mode);                     /**< Store the boot power mode. */
    int (*power_saved)(void *ctx, int *mode);                   /**< Read the boot power mode. */
    void (*power_status)(void *ctx, char *buf, size_t n);       /**< "chip=on|off cable=none|console|unknown". */
    void (*wifi_get)(void *ctx, char *ssid, size_t n, unsigned *channel); /**< Current AP. */
    int (*wifi_save)(void *ctx, const char *ssid, const char *pass, unsigned channel); /**< 0 = keep channel. */
    void (*log_level)(void *ctx, char level);                   /**< 'E','W','I','D', or 0 = off. */
    int (*set_reboot_on_disconnect)(void *ctx, int on);         /**< Save the R3 setting. */
    void (*reboot)(void *ctx);                                  /**< Restart soon (after the reply). */
    void (*info)(void *ctx, char *buf, size_t n);               /**< "fw=.. sdk=.. heap=.. uptime=.. reset=..". */
    int (*bat_read)(void *ctx, int *mv, int *cal);              /**< Calibrated mV and cal; -1 = no battery. */
    int (*bat_cal_save)(void *ctx, int cal);                    /**< Use and store a calibration (per mille). */
    int has_power;   /**< Nonzero if a chip power pin is configured. */
    int has_rtscts;  /**< Nonzero if RTS/CTS pins are configured. */
    int has_cabledetect; /**< Nonzero if the chip's INVALID output is wired (enables `uart power auto`). */
} cmd_ops_t;

/** @brief Command handler state: the serial settings and power mode in use. */
typedef struct {
    uart_cfg_t active; /**< Active (maybe unsaved) settings. */
    int power_mode;    /**< Active power_mode_t (maybe unsaved). */
} cmd_state_t;

/**
 * @brief Factory power mode: auto with a cable-detect pin, else on.
 * @param ops Operations (has_cabledetect is used).
 * @return power_mode_t.
 */
int cmd_power_default(const cmd_ops_t *ops);

/**
 * @brief Power mode to use at boot or `uart revert`, from what NVS held.
 * @details With cable detect, `on` is a temporary override (John 2026-10-25) and is never
 *          restored; neither is `auto` without cable detect. Both fall back to the default.
 * @param ops Operations (has_cabledetect is used).
 * @param found Nonzero if a saved mode was read.
 * @param mode The saved mode.
 * @return power_mode_t.
 */
int cmd_power_boot(const cmd_ops_t *ops, int found, int mode);

/** @brief Longest RESP text written by cmd_run. */
#define CMD_REPLY_MAX 200

/**
 * @brief Run one command.
 * @param st State (active settings).
 * @param ops Hardware operations.
 * @param text Command text without the sequence number, e.g. "uart get".
 * @param reply Receives the reply text (without "OK"/"ERR").
 * @param n Size of @p reply (CMD_REPLY_MAX is enough).
 * @return 1 for OK, 0 for ERR.
 */
int cmd_run(cmd_state_t *st, const cmd_ops_t *ops, const char *text, char *reply, size_t n);

/**
 * @brief Build the HELLO capability list for this firmware and its pin settings.
 * @param ops Operations (has_power, has_rtscts, has_cabledetect are used).
 * @param buf Destination.
 * @param n Size of @p buf.
 * @return @p buf.
 */
const char *cmd_caps(const cmd_ops_t *ops, char *buf, size_t n);

#endif /* CMD_H */
