#include "ssl.h"

#include "mbedtls/ctr_drbg.h"
#include "mbedtls/debug.h"
#include "mbedtls/entropy.h"
#include "mbedtls/error.h"
#include "mbedtls/platform.h"
#include "mbedtls/x509.h"

extern const uint8_t ca_crt_start[] asm("_binary_ca_crt_start");
extern const uint8_t ca_crt_end[] asm("_binary_ca_crt_end");
extern const uint8_t server_crt_start[] asm("_binary_server_crt_start");
extern const uint8_t server_crt_end[] asm("_binary_server_crt_end");
extern const uint8_t server_key_start[] asm("_binary_server_key_start");
extern const uint8_t server_key_end[] asm("_binary_server_key_end");

#define mbedtls_test_srv_crt server_crt_start
#define mbedtls_test_srv_crt_len server_crt_end - server_crt_start
#define mbedtls_test_cas_crt ca_crt_start
#define mbedtls_test_cas_crt_len ca_crt_end - ca_crt_start
#define mbedtls_test_srv_key server_key_start
#define mbedtls_test_srv_key_len server_key_end - server_key_start

static const char *pers = "ssl_server"; // used for ssl seed

static mbedtls_entropy_context entropy;
static mbedtls_net_context listen_fd, client_fd;
static mbedtls_ctr_drbg_context ctr_drbg;

static mbedtls_ssl_config conf;
// static mbedtls_x509_crt cacert;  //no longer used as srvcert includes ca cert
// in chain
static mbedtls_x509_crt srvcert;
static mbedtls_pk_context pkey;

mbedtls_ssl_context ssl;

/*
********************************************************************************************
*/
void ssl_init(SSL_DATA *ssldata, uint8_t *sslread_buf, int sslread_buf_size,
              uint8_t *sslwrite_buf, int sslwrite_buf_size) {
    ssldata->readbuf.data = sslread_buf;
    ssldata->readbuf.maxlen = sslread_buf_size;
    ssldata->writebuf.data = sslwrite_buf;
    ssldata->writebuf.maxlen = sslwrite_buf_size;
}

SSL_STATE ssl_start(SSL_DATA *ssldata) {
    static const char *TAG = "ssl_start";

    ESP_LOGD(TAG, "Starting ssl_start...");

    ssldata->retval = 0;
    ssldata->len = 0;
    ssldata->state = SSL_START;

    mbedtls_net_init(&listen_fd);
    mbedtls_net_init(&client_fd);
    mbedtls_ssl_init(&ssl);
    mbedtls_ssl_config_init(&conf);
    mbedtls_x509_crt_init(&srvcert);
    mbedtls_pk_init(&pkey);
    mbedtls_entropy_init(&entropy);
    mbedtls_ctr_drbg_init(&ctr_drbg);

    /*
     * 1. Load the certificates and private RSA key
     */
    ESP_LOGD(TAG, "Loading the server cert...");
    ssldata->retval = mbedtls_x509_crt_parse(
        &srvcert, (const unsigned char *)mbedtls_test_srv_crt,
        mbedtls_test_srv_crt_len);
    if (ssldata->retval != 0) {
        ESP_LOGE(TAG,
                 "Loading the server cert failed\n  !  mbedtls_x509_crt_parse "
                 "returned -0x%X\n\n",
                 -ssldata->retval);
        return (SSL_EXIT);
    }
    ESP_LOGD(TAG, " ok\n");

    ESP_LOGD(TAG, "Loading the ca cert...");
    ssldata->retval = mbedtls_x509_crt_parse(
        &srvcert, (const unsigned char *)mbedtls_test_cas_crt,
        mbedtls_test_cas_crt_len);

    if (ssldata->retval != 0) {
        ESP_LOGE(TAG,
                 "Loading the CA cert failed\n  !  mbedtls_x509_crt_parse "
                 "returned -0x%X\n\n",
                 -ssldata->retval);
        return (SSL_EXIT);
    }
    ESP_LOGD(TAG, " ok\n");

    ESP_LOGD(TAG, "Loading the server key...");
    ssldata->retval =
        mbedtls_pk_parse_key(&pkey, (const unsigned char *)mbedtls_test_srv_key,
                             mbedtls_test_srv_key_len, NULL, 0);
    if (ssldata->retval != 0) {
        ESP_LOGE(TAG,
                 "Loading the server key failed\n  !  mbedtls_pk_parse_key "
                 "returned -0x%X\n\n",
                 -ssldata->retval);
        return (SSL_EXIT);
    }
    ESP_LOGD(TAG, " ok\n");

    /*
     * 3. Seed the RNG
     */
    ESP_LOGD(TAG, "Seeding the random number generator...");
    if ((ssldata->retval = mbedtls_ctr_drbg_seed(
             &ctr_drbg, mbedtls_entropy_func, &entropy,
             (const unsigned char *)pers, strlen((char *)pers))) != 0) {
        ESP_LOGE(TAG,
                 "Seeding the random number generator failed\n  ! "
                 "mbedtls_ctr_drbg_seed returned -0x%X\n",
                 -ssldata->retval);
        return (SSL_EXIT);
    }
    ESP_LOGD(TAG, " ok\n");

    /*
     * 4. Setup stuff
     */
    ;
    ESP_LOGD(TAG, "Setting up the SSL data....");
    if ((ssldata->retval = mbedtls_ssl_config_defaults(
             &conf, MBEDTLS_SSL_IS_SERVER, MBEDTLS_SSL_TRANSPORT_STREAM,
             MBEDTLS_SSL_PRESET_DEFAULT)) != 0) {
        ESP_LOGE(TAG,
                 "Setting up the SSL config failed\n  ! "
                 "mbedtls_ssl_config_defaults returned -0x%X\n\n",
                 -ssldata->retval);
        return (SSL_EXIT);
    }
    ESP_LOGD(TAG, " ok\n");

    mbedtls_ssl_conf_rng(&conf, mbedtls_ctr_drbg_random, &ctr_drbg);

    ESP_LOGD(TAG, "Setting up the ca cert chain....");
    mbedtls_ssl_conf_ca_chain(&conf, srvcert.next, NULL);
    if ((ssldata->retval = mbedtls_ssl_conf_own_cert(&conf, &srvcert, &pkey)) !=
        0) {
        ESP_LOGE(TAG,
                 "Setting up the SSL data failed\n  ! "
                 "mbedtls_ssl_conf_own_cert returned -0x%X\n\n",
                 -ssldata->retval);
        return (SSL_EXIT);
    }
    ESP_LOGD(TAG, " ok\n");

    ESP_LOGD(TAG, "Setting up the SSL data....");
    if ((ssldata->retval = mbedtls_ssl_setup(&ssl, &conf)) != 0) {
        ESP_LOGE(TAG,
                 "Setting up the SSL data failed\n  ! mbedtls_ssl_setup "
                 "returned -0x%X\n\n",
                 -ssldata->retval);
        return (SSL_EXIT);
    }
    ESP_LOGD(TAG, " ok\n");

    /*
     * 2. Setup the listening TCP socket
     */
    ESP_LOGD(TAG, "Bind on https://%s:%s/ ...", HOST, PORT);
    if ((ssldata->retval = mbedtls_net_bind(&listen_fd, NULL, PORT,
                                            MBEDTLS_NET_PROTO_TCP)) != 0) {
        ESP_LOGE(TAG,
                 "Bind on https://%s:%s/ failed\n  ! mbedtls_net_bind returned "
                 "%X\n\n",
                 HOST, PORT, -ssldata->retval);
        return (SSL_EXIT);
    }
    ESP_LOGD(TAG, " ok\n");

    return (SSL_CONN);
}

/*
********************************************************************************************
*/
SSL_STATE ssl_conn(SSL_DATA *ssldata) {
    static const char *TAG = "ssl_reset";

    ESP_LOGD(TAG, "Starting ssl_reset...");

    ssldata->retval = 0;
    ssldata->len = 0;
    // ESP_LOGD(TAG, "ssldata->retval:  -0x%X\n\n", -ssldata->retval);
    //  RESET LOOP ********
    //  reset:

    mbedtls_net_free(&client_fd);
    mbedtls_ssl_session_reset(&ssl);

    /*
     * 5. Wait until a client connects
     */
    ESP_LOGD(TAG, "Waiting for a remote connection ...");
    if ((ssldata->retval =
             mbedtls_net_accept(&listen_fd, &client_fd, NULL, 0, NULL)) != 0) {
        ESP_LOGD(TAG,
                 "Waiting for a remote connection => connection failed\n  ! "
                 "mbedtls_net_accept returned -0x%X\n\n",
                 -ssldata->retval);
        return (SSL_EXIT);
    }

    mbedtls_ssl_set_bio(&ssl, &client_fd, mbedtls_net_send, mbedtls_net_recv,
                        NULL);
    ESP_LOGD(TAG, " ok\n");

    /*
     * 6. Handshake
     */
    ESP_LOGD(TAG, "Performing the SSL/TLS handshake...");

    while ((ssldata->retval = mbedtls_ssl_handshake(&ssl)) != 0) {
        if (ssldata->retval != MBEDTLS_ERR_SSL_WANT_READ &&
            ssldata->retval != MBEDTLS_ERR_SSL_WANT_WRITE) {
            ;
            ESP_LOGE(TAG,
                     "Performing the SSL/TLS handshake failed\n  ! "
                     "mbedtls_ssl_handshake returned -0x%X\n\n",
                     -ssldata->retval);
            return (SSL_RESET);
        }
    }

    ESP_LOGD(TAG, "Handshake complete ok\n");
    return (SSL_RWOK);
}

/*
SSL_STATE
ssl_close(SSL_DATA* ssldata) {
    static const char *TAG = "ssl_close";

    ESP_LOGD(TAG, "Closing the connection...");

    while ((ssldata->retval = mbedtls_ssl_close_notify(&ssl)) < 0) {
        if (ssldata->retval != MBEDTLS_ERR_SSL_WANT_READ &&
            ssldata->retval != MBEDTLS_ERR_SSL_WANT_WRITE) {
            ESP_LOGE(TAG,
                     " failed\n  ! mbedtls_ssl_close_notify returned -0x%X\n\n",
                     -ssldata->retval);
            return(SSL_RESET);
        }
    }

    ESP_LOGD(TAG, " ok\n");

    return(SSL_RESET);
}
*/

/*
********************************************************************************************
*/
SSL_STATE ssl_exit(SSL_DATA *ssldata) {
    static const char *TAG = "ssl_exit";

    ESP_LOGD(TAG, "Exiting SSL...\n");
    // EXIT LOOP ********;
    // exit:
    ESP_LOGD(TAG, "mbedtls_net_free(&client_fd)");
    mbedtls_net_free(&client_fd);
    ESP_LOGD(TAG, "mbedtls_net_free(&listen_fd)");
    mbedtls_net_free(&listen_fd);
    ESP_LOGD(TAG, "mbedtls_x509_crt_free(&srvcert)");
    mbedtls_x509_crt_free(&srvcert);
    ESP_LOGD(TAG, "mbedtls_pk_free(&pkey)");
    mbedtls_pk_free(&pkey);
    ESP_LOGD(TAG, "mbedtls_ssl_free(&ssl)");
    mbedtls_ssl_free(&ssl);
    ESP_LOGD(TAG, "mbedtls_ssl_config_free(&conf)");
    mbedtls_ssl_config_free(&conf);
    ESP_LOGD(TAG, "mbedtls_ctr_drbg_free(&ctr_drbg)");
    mbedtls_ctr_drbg_free(&ctr_drbg);
    ESP_LOGD(TAG, "mbedtls_entropy_free(&entropy)");
    mbedtls_entropy_free(&entropy);
    // mbedtls_exit(ssldata->retval);
    return (SSL_START);
}
