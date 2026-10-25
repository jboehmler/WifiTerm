/**
 * @file cabledet.h
 * @brief Cable detect and RS-232 chip power policy (NOTES I-21, `uart power auto`).
 * @details The TRS3243E's INVALID output is high while any receiver input sees a valid RS-232
 *          level (beyond +-2.7 V) and low when all inputs sit near 0 V. A console's idle TxD is
 *          -5..-12 V, so a real console reads valid; an Ethernet port or no cable reads invalid.
 *          In `auto` mode the chip is switched on only after CABLE_ON_MS of steady "valid", and
 *          off again after CABLE_OFF_MS of steady "invalid", so the drivers never drive an
 *          Ethernet port. Portable C99 with no ESP headers: unit-tested on the PC.
 */
#ifndef CABLEDET_H
#define CABLEDET_H

#include <stdint.h>

/** @brief `uart power` modes. */
typedef enum {
    POWER_OFF = 0,  /**< Chip always off. */
    POWER_ON = 1,   /**< Chip always on (manual override; bench modules without INVALID). */
    POWER_AUTO = 2, /**< Chip on only while a console is detected. */
} power_mode_t;

/** @brief What the INVALID input says about the cable. */
typedef enum {
    CABLE_UNKNOWN = 0, /**< No detect pin, or not settled since boot. */
    CABLE_NONE,        /**< No valid RS-232 levels: no cable, device off, or not a console port. */
    CABLE_CONSOLE,     /**< Valid RS-232 levels: a console is connected. */
} cable_t;

/** @brief Steady "valid" time before the cable counts as a console, ms. */
#define CABLE_ON_MS 1000
/** @brief Steady "invalid" time before the cable counts as gone, ms. */
#define CABLE_OFF_MS 3000

/** @brief cabledet_step / cabledet_set_mode result bits. */
enum {
    CD_CHIP_ON = 1,  /**< Switch the chip on now. */
    CD_CHIP_OFF = 2, /**< Switch the chip off now. */
    CD_EVENT = 4,    /**< Cable state changed: send cabledet_event() to the client. */
};

/** @brief Detector state. */
typedef struct {
    uint8_t mode;     /**< power_mode_t. */
    uint8_t detect;   /**< Nonzero if an INVALID pin is fitted. */
    uint8_t cable;    /**< cable_t. */
    uint8_t chip;     /**< Chip is on (as last requested). */
    uint8_t level;    /**< Last INVALID reading (1 = valid). */
    uint32_t since;   /**< Time @ref level last changed, ms. */
} cabledet_t;

/**
 * @brief Start with the chip off and the cable unknown.
 * @param d State.
 * @param mode power_mode_t (POWER_AUTO falls back to POWER_ON without a detect pin).
 * @param detect Nonzero if an INVALID pin is fitted.
 * @param now Current time, ms.
 */
void cabledet_init(cabledet_t *d, int mode, int detect, uint32_t now);

/**
 * @brief Feed one INVALID reading; call every bridge loop (every 10..50 ms).
 * @param d State.
 * @param valid INVALID pin level (1 = valid RS-232 seen); ignored without a detect pin.
 * @param now Current time, ms (wraps safely).
 * @return CD_* bits: what the caller must do now.
 */
int cabledet_step(cabledet_t *d, int valid, uint32_t now);

/**
 * @brief Change the mode (from `uart power ...`).
 * @param d State.
 * @param mode power_mode_t.
 * @return CD_* bits, or -1 if @p mode is POWER_AUTO without a detect pin.
 */
int cabledet_set_mode(cabledet_t *d, int mode);

/** @brief EVENT text for the current cable state: "cable console" or "cable none". */
const char *cabledet_event(const cabledet_t *d);

/** @brief Name of a power_mode_t: "off", "on" or "auto". */
const char *power_mode_name(int mode);

/** @brief Name of a cable_t: "unknown", "none" or "console". */
const char *cable_name(int cable);

#endif /* CABLEDET_H */
