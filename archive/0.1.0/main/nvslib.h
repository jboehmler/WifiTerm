#ifndef NVSLIB_H
#define NVSLIB_H

esp_err_t nvserrlog(const char *CALLER, const char *p_msg, esp_err_t err);
void nvsprintblob(const char *CALLER, void *p_blob, size_t blobsize);
void *nvsclearblob(const char *CALLER, void *blob, size_t blobsize);
void *nvscopyblob(const char *CALLER, void *destblob, void *srcblob,
                  size_t blobsize);

esp_err_t nvsopen(const char *CALLER, const char *namespace,
                  nvs_open_mode_t mode, nvs_handle_t *nvs_handle);
esp_err_t nvsgetblob(const char *CALLER, nvs_handle_t nvs_handle,
                     const char *p_keyname, void *blob, size_t *blob_size);
esp_err_t nvssetblob(const char *CALLER, nvs_handle_t nvs_handle,
                     const char *p_keyname, void *blob, size_t blob_size);
esp_err_t nvscommit(const char *CALLER, nvs_handle_t nvs_handle);
esp_err_t nvsclose(const char *CALLER, nvs_handle_t nvs_handle);

esp_err_t nvsreadblob(const char *CALLER, const char *namespace,
                      const char *p_keyname, void *blob, size_t *blobsize);
esp_err_t nvswriteblob(const char *CALLER, const char *namespace,
                       const char *p_keyname, void *blob, size_t blobsize);

#endif // NVSLIB_H
