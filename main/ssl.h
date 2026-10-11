#ifndef SSL_H
#define SSL_H

#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "mbedtls/net_sockets.h"
#include "mbedtls/ssl.h"

#include "esp_log.h"

#include "msgbuf.h"

#define MBEDTLS_DECLARE_PRIVATE_IDENTIFIERS

typedef enum SSL_STATE {
    SSL_START,
    SSL_RESET,
    SSL_CONN,
    SSL_RWOK,
    // SSL_CLOSE,
    SSL_EXIT,
} SSL_STATE;

// clang-format off
#ifdef SSL_STATE_STR
const char *ssl_state_str[] = {
    "SSL_START",
    "SSL_RESET",
    "SSL_CONN",
    "SSL_RWOK",
    //"SSL_CLOSE",
    "SSL_EXIT",
};

#else
extern char *ssl_state_str[];

#endif  //SSLFUNCS_C:w

// clang-format on

typedef struct SSL_DATA {
    int retval;
    int len;
    CHAR_BUFFER readbuf;
    CHAR_BUFFER writebuf;
    SSL_STATE state;
} SSL_DATA;

typedef enum SSL_ERRCHK {
    SSL_WROK,
    SSL_WANTRW,
    SSL_MBEDERR,
} SSL_ERRCHK;

/*
#define SSLRETURN(SSLDATA, SSLSTATUS)                                          \
    SSLDATA = SSLSTATUS;                                                       \
    return (SSLSTATUS);
*/
extern const char HOST[];
extern const char PORT[];

extern int ssl_ready(void);

extern mbedtls_ssl_context ssl;
extern void ssl_init(SSL_DATA *ssldata, uint8_t *sslread_buf,
                     int sslread_buf_size, uint8_t *sslwrite_buf,
                     int sslwrite_buf_size);
extern SSL_STATE ssl_start(SSL_DATA *ssldata);
extern SSL_STATE ssl_conn(SSL_DATA *ssldata);
// extern SSL_STATE ssl_close(SSL_DATA* ssldata);
extern SSL_STATE ssl_exit(SSL_DATA *ssldata);
extern MSGBUF_DATA sslread_msgdata;
extern MSGBUF_DATA sslwrite_msgdata;

/*
extern const int SSL_READ_SIZE;
extern const int SSL_WRITE_SIZE;
*/

#endif // SSL_H
