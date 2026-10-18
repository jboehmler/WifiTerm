#include "esp_err.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include <string.h>

#define NVSPRINTLEN 8

/*
char *appendstr(char *dest, char *src) {
    while (*dest) {
        dest++;
    }
    while (*dest++ = *src++);
    while (*dest++ = *src++);
    return --dest;
}
*/

esp_err_t nvserrlog(const char *CALLER, const char *p_msg, esp_err_t err) {
    // nvserrlog(CALLER, msg, err);
    if (err == ESP_OK) {
        ESP_LOGD(CALLER, "<%s> ESP_OK", p_msg);
        return (ESP_OK);
    }
    ESP_LOGD(CALLER, "<%s> err <0x%x>", p_msg, err);
    return (err);
}

void nvsprintblob(const char *CALLER, void *p_blob, size_t blobsize) {
    void *pblob = p_blob;

    printf("%s:  nvsprintblob size <%i>", CALLER, blobsize);
    for (int i = 0; i < blobsize; i++) {
        if ((i % NVSPRINTLEN) == 0) { // CRLF every NVSPRINTLEN bytes
            printf("\r\n");
        }

        printf(" %02x", *(char *)pblob);
        pblob++;
    }
    printf("\r\n");
}

void *nvsclearblob(const char *CALLER, void *p_blob, size_t blobsize) {
    ESP_LOGD(CALLER, "nvsclearblob size <%i>", blobsize);
    memset(p_blob, 0, blobsize);
    return (p_blob);
}

void *nvscopyblob(const char *CALLER, void *p_destblob, void *p_srcblob,
                  size_t blobsize) {
    ESP_LOGD(CALLER, "nvscopyblob size <%i>", blobsize);
    memcpy(p_destblob, p_srcblob, blobsize);
    return (p_destblob);
}

esp_err_t nvsopen(const char *CALLER, const char *namespace,
                  nvs_open_mode_t mode, nvs_handle_t *p_nvs_handle) {
    // char *caller = NULL;
    esp_err_t err;
    *p_nvs_handle = 0;

    ESP_LOGD(CALLER, "nvsopen");
    ESP_LOGD(CALLER, "before nvs_open namespace <%s>, mode <%i>, handle <%u>",
             namespace, mode, *p_nvs_handle);
    err = nvs_open(namespace, mode, p_nvs_handle);
    ESP_LOGD(
        CALLER,
        "after nvs_open namespace <%s>, mode <%i>, handle <%u>, err <0x%x>",
        namespace, mode, *p_nvs_handle, err);
    if (err != ESP_OK) {
        nvserrlog(CALLER, "nvs_open failed err", err);
    }
    if (*p_nvs_handle == 0) {
        ESP_LOGD(CALLER, "nvs_open failed invalid handle");
        return (ESP_ERR_NVS_INVALID_LENGTH);
    }
    ESP_LOGD(CALLER, "nvsopen done");
    return (err);
}

esp_err_t nvsgetblobsize(const char *CALLER, nvs_handle_t nvs_handle,
                         const char *p_keyname, size_t *p_blobsize) {
    esp_err_t err;

    ESP_LOGD(CALLER, "nvsgetblobsize");
    err = nvs_get_blob(nvs_handle, p_keyname, NULL, p_blobsize);
    ESP_LOGD(CALLER, "nvs_get_blob key <%s>, handle <%u>, err <0x%x>",
             p_keyname, nvs_handle, err);
    if (err != ESP_OK) {
        nvserrlog(CALLER, "error on nvs_get_blob getting blob size", err);
        if (err == ESP_ERR_NVS_NOT_FOUND) {
            nvserrlog(CALLER, "NVS NOT FOUND", err);
        }
        nvserrlog(CALLER, "nvs_get_blob size failed", err);
        return (err);
    }
    if (*p_blobsize == 0) {
        ESP_LOGD(CALLER, "nvsgetblobsize ZERO");
        return (ESP_ERR_NVS_INVALID_LENGTH);
    }
    ESP_LOGD(CALLER, "nvsgetblobsize done");
    return (err);
}

esp_err_t nvsgetblob(const char *CALLER, nvs_handle_t nvs_handle,
                     const char *p_keyname, void *p_blob, size_t *p_blobsize) {
    esp_err_t err;

    ESP_LOGD(CALLER, "nvsgetblob");
    if (p_blob == NULL || *p_blobsize == 0) {
        ESP_LOGD(CALLER, "nvsgetblobsize keyname <%s>, size <%i>", p_keyname,
                 *p_blobsize);
        err = nvsgetblobsize(CALLER, nvs_handle, p_keyname, p_blobsize);
        ESP_LOGD(CALLER, "nvsgetblobsize keyname <%s>, size <%i>, err <0x%x>",
                 p_keyname, *p_blobsize, err);
        if (err != ESP_OK) {
            nvserrlog(CALLER, "error on nvsgetblobsize", err);
            if (err == ESP_ERR_NVS_NOT_FOUND) {
                nvserrlog(CALLER, "NVS NOT FOUND", err);
            }
            nvserrlog(CALLER, "nvs_get_blob failed", err);
        }
        if (p_blob == NULL) {
            nvserrlog(CALLER, "nvsgetblobsize NULL blob", err);
            return (err); // blob == NULL is request for blob size only
        }
    }
    nvsclearblob(CALLER, p_blob, *p_blobsize);
    // nvsprintblob(CALLER, blob, *p_blobsize);
    err = nvs_get_blob(nvs_handle, p_keyname, p_blob, p_blobsize);
    ESP_LOGD(CALLER, "nvs_get_blob keyname <%s>, size <%i>, err <0x%x>",
             p_keyname, *p_blobsize, err);
    if (err != ESP_OK) {
        ESP_LOGD(CALLER, "error on nvs_get_blob");
        if (err == ESP_ERR_NVS_NOT_FOUND) {
            ESP_LOGD(CALLER, "NVS NOT FOUND");
        }
        nvserrlog(CALLER, "nvs_get_blob failed", err);
    }
    // nvsprintblob(CALLER, blob, *p_blobsize);
    ESP_LOGD(CALLER, "nvsgetblob done");
    return (err);
}

esp_err_t nvssetblob(const char *CALLER, nvs_handle_t nvs_handle,
                     const char *p_keyname, void *p_blob, size_t blobsize) {
    esp_err_t err;

    ESP_LOGD(CALLER, "nvssetblob");
    ESP_LOGD(CALLER, "nvssetblob keyname <%s>, size <%i>", p_keyname, blobsize);
    // nvsprintblob(CALLER, blob, blobsize);
    err = nvs_set_blob(nvs_handle, p_keyname, p_blob, blobsize);
    ESP_LOGD(CALLER, "nvs_set_blob keyname <%s>, size <%i>, err <0x%x>",
             p_keyname, blobsize, err);
    if (err != ESP_OK) {
        nvserrlog(CALLER, "nvs_set_blob failed", err);
    }
    ESP_LOGD(CALLER, "nvssetblob done");
    return (err);
}

esp_err_t nvscommit(const char *CALLER, nvs_handle_t nvs_handle) {
    esp_err_t err;

    // Commit
    ESP_LOGD(CALLER, "nvscommit");
    err = nvs_commit(nvs_handle);
    if (err != ESP_OK) {
        nvserrlog(CALLER, "nvs_commit failed", err);
    }
    ESP_LOGD(CALLER, "nvscommit done");
    return (err);
}

esp_err_t nvsclose(const char *CALLER, nvs_handle_t nvs_handle) {
    // Close
    ESP_LOGD(CALLER, "nvsclose");
    nvs_close(nvs_handle);
    ESP_LOGD(CALLER, "nvsclose done");
    return (ESP_OK);
}

const char *TAG_nvsreadblob = "nvsreadblob";
esp_err_t nvsreadblob(const char *CALLER, const char *namespace,
                      const char *p_keyname, void *p_blob, size_t *p_blobsize) {
    esp_err_t err;
    nvs_handle_t nvs_handle = 0;

    ESP_LOGD(TAG_nvsreadblob, "namespace <%s>, mode <%i>, nvs_handle <%i>",
             namespace, NVS_READWRITE, nvs_handle);
    err = nvsopen(TAG_nvsreadblob, namespace, NVS_READONLY, &nvs_handle);
    nvserrlog(CALLER, "nvsreadblob nvsopen", err);
    if (err != ESP_OK) {
        nvserrlog(CALLER, "nvsreadblob nvsopen failed", err);
        return (err);
    }

    nvsclearblob(CALLER, p_blob, *p_blobsize);
    err =
        nvsgetblob(TAG_nvsreadblob, nvs_handle, p_keyname, p_blob, p_blobsize);
    nvserrlog(CALLER, "nvsreadblob nvsgetblob", err);
    if (err != ESP_OK) {
        nvserrlog(CALLER, "nvsreadblob nvsgetblob failed", err);
        return (err);
    }

    // nvsprintblob(CALLER, p_blob, *p_blobsize);
    // ESP_LOGD(TAG_nvsreadblob, "nvsgetblob blob <%s>", TESTstr(teststr,
    // &blob));
    nvsclose(TAG_nvsreadblob, nvs_handle);
    nvserrlog(CALLER, "nvsreadblob nvsclose", err);
    if (err != ESP_OK) {
        nvserrlog(CALLER, "nvsreadblob nvsclose failed", err);
        return (err);
    }

    return (err);
}

const char *TAG_nvswriteblob = "nvswriteblob";
esp_err_t nvswriteblob(const char *CALLER, const char *namespace,
                       const char *p_keyname, void *p_blob, size_t blobsize) {
    esp_err_t err;
    nvs_handle_t nvs_handle = 0;

    ESP_LOGD(CALLER, "namespace <%s>, mode <%i>, nvs_handle <%i>", namespace,
             NVS_READWRITE, nvs_handle);
    err = nvsopen(TAG_nvswriteblob, namespace, NVS_READWRITE, &nvs_handle);
    nvserrlog(CALLER, "nvswriteblob nvsopen", err);
    if (err != ESP_OK) {
        nvserrlog(CALLER, "nvswriteblob nvsopen failed", err);
        return (err);
    }

    // nvsprintblob(CALLER, blob, blobsize);
    err = nvssetblob(TAG_nvswriteblob, nvs_handle, p_keyname, p_blob, blobsize);
    nvserrlog(CALLER, "nvswriteblob nvssetblob", err);
    if (err != ESP_OK) {
        nvserrlog(CALLER, "nvswriteblob nvssetblob failed", err);
        return (err);
    }

    err = nvscommit(TAG_nvswriteblob, nvs_handle);
    nvserrlog(CALLER, "nvswriteblob nvscommit", err);
    if (err != ESP_OK) {
        nvserrlog(CALLER, "nvswriteblob nvscommit failed", err);
        return (err);
    }

    nvsclose(TAG_nvswriteblob, nvs_handle);
    nvserrlog(CALLER, "nvswriteblob nvsclose", err);
    if (err != ESP_OK) {
        nvserrlog(CALLER, "nvswriteblob nvsclose failed", err);
        return (err);
    }

    return (err);
}
