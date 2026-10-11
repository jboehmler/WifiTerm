#include "msgbuf.h"

static TickType_t set_ticks(int timeout_ms) {
    TickType_t ticks;

    if (timeout_ms > 0)
        ticks = pdMS_TO_TICKS(timeout_ms);
    else if (timeout_ms < 0)
        ticks = portMAX_DELAY;
    else
        ticks = 0;
    return (ticks);
}

void msgbuf_warn(const char *TAG, MSGBUF_DATA *msgdata, char *errmsg) {
    ESP_LOGW(TAG, "Message buffer warning:  status %d errmsg <%s>",
             msgdata->status, errmsg);
}

static inline MSGBUF_STATUS setstatus(MSGBUF_DATA *msgdata,
                                      MSGBUF_STATUS status) {
    msgdata->status = status;
    return (msgdata->status);
}

/*
 * MESSAGE BUFFER FUNCTIONS
 */

// Create a message buffer from memory of bufsize_bytes and assign it to
// MSGBUF_DATA->msgbuf.
int msgbuf_create(const char *TAG, MSGBUF_DATA *msgdata, int bufsize_bytes) {
    msgdata->bufsize = bufsize_bytes;
    ESP_LOGD(TAG, "msgdata->bufsize:  %d", msgdata->bufsize);
    msgdata->msglen = 0;
    ESP_LOGD(TAG, "msgdata->msglen:  %d", msgdata->msglen);
    msgdata->msgbuf = xMessageBufferCreate(msgdata->bufsize);
    ESP_LOGD(TAG, "xMessageBufferCreate done.");
    if (msgdata->msgbuf == NULL) {
        setstatus(msgdata, MSGBUF_ERR_CREATE);
        msgbuf_warn(TAG, msgdata, "MessageBufferCreate failed.");
        return (0);
    }
    return (1);
}

int msgbuf_reset(const char *TAG, MSGBUF_DATA *msgdata) {
    if(xMessageBufferReset(msgdata->msgbuf) == pdFAIL) {
        ESP_LOGW(TAG, "Reset of message buffer failed.");
        return(0);
    }
    ESP_LOGD(TAG, "Reset of message buffer succeeded.");
    return(1);
}

int msgbuf_write(const char *TAG, MSGBUF_DATA *msgdata, uint8_t *src_bytes,
                 int src_len, int timeout_ms) {

    int freespace = 0;

    ESP_LOGD(TAG, "Starting msgbuf_write");
    msgdata->msglen = xMessageBufferSend(msgdata->msgbuf, (void *)src_bytes,
                                         src_len, set_ticks(timeout_ms));

    if (msgdata->msglen == src_len) {
        ESP_LOGD(TAG, "msgbuf_write wrote:  %d bytes  <%s>", msgdata->msglen,
                 src_bytes);
        setstatus(msgdata, MSGBUF_RDY);
        return (1);
    }
    ESP_LOGD(TAG, "msgbuf_write:  msgdata->msglen <%d> != src_len <%d>",
             msgdata->msglen, src_len);
    if (xMessageBufferIsFull(msgdata->msgbuf) == pdTRUE) {
        ESP_LOGW(TAG, "msgbuf_write:  Message buffer is full...");
        setstatus(msgdata, MSGBUF_FULL);
        return (0);
    }
    freespace = xMessageBufferSpaceAvailable(msgdata->msgbuf);
    ESP_LOGW(TAG, "msgbuf_write:  Message buffer space available:  <%d>",
             freespace);
    setstatus(msgdata, MSGBUF_ERR_WRITE);
    return (0);
}

int msgbuf_write_str(const char *TAG, MSGBUF_DATA *msgdata, char *src_char,
                     int timeout_ms) {
    int src_char_len;

    ESP_LOGD(TAG, "Starting msgbuf_write_str");
    src_char_len = strlen((char *)src_char);
    ESP_LOGD(TAG, "msgbuf_write_str:  Call msgbuf_write for %d bytes <%s>",
             src_char_len, src_char);
    if (msgbuf_write(TAG, msgdata, (uint8_t *)src_char, src_char_len,
                     timeout_ms)) {
        return (1);
    }
    return (0);
}

int msgbuf_read(const char *TAG, MSGBUF_DATA *msgdata, uint8_t *dst_bytes,
                int dst_maxlen, int timeout_ms) {

    ESP_LOGD(TAG, "msgbuf_read:  maxlen %d", dst_maxlen);
    msgdata->msglen = xMessageBufferReceive(msgdata->msgbuf, (void *)dst_bytes,
                                            dst_maxlen, set_ticks(timeout_ms));
    ESP_LOGD(TAG, "msgbuf_read:  msglen %d", msgdata->msglen);

    if (msgdata->msglen > 0) {
        ESP_LOGD(TAG, "msgbuf_read:  %d bytes", msgdata->msglen);
        setstatus(msgdata, MSGBUF_RDY);
        return (1);
    }
    if (xMessageBufferIsEmpty(msgdata->msgbuf) == pdTRUE) {
        ESP_LOGD(TAG, "msgbuf_read:  Read message buffer is empty...");
        setstatus(msgdata, MSGBUF_EMPTY);
    } else {
        ESP_LOGW(
            TAG,
            "msgbuf_read:  Read message buffer has data but read failed...");
        setstatus(msgdata, MSGBUF_ERR_READ);
    }
    return (0);
}

int msgbuf_read_str(const char *TAG, MSGBUF_DATA *msgdata, char *dst_char,
                    int dst_maxlen, int timeout_ms) {

    ESP_LOGD(TAG, "msgbuf_read_str calling msgbuf_read maxlen %d", dst_maxlen);
    msgbuf_read(TAG, msgdata, (uint8_t *)dst_char, dst_maxlen, timeout_ms);
    if (msgdata->status == MSGBUF_RDY) {
        ESP_LOGD(TAG, "msgbuf_read_str:  %d bytes maxlen %d", msgdata->msglen,
                 dst_maxlen);
        if (msgdata->msglen < dst_maxlen) {
            dst_char[msgdata->msglen] = '\0'; // make sure NULL at end
            ESP_LOGD(TAG, "msgbuf_read_str:  %d bytes <%s>  maxlen %d",
                     msgdata->msglen, dst_char, dst_maxlen);
            setstatus(msgdata, MSGBUF_RDY);
            return (1);
        }
        ESP_LOGW(TAG,
                 "msgbuf_read_str:  Read message buffer has data %d bytes but "
                 "%d maxlen string termination failed...",
                 msgdata->msglen, dst_maxlen);
        setstatus(msgdata, MSGBUF_ERR_READSTR);
    }
    return (0);
}
