/**
 * @file statusled.c
 * @brief Green state LED driver. See statusled.h.
 */
#include "statusled.h"

#include "config.h"
#include "driver/gpio.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "led.h"

static led_t s_led;           /**< Pattern state. */
static int s_booted;          /**< statusled_booted() was called. */
static int s_stations;        /**< Stations on the access point. */
static int s_session;         /**< Terminal session up. */
static int s_off;             /**< statusled_off() was called. */
static int s_level = -1;      /**< Pin level last written. */

/** @brief Milliseconds since boot. */
static uint32_t ms_now(void) { return (uint32_t)(esp_timer_get_time() / 1000); }

/** @brief Recompute the state from what is known. Call inside a critical section. */
static void update_state(void)
{
    int st = !s_booted ? LED_BOOT : s_session ? LED_TERM : s_stations > 0 ? LED_WAIT_TERM : LED_WAIT_WIFI;
    led_set_state(&s_led, st, ms_now());
}

/** @brief 10 ms tick: write the pattern's level to the pin when it changes. */
static void tick(void *arg)
{
    (void)arg;
    taskENTER_CRITICAL();
    int v = s_off ? 0 : led_level(&s_led, ms_now());
    taskEXIT_CRITICAL();
    if (v != s_level) {
        gpio_set_level(PIN_STATE_LED, (uint32_t)v);
        s_level = v;
    }
}

void statusled_init(int bat_quarters)
{
    gpio_config_t io = {
        .pin_bit_mask = 1UL << PIN_STATE_LED,
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&io);
    led_init(&s_led, ms_now(), bat_quarters);
    tick(NULL);
    const esp_timer_create_args_t args = {.callback = tick, .name = "statusled"};
    esp_timer_handle_t t;
    if (esp_timer_create(&args, &t) == ESP_OK) {
        esp_timer_start_periodic(t, 10000);
    }
}

void statusled_booted(void)
{
    taskENTER_CRITICAL();
    s_booted = 1;
    update_state();
    taskEXIT_CRITICAL();
}

void statusled_station(int delta)
{
    taskENTER_CRITICAL();
    s_stations += delta;
    if (s_stations < 0) {
        s_stations = 0;
    }
    update_state();
    taskEXIT_CRITICAL();
}

void statusled_session(int up)
{
    taskENTER_CRITICAL();
    s_session = up;
    update_state();
    taskEXIT_CRITICAL();
}

void statusled_fail(int step, uint32_t hold_ms)
{
    taskENTER_CRITICAL();
    led_fail(&s_led, step, ms_now(), hold_ms);
    taskEXIT_CRITICAL();
}

void statusled_traffic(void)
{
    taskENTER_CRITICAL();
    led_traffic(&s_led, ms_now());
    taskEXIT_CRITICAL();
}

void statusled_off(void)
{
    s_off = 1;
}
