#ifndef MSGBUF_H
#define MSGBUF_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/message_buffer.h"
#include "freertos/queue.h"

#include "esp_log.h"

/*
 * Use msgbuf
 * o create a MSGBUF_DATA var for the message buffer data:  MSGBUF_DATA msgdata;
 * o create the msgbuf from the buffer and data:  msgbuf_create(TAG, &msgdata,
 * bufsize_bytes) o msgbuf_create returns 0 for failure, 1 for success
 */
typedef enum MSGBUF_STATUS {
    MSGBUF_RDY,
    MSGBUF_ERR_CREATE,
    MSGBUF_EMPTY,
    MSGBUF_FULL,
    MSGBUF_ERR_WRITE,
    MSGBUF_ERR_WRITESTR,
    MSGBUF_ERR_READ,
    MSGBUF_ERR_READSTR,
} MSGBUF_STATUS;

typedef struct CHAR_BUFFER {
    int retval;
    int len;
    int maxlen;
    uint8_t *data;
} CHAR_BUFFER;

typedef struct MSGBUF_DATA {
    int bufsize;
    int msglen;
    MessageBufferHandle_t msgbuf;
    MSGBUF_STATUS status;
} MSGBUF_DATA;

extern void msgbuf_warn(const char *TAG, MSGBUF_DATA *msgdata, char *errmsg);
extern int msgbuf_create(const char *TAG, MSGBUF_DATA *msgdata,
                         int bufsize_bytes);
extern int msgbuf_write(const char *TAG, MSGBUF_DATA *msgdata,
                        uint8_t *src_bytes, int src_len, int timeout_ms);
extern int msgbuf_write_str(const char *TAG, MSGBUF_DATA *msgdata,
                            char *src_char, int timeout_ms);
extern int msgbuf_read(const char *TAG, MSGBUF_DATA *msgdata,
                       uint8_t *dst_bytes, int dst_maxlen, int timeout_ms);
extern int msgbuf_read_str(const char *TAG, MSGBUF_DATA *msgdata,
                           char *dst_char, int dst_maxlen, int timeout_ms);
extern int msgbuf_reset(const char *TAG, MSGBUF_DATA *msgdata);
#endif // MSGBUF_H
