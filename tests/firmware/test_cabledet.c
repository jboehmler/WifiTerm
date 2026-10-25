/**
 * @file test_cabledet.c
 * @brief Host tests for cabledet.c: debounce times, chip switching per mode, events, no-detect
 *        fallback and clock wrap (NOTES I-21).
 */
#include <stdio.h>
#include <string.h>

#include "cabledet.h"

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

/**
 * @brief Feed a steady INVALID level every 10 ms for @p ms, OR-ing the results.
 * @param d State. @param valid Level. @param t Clock, advanced in place. @param ms Duration.
 * @return All CD_* bits seen.
 */
static int hold(cabledet_t *d, int valid, uint32_t *t, uint32_t ms)
{
    int all = 0;
    for (uint32_t end = *t + ms; *t != end; *t += 10) {
        all |= cabledet_step(d, valid, *t);
    }
    return all;
}

/** @brief Run the auto-mode checks starting at clock @p t0 (to test wrap). */
static void auto_mode(uint32_t t0)
{
    cabledet_t d;
    uint32_t t = t0;

    cabledet_init(&d, POWER_AUTO, 1, t);
    check(d.mode == POWER_AUTO && !d.chip && d.cable == CABLE_UNKNOWN, "auto starts off and unknown");
    check(cabledet_step(&d, 0, t) == 0, "first step does nothing");

    /* Nothing plugged in: after 3 s the cable is "none"; the chip stays off throughout. */
    int a = hold(&d, 0, &t, CABLE_OFF_MS + 20);
    check(a == CD_EVENT && d.cable == CABLE_NONE && !d.chip, "no cable: one event, chip off");
    check(strcmp(cabledet_event(&d), "cable none") == 0, "event text none");

    /* A short blip of valid levels (an Ethernet port's noise) does not switch the chip on. */
    a = hold(&d, 1, &t, CABLE_ON_MS - 20);
    a |= hold(&d, 0, &t, 100);
    check(a == 0 && !d.chip, "blip under 1 s ignored");

    /* A console: on after 1 s steady, with an event. */
    a = hold(&d, 1, &t, CABLE_ON_MS - 10);
    check(a == 0 && !d.chip, "not on before 1 s");
    a = hold(&d, 1, &t, 20);
    check(a == (CD_EVENT | CD_CHIP_ON) && d.chip && d.cable == CABLE_CONSOLE, "on at 1 s");
    check(strcmp(cabledet_event(&d), "cable console") == 0, "event text console");
    check(hold(&d, 1, &t, 5000) == 0, "steady console: nothing more");

    /* Dropouts under 3 s (device rebooting, cable wiggled) keep the chip on. */
    a = hold(&d, 0, &t, CABLE_OFF_MS - 20);
    a |= hold(&d, 1, &t, 50);
    check(a == 0 && d.chip, "dropout under 3 s kept");

    /* Unplugged: off after 3 s. */
    a = hold(&d, 0, &t, CABLE_OFF_MS - 10);
    check(a == 0 && d.chip, "still on before 3 s");
    a = hold(&d, 0, &t, 20);
    check(a == (CD_EVENT | CD_CHIP_OFF) && !d.chip && d.cable == CABLE_NONE, "off at 3 s");
}

int main(void)
{
    cabledet_t d;
    uint32_t t = 0;

    auto_mode(0);
    auto_mode(0xFFFFFFFFu - 2000); /* clock wraps in the middle */

    /* Manual modes override the cable; events still report it. */
    cabledet_init(&d, POWER_ON, 1, t);
    check(cabledet_step(&d, 0, t) == CD_CHIP_ON, "on: chip on at once");
    check(hold(&d, 0, &t, CABLE_OFF_MS + 20) == CD_EVENT && d.chip, "on: no cable keeps chip on");
    check(cabledet_set_mode(&d, POWER_AUTO) == CD_CHIP_OFF, "on to auto with no cable: off");
    check(cabledet_set_mode(&d, POWER_AUTO) == 0, "same mode again: nothing");
    check(hold(&d, 1, &t, CABLE_ON_MS + 20) == (CD_EVENT | CD_CHIP_ON), "auto then console: on");
    check(cabledet_set_mode(&d, POWER_OFF) == CD_CHIP_OFF, "off: chip off despite console");
    check(hold(&d, 1, &t, 2000) == 0 && !d.chip, "off stays off");
    check(cabledet_set_mode(&d, POWER_AUTO) == CD_CHIP_ON, "back to auto with console: on");
    check(cabledet_set_mode(&d, 9) == -1 && d.mode == POWER_AUTO, "bad mode refused");

    /* No detect pin: auto is refused, falls back to on, and the cable is never guessed. */
    cabledet_init(&d, POWER_AUTO, 0, t);
    check(d.mode == POWER_ON, "auto without detect starts as on");
    check(cabledet_step(&d, 1, t) == CD_CHIP_ON, "no detect: chip on");
    check(cabledet_set_mode(&d, POWER_AUTO) == -1, "no detect: auto refused");
    check(hold(&d, 1, &t, 5000) == 0 && d.cable == CABLE_UNKNOWN, "no detect: no events");

    check(strcmp(power_mode_name(POWER_AUTO), "auto") == 0 && strcmp(power_mode_name(POWER_ON), "on") == 0 &&
              strcmp(power_mode_name(POWER_OFF), "off") == 0,
          "mode names");
    check(strcmp(cable_name(CABLE_UNKNOWN), "unknown") == 0 && strcmp(cable_name(CABLE_NONE), "none") == 0 &&
              strcmp(cable_name(CABLE_CONSOLE), "console") == 0,
          "cable names");

    printf("%d passed, %d failed\n", g_pass, g_fail);
    return g_fail ? 1 : 0;
}
