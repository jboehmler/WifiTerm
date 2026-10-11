/**
 * @file test_util.c
 * @brief Host (gcc) tests for timeutil.c (clock lower bound) and frame_kv_get (HELLO keys).
 */
#include "frames.h"
#include "timeutil.h"

#include <stdio.h>
#include <string.h>

static int g_fail, g_pass;

/** @brief Record one check. */
static void check(int ok, const char *what)
{
    if (ok) {
        g_pass++;
    } else {
        g_fail++;
        printf("FAIL: %s\n", what);
    }
}

int main(void)
{
    char v[16];

    /* Known dates (checked with `date -u -d ... +%s`). */
    check(timeutil_days_to_unix(1970, 1, 1) == 0, "epoch");
    check(timeutil_days_to_unix(2000, 3, 1) == 951868800, "2000-03-01 (leap year)");
    check(timeutil_days_to_unix(2026, 10, 11) == 1791676800, "2026-10-11");
    check(timeutil_build_time("Oct 11 2026", "20:40:05") == 1791676800u + 20 * 3600 + 40 * 60 + 5, "build time");
    check(timeutil_build_time("Feb  9 2027", "00:00:00") == (uint32_t)timeutil_days_to_unix(2027, 2, 9), "space-padded day");
    check(timeutil_build_time("Foo 11 2026", "20:40:05") == 0, "bad month");
    check(timeutil_build_time("Oct 11 2026", "2040:05") == 0, "bad time");
    check(timeutil_build_time("Oct 11 26", "20:40:05") == 0, "short date");
    check(timeutil_build_time(__DATE__, __TIME__) > 1700000000u, "this build's own time parses");

    check(frame_kv_get("proto=1-1 client=0.2.0 time=1791676800", "time", v, sizeof v) && strcmp(v, "1791676800") == 0, "time");
    check(frame_kv_get("time=5", "time", v, sizeof v) && strcmp(v, "5") == 0, "only key");
    check(!frame_kv_get("xtime=5 times=6", "time", v, sizeof v), "no partial key match");
    check(!frame_kv_get("", "time", v, sizeof v), "empty");
    check(frame_kv_get("a=1  time=123456789012345678", "time", v, 6) && strcmp(v, "12345") == 0, "truncated");
    check(frame_kv_get("time= x=1", "time", v, sizeof v) && v[0] == 0, "empty value");

    printf("%d passed, %d failed\n", g_pass, g_fail);
    return g_fail ? 1 : 0;
}
