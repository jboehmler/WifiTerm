/**
 * @file test_frames.c
 * @brief Host (gcc) test of firmware/main/frames.c against tests/vectors/frames.txt.
 * @details Build and run with `make -C tests/firmware`. Exit status 0 means every check passed.
 */
#include "frames.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/** @brief Longest vector line (1024-byte frame is about 4.2 kB of hex). */
#define LINE_MAX_LEN 8192

static int g_fail; /**< Failed checks. */
static int g_pass; /**< Passed checks. */

/** @brief Record one check. @param ok Result. @param what Description. @param line Vector line number. */
static void check(int ok, const char *what, int line)
{
    if (ok) {
        g_pass++;
    } else {
        g_fail++;
        printf("FAIL line %d: %s\n", line, what);
    }
}

/**
 * @brief Decode a hex field ("-" = empty) into @p out.
 * @param s Hex text.
 * @param out Destination.
 * @param cap Capacity of @p out.
 * @return Byte count.
 */
static size_t unhex(const char *s, uint8_t *out, size_t cap)
{
    size_t n = 0;
    if (strcmp(s, "-") == 0) {
        return 0;
    }
    while (s[0] && s[1] && n < cap) {
        unsigned v;
        sscanf(s, "%2x", &v);
        out[n++] = (uint8_t)v;
        s += 2;
    }
    return n;
}

/** @brief Feed @p buf in @p step-sized chunks; return frames completed, @p last = final status. */
static int decode_all(frame_decoder_t *d, const uint8_t *buf, size_t len, size_t step,
                      frame_status_t *last)
{
    int frames = 0;
    size_t off = 0;
    *last = FRAME_NEED_MORE;
    while (off < len) {
        size_t chunk = (len - off < step) ? len - off : step;
        size_t used;
        while (chunk) {
            *last = frame_decoder_feed(d, buf + off, chunk, &used);
            off += used;
            chunk -= used;
            if (*last == FRAME_BAD) {
                return frames;
            }
            if (*last == FRAME_READY) {
                frames++;
            }
        }
    }
    return frames;
}

int main(int argc, char **argv)
{
    const char *path = argc > 1 ? argv[1] : "../vectors/frames.txt";
    FILE *f = fopen(path, "r");
    static char line[LINE_MAX_LEN];
    static uint8_t a[FRAME_MAX_LEN + 8], b[FRAME_MAX_LEN + 8], out[FRAME_MAX_LEN];
    static uint8_t stream[64 * 1024];
    size_t stream_len = 0;
    int stream_frames = 0;
    int lineno = 0;
    frame_decoder_t d;

    if (!f) {
        perror(path);
        return 2;
    }
    while (fgets(line, sizeof line, f)) {
        char *w[6] = {0};
        int nw = 0;
        lineno++;
        for (char *tok = strtok(line, " \r\n"); tok && nw < 6; tok = strtok(NULL, " \r\n")) {
            w[nw++] = tok;
        }
        if (nw == 0 || w[0][0] == '#') {
            continue;
        }
        if (strcmp(w[0], "frame") == 0) {
            int type = atoi(w[1]);
            size_t plen = unhex(w[2], a, sizeof a);
            size_t elen = unhex(w[3], b, sizeof b);
            size_t n = frame_encode(out, (uint8_t)type, a, plen);
            check(n == elen && memcmp(out, b, n) == 0, "encode", lineno);

            /* Byte by byte and all at once must both give exactly one frame. */
            size_t steps[] = {1, 7, elen};
            for (size_t s = 0; s < 3; s++) {
                frame_status_t last;
                frame_decoder_init(&d);
                int got = decode_all(&d, b, elen, steps[s], &last);
                check(got == 1 && last == FRAME_READY && frame_decoder_type(&d) == type &&
                          frame_decoder_len(&d) == plen &&
                          memcmp(frame_decoder_payload(&d), a, plen) == 0 &&
                          frame_decoder_payload(&d)[plen] == 0,
                      "decode", lineno);
            }
            if (stream_len + elen <= sizeof stream) {
                memcpy(stream + stream_len, b, elen);
                stream_len += elen;
                stream_frames++;
            }
        } else if (strcmp(w[0], "bad") == 0) {
            size_t n = unhex(w[1], a, sizeof a);
            frame_status_t last;
            frame_decoder_init(&d);
            decode_all(&d, a, n, 1, &last);
            check(last == FRAME_BAD, "reject oversize", lineno);
        } else if (strcmp(w[0], "cmd") == 0) {
            size_t n = unhex(w[1], a, sizeof a - 1);
            unsigned want_seq = (unsigned)atoi(w[2]);
            size_t tlen = unhex(w[3], b, sizeof b - 1);
            unsigned seq = 0;
            const char *text = NULL;
            a[n] = 0;
            b[tlen] = 0;
            int rc = frame_parse_cmd((const char *)a, &seq, &text);
            if (want_seq == 0) {
                check(rc == -1, "cmd invalid", lineno);
            } else {
                check(rc == 0 && seq == want_seq && strcmp(text, (const char *)b) == 0, "cmd parse",
                      lineno);
            }
        } else if (strcmp(w[0], "resp") == 0) {
            unsigned seq = (unsigned)atoi(w[1]);
            int ok = strcmp(w[2], "OK") == 0;
            size_t tlen = unhex(w[3], a, sizeof a - 1);
            size_t elen = unhex(w[4], b, sizeof b);
            a[tlen] = 0;
            size_t n = frame_encode_resp(out, seq, ok, (const char *)a);
            check(n == elen && memcmp(out, b, n) == 0, "resp encode", lineno);
        } else if (strcmp(w[0], "proto") == 0) {
            size_t n = unhex(w[1], a, sizeof a - 1);
            a[n] = 0;
            check(frame_choose_proto((const char *)a) == atoi(w[2]), "proto choose", lineno);
        } else {
            check(0, "unknown vector kind", lineno);
        }
    }
    fclose(f);

    /* All frame vectors back to back, fed in odd-sized chunks. */
    {
        frame_status_t last;
        frame_decoder_init(&d);
        check(decode_all(&d, stream, stream_len, 13, &last) == stream_frames, "stream", 0);
    }
    /* Encoder limits and RESP truncation. */
    check(frame_encode(out, FRAME_DATA, a, FRAME_MAX_PAYLOAD + 1) == 0, "encode limit", 0);
    {
        static char big[2000];
        memset(big, 'x', sizeof big - 1);
        size_t n = frame_encode_resp(out, 1, 1, big);
        check(n == FRAME_MAX_LEN && out[1] == 0x04 && out[2] == 0x00, "resp truncate", 0);
    }
    printf("%d passed, %d failed\n", g_pass, g_fail);
    return g_fail ? 1 : 0;
}
