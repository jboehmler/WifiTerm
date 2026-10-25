/**
 * @file settings.c
 * @brief NVS storage for settings. See settings.h.
 */
#include "settings.h"

#include "battery.h"

#include <string.h>

#include "config.h"
#include "esp_log.h"
#include "nvs.h"
#include "nvs_flash.h"

static const char *TAG = "settings";

/** @brief NVS namespace for everything this firmware stores. */
#define NS "wifiterm"

/** @brief Layout version of the "uart" blob; change it if uart_cfg_t changes. */
#define UART_BLOB_VERSION 1

/** @brief Stored form of uart_cfg_t, with a version byte in front. */
typedef struct {
    uint8_t version;  /**< UART_BLOB_VERSION. */
    uart_cfg_t cfg;   /**< Settings. */
} uart_blob_t;

int settings_init(void)
{
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_LOGW(TAG, "NVS layout changed (0x%x); erasing", err);
        nvs_flash_erase();
        err = nvs_flash_init();
    }
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "nvs_flash_init failed: 0x%x", err);
        return -1;
    }
    return 0;
}

/** @brief Open the namespace. @param rw Nonzero for read/write. @param h Handle out. @return 0 on success. */
static int open_ns(int rw, nvs_handle_t *h)
{
    esp_err_t err = nvs_open(NS, rw ? NVS_READWRITE : NVS_READONLY, h);
    if (err != ESP_OK && !(err == ESP_ERR_NVS_NOT_FOUND && !rw)) {
        ESP_LOGE(TAG, "nvs_open: 0x%x", err);
    }
    return err == ESP_OK ? 0 : -1;
}

int settings_uart_load(uart_cfg_t *c)
{
    nvs_handle_t h;
    uart_blob_t b;
    size_t len = sizeof b;
    int found = 0;

    *c = UART_CFG_DEFAULT;
    if (open_ns(0, &h) == 0) {
        if (nvs_get_blob(h, "uart", &b, &len) == ESP_OK && len == sizeof b &&
            b.version == UART_BLOB_VERSION && uart_cfg_valid(&b.cfg)) {
            *c = b.cfg;
            found = 1;
        }
        nvs_close(h);
    }
    return found ? 0 : -1;
}

int settings_uart_save(const uart_cfg_t *c)
{
    nvs_handle_t h;
    uart_blob_t b;
    esp_err_t err;

    memset(&b, 0, sizeof b);
    b.version = UART_BLOB_VERSION;
    b.cfg = *c;
    if (open_ns(1, &h)) {
        return -1;
    }
    err = nvs_set_blob(h, "uart", &b, sizeof b);
    if (err == ESP_OK) {
        err = nvs_commit(h);
    }
    nvs_close(h);
    return err == ESP_OK ? 0 : -1;
}

int settings_power_load(int *mode)
{
    nvs_handle_t h;
    uint8_t v = 0xff;

    if (open_ns(0, &h) == 0) {
        nvs_get_u8(h, "power", &v);
        nvs_close(h);
    }
    if (v > POWER_AUTO) {
        return -1;
    }
    *mode = v;
    return 0;
}

int settings_power_save(int mode)
{
    nvs_handle_t h;
    esp_err_t err;

    if (open_ns(1, &h)) {
        return -1;
    }
    err = nvs_set_u8(h, "power", (uint8_t)mode);
    if (err == ESP_OK) {
        err = nvs_commit(h);
    }
    nvs_close(h);
    return err == ESP_OK ? 0 : -1;
}

int settings_batcal_load(void)
{
    nvs_handle_t h;
    uint16_t v = 0;

    if (open_ns(0, &h) == 0) {
        nvs_get_u16(h, "batcal", &v);
        nvs_close(h);
    }
    return v >= BAT_CAL_MIN && v <= BAT_CAL_MAX ? v : BAT_CAL_DEFAULT;
}

int settings_batcal_save(int cal)
{
    nvs_handle_t h;
    esp_err_t err;

    if (open_ns(1, &h)) {
        return -1;
    }
    err = nvs_set_u16(h, "batcal", (uint16_t)cal);
    if (err == ESP_OK) {
        err = nvs_commit(h);
    }
    nvs_close(h);
    return err == ESP_OK ? 0 : -1;
}

void settings_ap_load(ap_cfg_t *a)
{
    nvs_handle_t h;
    size_t n;
    uint8_t ch = 0;

    strcpy(a->ssid, AP_SSID_DEFAULT);
    strcpy(a->pass, AP_PASS_DEFAULT);
    a->channel = AP_CHANNEL_DEFAULT;
    if (open_ns(0, &h)) {
        return;
    }
    ap_cfg_t t;
    n = sizeof t.ssid;
    if (nvs_get_str(h, "ap_ssid", t.ssid, &n) == ESP_OK && t.ssid[0]) {
        n = sizeof t.pass;
        if (nvs_get_str(h, "ap_pass", t.pass, &n) == ESP_OK && strlen(t.pass) >= PASS_MIN) {
            strcpy(a->ssid, t.ssid);
            strcpy(a->pass, t.pass);
        }
    }
    if (nvs_get_u8(h, "ap_chan", &ch) == ESP_OK && ch >= 1 && ch <= 13) {
        a->channel = ch;
    }
    nvs_close(h);
}

int settings_ap_save(const char *ssid, const char *pass, unsigned channel)
{
    nvs_handle_t h;
    esp_err_t err;

    if (open_ns(1, &h)) {
        return -1;
    }
    err = nvs_set_str(h, "ap_ssid", ssid);
    if (err == ESP_OK) {
        err = nvs_set_str(h, "ap_pass", pass);
    }
    if (err == ESP_OK && channel) {
        err = nvs_set_u8(h, "ap_chan", (uint8_t)channel);
    }
    if (err == ESP_OK) {
        err = nvs_commit(h);
    }
    nvs_close(h);
    ESP_LOGI(TAG, "access point saved: ssid=%s (password not logged)", ssid);
    return err == ESP_OK ? 0 : -1;
}

int settings_reboot_on_disconnect(void)
{
    nvs_handle_t h;
    uint8_t v = 0;

    if (open_ns(0, &h) == 0) {
        nvs_get_u8(h, "reboot_disc", &v);
        nvs_close(h);
    }
    return v != 0;
}

int settings_set_reboot_on_disconnect(int on)
{
    nvs_handle_t h;
    esp_err_t err;

    if (open_ns(1, &h)) {
        return -1;
    }
    err = nvs_set_u8(h, "reboot_disc", on ? 1 : 0);
    if (err == ESP_OK) {
        err = nvs_commit(h);
    }
    nvs_close(h);
    return err == ESP_OK ? 0 : -1;
}

void settings_reset_wifi(void)
{
    nvs_handle_t h;

    if (open_ns(1, &h) == 0) {
        nvs_erase_key(h, "ap_ssid");
        nvs_erase_key(h, "ap_pass");
        nvs_erase_key(h, "ap_chan");
        nvs_commit(h);
        nvs_close(h);
    }
}

void settings_reset_all(void)
{
    nvs_handle_t h;

    if (open_ns(1, &h) == 0) {
        nvs_erase_all(h);
        nvs_commit(h);
        nvs_close(h);
    }
}
