/**
 * @file cmd.c
 * @brief ESP command handler. See cmd.h. Replies match tools/mock_esp.py word for word.
 */
#include "cmd.h"

#include "battery.h"

#include <ctype.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/** @brief Most words in one command line. */
#define MAX_WORDS 8
/** @brief Longest command line handled (CMD payload limit). */
#define LINE_MAX 1024

const uart_cfg_t UART_CFG_DEFAULT = {9600, 8, 'N', 2, FLOW_NONE};

/** @brief Flow names, indexed by flow_t. */
static const char *const FLOW_NAMES[] = {"none", "rtscts", "xonxoff"};

const char *uart_cfg_text(const uart_cfg_t *c, char *buf, size_t n)
{
    const char *stop = c->stop2 == 3 ? "1.5" : (c->stop2 == 4 ? "2" : "1");
    snprintf(buf, n, "%lu,%u,%c,%s,%s", (unsigned long)c->baud, (unsigned)c->bits, c->parity, stop,
             c->flow <= FLOW_XONXOFF ? FLOW_NAMES[c->flow] : "?");
    return buf;
}

int uart_cfg_valid(const uart_cfg_t *c)
{
    return c->baud >= UART_BAUD_MIN && c->baud <= UART_BAUD_MAX && c->bits >= 5 && c->bits <= 8 &&
           (c->parity == 'N' || c->parity == 'E' || c->parity == 'O') && c->stop2 >= 2 &&
           c->stop2 <= 4 && c->flow <= FLOW_XONXOFF;
}

/** @brief Write a formatted reply. @return @p ok, for `return reply(...)`. */
static int reply_f(int ok, char *reply, size_t n, const char *fmt, ...)
    __attribute__((format(printf, 4, 5)));

static int reply_f(int ok, char *reply, size_t n, const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(reply, n, fmt, ap);
    va_end(ap);
    return ok;
}

/** @brief Parse an unsigned decimal; 0 on success. Digits only, no sign or spaces. */
static int parse_uint(const char *s, unsigned long *out)
{
    if (!*s) {
        return -1;
    }
    for (const char *p = s; *p; p++) {
        if (!isdigit((unsigned char)*p)) {
            return -1;
        }
    }
    if (strlen(s) > 9) {
        return -1; /* larger than any value we accept */
    }
    *out = strtoul(s, NULL, 10);
    return 0;
}

/** @brief `uart set key=value...`: all keys checked before any change. */
static int uart_set(cmd_state_t *st, const cmd_ops_t *ops, char **w, int nw, char *reply, size_t n)
{
    uart_cfg_t c = st->active;
    char buf[40];

    if (nw == 0) {
        return reply_f(0, reply, n, "uart set needs baud=, bits=, parity=, stop= or flow=");
    }
    for (int i = 0; i < nw; i++) {
        char *eq = strchr(w[i], '=');
        if (!eq) {
            return reply_f(0, reply, n, "expected key=value, got '%s'", w[i]);
        }
        *eq = 0;
        const char *key = w[i], *val = eq + 1;
        unsigned long v;
        if (strcmp(key, "baud") == 0) {
            if (parse_uint(val, &v) || v < UART_BAUD_MIN || v > UART_BAUD_MAX) {
                return reply_f(0, reply, n, "baud must be %d..%d", UART_BAUD_MIN, UART_BAUD_MAX);
            }
            c.baud = (uint32_t)v;
        } else if (strcmp(key, "bits") == 0) {
            if (parse_uint(val, &v) || v < 5 || v > 8) {
                return reply_f(0, reply, n, "bits must be one of 5|6|7|8");
            }
            c.bits = (uint8_t)v;
        } else if (strcmp(key, "parity") == 0) {
            char p = (char)toupper((unsigned char)val[0]);
            if (strlen(val) != 1 || (p != 'N' && p != 'E' && p != 'O')) {
                return reply_f(0, reply, n, "parity must be one of N|E|O");
            }
            c.parity = p;
        } else if (strcmp(key, "stop") == 0) {
            if (strcmp(val, "1") == 0) {
                c.stop2 = 2;
            } else if (strcmp(val, "1.5") == 0) {
                c.stop2 = 3;
            } else if (strcmp(val, "2") == 0) {
                c.stop2 = 4;
            } else {
                return reply_f(0, reply, n, "stop must be one of 1|1.5|2");
            }
        } else if (strcmp(key, "flow") == 0) {
            if (strcmp(val, "none") == 0) {
                c.flow = FLOW_NONE;
            } else if (strcmp(val, "xonxoff") == 0) {
                c.flow = FLOW_XONXOFF;
            } else if (strcmp(val, "rtscts") == 0) {
                if (!ops->has_rtscts) {
                    return reply_f(0, reply, n, "rtscts needs the RTS/CTS pins configured");
                }
                c.flow = FLOW_RTSCTS;
            } else {
                return reply_f(0, reply, n, "flow must be one of none|rtscts|xonxoff");
            }
        } else {
            return reply_f(0, reply, n, "unknown key '%s'", key);
        }
    }
    if (ops->uart_apply(ops->ctx, &c)) {
        return reply_f(0, reply, n, "UART rejected the settings");
    }
    st->active = c;
    return reply_f(1, reply, n, "%s", uart_cfg_text(&c, buf, sizeof buf));
}

/** @brief `wifi set ssid=<s> pass=<p> [channel=<n>]`. */
static int wifi_set(const cmd_ops_t *ops, char **w, int nw, char *reply, size_t n)
{
    const char *ssid = NULL, *pass = NULL, *chan = NULL;
    unsigned long ch = 0;

    for (int i = 0; i < nw; i++) {
        char *eq = strchr(w[i], '=');
        const char *val = eq ? eq + 1 : "";
        if (eq) {
            *eq = 0;
        }
        if (strcmp(w[i], "ssid") == 0) {
            ssid = val;
        } else if (strcmp(w[i], "pass") == 0) {
            pass = val;
        } else if (strcmp(w[i], "channel") == 0) {
            chan = val;
        } else {
            ssid = pass = NULL; /* unknown key: usage */
            break;
        }
    }
    if (!ssid || !pass) {
        return reply_f(0, reply, n, "usage: wifi set ssid=<s> pass=<p> [channel=<n>]");
    }
    if (strlen(ssid) < 1 || strlen(ssid) > SSID_MAX) {
        return reply_f(0, reply, n, "ssid must be 1..%d characters", SSID_MAX);
    }
    if (strlen(pass) < PASS_MIN || strlen(pass) > PASS_MAX) {
        return reply_f(0, reply, n, "pass must be %d..%d characters", PASS_MIN, PASS_MAX);
    }
    if (chan && (parse_uint(chan, &ch) || ch < 1 || ch > 13)) {
        return reply_f(0, reply, n, "channel must be 1..13");
    }
    if (ops->wifi_save(ops->ctx, ssid, pass, (unsigned)ch)) {
        return reply_f(0, reply, n, "could not save WiFi settings");
    }
    return reply_f(1, reply, n, "saved; takes effect after reboot");
}

int cmd_power_default(const cmd_ops_t *ops)
{
    return ops->has_cabledetect ? POWER_AUTO : POWER_ON;
}

int cmd_power_boot(const cmd_ops_t *ops, int found, int mode)
{
    if (!found || mode < POWER_OFF || mode > POWER_AUTO ||
        (mode == POWER_AUTO && !ops->has_cabledetect) || (mode == POWER_ON && ops->has_cabledetect)) {
        return cmd_power_default(ops);
    }
    return mode;
}

/** @brief Switch to power mode @p mode (no-op without a power pin). @return 0 on success. */
static int power_apply(cmd_state_t *st, const cmd_ops_t *ops, int mode)
{
    if (!ops->has_power) {
        return 0;
    }
    if (mode == POWER_AUTO && !ops->has_cabledetect) {
        mode = POWER_ON;
    }
    if (ops->uart_power(ops->ctx, mode)) {
        return -1;
    }
    st->power_mode = mode;
    return 0;
}

/** @brief `uart power [on|off|auto]`. */
static int uart_power(cmd_state_t *st, const cmd_ops_t *ops, char **w, int nw, char *reply, size_t n)
{
    int mode;

    if (!ops->has_power) {
        return reply_f(0, reply, n, "no power pin configured");
    }
    if (nw == 0) {
        char status[60];
        ops->power_status(ops->ctx, status, sizeof status);
        return reply_f(1, reply, n, "mode=%s %s", power_mode_name(st->power_mode), status);
    }
    if (nw != 1) {
        return reply_f(0, reply, n, "usage: uart power [on|off|auto]");
    }
    if (strcmp(w[0], "on") == 0) {
        mode = POWER_ON;
    } else if (strcmp(w[0], "off") == 0) {
        mode = POWER_OFF;
    } else if (strcmp(w[0], "auto") == 0) {
        if (!ops->has_cabledetect) {
            return reply_f(0, reply, n, "auto needs the cable-detect pin configured");
        }
        mode = POWER_AUTO;
    } else {
        return reply_f(0, reply, n, "power must be one of on|off|auto");
    }
    if (power_apply(st, ops, mode)) {
        return reply_f(0, reply, n, "power switch failed");
    }
    return 1;
}

/** @brief True if words @p w match the given literal words exactly in count and text. */
static int is(char **w, int nw, int count, const char *a, const char *b)
{
    return nw == count && strcmp(w[0], a) == 0 && (!b || (nw > 1 && strcmp(w[1], b) == 0));
}

/**
 * @brief `bat`, `bat cal <mV>`, `bat cal reset` (NOTES I-24).
 * @details `bat` shows "mv=3870 pct=62 cal=1000". `bat cal <mV>` takes the cell voltage read
 *          with a meter and scales the A0 reading to match (within +-10 %), saved at once.
 * @param ops Operations. @param w Words after "bat". @param nw Their count.
 * @param reply Reply buffer. @param n Its size. @return 1 OK, 0 error.
 */
static int bat_cmd(const cmd_ops_t *ops, char **w, int nw, char *reply, size_t n)
{
    int mv = 0, cal = BAT_CAL_DEFAULT;
    if (ops->bat_read(ops->ctx, &mv, &cal)) {
        return reply_f(0, reply, n, "no battery fitted");
    }
    if (nw == 2 && strcmp(w[0], "cal") == 0) {
        int c;
        if (strcmp(w[1], "reset") == 0) {
            c = BAT_CAL_DEFAULT;
        } else {
            char *end;
            long meter = strtol(w[1], &end, 10);
            if (*end || meter < BAT_ABSENT_MV || meter > 5000) {
                return reply_f(0, reply, n, "give the meter reading in mV, e.g. bat cal 3912");
            }
            c = battery_new_cal(mv, (int)meter, cal);
            if (c < 0) {
                return reply_f(0, reply, n, "more than 10%% off: check the meter reading");
            }
        }
        if (ops->bat_cal_save(ops->ctx, c)) {
            return reply_f(0, reply, n, "could not save");
        }
        mv = (mv * c + cal / 2) / cal; /* re-scale the shown reading to the new calibration */
        cal = c;
    } else if (nw != 0) {
        return reply_f(0, reply, n, "usage: bat | bat cal <mV> | bat cal reset");
    }
    return reply_f(1, reply, n, "mv=%d pct=%d cal=%d", mv, battery_percent(mv), cal);
}

/** @brief True if the first two words are @p a @p b (any count). */
static int starts(char **w, int nw, const char *a, const char *b)
{
    return nw >= 2 && strcmp(w[0], a) == 0 && strcmp(w[1], b) == 0;
}

int cmd_run(cmd_state_t *st, const cmd_ops_t *ops, const char *text, char *reply, size_t n)
{
    char line[LINE_MAX + 1];
    char *w[MAX_WORDS];
    int nw = 0;
    char buf[40];

    reply[0] = 0;
    strncpy(line, text, LINE_MAX);
    line[LINE_MAX] = 0;
    for (char *tok = strtok(line, " \t"); tok; tok = strtok(NULL, " \t")) {
        if (nw == MAX_WORDS) {
            return reply_f(0, reply, n, "too many words");
        }
        w[nw++] = tok;
    }
    if (nw == 0) {
        return reply_f(0, reply, n, "empty command");
    }

    if (is(w, nw, 1, "info", NULL)) {
        char info[CMD_REPLY_MAX - 40];
        ops->info(ops->ctx, info, sizeof info);
        return reply_f(1, reply, n, "%s uart=%s%s%s", info, uart_cfg_text(&st->active, buf, sizeof buf),
                       ops->has_power ? " power=" : "", ops->has_power ? power_mode_name(st->power_mode) : "");
    }
    if (strcmp(w[0], "fw") == 0 && ops->has_ota) {
        return ops->fw(ops->ctx, w + 1, nw - 1, reply, n);
    }
    if (nw >= 1 && strcmp(w[0], "bat") == 0) {
        return bat_cmd(ops, w + 1, nw - 1, reply, n);
    }
    if (is(w, nw, 2, "uart", "get")) {
        return reply_f(1, reply, n, "%s", uart_cfg_text(&st->active, buf, sizeof buf));
    }
    if (starts(w, nw, "uart", "set")) {
        return uart_set(st, ops, w + 2, nw - 2, reply, n);
    }
    if (is(w, nw, 2, "uart", "save")) {
        /* With cable detect, forced `on` is temporary: the saved power mode is left as it was. */
        int temp_on = ops->has_cabledetect && st->power_mode == POWER_ON;
        if (ops->uart_save(ops->ctx, &st->active) ||
            (ops->has_power && !temp_on && ops->power_save(ops->ctx, st->power_mode))) {
            return reply_f(0, reply, n, "could not save");
        }
        return temp_on ? reply_f(1, reply, n, "saved; power on is temporary and not saved") : 1;
    }
    if (is(w, nw, 2, "uart", "revert") || is(w, nw, 2, "uart", "default")) {
        uart_cfg_t c = UART_CFG_DEFAULT;
        int mode = cmd_power_default(ops);
        if (strcmp(w[1], "revert") == 0) {
            if (ops->uart_saved(ops->ctx, &c) || !uart_cfg_valid(&c)) {
                c = UART_CFG_DEFAULT;
            }
            if (ops->has_power) {
                int saved = 0;
                int found = ops->power_saved(ops->ctx, &saved) == 0;
                mode = cmd_power_boot(ops, found, saved);
            }
        }
        if (ops->uart_apply(ops->ctx, &c)) {
            return reply_f(0, reply, n, "UART rejected the settings");
        }
        st->active = c;
        if (power_apply(st, ops, mode)) {
            return reply_f(0, reply, n, "power switch failed");
        }
        return reply_f(1, reply, n, "%s", uart_cfg_text(&c, buf, sizeof buf));
    }
    if (starts(w, nw, "uart", "break") && nw <= 3) {
        unsigned long ms = BREAK_MS_DEFAULT;
        if (nw == 3 && (parse_uint(w[2], &ms) || ms < 1 || ms > BREAK_MS_MAX)) {
            return reply_f(0, reply, n, "break ms must be 1..%d", BREAK_MS_MAX);
        }
        if (ops->uart_break(ops->ctx, (unsigned)ms)) {
            return reply_f(0, reply, n, "break failed");
        }
        return 1;
    }
    if (starts(w, nw, "uart", "power")) {
        return uart_power(st, ops, w + 2, nw - 2, reply, n);
    }
    if (is(w, nw, 2, "wifi", "get")) {
        char ssid[SSID_MAX + 1] = "";
        unsigned ch = 0;
        ops->wifi_get(ops->ctx, ssid, sizeof ssid, &ch);
        return reply_f(1, reply, n, "ssid=%s channel=%u", ssid, ch);
    }
    if (starts(w, nw, "wifi", "set")) {
        return wifi_set(ops, w + 2, nw - 2, reply, n);
    }
    if (starts(w, nw, "log", "on") && nw <= 3) {
        char level = nw == 3 ? (char)toupper((unsigned char)w[2][0]) : 'I';
        if ((nw == 3 && strlen(w[2]) != 1) || !strchr("EWID", level)) {
            return reply_f(0, reply, n, "level must be E, W, I or D");
        }
        ops->log_level(ops->ctx, level);
        return 1;
    }
    if (is(w, nw, 2, "log", "off")) {
        ops->log_level(ops->ctx, 0);
        return 1;
    }
    if (starts(w, nw, "set", "reboot-on-disconnect") && nw == 3 &&
        (strcmp(w[2], "on") == 0 || strcmp(w[2], "off") == 0)) {
        if (ops->set_reboot_on_disconnect(ops->ctx, strcmp(w[2], "on") == 0)) {
            return reply_f(0, reply, n, "could not save");
        }
        return 1;
    }
    if (is(w, nw, 1, "reboot", NULL)) {
        ops->reboot(ops->ctx);
        return 1;
    }
    /* Rebuild the words for the message (strtok split them). */
    {
        size_t used = 0;
        used += (size_t)snprintf(reply, n, "unknown command:");
        for (int i = 0; i < nw && used < n; i++) {
            used += (size_t)snprintf(reply + used, n - used, " %s", w[i]);
        }
    }
    return 0;
}

const char *cmd_caps(const cmd_ops_t *ops, char *buf, size_t n)
{
    snprintf(buf, n,
             "info,uart.get,uart.set,uart.save,uart.revert,uart.default,uart.break,%s"
             "wifi.get,wifi.set,log,reboot,set.reboot-on-disconnect,bat%s%s%s",
             ops->has_power ? "uart.power," : "", ops->has_rtscts ? ",flow.rtscts" : "",
             ops->has_power && ops->has_cabledetect ? ",cabledetect" : "", ops->has_ota ? ",fw.update" : "");
    return buf;
}
