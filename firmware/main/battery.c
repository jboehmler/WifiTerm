/**
 * @file battery.c
 * @brief Battery level and low-battery policy. See battery.h.
 */
#include "battery.h"

/** @brief Typical LiPo resting curve at light load: mV -> percent, falling. */
static const struct { int mv, pct; } CURVE[] = {
    {4200, 100}, {4100, 90}, {4000, 79}, {3900, 68}, {3800, 54}, {3750, 45},
    {3700, 35},  {3650, 25}, {3600, 15}, {3500, 6},  {3400, 2},  {3300, 0},
};

int battery_mv(unsigned raw)
{
    if (raw > 1023) {
        raw = 1023;
    }
    return (int)((raw * BAT_FULL_SCALE_MV + 511) / 1023);
}

int battery_percent(int mv)
{
    const int n = (int)(sizeof CURVE / sizeof CURVE[0]);
    if (mv < BAT_ABSENT_MV) {
        return -1;
    }
    if (mv >= CURVE[0].mv) {
        return 100;
    }
    for (int i = 1; i < n; i++) {
        if (mv >= CURVE[i].mv) {
            int span = CURVE[i - 1].mv - CURVE[i].mv;
            return CURVE[i].pct + (mv - CURVE[i].mv) * (CURVE[i - 1].pct - CURVE[i].pct) / span;
        }
    }
    return 0;
}

int battery_quarters(int mv)
{
    int p = battery_percent(mv);
    if (p < 0) {
        return 0;
    }
    return p > 75 ? 4 : p > 50 ? 3 : p > 25 ? 2 : 1;
}

void battery_init(battery_t *b)
{
    *b = (battery_t){0};
}

int battery_step(battery_t *b, int mv, uint32_t now)
{
    int ev = 0;

    /* Light filter: WiFi bursts make single readings sag. */
    b->mv = b->mv ? (b->mv * 3 + mv) / 4 : mv;
    if (b->mv < BAT_ABSENT_MV) {
        b->low_sent = b->below = 0;
        return 0;
    }
    if (!b->low_sent && b->mv <= BAT_LOW_MV) {
        b->low_sent = 1;
        ev |= BAT_EV_LOW;
    } else if (b->low_sent && b->mv > BAT_LOW_CLEAR_MV) {
        b->low_sent = 0;
    }
    if (b->mv <= BAT_EMPTY_MV) {
        if (!b->below) {
            b->below = 1;
            b->below_at = now;
        } else if (!b->empty && now - b->below_at >= BAT_EMPTY_MS) {
            b->empty = 1;
            ev |= BAT_EV_EMPTY;
        }
    } else {
        b->below = 0;
    }
    return ev;
}

int battery_apply_cal(int mv, int cal)
{
    return (mv * cal + 500) / 1000;
}

int battery_new_cal(int shown_mv, int meter_mv, int cal)
{
    if (shown_mv < BAT_ABSENT_MV || meter_mv < BAT_ABSENT_MV) {
        return -1;
    }
    long c = ((long)cal * meter_mv + shown_mv / 2) / shown_mv;
    return c < BAT_CAL_MIN || c > BAT_CAL_MAX ? -1 : (int)c;
}
