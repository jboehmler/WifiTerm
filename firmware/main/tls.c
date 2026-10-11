/**
 * @file tls.c
 * @brief TLS server session. See tls.h. All calls come from the bridge task only (R5: no
 *        concurrent mbedtls_ssl_read/write from different tasks).
 */
#include "tls.h"

#include <string.h>

#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "lwip/sockets.h"
#include "mbedtls/ctr_drbg.h"
#include "mbedtls/entropy.h"
#include "mbedtls/error.h"
#include "mbedtls/net_sockets.h"
#include "mbedtls/ssl.h"
#include "mbedtls/x509_crt.h"

static const char *TAG = "tls";

/* Certificates embedded by component.mk (COMPONENT_EMBED_TXTFILES adds a final NUL). */
extern const uint8_t ca_crt_start[] asm("_binary_ca_crt_start");
extern const uint8_t ca_crt_end[] asm("_binary_ca_crt_end");
extern const uint8_t server_crt_start[] asm("_binary_server_crt_start");
extern const uint8_t server_crt_end[] asm("_binary_server_crt_end");
extern const uint8_t server_key_start[] asm("_binary_server_key_start");
extern const uint8_t server_key_end[] asm("_binary_server_key_end");

static mbedtls_entropy_context s_entropy;
static mbedtls_ctr_drbg_context s_drbg;
static mbedtls_x509_crt s_ca, s_cert;
static mbedtls_pk_context s_key;
static mbedtls_ssl_config s_conf;
static mbedtls_ssl_context s_ssl;
static mbedtls_net_context s_net;
static int s_active;

/** @brief Log an mbedTLS error code with its text. */
static void log_err(const char *what, int rc)
{
    char buf[80];
    mbedtls_strerror(rc, buf, sizeof buf);
    ESP_LOGW(TAG, "%s: -0x%04x %s", what, -rc, buf);
}

/**
 * @brief Certificate check hook: the clock is only a lower bound, so a certificate that
 *        looks "not yet valid" is accepted; everything else (expired, wrong CA) still fails.
 */
static int verify_cb(void *ctx, mbedtls_x509_crt *crt, int depth, uint32_t *flags)
{
    (void)ctx;
    (void)crt;
    if (*flags & MBEDTLS_X509_BADCERT_FUTURE) {
        ESP_LOGD(TAG, "depth %d: ignoring not-yet-valid (no real-time clock)", depth);
        *flags &= ~(uint32_t)MBEDTLS_X509_BADCERT_FUTURE;
    }
    if (*flags) {
        ESP_LOGW(TAG, "client certificate rejected at depth %d, flags 0x%x", depth, (unsigned)*flags);
    }
    return 0;
}

int tls_init(void)
{
    int rc;

    mbedtls_entropy_init(&s_entropy);
    mbedtls_ctr_drbg_init(&s_drbg);
    mbedtls_x509_crt_init(&s_ca);
    mbedtls_x509_crt_init(&s_cert);
    mbedtls_pk_init(&s_key);
    mbedtls_ssl_config_init(&s_conf);
    mbedtls_ssl_init(&s_ssl);
    mbedtls_net_init(&s_net);

    if ((rc = mbedtls_ctr_drbg_seed(&s_drbg, mbedtls_entropy_func, &s_entropy,
                                    (const unsigned char *)"wifiterm", 8)) != 0 ||
        (rc = mbedtls_x509_crt_parse(&s_ca, ca_crt_start, ca_crt_end - ca_crt_start)) != 0 ||
        (rc = mbedtls_x509_crt_parse(&s_cert, server_crt_start, server_crt_end - server_crt_start)) != 0 ||
        (rc = mbedtls_pk_parse_key(&s_key, server_key_start, server_key_end - server_key_start, NULL, 0)) != 0 ||
        (rc = mbedtls_ssl_config_defaults(&s_conf, MBEDTLS_SSL_IS_SERVER, MBEDTLS_SSL_TRANSPORT_STREAM,
                                          MBEDTLS_SSL_PRESET_DEFAULT)) != 0) {
        log_err("TLS setup", rc);
        return -1;
    }
    mbedtls_ssl_conf_rng(&s_conf, mbedtls_ctr_drbg_random, &s_drbg);
    mbedtls_ssl_conf_ca_chain(&s_conf, &s_ca, NULL);
    mbedtls_ssl_conf_authmode(&s_conf, MBEDTLS_SSL_VERIFY_REQUIRED); /* R12 */
    mbedtls_ssl_conf_verify(&s_conf, verify_cb, NULL);
    mbedtls_ssl_conf_min_version(&s_conf, MBEDTLS_SSL_MAJOR_VERSION_3, MBEDTLS_SSL_MINOR_VERSION_3);
    if ((rc = mbedtls_ssl_conf_own_cert(&s_conf, &s_cert, &s_key)) != 0 ||
        (rc = mbedtls_ssl_setup(&s_ssl, &s_conf)) != 0) {
        log_err("TLS config", rc);
        return -1;
    }
    ESP_LOGI(TAG, "TLS ready, client certificate required");
    return 0;
}

int tls_start(int fd, unsigned timeout_ms)
{
    struct timeval tv = {.tv_sec = timeout_ms / 1000, .tv_usec = (timeout_ms % 1000) * 1000};
    int rc;

    s_net.fd = fd;
    /* Handshake on a blocking socket with a time limit, then switch to non-blocking. */
    setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv);
    setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof tv);
    mbedtls_ssl_session_reset(&s_ssl);
    mbedtls_ssl_set_bio(&s_ssl, &s_net, mbedtls_net_send, mbedtls_net_recv, NULL);
    while ((rc = mbedtls_ssl_handshake(&s_ssl)) != 0) {
        if (rc != MBEDTLS_ERR_SSL_WANT_READ && rc != MBEDTLS_ERR_SSL_WANT_WRITE) {
            log_err("handshake", rc);
            uint32_t flags = mbedtls_ssl_get_verify_result(&s_ssl);
            if (flags && flags != (uint32_t)-1) {
                char why[120];
                mbedtls_x509_crt_verify_info(why, sizeof why, "", flags);
                ESP_LOGW(TAG, "client certificate: %s", why);
            }
            mbedtls_net_free(&s_net);
            return -1;
        }
    }
    mbedtls_net_set_nonblock(&s_net);
    s_active = 1;
    ESP_LOGI(TAG, "session up (%s, %s)", mbedtls_ssl_get_version(&s_ssl), mbedtls_ssl_get_ciphersuite(&s_ssl));
    return 0;
}

int tls_fd(void)
{
    return s_active ? s_net.fd : -1;
}

int tls_pending(void)
{
    return s_active && mbedtls_ssl_get_bytes_avail(&s_ssl) > 0;
}

int tls_read(uint8_t *buf, size_t n)
{
    int rc = mbedtls_ssl_read(&s_ssl, buf, n);

    if (rc > 0) {
        return rc;
    }
    if (rc == MBEDTLS_ERR_SSL_WANT_READ || rc == MBEDTLS_ERR_SSL_WANT_WRITE) {
        return 0;
    }
    if (rc == 0 || rc == MBEDTLS_ERR_SSL_PEER_CLOSE_NOTIFY) {
        ESP_LOGI(TAG, "client closed the session");
    } else {
        log_err("read", rc);
    }
    return -1;
}

int tls_write(const uint8_t *buf, size_t n, unsigned timeout_ms)
{
    TickType_t start = xTaskGetTickCount();

    while (n) {
        int rc = mbedtls_ssl_write(&s_ssl, buf, n);
        if (rc > 0) {
            buf += rc;
            n -= (size_t)rc;
        } else if (rc == MBEDTLS_ERR_SSL_WANT_WRITE || rc == MBEDTLS_ERR_SSL_WANT_READ) {
            if (xTaskGetTickCount() - start > pdMS_TO_TICKS(timeout_ms)) {
                ESP_LOGW(TAG, "client not reading for %u ms", timeout_ms);
                return -1;
            }
            vTaskDelay(1);
        } else {
            log_err("write", rc);
            return -1;
        }
    }
    return 0;
}

void tls_close(void)
{
    if (!s_active) {
        return;
    }
    mbedtls_ssl_close_notify(&s_ssl);
    mbedtls_net_free(&s_net);
    s_active = 0;
}
