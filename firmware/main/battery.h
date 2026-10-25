/**
 * @file battery.h
 * @brief Battery level from A0 and low-battery policy (NOTES I-24). Portable C99, host-tested.
 * @details A0 on the D1 mini has its own 220k/100k divider; the board adds 100k from the
 *          battery, so A0 sees Vbat * 100 / 420 and the ESP's 0..1 V ADC reads 0..4.2 V.
 *          No resistor fitted (non-battery build): A0 reads about 0, so "no battery".
 *          Percent comes from a typical LiPo discharge curve, so expect +-10-15 %.
 */
#ifndef BATTERY_H
#define BATTERY_H

#include <stdint.h>

#define BAT_FULL_SCALE_MV 4200 /**< Battery voltage at ADC reading 1023, before calibration. */
#define BAT_CAL_DEFAULT   1000 /**< Calibration, per mille: 1000 = no correction. */
#define BAT_CAL_MIN       900  /**< Smallest accepted correction (-10 %). */
#define BAT_CAL_MAX       1100 /**< Largest accepted correction (+10 %). */
#define BAT_ABSENT_MV     2500 /**< Below this: no battery fitted. */
#define BAT_LOW_MV        3500 /**< "battery low" warning at or below this (about 6 %). */
#define BAT_LOW_CLEAR_MV  3650 /**< Warning re-armed above this (charging). */
#define BAT_EMPTY_MV      3350 /**< Shut down after BAT_EMPTY_MS at or below this. */
#define BAT_EMPTY_MS      10000
#define BAT_RESUME_MV     3700 /**< In shutdown, restart once the battery is back above this. */

/** @brief battery_step() result bits. */
enum { BAT_EV_LOW = 1, BAT_EV_EMPTY = 2 };

/** @brief Policy state. */
typedef struct {
    int mv;              /**< Filtered voltage, mV (0 before the first sample). */
    uint8_t low_sent;    /**< "battery low" already reported. */
    uint8_t empty;       /**< Shutdown requested. */
    uint8_t below;       /**< Currently at or below BAT_EMPTY_MV. */
    uint32_t below_at;   /**< Since when. */
} battery_t;

/** @brief ADC reading (0..1023) to battery mV. */
int battery_mv(unsigned raw);

/** @brief Charge estimate. @param mv Battery mV. @return 0..100, or -1 if no battery. */
int battery_percent(int mv);

/**
 * @brief Apply a calibration to a voltage.
 * @param mv Uncalibrated or calibrated millivolts (0 stays 0).
 * @param cal Per mille, BAT_CAL_MIN..BAT_CAL_MAX.
 * @return mv * cal / 1000, rounded.
 */
int battery_apply_cal(int mv, int cal);

/**
 * @brief New calibration from a meter reading (`bat cal <mV>`).
 * @param shown_mv Voltage the ESP shows now (with calibration @p cal applied).
 * @param meter_mv Voltage measured on the cell with a meter.
 * @param cal Calibration in use, per mille.
 * @return New calibration, or -1 if out of BAT_CAL_MIN..BAT_CAL_MAX or no battery.
 */
int battery_new_cal(int shown_mv, int meter_mv, int cal);

/** @brief Battery level as 1-4 quarters for the boot blinks, or 0 if no battery. */
int battery_quarters(int mv);

/** @brief Clear the policy state. */
void battery_init(battery_t *b);

/**
 * @brief Feed one sample (about once a second).
 * @param b State.
 * @param mv battery_mv() of the latest reading.
 * @param now Current time, ms.
 * @return BAT_EV_* bits that just became true.
 */
int battery_step(battery_t *b, int mv, uint32_t now);

#endif /* BATTERY_H */
