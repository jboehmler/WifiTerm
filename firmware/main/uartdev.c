/**
 * @file uartdev.c
 * @brief Device UART. See uartdev.h. The UART in use is DEVICE_UART (UART0) with
 *        uart_enable_swap(): RX = GPIO13 (D7), TX = GPIO15 (D8).
 */
#include "uartdev.h"

#include <string.h>

/* FreeRTOS first: driver/uart.h uses its types. */
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"

#include "config.h"
#include "driver/gpio.h"
#include "driver/uart.h"
#include "esp8266/uart_struct.h"
#include "esp_log.h"

static const char *TAG = "uartdev";

static QueueHandle_t s_events;          /**< UART driver event queue. */
static TickType_t s_last_event[3];      /**< Last report time per event kind (rate limit). */
static uint32_t s_event_pending;        /**< Bit per kind: reported but not yet sent. */
static int s_powered;                   /**< RS-232 chip on (TX released) or off (TX held low). */

/** @brief Event kinds, as bits in s_event_pending. */
enum { EV_OVERFLOW = 0, EV_FRAME = 1, EV_PARITY = 2 };

/** @brief EVENT texts, indexed by kind. */
static const char *const EV_TEXT[] = {"uart overflow", "uart frame-error", "uart parity-error"};

int uartdev_init_console(void)
{
    uart_config_t uc = {
        .baud_rate = LOG_BAUD,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
    };
    if (uart_param_config(DEVICE_UART, &uc) != ESP_OK ||
        uart_driver_install(DEVICE_UART, UART_RX_BUF, UART_TX_BUF, 16, &s_events, 0) != ESP_OK) {
        ESP_LOGE(TAG, "UART0 driver install failed");
        return -1;
    }
    return 0;
}

int uartdev_console_getc(unsigned ms)
{
    uint8_t c;
    return uart_read_bytes(DEVICE_UART, &c, 1, pdMS_TO_TICKS(ms)) == 1 ? c : -1;
}

void uartdev_console_puts(const char *s)
{
    uart_write_bytes(DEVICE_UART, s, strlen(s));
    uart_wait_tx_done(DEVICE_UART, pdMS_TO_TICKS(500));
}

int uartdev_apply(const uart_cfg_t *c)
{
    static const uart_word_length_t bits[] = {UART_DATA_5_BITS, UART_DATA_6_BITS, UART_DATA_7_BITS,
                                              UART_DATA_8_BITS};
    uart_config_t uc = {
        .baud_rate = (int)c->baud,
        .data_bits = bits[c->bits - 5],
        .parity = c->parity == 'E' ? UART_PARITY_EVEN : (c->parity == 'O' ? UART_PARITY_ODD : UART_PARITY_DISABLE),
        .stop_bits = c->stop2 == 3 ? UART_STOP_BITS_1_5 : (c->stop2 == 4 ? UART_STOP_BITS_2 : UART_STOP_BITS_1),
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE, /* xonxoff is done in bridge.c; rtscts later */
    };
    if (!uart_cfg_valid(c)) {
        return -1;
    }
    uart_wait_tx_done(DEVICE_UART, pdMS_TO_TICKS(1000));
    if (uart_param_config(DEVICE_UART, &uc) != ESP_OK) {
        return -1;
    }
    char t[40];
    ESP_LOGI(TAG, "device UART %s", uart_cfg_text(c, t, sizeof t));
    return 0;
}

int uartdev_start(const uart_cfg_t *c)
{
    uart_wait_tx_done(DEVICE_UART, pdMS_TO_TICKS(500));
    if (uartdev_apply(c)) {
        return -1;
    }
    uart_enable_swap(); /* UART0 now on GPIO13 (RX, D7) / GPIO15 (TX, D8) */
    uart_flush_input(DEVICE_UART);
    xQueueReset(s_events);
    return 0;
}

int uartdev_read(uint8_t *buf, size_t n)
{
    int got = uart_read_bytes(DEVICE_UART, buf, n, 0);
    return got > 0 ? got : 0;
}

int uartdev_write(const uint8_t *buf, size_t n)
{
    int sent = uart_write_bytes(DEVICE_UART, (const char *)buf, n);
    return sent > 0 ? sent : 0;
}

size_t uartdev_rx_pending(void)
{
    size_t n = 0;
    uart_get_buffered_data_len(DEVICE_UART, &n);
    return n;
}

int uartdev_break(unsigned ms)
{
    uart_wait_tx_done(DEVICE_UART, pdMS_TO_TICKS(2000));
    uart0.conf0.txd_brk = 1; /* hold TX at space (0) */
    vTaskDelay(pdMS_TO_TICKS(ms));
    uart0.conf0.txd_brk = s_powered ? 0 : 1; /* stay low if the chip was switched off meanwhile */
    return 0;
}

int uartdev_cable_valid(void)
{
#if HAVE_CABLE_DETECT
    static int configured;
    if (!configured) {
        /* INVALID is a push-pull output of the chip, so no pull resistor is needed. */
        gpio_config_t io = {
            .pin_bit_mask = 1UL << PIN_CABLE_DETECT,
            .mode = GPIO_MODE_INPUT,
            .pull_up_en = GPIO_PULLUP_DISABLE,
            .pull_down_en = GPIO_PULLDOWN_DISABLE,
            .intr_type = GPIO_INTR_DISABLE,
        };
        gpio_config(&io);
        configured = 1;
    }
    return gpio_get_level(PIN_CABLE_DETECT) == CABLE_VALID_LEVEL;
#else
    return 0;
#endif
}

int uartdev_power(int on)
{
#if HAVE_CHIP_POWER
    static int configured;
    if (!configured) {
        gpio_config_t io = {
            .pin_bit_mask = 1UL << PIN_CHIP_POWER,
            .mode = GPIO_MODE_OUTPUT,
            .pull_up_en = GPIO_PULLUP_DISABLE,
            .pull_down_en = GPIO_PULLDOWN_DISABLE,
            .intr_type = GPIO_INTR_DISABLE,
        };
        /* Set the level first so the pin never glitches to "on". */
        gpio_set_level(PIN_CHIP_POWER, CHIP_POWER_ON_LEVEL ? 0 : 1);
        gpio_config(&io);
        configured = 1;
    }
    /* With the chip off, hold device TX (D8) low: an idle-high TX would otherwise feed a chip
     * powered from a GPIO through its input pin and keep it half running (NOTES I-19). */
    if (!on) {
        uart_wait_tx_done(DEVICE_UART, pdMS_TO_TICKS(1000));
        uart0.conf0.txd_brk = 1;
    }
    gpio_set_level(PIN_CHIP_POWER, on ? CHIP_POWER_ON_LEVEL : !CHIP_POWER_ON_LEVEL);
    if (on) {
        uart0.conf0.txd_brk = 0;
    }
    s_powered = on;
    ESP_LOGI(TAG, "RS-232 chip power %s", on ? "on" : "off");
    return 0;
#else
    (void)on;
    return -1;
#endif
}

int uartdev_event(char *text, size_t n)
{
    uart_event_t ev;
    TickType_t now = xTaskGetTickCount();

    while (s_events && xQueueReceive(s_events, &ev, 0) == pdTRUE) {
        int kind = -1;
        switch (ev.type) {
        case UART_FIFO_OVF:
        case UART_BUFFER_FULL:
            kind = EV_OVERFLOW;
            uart_flush_input(DEVICE_UART); /* the driver stops receiving until flushed */
            xQueueReset(s_events);
            break;
        case UART_FRAME_ERR:
            kind = EV_FRAME;
            break;
        case UART_PARITY_ERR:
            kind = EV_PARITY;
            break;
        default:
            break;
        }
        if (kind >= 0) {
            s_event_pending |= 1u << kind;
        }
    }
    for (int k = 0; k < 3; k++) {
        if ((s_event_pending & (1u << k)) && (now - s_last_event[k]) >= pdMS_TO_TICKS(1000)) {
            s_event_pending &= ~(1u << k);
            s_last_event[k] = now;
            strncpy(text, EV_TEXT[k], n - 1);
            text[n - 1] = 0;
            ESP_LOGW(TAG, "%s", text);
            return 1;
        }
    }
    return 0;
}
