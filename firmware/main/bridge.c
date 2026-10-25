/**
 * @file bridge.c
 * @brief The bridge: one task that owns the TLS session and the device UART (R5).
 * @details Loop: select() on the listening socket and the session socket with a 10 ms
 *          timeout, then move bytes both ways as frames (docs/protocol.md). Nothing else
 *          touches mbedTLS, so no locks are needed and no task is ever suspended inside it.
 *          The ESP has no modes: DATA always goes to the device, CMD never does.
 *          Each loop also feeds the cable detector, which switches the RS-232 chip (NOTES I-21).
 */
#include "bridge.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>

#include "cmd.h"
#include "config.h"
#include "esp_idf_version.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/timers.h"
#include "frames.h"
#include "logfwd.h"
#include "lwip/sockets.h"
#include "nvs.h"
#include "settings.h"
#include "timeutil.h"
#include "tls.h"
#include "uartdev.h"
#include "wifi_ap.h"

static const char *TAG = "bridge";

/** @brief XON / XOFF bytes for flow=xonxoff. */
#define XON 0x11
#define XOFF 0x13

/** @brief Bytes read from the device per DATA frame (small keeps typing latency low). */
#define UART_CHUNK 512

/** @brief Handshake time limit. */
#define HANDSHAKE_MS 10000

/** @brief Time limit for a write to a slow client before the session is dropped. */
#define WRITE_MS 5000

static cmd_state_t s_cmd;              /**< Active serial settings. */
static int s_power;                    /**< RS-232 chip powered. */
static cabledet_t s_cd;                 /**< Cable detect and power policy (`uart power auto`). */
static int s_cable_event;               /**< Cable state to send to the client as an EVENT. */
static int s_reboot_on_disc;           /**< R3 setting, cached. */
static TickType_t s_reboot_at;         /**< Nonzero: restart at this tick (after `reboot`). */
static volatile TickType_t s_heartbeat; /**< Updated every loop; checked by the watchdog timer. */
static int s_tx_paused;                /**< Device sent XOFF. */
static int s_rx_throttled;             /**< We sent XOFF to the device. */

/* ------------------------------------------------------------------ clock lower bound */

/**
 * @brief Set the clock to the later of the build time and the last time a client sent, so
 *        expired certificates are rejected even without a real-time clock.
 */
static void clock_init(void)
{
    uint32_t t = timeutil_build_time(__DATE__, __TIME__);
    uint32_t saved = 0;
    nvs_handle_t h;

    if (nvs_open("wifiterm", NVS_READONLY, &h) == ESP_OK) {
        nvs_get_u32(h, "time", &saved);
        nvs_close(h);
    }
    if (saved > t) {
        t = saved;
    }
    struct timeval tv = {.tv_sec = (time_t)t, .tv_usec = 0};
    settimeofday(&tv, NULL);
    ESP_LOGI(TAG, "clock lower bound %u (build %s %s)", (unsigned)t, __DATE__, __TIME__);
}

/** @brief Client HELLO said what time it is: move the clock forward, save now and then. */
static void clock_from_client(uint32_t t)
{
    struct timeval now;
    uint32_t saved = 0;
    nvs_handle_t h;

    gettimeofday(&now, NULL);
    if (t <= (uint32_t)now.tv_sec) {
        return;
    }
    now.tv_sec = (time_t)t;
    now.tv_usec = 0;
    settimeofday(&now, NULL);
    if (nvs_open("wifiterm", NVS_READWRITE, &h) == ESP_OK) {
        nvs_get_u32(h, "time", &saved);
        if (t > saved + 3600) { /* at most one flash write per hour of clock advance */
            nvs_set_u32(h, "time", t);
            nvs_commit(h);
        }
        nvs_close(h);
    }
}

/* ------------------------------------------------------------------ command operations */

static int op_uart_apply(void *c, const uart_cfg_t *u)
{
    (void)c;
    if (uartdev_apply(u)) {
        return -1;
    }
    if (u->flow != FLOW_XONXOFF) {
        s_tx_paused = s_rx_throttled = 0;
    }
    return 0;
}
static int op_uart_save(void *c, const uart_cfg_t *u) { (void)c; return settings_uart_save(u); }
static int op_uart_saved(void *c, uart_cfg_t *u) { (void)c; return settings_uart_load(u); }
static int op_uart_break(void *c, unsigned ms) { (void)c; return uartdev_break(ms); }
/** @brief Carry out the CD_CHIP_* bits from the cable detector. @return 0 on success. */
static int chip_act(int act)
{
    if (act & (CD_CHIP_ON | CD_CHIP_OFF)) {
        int on = (act & CD_CHIP_ON) != 0;
        if (HAVE_CHIP_POWER && uartdev_power(on)) { /* no pin: the chip is simply always on */
            return -1;
        }
        s_power = on;
    }
    return 0;
}

/** @brief Milliseconds since boot (wraps after 49 days; cabledet copes). */
static uint32_t ms_now(void) { return (uint32_t)(esp_timer_get_time() / 1000); }

static int op_uart_power(void *c, int mode)
{
    (void)c;
    int act = cabledet_set_mode(&s_cd, mode);
    return act < 0 ? -1 : chip_act(act);
}
static int op_power_save(void *c, int mode) { (void)c; return settings_power_save(mode); }
static int op_power_saved(void *c, int *mode) { (void)c; return settings_power_load(mode); }
static void op_power_status(void *c, char *buf, size_t n)
{
    (void)c;
    snprintf(buf, n, "chip=%s cable=%s", s_power ? "on" : "off", cable_name(s_cd.cable));
}
static void op_wifi_get(void *c, char *ssid, size_t n, unsigned *ch)
{
    (void)c;
    snprintf(ssid, n, "%s", wifi_ap_current()->ssid);
    *ch = wifi_ap_current()->channel;
}
static int op_wifi_save(void *c, const char *s, const char *p, unsigned ch)
{
    (void)c;
    return settings_ap_save(s, p, ch);
}
static void op_log_level(void *c, char level) { (void)c; logfwd_set_level(level); }
static int op_rod(void *c, int on)
{
    (void)c;
    if (settings_set_reboot_on_disconnect(on)) {
        return -1;
    }
    s_reboot_on_disc = on;
    return 0;
}
static void op_reboot(void *c)
{
    (void)c;
    s_reboot_at = xTaskGetTickCount() + pdMS_TO_TICKS(REBOOT_DELAY_MS);
    if (!s_reboot_at) {
        s_reboot_at = 1;
    }
}

/** @brief Reset reason as a word for `info`. */
static const char *reset_reason(void)
{
    switch (esp_reset_reason()) {
    case ESP_RST_POWERON: return "power-on";
    case ESP_RST_EXT: return "external";
    case ESP_RST_SW: return "software";
    case ESP_RST_PANIC: return "panic";
    case ESP_RST_INT_WDT: return "interrupt-watchdog";
    case ESP_RST_TASK_WDT: return "task-watchdog";
    case ESP_RST_WDT: return "watchdog";
    case ESP_RST_DEEPSLEEP: return "deep-sleep";
    case ESP_RST_BROWNOUT: return "brownout";
    case ESP_RST_FAST_SW: return "fast-software";
    default: return "unknown";
    }
}

static void op_info(void *c, char *buf, size_t n)
{
    (void)c;
    snprintf(buf, n, "fw=%s sdk=%s heap=%u uptime=%u reset=%s", FW_VERSION, esp_get_idf_version(),
             (unsigned)esp_get_free_heap_size(), (unsigned)(esp_timer_get_time() / 1000000),
             reset_reason());
}

/** @brief The real hardware behind the portable command handler. */
static const cmd_ops_t s_ops = {
    NULL, op_uart_apply, op_uart_save, op_uart_saved, op_uart_break, op_uart_power, op_power_save,
    op_power_saved, op_power_status, op_wifi_get, op_wifi_save, op_log_level, op_rod, op_reboot,
    op_info, HAVE_CHIP_POWER, HAVE_RTSCTS, HAVE_CABLE_DETECT,
};

/* ------------------------------------------------------------------ session */

/** @brief Session state. */
typedef struct {
    frame_decoder_t dec;   /**< Incoming frame decoder. */
    int hello_done;        /**< Client HELLO answered. */
    TickType_t last_rx;    /**< Last time anything arrived. */
} session_t;

static session_t s_sess;
static uint8_t s_out[FRAME_MAX_LEN]; /**< Encode buffer for outgoing frames. */

/** @brief Send one frame. @return 0 on success. */
static int send_frame(uint8_t type, const void *payload, size_t len)
{
    size_t n = frame_encode(s_out, type, payload, len);
    return n ? tls_write(s_out, n, WRITE_MS) : -1;
}

/** @brief Answer the client's HELLO. @return 0 if a protocol version was agreed. */
static int on_hello(const char *payload)
{
    char caps[200], reply[300], t[16];
    int proto = frame_choose_proto(payload);

    if (frame_kv_get(payload, "time", t, sizeof t)) {
        clock_from_client((uint32_t)strtoul(t, NULL, 10));
    }
    if (!proto) {
        snprintf(reply, sizeof reply, "proto-unsupported %d-%d", PROTO_MIN, PROTO_MAX);
        send_frame(FRAME_EVENT, reply, strlen(reply));
        ESP_LOGW(TAG, "no common protocol: %s", payload);
        return -1;
    }
    snprintf(reply, sizeof reply, "proto=%d fw=%s caps=%s", proto, FW_VERSION, cmd_caps(&s_ops, caps, sizeof caps));
    ESP_LOGI(TAG, "HELLO %s", payload);
    return send_frame(FRAME_HELLO, reply, strlen(reply));
}

/** @brief Send device bytes to the client, handling XON/XOFF from the device. */
static int to_client(uint8_t *buf, int n)
{
    if (s_cmd.active.flow == FLOW_XONXOFF) {
        int k = 0;
        for (int i = 0; i < n; i++) {
            if (buf[i] == XOFF) {
                s_tx_paused = 1;
            } else if (buf[i] == XON) {
                s_tx_paused = 0;
            } else {
                buf[k++] = buf[i];
            }
        }
        n = k;
    }
    return n ? send_frame(FRAME_DATA, buf, (size_t)n) : 0;
}

/** @brief Handle one frame from the client. @return 0 to continue, < 0 to end the session. */
static int on_frame(uint8_t type, const uint8_t *payload, size_t len)
{
    if (!s_sess.hello_done) {
        if (type != FRAME_HELLO) {
            ESP_LOGW(TAG, "frame type %u before HELLO", type);
            return -1;
        }
        if (on_hello((const char *)payload)) {
            return -1;
        }
        s_sess.hello_done = 1;
        /* Tell a new client the cable state once it is known (sent by to_client_all). */
        s_cable_event = HAVE_CABLE_DETECT && s_cd.cable != CABLE_UNKNOWN;
        return 0;
    }
    switch (type) {
    case FRAME_DATA:
        if (s_power && len) {
            uartdev_write(payload, len);
        }
        return 0;
    case FRAME_CMD: {
        unsigned seq;
        const char *text;
        char reply[CMD_REPLY_MAX];
        if (frame_parse_cmd((const char *)payload, &seq, &text)) {
            ESP_LOGW(TAG, "bad CMD");
            return 0;
        }
        /* Never log a wifi password. */
        ESP_LOGI(TAG, "cmd %u: %s", seq, strncmp(text, "wifi set", 8) == 0 ? "wifi set ..." : text);
        int ok = cmd_run(&s_cmd, &s_ops, text, reply, sizeof reply);
        size_t n = frame_encode_resp(s_out, seq, ok, reply);
        return tls_write(s_out, n, WRITE_MS);
    }
    case FRAME_PING:
        return send_frame(FRAME_PONG, payload, len);
    default:
        return 0; /* PONG, and unknown types from newer clients */
    }
}

/** @brief Read and handle whatever the client sent. @return < 0 if the session ended. */
static int from_client(void)
{
    static uint8_t buf[512];

    /* While the device holds us off (XOFF), stop reading: TCP backpressure reaches the PC. */
    while (!s_tx_paused) {
        int n = tls_read(buf, sizeof buf);
        if (n < 0) {
            return -1;
        }
        if (n == 0) {
            return 0;
        }
        s_sess.last_rx = xTaskGetTickCount();
        size_t off = 0;
        while (off < (size_t)n) {
            size_t used;
            frame_status_t st = frame_decoder_feed(&s_sess.dec, buf + off, (size_t)n - off, &used);
            off += used;
            if (st == FRAME_BAD) {
                ESP_LOGW(TAG, "frame too long, closing");
                return -1;
            }
            if (st == FRAME_READY &&
                on_frame(frame_decoder_type(&s_sess.dec), frame_decoder_payload(&s_sess.dec),
                         frame_decoder_len(&s_sess.dec)) < 0) {
                return -1;
            }
        }
    }
    return 0;
}

/** @brief Move device output, UART events and log lines to the client. @return < 0 on failure. */
static int to_client_all(void)
{
    static uint8_t buf[UART_CHUNK];
    char text[LINE_MAX_EVENT];
    int n;

    if (s_cmd.active.flow == FLOW_XONXOFF) {
        size_t pending = uartdev_rx_pending();
        if (!s_rx_throttled && pending > UART_RX_BUF * 3 / 4) {
            uint8_t x = XOFF;
            uartdev_write(&x, 1);
            s_rx_throttled = 1;
        } else if (s_rx_throttled && pending < UART_RX_BUF / 4) {
            uint8_t x = XON;
            uartdev_write(&x, 1);
            s_rx_throttled = 0;
        }
    }
    while ((n = uartdev_read(buf, sizeof buf)) > 0) {
        if (to_client(buf, n)) {
            return -1;
        }
    }
    while (uartdev_event(text, sizeof text)) {
        if (send_frame(FRAME_EVENT, text, strlen(text))) {
            return -1;
        }
    }
    if (s_cable_event) {
        const char *ev = cabledet_event(&s_cd);
        s_cable_event = 0;
        if (send_frame(FRAME_EVENT, ev, strlen(ev))) {
            return -1;
        }
    }
    size_t len;
    static char line[FRAME_MAX_PAYLOAD];
    while ((len = logfwd_take(line, sizeof line)) > 0) {
        if (send_frame(FRAME_LOG, line, len)) {
            return -1;
        }
    }
    return 0;
}

/** @brief End the session; restart if reboot-on-disconnect is on. */
static void end_session(void)
{
    tls_close();
    logfwd_set_level(0);
    s_tx_paused = 0;
    ESP_LOGI(TAG, "session ended");
    if (s_reboot_on_disc) {
        ESP_LOGW(TAG, "reboot-on-disconnect is on: restarting");
        vTaskDelay(pdMS_TO_TICKS(200));
        esp_restart();
    }
}

/* ------------------------------------------------------------------ listener and loop */

/** @brief Open the listening socket. @return fd, or -1. */
static int listen_socket(void)
{
    struct sockaddr_in addr = {.sin_family = AF_INET, .sin_port = htons(TLS_PORT), .sin_addr.s_addr = htonl(INADDR_ANY)};
    int one = 1;
    int fd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);

    if (fd < 0) {
        return -1;
    }
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);
    if (bind(fd, (struct sockaddr *)&addr, sizeof addr) < 0 || listen(fd, 1) < 0) {
        close(fd);
        return -1;
    }
    return fd;
}

/** @brief Software watchdog (R3): restart if the bridge loop stops checking in. */
static void watchdog_cb(TimerHandle_t t)
{
    (void)t;
    if (xTaskGetTickCount() - s_heartbeat > pdMS_TO_TICKS(WATCHDOG_MS)) {
        ESP_LOGE(TAG, "bridge stuck for %d ms: restarting", WATCHDOG_MS);
        esp_restart();
    }
}

/** @brief The bridge task. */
static void bridge_task(void *arg)
{
    (void)arg;
    int lfd = -1, failures = 0;

    for (;;) {
        TickType_t now = xTaskGetTickCount();
        s_heartbeat = now;

        /* Cable detect runs with or without a client, so `auto` never drives an Ethernet port. */
        int act = cabledet_step(&s_cd, uartdev_cable_valid(), ms_now());
        if (chip_act(act)) {
            ESP_LOGE(TAG, "RS-232 chip power switch failed");
        }
        if (act & CD_EVENT) {
            ESP_LOGI(TAG, "%s", cabledet_event(&s_cd));
            s_cable_event = 1;
        }

        if (s_reboot_at && (int32_t)(now - s_reboot_at) >= 0) {
            ESP_LOGW(TAG, "restarting (reboot command)");
            tls_close();
            esp_restart();
        }
        if (lfd < 0) {
            lfd = listen_socket();
            if (lfd < 0) {
                ESP_LOGE(TAG, "listen on %d failed (%d in a row)", TLS_PORT, ++failures);
                if (failures >= ACCEPT_FAIL_REBOOT) {
                    esp_restart();
                }
                vTaskDelay(pdMS_TO_TICKS(1000));
                continue;
            }
            ESP_LOGI(TAG, "listening on port %d", TLS_PORT);
        }

        int sfd = tls_fd();
        fd_set rfds;
        FD_ZERO(&rfds);
        FD_SET(lfd, &rfds);
        if (sfd >= 0 && !s_tx_paused) {
            FD_SET(sfd, &rfds); /* not while the device holds us off, or select() would spin */
        }
        /* 10 ms with a client keeps typing latency low; 50 ms idle still drains the UART. */
        struct timeval tv = {.tv_sec = 0, .tv_usec = sfd >= 0 ? 10000 : 50000};
        int maxfd = sfd > lfd ? sfd : lfd;
        int ready = select(maxfd + 1, &rfds, NULL, NULL, &tv);

        if (ready > 0 && FD_ISSET(lfd, &rfds)) {
            struct sockaddr_in peer;
            socklen_t plen = sizeof peer;
            int cfd = accept(lfd, (struct sockaddr *)&peer, &plen);
            if (cfd < 0) {
                ESP_LOGE(TAG, "accept failed (%d in a row)", ++failures);
                if (failures >= ACCEPT_FAIL_REBOOT) {
                    esp_restart();
                }
                close(lfd);
                lfd = -1;
                continue;
            }
            failures = 0;
            if (sfd >= 0) {
                /* One client at a time; no RAM for a second TLS session, so close at once. */
                ESP_LOGW(TAG, "busy: refusing %s", inet_ntoa(peer.sin_addr));
                close(cfd);
            } else {
                ESP_LOGI(TAG, "connection from %s", inet_ntoa(peer.sin_addr));
                s_heartbeat = xTaskGetTickCount();
                if (tls_start(cfd, HANDSHAKE_MS) == 0) {
                    frame_decoder_init(&s_sess.dec);
                    s_sess.hello_done = 0;
                    s_sess.last_rx = xTaskGetTickCount();
                    logfwd_set_level(0);
                    sfd = tls_fd();
                }
            }
        }

        if (sfd >= 0) {
            int fail = 0;
            if ((ready > 0 && FD_ISSET(sfd, &rfds)) || tls_pending()) {
                fail = from_client() < 0;
            }
            if (!fail && s_sess.hello_done) {
                fail = to_client_all() < 0;
            }
            if (!fail && xTaskGetTickCount() - s_sess.last_rx > pdMS_TO_TICKS(CLIENT_TIMEOUT_MS)) {
                ESP_LOGW(TAG, "nothing from the client for %d ms", CLIENT_TIMEOUT_MS);
                fail = 1;
            }
            if (fail) {
                end_session();
            }
        } else {
            /* No client: device output is dropped so the buffer never overflows. */
            static uint8_t sink[128];
            while (uartdev_read(sink, sizeof sink) > 0) {
            }
            char ev[LINE_MAX_EVENT];
            while (uartdev_event(ev, sizeof ev)) {
            }
        }
    }
}

void bridge_start(const uart_cfg_t *active)
{
    s_cmd.active = *active;
    int saved = 0;
    int found = settings_power_load(&saved) == 0;
    s_cmd.power_mode = cmd_power_boot(&s_ops, found, saved);
    if (!HAVE_CHIP_POWER) {
        s_cmd.power_mode = POWER_ON;
    }
    cabledet_init(&s_cd, s_cmd.power_mode, HAVE_CABLE_DETECT, ms_now());
    ESP_LOGI(TAG, "power mode %s", power_mode_name(s_cmd.power_mode));
    s_reboot_on_disc = settings_reboot_on_disconnect();
    clock_init();
    s_heartbeat = xTaskGetTickCount();
    TimerHandle_t wd = xTimerCreate("watchdog", pdMS_TO_TICKS(5000), pdTRUE, NULL, watchdog_cb);
    if (wd) {
        xTimerStart(wd, 0);
    }
    /* Stack in bytes on this port; the TLS handshake (ECDSA) runs on it. */
    xTaskCreate(bridge_task, "bridge", 8192, NULL, 5, NULL);
}
