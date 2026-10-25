/**
 * @file test_led.c
 * @brief Host tests for led.c (state LED patterns) and battery.c (level and low-battery policy).
 */
#include <stdio.h>

#include "battery.h"
#include "led.h"

static int g_pass, g_fail;

/** @brief Count one check; print it if it failed. */
static void check(int ok, const char *what)
{
    if (ok) {
        g_pass++;
    } else {
        g_fail++;
        printf("FAIL: %s\n", what);
    }
}

/** @brief Number of off-to-on edges in [t0, t0 + ms), sampled every ms. */
static int rises(led_t *l, uint32_t t0, uint32_t ms)
{
    int n = 0, prev = led_level(l, t0);
    for (uint32_t t = t0 + 1; t != t0 + ms; t++) {
        int v = led_level(l, t);
        n += v && !prev;
        prev = v;
    }
    return n;
}

/** @brief Milliseconds on in [t0, t0 + ms). */
static uint32_t on_ms(led_t *l, uint32_t t0, uint32_t ms)
{
    uint32_t n = 0;
    for (uint32_t t = t0; t != t0 + ms; t++) {
        n += (uint32_t)led_level(l, t);
    }
    return n;
}

/** @brief LED pattern checks starting at clock @p t0 (run twice to cross the wrap). */
static void led_tests(uint32_t t0)
{
    led_t l;

    /* Boot without battery: steady on. */
    led_init(&l, t0, 0);
    check(on_ms(&l, t0, 3000) == 3000, "boot steady");

    /* Boot with 3 quarters: 3 blinks, then steady. */
    led_init(&l, t0, 3);
    check(rises(&l, t0, 1500) == 2 && led_level(&l, t0) == 1, "3 battery blinks (first starts on)");
    check(on_ms(&l, t0 + 1500, 2000) == 2000, "steady after battery blinks");

    /* With a battery, steady holds 3 s after the blinks even if WiFi is up sooner. */
    led_t h;
    led_init(&h, t0, 2);
    led_set_state(&h, LED_WAIT_WIFI, t0 + 1200);
    check(on_ms(&h, t0 + 1000, 3000) == 3000 && on_ms(&h, t0 + 4000, 1000) < 1000, "steady held 3 s");

    /* State 2: 1 s on, 1 s off. */
    led_set_state(&l, LED_WAIT_WIFI, t0 + 5000);
    check(on_ms(&l, t0 + 5000, 4000) == 2000 && rises(&l, t0 + 5000, 4000) == 1, "slow blink");

    /* State 3: 100 ms wink every 2 s. */
    led_set_state(&l, LED_WAIT_TERM, t0 + 10000);
    check(on_ms(&l, t0 + 10000, 4000) == 200 && rises(&l, t0 + 10000, 4000) == 1, "wink");

    /* State 4: 2.5 Hz regular blink. */
    led_set_state(&l, LED_TERM, t0 + 20000);
    check(rises(&l, t0 + 20000, 2000) == 4 && on_ms(&l, t0 + 20000, 2000) == 1000, "regular blink");

    /* State 5: traffic every 30 ms for 1 s: mostly on with off-pulses at most every 80 ms. */
    uint32_t t = t0 + 30000, off = 0;
    for (uint32_t i = 0; i < 1000; i++, t++) {
        if (i % 30 == 0) {
            led_traffic(&l, t);
        }
        off += (uint32_t)!led_level(&l, t);
    }
    check(off >= 12 * LED_PULSE_OFF_MS - 40 && off <= 13 * LED_PULSE_OFF_MS, "traffic off-pulses");
    {
        int r = rises(&l, t + LED_TRAFFIC_MS, 2000); /* 4 or 5 edges in 5 periods, by phase */
        check((r == 4 || r == 5) && on_ms(&l, t + LED_TRAFFIC_MS, 2000) == 1000, "back to regular blink after traffic");
    }

    /* Failure code 3 for 10 s, over any state: 3 blinks per 3.5 s period, then normal. */
    led_set_state(&l, LED_WAIT_WIFI, t0 + 40000);
    led_fail(&l, 3, t0 + 40000, 10000);
    check(rises(&l, t0 + 40000, 3500) == 2 && led_level(&l, t0 + 40000) == 1, "code 3, first period");
    check(rises(&l, t0 + 43500, 3500) == 2 && led_level(&l, t0 + 43500) == 1 && on_ms(&l, t0 + 43500, 3500) == 600, "code 3, second period");
    check(on_ms(&l, t0 + 50000, 2000) >= 1000, "code ends after hold");
    led_fail(&l, 2, t0 + 60000, 0);
    check(rises(&l, t0 + 60000, 30000) >= 8 * 2 - 1, "code held until cleared");
    led_fail(&l, 0, t0 + 90000, 0);
    check(l.fail == 0, "code cleared");
    led_set_state(&l, 9, t0);
    check(l.state == LED_WAIT_WIFI, "bad state ignored");
}

/** @brief Battery conversion and policy checks. */
static void battery_tests(void)
{
    battery_t b;

    check(battery_mv(1023) == BAT_FULL_SCALE_MV && battery_mv(0) == 0 && battery_mv(5000) == BAT_FULL_SCALE_MV,
          "mv scale");
    check(battery_percent(4250) == 100 && battery_percent(3300) == 0 && battery_percent(3200) == 0, "percent ends");
    check(battery_percent(3800) == 54 && battery_percent(3850) == 61, "percent interpolates");
    check(battery_percent(100) == -1 && battery_quarters(100) == 0, "no battery");
    check(battery_quarters(4150) == 4 && battery_quarters(3850) == 3 && battery_quarters(3700) == 2 &&
              battery_quarters(3500) == 1,
          "quarters");

    battery_init(&b);
    uint32_t t = 0;
    int ev = 0;
    for (int mv = 4000; mv >= 3360; mv -= 10, t += 1000) {
        ev |= battery_step(&b, mv, t);
    }
    check(ev == BAT_EV_LOW && b.low_sent, "low once on the way down");
    ev = 0;
    for (int i = 0; i < 9; i++, t += 1000) {
        ev |= battery_step(&b, 3300, t);
    }
    check(ev == 0 && !b.empty, "not empty before 10 s");
    for (int i = 0; i < 4; i++, t += 1000) {
        ev |= battery_step(&b, 3300, t);
    }
    check(ev == BAT_EV_EMPTY && b.empty, "empty after 10 s below");
    battery_init(&b);
    check(battery_step(&b, 0, 0) == 0 && battery_step(&b, 0, 1000) == 0, "absent: no events");
    battery_init(&b);
    battery_step(&b, 3450, 0);
    check(b.low_sent, "low at first reading");
    for (int i = 0; i < 20; i++) {
        battery_step(&b, 4000, (uint32_t)i * 1000);
    }
    check(!b.low_sent, "low re-armed when charged");
}

int main(void)
{
    led_tests(0);
    led_tests(0xFFFFFFFFu - 25000);
    battery_tests();
    printf("%d passed, %d failed\n", g_pass, g_fail);
    return g_fail ? 1 : 0;
}
