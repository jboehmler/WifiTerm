/**
 * @file cabledet.c
 * @brief Cable detect and chip power policy. See cabledet.h.
 */
#include "cabledet.h"

/** @brief Ask for the chip state the mode and cable call for. @return CD_CHIP_* bits. */
static int settle_chip(cabledet_t *d)
{
    int want = d->mode == POWER_ON || (d->mode == POWER_AUTO && d->cable == CABLE_CONSOLE);
    if (want == d->chip) {
        return 0;
    }
    d->chip = (uint8_t)want;
    return want ? CD_CHIP_ON : CD_CHIP_OFF;
}

void cabledet_init(cabledet_t *d, int mode, int detect, uint32_t now)
{
    d->detect = detect ? 1 : 0;
    d->mode = (uint8_t)(mode == POWER_AUTO && !detect ? POWER_ON : mode);
    d->cable = CABLE_UNKNOWN;
    d->chip = 0;
    d->level = 0;
    d->since = now;
}

int cabledet_step(cabledet_t *d, int valid, uint32_t now)
{
    int act = 0;

    if (d->detect) {
        valid = valid ? 1 : 0;
        if (valid != d->level) {
            d->level = (uint8_t)valid;
            d->since = now;
        }
        uint32_t held = now - d->since;
        if (d->level && held >= CABLE_ON_MS && d->cable != CABLE_CONSOLE) {
            d->cable = CABLE_CONSOLE;
            act |= CD_EVENT;
        } else if (!d->level && held >= CABLE_OFF_MS && d->cable != CABLE_NONE) {
            d->cable = CABLE_NONE;
            act |= CD_EVENT;
        }
    }
    return act | settle_chip(d);
}

int cabledet_set_mode(cabledet_t *d, int mode)
{
    if (mode < POWER_OFF || mode > POWER_AUTO || (mode == POWER_AUTO && !d->detect)) {
        return -1;
    }
    d->mode = (uint8_t)mode;
    return settle_chip(d);
}

const char *cabledet_event(const cabledet_t *d)
{
    return d->cable == CABLE_CONSOLE ? "cable console" : "cable none";
}

const char *power_mode_name(int mode)
{
    return mode == POWER_AUTO ? "auto" : (mode == POWER_ON ? "on" : "off");
}

const char *cable_name(int cable)
{
    return cable == CABLE_CONSOLE ? "console" : (cable == CABLE_NONE ? "none" : "unknown");
}
