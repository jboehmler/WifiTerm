/**
 * @file ota.c
 * @brief Flash slots, hashing, signature and trial boots for the firmware update. See ota.h.
 */
#include "ota.h"

#include <stdio.h>
#include <string.h>

#include "config.h"
#include "esp_log.h"
#include "esp_ota_ops.h"
#include "esp_partition.h"
#include "esp_system.h"
#include "mbedtls/pk.h"
#include "mbedtls/sha256.h"
#include "settings.h"

static const char *TAG = "ota";

/* fw-sign.pub, embedded by component.mk (NUL-terminated, so PEM parses with the NUL). */
extern const uint8_t fw_sign_pub_start[] asm("_binary_fw_sign_pub_start");
extern const uint8_t fw_sign_pub_end[] asm("_binary_fw_sign_pub_end");

static esp_ota_handle_t s_handle;       /**< Open update, or 0. */
static const esp_partition_t *s_target; /**< Slot being written. */
static mbedtls_sha256_context s_sha;    /**< Hash of the image so far. */

/** @brief The spare slot, or NULL without the OTA layout. */
static const esp_partition_t *spare(void)
{
    const esp_partition_t *next = esp_ota_get_next_update_partition(NULL);
    return next && next != esp_ota_get_running_partition() ? next : NULL;
}

int ota_available(void)
{
    return spare() != NULL;
}

static uint32_t op_max(void *c)
{
    (void)c;
    const esp_partition_t *p = spare();
    return p ? p->size : 0;
}

static int op_sig(void *c, const uint8_t hash[32], const uint8_t *sig, size_t len)
{
    (void)c;
    mbedtls_pk_context pk;
    mbedtls_pk_init(&pk);
    int rc = mbedtls_pk_parse_public_key(&pk, fw_sign_pub_start, (size_t)(fw_sign_pub_end - fw_sign_pub_start));
    if (rc == 0) {
        rc = mbedtls_pk_verify(&pk, MBEDTLS_MD_SHA256, hash, 32, sig, len);
    } else {
        ESP_LOGE(TAG, "built-in signing key unreadable (-0x%x)", -rc);
    }
    mbedtls_pk_free(&pk);
    if (rc) {
        ESP_LOGW(TAG, "update refused: bad signature (-0x%x)", -rc);
    }
    return rc ? -1 : 0;
}

static void op_abort(void *c);

static int op_begin(void *c, uint32_t size)
{
    op_abort(c);
    s_target = spare();
    if (!s_target) {
        return -1;
    }
    ESP_LOGI(TAG, "update of %u bytes into %s: erasing", (unsigned)size, s_target->label);
    esp_err_t err = esp_ota_begin(s_target, size, &s_handle); /* erases: several seconds */
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_ota_begin: 0x%x", err);
        s_handle = 0;
        return -1;
    }
    return 0;
}

static int op_write(void *c, const uint8_t *p, size_t len)
{
    (void)c;
    esp_err_t err = s_handle ? esp_ota_write(s_handle, p, len) : ESP_FAIL;
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "esp_ota_write: 0x%x", err);
    }
    return err == ESP_OK ? 0 : -1;
}

static int op_finish(void *c)
{
    (void)c;
    esp_err_t err = esp_ota_end(s_handle); /* checks the image header and checksum */
    s_handle = 0;
    if (err == ESP_OK) {
        err = esp_ota_set_boot_partition(s_target);
    }
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "new image refused: 0x%x", err);
        return -1;
    }
    settings_trial_save(1);
    ESP_LOGI(TAG, "%s verified and set to boot (on trial)", s_target->label);
    return 0;
}

static void op_abort(void *c)
{
    (void)c;
    if (s_handle) {
        esp_ota_end(s_handle); /* no abort call in this SDK; ending frees the handle */
        s_handle = 0;
        ESP_LOGW(TAG, "update dropped");
    }
}

static void op_hstart(void *c)
{
    (void)c;
    mbedtls_sha256_init(&s_sha);
    mbedtls_sha256_starts_ret(&s_sha, 0);
}

static void op_hupdate(void *c, const uint8_t *p, size_t len)
{
    (void)c;
    mbedtls_sha256_update_ret(&s_sha, p, len);
}

static void op_hfinish(void *c, uint8_t out[32])
{
    (void)c;
    mbedtls_sha256_finish_ret(&s_sha, out);
    mbedtls_sha256_free(&s_sha);
}

static void op_status(void *c, char *buf, size_t n)
{
    (void)c;
    const esp_partition_t *run = esp_ota_get_running_partition(), *next = spare();
    int trial = settings_trial_load();
    snprintf(buf, n, "running=%s fw=%s next=%s%s", run ? run->label : "?", FW_VERSION,
             next ? next->label : "none(USB-only-layout)", trial ? " trial=yes" : "");
}

const fwup_ops_t ota_ops = {
    NULL, op_max, op_sig, op_begin, op_write, op_finish, op_abort, op_hstart, op_hupdate, op_hfinish, op_status,
};

void ota_boot_check(void)
{
    int trial = settings_trial_load();
    if (!trial) {
        return;
    }
    if (fwup_should_fall_back(trial)) {
        const esp_partition_t *prev = spare();
        settings_trial_save(0);
        if (prev && esp_ota_set_boot_partition(prev) == ESP_OK) {
            ESP_LOGE(TAG, "new firmware never accepted a client in %d boots: back to %s", FWUP_TRIAL_BOOTS,
                     prev->label);
            esp_restart();
        }
        ESP_LOGE(TAG, "cannot fall back: previous slot not bootable");
        return;
    }
    settings_trial_save(trial + 1);
    ESP_LOGW(TAG, "new firmware on trial: boot %d of %d", trial, FWUP_TRIAL_BOOTS);
}

void ota_mark_good(void)
{
    if (settings_trial_load()) {
        settings_trial_save(0);
        ESP_LOGI(TAG, "new firmware %s confirmed (client connected)", FW_VERSION);
    }
}
