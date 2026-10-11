/**
 * @file timeutil.c
 * @brief Date helpers. See timeutil.h.
 */
#include "timeutil.h"

#include <string.h>

int64_t timeutil_days_to_unix(int y, unsigned m, unsigned d)
{
    /* Howard Hinnant's days_from_civil. */
    y -= m <= 2;
    const int64_t era = (y >= 0 ? y : y - 399) / 400;
    const unsigned yoe = (unsigned)(y - era * 400);
    const unsigned doy = (153 * (m + (m > 2 ? (unsigned)-3 : 9)) + 2) / 5 + d - 1;
    const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    return (era * 146097 + (int64_t)doe - 719468) * 86400;
}

/** @brief Two-digit (or space-padded) number at @p s; -1 if not digits. */
static int num2(const char *s)
{
    int hi = s[0] == ' ' ? 0 : s[0] - '0';
    int lo = s[1] - '0';
    if (hi < 0 || hi > 9 || lo < 0 || lo > 9) {
        return -1;
    }
    return hi * 10 + lo;
}

uint32_t timeutil_build_time(const char *date, const char *time)
{
    static const char months[] = "JanFebMarAprMayJunJulAugSepOctNovDec";
    const char *p;
    int day, year, hh, mm, ss;

    if (strlen(date) != 11 || strlen(time) != 8 || time[2] != ':' || time[5] != ':') {
        return 0;
    }
    p = strstr(months, (char[4]){date[0], date[1], date[2], 0});
    if (!p || (p - months) % 3) {
        return 0;
    }
    day = num2(date + 4);
    year = num2(date + 7) * 100 + num2(date + 9);
    hh = num2(time);
    mm = num2(time + 3);
    ss = num2(time + 6);
    if (day < 1 || year < 1970 || hh < 0 || hh > 23 || mm < 0 || mm > 59 || ss < 0 || ss > 59 ||
        num2(date + 7) < 0 || num2(date + 9) < 0) {
        return 0;
    }
    return (uint32_t)(timeutil_days_to_unix(year, (unsigned)((p - months) / 3 + 1), (unsigned)day) +
                      hh * 3600 + mm * 60 + ss);
}
