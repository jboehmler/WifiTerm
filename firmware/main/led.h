/**
 * @file led.h
 * @brief Green state LED patterns (NOTES I-22, John 2026-10-25). Portable C99, host-tested.
 * @details States, in boot order:
 *          1 booting: steady on (after the battery blinks, if a battery is fitted).
 *          2 waiting for a WiFi station: slow blink, 1 s on / 1 s off.
 *          3 station joined, no terminal: short wink every 2 s.
 *          4 terminal connected, idle: regular blink, about 2.5 per second.
 *          5 traffic: erratic flicker, one short off-pulse per burst; back to 4 after 0.5 s.
 *          Battery level at boot: 1-4 quick blinks (quarters), then steady for at least 3 s.
 *          Failure at step N: N blinks, 2 s pause, repeated (optionally for a limited time).
 *          The caller computes the level every few ms and drives the pin.
 */
#ifndef LED_H
#define LED_H

#include <stdint.h>

/** @brief Pattern timings, ms. */
#define LED_SLOW_ON_MS     1000 /**< State 2: on time (and off time). */
#define LED_WINK_PERIOD_MS 2000 /**< State 3: wink period. */
#define LED_WINK_ON_MS     100  /**< State 3: wink length. */
#define LED_BLINK_HALF_MS  200  /**< State 4: half period (2.5 Hz). */
#define LED_TRAFFIC_MS     500  /**< State 5 lasts this long after the last traffic. */
#define LED_PULSE_OFF_MS   40   /**< State 5: off-pulse length. */
#define LED_PULSE_GAP_MS   80   /**< State 5: shortest time between off-pulses. */
#define LED_CODE_ON_MS     200  /**< Failure and battery blinks: on time. */
#define LED_CODE_OFF_MS    300  /**< Failure and battery blinks: off time between blinks. */
#define LED_CODE_PAUSE_MS  2000 /**< Failure code: pause after the blinks. */
#define LED_BOOT_MIN_MS    3000 /**< With a battery: steady at least this long after its blinks. */

/** @brief LED states (failure and battery blinks are overlays). */
enum { LED_BOOT = 1, LED_WAIT_WIFI = 2, LED_WAIT_TERM = 3, LED_TERM = 4 };

/** @brief Pattern state. All times are ms and wrap safely. */
typedef struct {
    uint8_t state;       /**< LED_BOOT .. LED_TERM. */
    uint8_t fail;        /**< Failed step shown as blinks, 0 = none. */
    uint8_t bat;         /**< Battery blinks still to show at boot (1-4), 0 = none. */
    uint8_t traffic;     /**< Nonzero once led_traffic() has been called. */
    uint32_t boot_until; /**< Steady until then after the battery blinks (0 = no battery). */
    uint8_t fail_hold;   /**< Nonzero if the failure code ends at fail_until. */
    uint32_t state_at;   /**< When the state was entered. */
    uint32_t fail_at;    /**< When the failure code started. */
    uint32_t fail_until; /**< When a held failure code ends. */
    uint32_t bat_at;     /**< When the battery blinks started. */
    uint32_t traffic_at; /**< Last traffic. */
    uint32_t pulse_at;   /**< Last off-pulse start. */
} led_t;

/**
 * @brief Start in state 1, showing the battery level first.
 * @param l State.
 * @param now Current time.
 * @param bat_quarters 1-4 to blink the battery level, 0 for no battery.
 */
void led_init(led_t *l, uint32_t now, int bat_quarters);

/** @brief Enter LED_BOOT .. LED_TERM (no change if already there). */
void led_set_state(led_t *l, int state, uint32_t now);

/**
 * @brief Show "failed at step N".
 * @param l State.
 * @param step 1-9; 0 clears.
 * @param now Current time.
 * @param hold_ms Show for this long, or 0 until cleared.
 */
void led_fail(led_t *l, int step, uint32_t now, uint32_t hold_ms);

/** @brief Data moved (either direction): flicker while it continues (state 4 only). */
void led_traffic(led_t *l, uint32_t now);

/** @brief The LED level now. @return 1 = on, 0 = off. */
int led_level(led_t *l, uint32_t now);

#endif /* LED_H */
