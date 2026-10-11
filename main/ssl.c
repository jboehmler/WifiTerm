#include <stdlib.h>

// clang-format off
#define SSL_STATE_STR  // declare ssl_state_str array from ssl.h only here
#include "ssl.h"
// clang-format on

#include "ticks.h"

const char HOST[] = "192.168.4.1";
const char PORT[] = "8443";

static const int block10ms = 1000;

// clang-format off
#define SSL_BUF_SIZE 256

/* SSL READ BUFFERS - read data from SSL and put into a message buffer
 */
static uint8_t sslread_buf[SSL_BUF_SIZE];
static const unsigned int sslread_buf_size = sizeof(sslread_buf);

MSGBUF_DATA sslread_msgdata;
/*
 * msgbuf_create(TAG, sslread_msgdata, sslread_buf_size)
 *
 * sslwrite_msgdata -> msgbuf_read(sslwrite_msgdata, sslwrite_buf) -> mbed_ssl_write(sslwrite_buf) -> SSL
 */
/* SSL WRITE BUFFERS - read data from a message buffer and send to SSL
 */

static uint8_t sslwrite_buf[SSL_BUF_SIZE];
static const unsigned int sslwrite_buf_size = SSL_BUF_SIZE;
// clang-format on

MSGBUF_DATA sslwrite_msgdata;
// msgbuf_create(TAG, sslwrite_msgdata, sslwrite_buf_size)

SSL_DATA ssldata;
/*
 * void ssl_init(SSL_DATA *ssldata, uint8_t *ssl_readbuf, int ssl_readbuf_size,
 * uint8_t *ssl_writebuf, int ssl_writebuf_size)
 * ssl_init(&ssldata, sslread_buf, sslread_buf_size, sslwrite_buf,
 * sslwrite_buf_size)
 */

static inline void print_stack_pointer(char *callstr) {
    static const char *TAG = "stack pointer";

    void *p = NULL;
    ESP_LOGD(TAG, "%s stack address:  %p", callstr, (void *)&p);
}

inline int ssl_ready(void) { return (ssldata.state == SSL_RWOK); }

SSL_ERRCHK ssl_errorcheck(const char *TAG, char *caller_str,
                          CHAR_BUFFER *bufdata) {

    if (bufdata->retval > 0) {
        bufdata->len = bufdata->retval;
        return (SSL_WROK);
    }
    // retval <= 0 are errors except WANT_READ/WRITE below
    else {
        // log specific errors
        switch (bufdata->retval) {
        case MBEDTLS_ERR_SSL_WANT_READ:
            ESP_LOGD(TAG, "ssl_errorcheck connection has WANT_READ\n");
            return (SSL_WANTRW);
            break;

        case MBEDTLS_ERR_SSL_WANT_WRITE:
            ESP_LOGD(TAG, "ssl_errorcheck connection has WANT_WRITE\n");
            return (SSL_WANTRW);
            break;

        case MBEDTLS_ERR_SSL_PEER_CLOSE_NOTIFY:
            ESP_LOGD(TAG, "ssl_errorcheck connection was closed gracefully\n");
            break;

        case MBEDTLS_ERR_NET_CONN_RESET:
            ESP_LOGD(TAG, "ssl_errorcheck connection was reset by peer\n");
            break;

        default:
            ESP_LOGD(TAG, "ssl_errorcheck mbedtls_ssl_%s returned -0x%x\n",
                     caller_str, -bufdata->retval);
            break;
        }
    }
    bufdata->len = 0;
    return (SSL_MBEDERR);
}

/*
 * 7. Read the HTTP Request
 * SSL -> mbed_ssl_read(sslread_buf) -> msgbuf_write(sslread_msgdata,
 * sslread_buf) -> sslread_msgdata
 */
void ssl_read_task(void *pvParameters) {
    static const char *TAG = "ssl_read_task";

    SSL_ERRCHK err;

    ESP_LOGD(TAG, "Start ssl_read_task...");
    ssldata.readbuf.len = ssldata.readbuf.maxlen - 1;
    memset(ssldata.readbuf.data, 0, ssldata.readbuf.maxlen);
    while (1) {
        if (ssldata.state != SSL_RWOK) {
            ESP_LOGD(TAG, "Waiting for SSL_RWOK...");
            task_wait_s(1);
            // vTaskSuspend(NULL);
            continue;
        }
        // print_stack_pointer("Before read from client");
        do {
            ssldata.readbuf.len = ssldata.readbuf.maxlen - 1;
            memset(ssldata.readbuf.data, 0, ssldata.readbuf.maxlen);

            // SSL READ IS HERE
            ssldata.readbuf.retval = mbedtls_ssl_read(
                &ssl, ssldata.readbuf.data, ssldata.readbuf.len);

            err = ssl_errorcheck(TAG, "read", &ssldata.readbuf);
        } while (err == SSL_WANTRW);
        // print_stack_pointer("After read from client");

        switch (err) {
        case SSL_WROK:
            ESP_LOGI(TAG, " %d bytes read:  <%s>", ssldata.readbuf.len,
                     (char *)ssldata.readbuf.data);
            ESP_LOGD(TAG, "Write to message buffer...");
            if (msgbuf_write(TAG, &sslread_msgdata, ssldata.readbuf.data,
                             ssldata.readbuf.len, block10ms))
                ESP_LOGD(TAG, "msgbuf_write:  %d bytes  <%s>",
                         sslread_msgdata.msglen, ssldata.readbuf.data);
            break;

        case SSL_MBEDERR:
            if (ssldata.state != SSL_RWOK) {
                ESP_LOGW(TAG,
                         "MBEDTLS ERROR being handled:  ssldata.state %s.  "
                         "Ignore...",
                         ssl_state_str[ssldata.state]);
                task_wait_s(1);
                continue;
            }
            switch (ssldata.readbuf.retval) {
            case MBEDTLS_ERR_SSL_PEER_CLOSE_NOTIFY:
                ESP_LOGW(TAG, "MBEDTLS_ERR_SSL_PEER_CLOSE_NOTIFY SSL_RESET");
                ssldata.state = SSL_RESET;
                break;

            case MBEDTLS_ERR_NET_CONN_RESET:
                ESP_LOGW(TAG, "MBEDTLK_ERR_NET_CONN_RESET SSL_EXIT");
                ssldata.state = SSL_EXIT;
                break;

            default:
                ESP_LOGE(TAG, "SSL_MBEDERR returned:  -0x%X SSL_EXIT\n\n",
                         -ssldata.readbuf.retval);
                ssldata.state = SSL_EXIT;
                break;
            }
            break;

        default:
            ESP_LOGE(TAG, "Undefined err:  %d", err);
            break;
        }
        // ssldata.state = SSL_RWOK;
    }
}

/*
 * 8. Write the 200 Response
 * sslwrite_msgdata -> msgbuf_read(sslwrite_msgdata, sslwrite_buf) ->
 * mbed_ssl_write(sslwrite_buf) -> SSL
 */
void ssl_write_task(void *pvParameters) {
    static const char *TAG = "ssl_write_task";

    SSL_ERRCHK err;

    ESP_LOGD(TAG, "Start ssl_write_task...");
    ssldata.writebuf.len = ssldata.writebuf.maxlen - 1;
    memset(ssldata.writebuf.data, 0, ssldata.writebuf.maxlen);
    while (1) {
        if (ssldata.state != SSL_RWOK) {
            ESP_LOGD(TAG, "Waiting for SSL_RWOK...");
            task_wait_s(1);
            // vTaskSuspend(NULL);
            continue;
        }
        // print_stack_pointer("Before write to client");

        // sslwrite_msgbuf -> temporary buffer
        ESP_LOGD(TAG, "Read message buffer...");
        if (msgbuf_read_str(TAG, &sslwrite_msgdata,
                            (char *)ssldata.writebuf.data,
                            ssldata.writebuf.maxlen, block10ms) == 0) {
            ESP_LOGD(TAG, "Read message buffer zero bytes...");
            task_wait_ms(10);
            continue;
        }

        do {

            // SSL SEND IS HERE
            ESP_LOGD(TAG, " SSL send %d bytes:  <%s>", sslwrite_msgdata.msglen,
                     (char *)ssldata.writebuf.data);
            ssldata.writebuf.retval = mbedtls_ssl_write(
                &ssl, ssldata.writebuf.data, sslwrite_msgdata.msglen);

            err = ssl_errorcheck(TAG, "write", &ssldata.writebuf);
        } while (err == SSL_WANTRW);
        // print_stack_pointer("After write to client");

        switch (err) {
        case SSL_WROK:
            ssldata.writebuf.len = ssldata.writebuf.retval;
            ESP_LOGI(TAG, " %d bytes written:  <%s>", ssldata.writebuf.len,
                     (char *)ssldata.writebuf.data);
            break;

        case SSL_MBEDERR:
            if (ssldata.state != SSL_RWOK) {
                ESP_LOGW(TAG,
                         "MBEDTLS ERROR handled:  ssldata.state %s.  Ignore...",
                         ssl_state_str[ssldata.state]);
                task_wait_s(1);
                continue;
            }
            switch (ssldata.writebuf.retval) {
            case MBEDTLS_ERR_SSL_PEER_CLOSE_NOTIFY:
                ESP_LOGW(TAG, "MBEDTLS_ERR_SSL_PEER_CLOSE_NOTIFY SSL_RESET");
                ssldata.state = SSL_RESET;
                break;

            case MBEDTLS_ERR_NET_CONN_RESET:
                ESP_LOGW(TAG, "MBEDTLK_ERR_NET_CONN_RESET SSL_EXIT");
                ssldata.state = SSL_EXIT;
                break;

            default:
                ESP_LOGE(TAG, "SSL_MBEDERR returned:  -0x%X SSL_EXIT\n\n",
                         -ssldata.writebuf.retval);
                break;
            }
            break;

        default:
            ESP_LOGE(TAG, "Undefined err:  %d", err);
            break;
        }
        // ssldata.state = SSL_RWOK;
    }
}

TaskHandle_t read_task_handle;
TaskHandle_t write_task_handle;

void sslmain_task(void *pvParameters) {
    static const char *TAG = "sslmain_task";

    int rwokstart = 1;
    int taskcnt = 0;
    int resetcnt = 0;
    int exitcnt = 0;
    const int tskPRIORITY = tskIDLE_PRIORITY + 2;

    ESP_LOGD(TAG, "Creating sslread message buffer data...");
    if (msgbuf_create(TAG, &sslread_msgdata, sslread_buf_size) == 0) {
        ESP_LOGE(TAG, "Create sslread message buffer failed.\n");
    }
    ESP_LOGD(TAG, "Creating sslwrite message buffer data...");
    if (msgbuf_create(TAG, &sslwrite_msgdata, sslwrite_buf_size) == 0) {
        ESP_LOGE(TAG, "Create sslwrite message buffer failed.\n");
    }

    ESP_LOGD(TAG, "Initializing ssl data...");
    ssl_init(&ssldata, sslread_buf, sslread_buf_size, sslwrite_buf,
             sslwrite_buf_size);
    ESP_LOGD(TAG, "Starting SSL task...");
    ssldata.state = SSL_START;
    ESP_LOGD(TAG, "Creating ssl_read_task...");
    xTaskCreate(ssl_read_task, "read_task", 2048, NULL, tskPRIORITY,
                &read_task_handle);
    ESP_LOGD(TAG, "Suspending ssl_read_task...");
    vTaskSuspend(read_task_handle);
    ESP_LOGD(TAG, "Creating ssl_write_task...");
    xTaskCreate(ssl_write_task, "write_task", 2048, NULL, tskPRIORITY,
                &write_task_handle);
    ESP_LOGD(TAG, "Suspending ssl_write_task...");
    vTaskSuspend(write_task_handle);

    do {
        taskcnt++;
        switch (ssldata.state) {
        case SSL_START:
            ESP_LOGI("SSL_START",
                     "taskcnt:  %d  resetcnt:  %d  exitcnt:  %d  SSL "
                     "state:  %s\n",
                     taskcnt, resetcnt, exitcnt, ssl_state_str[ssldata.state]);
            // print_stack_pointer("Before ssl_start");
            ssldata.state = ssl_start(&ssldata);
            // print_stack_pointer("After ssl_start");
            break;

        case SSL_CONN:
            ESP_LOGI("SSL_EXIT",
                     "taskcnt:  %d  resetcnt:  %d  exitcnt:  %d  SSL "
                     "state:  %s\n",
                     taskcnt, resetcnt, exitcnt, ssl_state_str[ssldata.state]);
            rwokstart = 1;
            // print_stack_pointer("Before ssl_conn");
            ssldata.state = ssl_conn(&ssldata);
            // print_stack_pointer("After ssl_conn");
            break;

        case SSL_RWOK:
            // stay here until ssl error during read/write
            if (rwokstart) {
                ESP_LOGI("SSL_RWOK",
                         "taskcnt:  %d  resetcnt:  %d  exitcnt:  %d  SSL "
                         "state:  %s\n",
                         taskcnt, resetcnt, exitcnt,
                         ssl_state_str[ssldata.state]);
                rwokstart = 0;
                ESP_LOGD(TAG, "Resume ssl_read_task...");
                vTaskResume(read_task_handle);
                ESP_LOGD(TAG, "Resume ssl_write_task...");
                vTaskResume(write_task_handle);
            }
            ESP_LOGD(TAG, "SSL RWOK waiting...");
            task_wait_ms(1000);
            break;

            /*
            case SSL_CLOSE:
                ssl_close(&ssldata);
                break;
            */

        case SSL_RESET:
            resetcnt++;
            ESP_LOGI("SSL_RESET",
                     "taskcnt:  %d  resetcnt:  %d  exitcnt:  %d  SSL "
                     "state:  %s\n",
                     taskcnt, resetcnt, exitcnt, ssl_state_str[ssldata.state]);
            ESP_LOGD(TAG, "Suspending ssl_read_task...");
            vTaskSuspend(read_task_handle);
            ESP_LOGD(TAG, "Suspending ssl_write_task...");
            vTaskSuspend(write_task_handle);
            ssldata.state = SSL_CONN;
            break;

        case SSL_EXIT:
            exitcnt++;
            ESP_LOGI("SSL_EXIT",
                     "taskcnt:  %d  resetcnt:  %d  exitcnt:  %d  SSL "
                     "state:  %s\n",
                     taskcnt, resetcnt, exitcnt, ssl_state_str[ssldata.state]);
            ESP_LOGD(TAG, "Suspending ssl_read_task...");
            vTaskSuspend(read_task_handle);
            ESP_LOGD(TAG, "Suspending ssl_write_task...");
            vTaskSuspend(write_task_handle);
            ssldata.state = ssl_exit(&ssldata);
            break;

            /* commented to make errors for uncased states
            default:
                ESP_LOGE(TAG, "Main loop default case invalid SSL_STATE:
            %d", ssldata.state); break;
            */
        }
    } while (1);
    ESP_LOGE(TAG, "Exiting SSL.  SHOULD NEVER GET HERE...\n");
}
