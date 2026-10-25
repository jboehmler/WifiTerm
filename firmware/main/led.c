/**
 * @file led.c
 * @brief Green state LED patterns. See led.h.
 */
#include "led.h"

void led_init(led_t *l, uint32_t now, int bat_quarters)
{
    *l = (led_t){0};
    l->state = LED_BOOT;
    l->state_at = now;
    l->bat = (uint8_t)(bat_quarters >= 1 && bat_quarters <= 4 ? bat_quarters : 0);
    l->bat_at = now;
    if (l->bat) {
        l->boot_until = now + (LED_CODE_ON_MS + LED_CODE_OFF_MS) * l->bat + LED_BOOT_MIN_MS;
    }
}

void led_set_state(led_t *l, int state, uint32_t now)
{
    if (state < LED_BOOT || state > LED_TERM || state == l->state) {
        return;
    }
    l->state = (uint8_t)state;
    l->state_at = now;
}

void led_fail(led_t *l, int step, uint32_t now, uint32_t hold_ms)
{
    l->fail = (uint8_t)(step >= 1 && step <= 9 ? step : 0);
    l->fail_at = now;
    l->fail_hold = hold_ms != 0;
    l->fail_until = now + hold_ms;
}

void led_traffic(led_t *l, uint32_t now)
{
    if (!l->traffic || now - l->pulse_at >= LED_PULSE_GAP_MS) {
        l->pulse_at = now;
    }
    l->traffic = 1;
    l->traffic_at = now;
}

/** @brief Level within a run of @p n code blinks started at @p t0, or -1 once they are over. */
static int code_level(uint32_t t, int n)
{
    uint32_t each = LED_CODE_ON_MS + LED_CODE_OFF_MS;
    if (t >= each * (uint32_t)n) {
        return -1;
    }
    return t % each < LED_CODE_ON_MS;
}

int led_level(led_t *l, uint32_t now)
{
    if (l->fail) {
        if (l->fail_hold && (int32_t)(now - l->fail_until) >= 0) {
            l->fail = 0;
        } else {
            uint32_t period = (LED_CODE_ON_MS + LED_CODE_OFF_MS) * l->fail + LED_CODE_PAUSE_MS;
            int v = code_level((now - l->fail_at) % period, l->fail);
            return v < 0 ? 0 : v;
        }
    }
    if (l->bat) {
        int v = code_level(now - l->bat_at, l->bat);
        if (v >= 0) {
            return v;
        }
        l->bat = 0; /* shown once, at boot */
    }
    if (l->boot_until) {
        if ((int32_t)(now - l->boot_until) < 0) {
            return 1;
        }
        l->boot_until = 0;
    }
    uint32_t t = now - l->state_at;
    switch (l->state) {
    case LED_WAIT_WIFI:
        return t % (2 * LED_SLOW_ON_MS) < LED_SLOW_ON_MS;
    case LED_WAIT_TERM:
        return t % LED_WINK_PERIOD_MS < LED_WINK_ON_MS;
    case LED_TERM:
        if (l->traffic && now - l->traffic_at < LED_TRAFFIC_MS) {
            return now - l->pulse_at >= LED_PULSE_OFF_MS;
        }
        return t % (2 * LED_BLINK_HALF_MS) < LED_BLINK_HALF_MS;
    default:
        return 1; /* LED_BOOT */
    }
}
