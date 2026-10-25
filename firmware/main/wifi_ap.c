/**
 * @file wifi_ap.c
 * @brief Access point. See wifi_ap.h.
 */
#include "wifi_ap.h"

#include <string.h>

#include "config.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "statusled.h"
#include "tcpip_adapter.h"

static const char *TAG = "wifi_ap";

static ap_cfg_t s_ap; /**< Settings in use. */

/** @brief Log stations joining and leaving (no restart on leave: R3); tell the state LED. */
static void on_wifi_event(void *arg, esp_event_base_t base, int32_t id, void *data)
{
    (void)arg;
    (void)base;
    if (id == WIFI_EVENT_AP_STACONNECTED) {
        wifi_event_ap_staconnected_t *e = data;
        ESP_LOGI(TAG, "station " MACSTR " joined", MAC2STR(e->mac));
        statusled_station(+1);
    } else if (id == WIFI_EVENT_AP_STADISCONNECTED) {
        wifi_event_ap_stadisconnected_t *e = data;
        ESP_LOGI(TAG, "station " MACSTR " left", MAC2STR(e->mac));
        statusled_station(-1);
    }
}

int wifi_ap_start(const ap_cfg_t *ap)
{
    wifi_init_config_t init = WIFI_INIT_CONFIG_DEFAULT();
    wifi_config_t wc;

    s_ap = *ap;
    tcpip_adapter_init();
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    ESP_ERROR_CHECK(esp_wifi_init(&init));
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_RAM));
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, on_wifi_event, NULL));

    memset(&wc, 0, sizeof wc);
    memcpy(wc.ap.ssid, ap->ssid, strlen(ap->ssid));
    wc.ap.ssid_len = (uint8_t)strlen(ap->ssid);
    strncpy((char *)wc.ap.password, ap->pass, sizeof wc.ap.password - 1);
    wc.ap.channel = (uint8_t)ap->channel;
    wc.ap.authmode = WIFI_AUTH_WPA2_PSK;
    wc.ap.max_connection = AP_MAX_STA;
    wc.ap.beacon_interval = 100;

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));
    ESP_ERROR_CHECK(esp_wifi_set_config(ESP_IF_WIFI_AP, &wc));
    esp_err_t err = esp_wifi_start();
    ESP_LOGI(TAG, "access point %s on channel %u: %s", ap->ssid, ap->channel,
             err == ESP_OK ? "started" : "FAILED");
    return err == ESP_OK ? 0 : -1;
}

const ap_cfg_t *wifi_ap_current(void)
{
    return &s_ap;
}
