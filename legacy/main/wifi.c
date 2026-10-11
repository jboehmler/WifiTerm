/*  WiFi softAP Example

   This example code is in the Public Domain (or CC0 licensed, at your option.)

   Unless required by applicable law or agreed to in writing, this
   software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
   CONDITIONS OF ANY KIND, either express or implied.
*/
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "esp_event.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include <string.h>

#include "lwip/err.h"
#include "lwip/sys.h"

#include "nvs.h"
#include "nvs_flash.h"

#include "wifi.h"

// #define APP_MAIN

#define SOFTAP
#define DEFAULT_WIFI_SSID "WIFITERM"
#define DEFAULT_WIFI_PASS "WifiTerm"
#define DEFAULT_STA_CONN 2

typedef enum APSTATUS { APOK, APNOSTA, STAIPOK } APSTATUS;
typedef struct APCONN {
    APSTATUS apstatus;
    int stacnt;
} APCONN;

static APCONN apconn = {.apstatus = APNOSTA, .stacnt = 0};

int sta_connected(void) {
    if (apconn.apstatus == STAIPOK) {
        return (1);
    }
    return (0);
}

#ifdef SOFTAP

void get_stalist(char *callstr) {
    const char *TAG = "get_stalist";
    const int buflen = 20;
    char buf[buflen];

    wifi_sta_list_t wifi_sta_list;
    tcpip_adapter_sta_list_t tcpip_sta_list;

    esp_wifi_ap_get_sta_list(&wifi_sta_list);
    tcpip_adapter_get_sta_list(&wifi_sta_list, &tcpip_sta_list);
    ESP_LOGD(TAG, "%s Stations:  %d", callstr, wifi_sta_list.num);
    for (int i = 0; i < wifi_sta_list.num; i++) {
        /*
        ESP_LOGD(TAG, "StaInfo:" MACSTR "," IPSTR "",
               MAC2STR(wifi_sta_list.sta[i].mac),
               IP2STR(&tcpip_sta_list.sta[i].ip));
               */
        ipaddr_ntoa_r(&tcpip_sta_list.sta[i].ip, buf, buflen);
        ESP_LOGD(TAG, "%s Station %d:%s", callstr, i, buf);
    }
}

/*
struct station_info * station = wifi_softap_get_station_info();
while(station){
 os_printf(bssid : MACSTR, ip : IPSTR/n,
 MAC2STR(station->bssid), IP2STR(&station->ip));
 station = STAILQ_NEXT(station, next);
}
*/

static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data) {
    const char *wifi_TAG = "wifi_AP_event";

    ESP_LOGD(wifi_TAG, "base:event id  %s:%d", event_base, event_id);
    if (event_id == IP_EVENT_AP_STAIPASSIGNED) {
        get_stalist("IP_EVENT_AP_STAIPASSIGNED");
        apconn.apstatus = STAIPOK;
    } else if (event_id == WIFI_EVENT_AP_STACONNECTED) {
        wifi_event_ap_staconnected_t *event =
            (wifi_event_ap_staconnected_t *)event_data;
        ESP_LOGD(wifi_TAG, "station " MACSTR " join, AID=%d",
                 MAC2STR(event->mac), event->aid);
        apconn.stacnt++;
        apconn.apstatus = APOK;
        // get_stalist("WIFI_EVEN_AP_STACONNECTED");  //may be before ip address
        // assigned
    } else if (event_id == WIFI_EVENT_AP_STADISCONNECTED) {
        wifi_event_ap_stadisconnected_t *event =
            (wifi_event_ap_stadisconnected_t *)event_data;
        ESP_LOGD(wifi_TAG, "station " MACSTR " leave, AID=%d",
                 MAC2STR(event->mac), event->aid);
        apconn.stacnt--;
        if (apconn.stacnt == 0) {
            apconn.apstatus = APNOSTA;
            esp_restart();
        }
    } else {
        ESP_LOGI(wifi_TAG, "unregistered event id:  %d", event_id);
    }
}

esp_err_t wifi_init(void) {
    const char *TAG = "wifi_init";
    wifi_config_t wifi_config;
    esp_err_t ret = ESP_OK;

    ESP_LOGD(TAG, "ESP_WIFI_MODE_AP");
    tcpip_adapter_init();
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    // set wifi to defaults
    wifi_init_config_t init_config = WIFI_INIT_CONFIG_DEFAULT();

    // initialize wifi
    ESP_ERROR_CHECK(esp_wifi_init(&init_config));

    // check for wifi parameters saved in nvs
    ESP_ERROR_CHECK(esp_wifi_get_config(ESP_IF_WIFI_AP, &wifi_config));
    // see if it's likely that wifi data in nvs is good
    ESP_LOGI(TAG,
             "nvs wifi ssid_len <%d>, ssid <%s>, strlen(ssid) <%d>, and "
             "password <%s>",
             wifi_config.ap.ssid_len, (char *)wifi_config.ap.ssid,
             strlen((char *)wifi_config.ap.ssid),
             (char *)wifi_config.ap.password);
    if (strlen((char *)wifi_config.ap.password) > 0 &&
        wifi_config.ap.ssid_len > 0 &&
        wifi_config.ap.ssid_len == strlen((char *)wifi_config.ap.ssid)) {
        ESP_LOGI(TAG, "nvs wifi info used:  ssid <%s>, pass <%s>",
                 (char *)wifi_config.ap.ssid, (char *)wifi_config.ap.password);
    } else {
        strcpy((char *)wifi_config.ap.ssid, DEFAULT_WIFI_SSID);
        wifi_config.ap.ssid_len = strlen(DEFAULT_WIFI_SSID);
        strcpy((char *)wifi_config.ap.password, DEFAULT_WIFI_PASS);
        wifi_config.ap.max_connection = DEFAULT_STA_CONN;
        wifi_config.ap.authmode = WIFI_AUTH_WPA_WPA2_PSK;

        ESP_LOGI(TAG, "default parms:  ssid <%s>, pass <%s>",
                 (char *)wifi_config.ap.ssid, (char *)wifi_config.ap.password);
        if (strlen(DEFAULT_WIFI_PASS) == 0) {
            wifi_config.ap.authmode = WIFI_AUTH_OPEN;
        }

        ret = esp_wifi_set_config(ESP_IF_WIFI_AP, &wifi_config);
        if (ret != ESP_OK) {
            ESP_LOGE(TAG, "set_config failed with ret <%d>", ret);
        }
    }

    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, ESP_EVENT_ANY_ID,
                                               &wifi_event_handler, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID,
                                               &wifi_event_handler, NULL));

    /*
    ESP_ERROR_CHECK(esp_event_handler_register(
        ESP_EVENT_ANY_BASE, ESP_EVENT_ANY_ID, all_event_handler, NULL));
*/

    ret = esp_wifi_start();
    ESP_LOGI(TAG,
             "wifi init started ret <%d>, ssid_len <%d>, ssid <%s>, "
             "strlen(ssid) <%d>, and password <%s>",
             ret, wifi_config.ap.ssid_len, (char *)wifi_config.ap.ssid,
             strlen((char *)wifi_config.ap.ssid),
             (char *)wifi_config.ap.password);
    return (ret);
}

#endif // SOFTAP

#ifdef APP_MAIN
void app_main() {
    ESP_ERROR_CHECK(nvs_flash_init());
    ESP_LOGI(wifi_TAG, "ESP_WIFI_MODE_AP");
    wifi_init();
}
#endif // APP_MAIN
