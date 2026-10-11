/**
 * @file frames.c
 * @brief Protocol v1 frame encoder and decoder. See frames.h.
 */
#include "frames.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void frame_decoder_init(frame_decoder_t *d)
{
    d->hdr_got = 0;
    d->len = 0;
    d->got = 0;
    d->payload[0] = 0;
}

frame_status_t frame_decoder_feed(frame_decoder_t *d, const uint8_t *data, size_t len, size_t *used)
{
    size_t i = 0;

    /* A frame was handed out by the previous call: start a new one. */
    if (d->hdr_got == FRAME_HEADER_LEN && d->got == d->len) {
        frame_decoder_init(d);
    }
    while (d->hdr_got < FRAME_HEADER_LEN && i < len) {
        d->hdr[d->hdr_got++] = data[i++];
        if (d->hdr_got == FRAME_HEADER_LEN) {
            d->len = (uint16_t)((d->hdr[1] << 8) | d->hdr[2]);
            if (d->len > FRAME_MAX_PAYLOAD) {
                *used = i;
                return FRAME_BAD;
            }
        }
    }
    if (d->hdr_got == FRAME_HEADER_LEN) {
        size_t take = d->len - d->got;
        if (take > len - i) {
            take = len - i;
        }
        memcpy(d->payload + d->got, data + i, take);
        d->got += take;
        i += take;
        if (d->got == d->len) {
            d->payload[d->len] = 0;
            *used = i;
            return FRAME_READY;
        }
    }
    *used = i;
    return FRAME_NEED_MORE;
}

size_t frame_encode(uint8_t *out, uint8_t type, const void *payload, size_t len)
{
    if (len > FRAME_MAX_PAYLOAD) {
        return 0;
    }
    out[0] = type;
    out[1] = (uint8_t)(len >> 8);
    out[2] = (uint8_t)len;
    if (len) {
        memcpy(out + FRAME_HEADER_LEN, payload, len);
    }
    return FRAME_HEADER_LEN + len;
}

size_t frame_encode_resp(uint8_t *out, unsigned seq, int ok, const char *text)
{
    /* snprintf needs room for its NUL; the extra byte is never sent. */
    char buf[FRAME_MAX_PAYLOAD + 1];
    int n;

    if (text && *text) {
        n = snprintf(buf, sizeof buf, "%u %s %s", seq, ok ? "OK" : "ERR", text);
    } else {
        n = snprintf(buf, sizeof buf, "%u %s", seq, ok ? "OK" : "ERR");
    }
    if (n < 0) {
        n = 0;
    } else if (n > FRAME_MAX_PAYLOAD) {
        n = FRAME_MAX_PAYLOAD; /* truncated */
    }
    return frame_encode(out, FRAME_RESP, buf, (size_t)n);
}

int frame_parse_cmd(const char *payload, unsigned *seq, const char **text)
{
    char *end;
    unsigned long v;

    if (*payload < '0' || *payload > '9') {
        return -1;
    }
    v = strtoul(payload, &end, 10);
    if (v < 1 || v > 65535 || (*end != ' ' && *end != 0)) {
        return -1;
    }
    *seq = (unsigned)v;
    *text = (*end == ' ') ? end + 1 : end;
    return 0;
}

int frame_choose_proto(const char *payload)
{
    const char *p = payload;

    /* Find the word "proto=" at the start or after a space. */
    while ((p = strstr(p, "proto=")) != NULL) {
        if (p == payload || p[-1] == ' ') {
            break;
        }
        p++;
    }
    if (!p) {
        return 0;
    }
    p += 6;
    if (*p < '0' || *p > '9') {
        return 0;
    }
    char *end;
    long lo = strtol(p, &end, 10);
    long hi = lo;
    if (*end == '-') {
        const char *q = end + 1;
        if (*q < '0' || *q > '9') {
            return 0;
        }
        hi = strtol(q, &end, 10);
    }
    if (*end != ' ' && *end != 0) {
        return 0;
    }
    if (hi > PROTO_MAX) {
        hi = PROTO_MAX;
    }
    if (lo < PROTO_MIN) {
        lo = PROTO_MIN;
    }
    return (lo <= hi) ? (int)hi : 0;
}

int frame_kv_get(const char *payload, const char *key, char *out, size_t n)
{
    size_t klen = strlen(key);
    const char *p = payload;

    while (*p) {
        while (*p == ' ') {
            p++;
        }
        const char *end = strchr(p, ' ');
        size_t wlen = end ? (size_t)(end - p) : strlen(p);
        if (wlen > klen && strncmp(p, key, klen) == 0 && p[klen] == '=') {
            size_t vlen = wlen - klen - 1;
            if (vlen >= n) {
                vlen = n - 1;
            }
            memcpy(out, p + klen + 1, vlen);
            out[vlen] = 0;
            return 1;
        }
        p += wlen;
    }
    return 0;
}
