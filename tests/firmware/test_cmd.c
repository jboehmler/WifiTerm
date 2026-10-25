/**
 * @file test_cmd.c
 * @brief Host (gcc) test of firmware/main/cmd.c against tests/vectors/commands.txt, plus
 *        checks that the hardware operations are called with the right values.
 */
#include "cmd.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int g_fail, g_pass;

/** @brief Record one check. */
static void check(int ok, const char *what, const char *detail)
{
    if (ok) {
        g_pass++;
    } else {
        g_fail++;
        printf("FAIL: %s: %s\n", what, detail);
    }
}

/** @brief What the fake hardware saw. */
typedef struct {
    uart_cfg_t applied, saved;
    int have_saved;
    unsigned break_ms;
    int power;        /**< Last power mode asked for. */
    int saved_power;  /**< Saved power mode, or -1. */
    char ssid[40], pass[70];
    unsigned channel;
    char level;
    int reboot_on_disc, reboots;
    int bat_mv, bat_cal; /**< Battery fake: 0 mV = none fitted. */
} fake_t;

static int f_apply(void *c, const uart_cfg_t *u) { ((fake_t *)c)->applied = *u; return 0; }
static int f_save(void *c, const uart_cfg_t *u) { fake_t *f = c; f->saved = *u; f->have_saved = 1; return 0; }
static int f_saved(void *c, uart_cfg_t *u) { fake_t *f = c; if (!f->have_saved) return -1; *u = f->saved; return 0; }
static int f_break(void *c, unsigned ms) { ((fake_t *)c)->break_ms = ms; return 0; }
static int f_power(void *c, int mode) { ((fake_t *)c)->power = mode; return 0; }
static int f_power_save(void *c, int mode) { ((fake_t *)c)->saved_power = mode; return 0; }
static int f_power_saved(void *c, int *mode)
{
    fake_t *f = c;
    if (f->saved_power < 0) return -1;
    *mode = f->saved_power;
    return 0;
}
/** @brief Fake status: the chip follows the mode (auto counts as on); no cable is ever seen. */
static void f_power_status(void *c, char *b, size_t n)
{
    snprintf(b, n, "chip=%s cable=unknown", ((fake_t *)c)->power ? "on" : "off");
}
static void f_wifi_get(void *c, char *s, size_t n, unsigned *ch) { (void)c; snprintf(s, n, "WIFITERM"); *ch = 1; }
static int f_wifi_save(void *c, const char *s, const char *p, unsigned ch)
{
    fake_t *f = c;
    snprintf(f->ssid, sizeof f->ssid, "%s", s);
    snprintf(f->pass, sizeof f->pass, "%s", p);
    f->channel = ch;
    return 0;
}
static void f_level(void *c, char l) { ((fake_t *)c)->level = l; }
static int f_rod(void *c, int on) { ((fake_t *)c)->reboot_on_disc = on; return 0; }
static void f_reboot(void *c) { ((fake_t *)c)->reboots++; }
static void f_info(void *c, char *b, size_t n) { (void)c; snprintf(b, n, "fw=test sdk=host heap=1 uptime=0 reset=power-on"); }
static int f_bat_read(void *c, int *mv, int *cal)
{
    fake_t *f = c;
    if (!f->bat_mv) return -1;
    *mv = f->bat_mv;
    *cal = f->bat_cal;
    return 0;
}
static int f_bat_cal_save(void *c, int cal) { ((fake_t *)c)->bat_cal = cal; return 0; }

int main(int argc, char **argv)
{
    const char *path = argc > 1 ? argv[1] : "../vectors/commands.txt";
    FILE *fp = fopen(path, "r");
    char line[512], reply[CMD_REPLY_MAX], got[CMD_REPLY_MAX + 8];
    fake_t f = {0};
    cmd_ops_t ops = {&f, f_apply, f_save, f_saved, f_break, f_power, f_power_save, f_power_saved,
                     f_power_status, f_wifi_get, f_wifi_save, f_level, f_rod, f_reboot, f_info, f_bat_read,
                     f_bat_cal_save, 1, 0, 0};
    cmd_state_t st = {UART_CFG_DEFAULT, POWER_ON};

    f.saved_power = -1;
    f.power = POWER_ON;

    if (!fp) {
        perror(path);
        return 2;
    }
    while (fgets(line, sizeof line, fp)) {
        line[strcspn(line, "\r\n")] = 0;
        if (!line[0] || line[0] == '#') {
            continue;
        }
        char *sep = strstr(line, " => ");
        if (!sep) {
            check(0, "vector syntax", line);
            continue;
        }
        *sep = 0;
        const char *want = sep + 4;
        int ok = cmd_run(&st, &ops, line, reply, sizeof reply);
        snprintf(got, sizeof got, "%s%s%s", ok ? "OK" : "ERR", ok && reply[0] ? " " : "", ok ? reply : "");
        if (strcmp(want, "OK*") == 0) {
            check(ok, line, reply);
        } else if (strcmp(want, "ERR") == 0) {
            check(!ok && reply[0], line, got);
        } else {
            check(strcmp(got, want) == 0, line, got);
        }
    }
    fclose(fp);

    /* The hardware saw what the commands asked for. */
    cmd_run(&st, &ops, "uart set baud=57600 flow=xonxoff", reply, sizeof reply);
    check(f.applied.baud == 57600 && f.applied.flow == FLOW_XONXOFF, "apply", reply);
    check(cmd_run(&st, &ops, "uart set baud=1 bits=7", reply, sizeof reply) == 0 && st.active.baud == 57600 &&
              st.active.bits == 8,
          "failed set changes nothing", reply);
    cmd_run(&st, &ops, "uart break 123", reply, sizeof reply);
    check(f.break_ms == 123, "break ms", reply);
    cmd_run(&st, &ops, "uart power off", reply, sizeof reply);
    check(f.power == 0, "power off", reply);
    cmd_run(&st, &ops, "wifi set ssid=LAB pass=secret123", reply, sizeof reply);
    check(strcmp(f.ssid, "LAB") == 0 && strcmp(f.pass, "secret123") == 0 && f.channel == 0, "wifi save", reply);
    cmd_run(&st, &ops, "log on w", reply, sizeof reply);
    check(f.level == 'W', "log level", reply);
    cmd_run(&st, &ops, "log off", reply, sizeof reply);
    check(f.level == 0, "log off", reply);
    cmd_run(&st, &ops, "set reboot-on-disconnect on", reply, sizeof reply);
    check(f.reboot_on_disc == 1, "reboot-on-disconnect", reply);
    cmd_run(&st, &ops, "reboot", reply, sizeof reply);
    check(f.reboots == 1, "reboot", reply);
    cmd_run(&st, &ops, "info", reply, sizeof reply);
    check(strstr(reply, "uart=57600,8,N,1,xonxoff") != NULL, "info has uart", reply);

    /* No power pin: command refused, cap hidden. */
    ops.has_power = 0;
    check(cmd_run(&st, &ops, "uart power on", reply, sizeof reply) == 0, "no power pin", reply);
    char caps[200];
    cmd_caps(&ops, caps, sizeof caps);
    check(strstr(caps, "uart.power") == NULL && strstr(caps, "uart.break") != NULL, "caps without power", caps);
    ops.has_power = 1;
    cmd_caps(&ops, caps, sizeof caps);
    check(strstr(caps, "uart.power,wifi.get") != NULL, "caps with power", caps);
    check(strstr(caps, "cabledetect") == NULL, "caps without cable detect", caps);

    /* Battery (NOTES I-24): none fitted, then a cell reading 3850 mV that a meter calls 3900. */
    check(strstr(caps, ",bat") != NULL, "caps has bat", caps);
    check(cmd_run(&st, &ops, "bat", reply, sizeof reply) == 0, "bat without battery", reply);
    f.bat_mv = 3850;
    f.bat_cal = 1000;
    check(cmd_run(&st, &ops, "bat", reply, sizeof reply) == 1 && strcmp(reply, "mv=3850 pct=61 cal=1000") == 0,
          "bat", reply);
    check(cmd_run(&st, &ops, "bat cal 3900", reply, sizeof reply) == 1 && f.bat_cal == 1013 &&
              strcmp(reply, "mv=3900 pct=68 cal=1013") == 0,
          "bat cal", reply);
    f.bat_mv = 3900;
    check(cmd_run(&st, &ops, "bat cal 4500", reply, sizeof reply) == 0 && f.bat_cal == 1013, "bat cal >10% off", reply);
    check(cmd_run(&st, &ops, "bat cal 39x0", reply, sizeof reply) == 0, "bat cal not a number", reply);
    check(cmd_run(&st, &ops, "bat cal", reply, sizeof reply) == 0, "bat cal without value", reply);
    check(cmd_run(&st, &ops, "bat cal reset", reply, sizeof reply) == 1 && f.bat_cal == 1000 &&
              strcmp(reply, "mv=3850 pct=61 cal=1000") == 0,
          "bat cal reset", reply);
    f.bat_mv = 0;

    /* Cable detect fitted: `uart power auto`, saved and restored with the serial settings. */
    check(cmd_power_default(&ops) == POWER_ON, "default without detect", "");
    ops.has_cabledetect = 1;
    check(cmd_power_default(&ops) == POWER_AUTO, "default with detect", "");
    cmd_caps(&ops, caps, sizeof caps);
    check(strstr(caps, ",cabledetect") != NULL, "caps with cable detect", caps);
    check(cmd_run(&st, &ops, "uart power auto", reply, sizeof reply) == 1 && f.power == POWER_AUTO &&
              st.power_mode == POWER_AUTO,
          "power auto", reply);
    cmd_run(&st, &ops, "uart power", reply, sizeof reply);
    check(strncmp(reply, "mode=auto ", 10) == 0, "power status", reply);
    cmd_run(&st, &ops, "info", reply, sizeof reply);
    check(strstr(reply, " power=auto") != NULL, "info has power", reply);
    cmd_run(&st, &ops, "uart save", reply, sizeof reply);
    check(f.saved_power == POWER_AUTO, "save keeps power mode", reply);
    cmd_run(&st, &ops, "uart power off", reply, sizeof reply);
    cmd_run(&st, &ops, "uart revert", reply, sizeof reply);
    check(f.power == POWER_AUTO && st.power_mode == POWER_AUTO, "revert restores power mode", reply);
    cmd_run(&st, &ops, "uart power on", reply, sizeof reply);
    cmd_run(&st, &ops, "uart default", reply, sizeof reply);
    check(f.power == POWER_AUTO, "default power mode is auto", reply);
    f.saved_power = 7; /* garbage in NVS */
    cmd_run(&st, &ops, "uart power off", reply, sizeof reply);
    cmd_run(&st, &ops, "uart revert", reply, sizeof reply);
    check(f.power == POWER_AUTO, "bad saved mode gives default", reply);
    /* Forced on is temporary with cable detect: not saved, never restored. */
    f.saved_power = POWER_OFF;
    cmd_run(&st, &ops, "uart power on", reply, sizeof reply);
    check(cmd_run(&st, &ops, "uart save", reply, sizeof reply) == 1 && f.saved_power == POWER_OFF &&
              strstr(reply, "not saved") != NULL,
          "power on not saved", reply);
    f.saved_power = POWER_ON; /* saved by older firmware */
    cmd_run(&st, &ops, "uart revert", reply, sizeof reply);
    check(f.power == POWER_AUTO, "saved on restored as auto", reply);
    check(cmd_power_boot(&ops, 1, POWER_OFF) == POWER_OFF && cmd_power_boot(&ops, 0, POWER_OFF) == POWER_AUTO,
          "boot mode with detect", "");
    ops.has_cabledetect = 0;
    check(cmd_power_boot(&ops, 1, POWER_ON) == POWER_ON && cmd_power_boot(&ops, 1, POWER_AUTO) == POWER_ON,
          "boot mode without detect", "");
    check(cmd_run(&st, &ops, "uart power auto", reply, sizeof reply) == 0, "auto without detect", reply);
    f.saved_power = POWER_AUTO; /* saved on a shield, firmware now built without detect */
    cmd_run(&st, &ops, "uart revert", reply, sizeof reply);
    check(f.power == POWER_ON && st.power_mode == POWER_ON, "saved auto without detect gives on", reply);

    /* Long and odd input never overflows. */
    {
        static char big[3000];
        memset(big, 'x', sizeof big - 1);
        check(cmd_run(&st, &ops, big, reply, sizeof reply) == 0 && strlen(reply) < sizeof reply, "long input", "");
        check(cmd_run(&st, &ops, "a b c d e f g h i j", reply, sizeof reply) == 0, "too many words", reply);
        check(cmd_run(&st, &ops, "   ", reply, sizeof reply) == 0, "blank", reply);
    }
    /* Text format of every stop/flow value. */
    {
        uart_cfg_t c = {300, 5, 'O', 4, FLOW_RTSCTS};
        char b[40];
        check(strcmp(uart_cfg_text(&c, b, sizeof b), "300,5,O,2,rtscts") == 0, "text", b);
        check(uart_cfg_valid(&c), "valid", b);
        c.stop2 = 1;
        check(!uart_cfg_valid(&c), "invalid stop", b);
    }
    printf("%d passed, %d failed\n", g_pass, g_fail);
    return g_fail ? 1 : 0;
}
