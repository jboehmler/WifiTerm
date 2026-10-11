/**
 * @file timeutil.h
 * @brief Date helpers for certificate checks without a real-time clock.
 * @details The ESP8266 starts at 1970, so expiry checks need a "not earlier than" time:
 *          the later of the firmware build time and the last time a client sent. Portable C99.
 */
#ifndef TIMEUTIL_H
#define TIMEUTIL_H

#include <stdint.h>

/**
 * @brief Seconds since 1970-01-01 UTC for a date.
 * @param y Year (>= 1970). @param m Month 1..12. @param d Day 1..31.
 * @return Seconds at 00:00:00 that day.
 */
int64_t timeutil_days_to_unix(int y, unsigned m, unsigned d);

/**
 * @brief Parse the compiler's __DATE__ ("Oct 11 2026") and __TIME__ ("20:40:00").
 * @param date __DATE__. @param time __TIME__.
 * @return Unix time (taken as UTC), or 0 if either string is malformed.
 */
uint32_t timeutil_build_time(const char *date, const char *time);

#endif /* TIMEUTIL_H */
