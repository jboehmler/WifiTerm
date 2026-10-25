/**
 * @file fwup.c
 * @brief Signed firmware update protocol. See fwup.h.
 */
#include "fwup.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void fwup_init(fwup_t *u)
{
    memset(u, 0, sizeof *u);
}

/** @brief Hex digit value, or -1. */
static int hexval(char c)
{
    if (c >= '0' && c <= '9') {
        return c - '0';
    }
    if (c >= 'a' && c <= 'f') {
        return c - 'a' + 10;
    }
    if (c >= 'A' && c <= 'F') {
        return c - 'A' + 10;
    }
    return -1;
}

/**
 * @brief Decode hex text.
 * @param s Text. @param out Buffer. @param max Its size.
 * @return Bytes decoded, or -1 if not even-length hex or too long.
 */
static int unhex(const char *s, uint8_t *out, size_t max)
{
    size_t len = strlen(s);
    if (len == 0 || len % 2 || len / 2 > max) {
        return -1;
    }
    for (size_t i = 0; i < len / 2; i++) {
        int hi = hexval(s[2 * i]), lo = hexval(s[2 * i + 1]);
        if (hi < 0 || lo < 0) {
            return -1;
        }
        out[i] = (uint8_t)(hi << 4 | lo);
    }
    return (int)(len / 2);
}

/** @brief Value of "key=value" among @p w, or NULL. */
static const char *kv(char **w, int nw, const char *key)
{
    size_t k = strlen(key);
    for (int i = 0; i < nw; i++) {
        if (strncmp(w[i], key, k) == 0 && w[i][k] == '=') {
            return w[i] + k + 1;
        }
    }
    return NULL;
}

/** @brief `fw begin size=<n> sha256=<hex> sig=<hex>`. */
static int begin(fwup_t *u, const fwup_ops_t *ops, char **w, int nw, char *reply, size_t n)
{
    const char *s_size = kv(w, nw, "size"), *s_sha = kv(w, nw, "sha256"), *s_sig = kv(w, nw, "sig");
    uint8_t sig[FWUP_SIG_MAX], sha[32];
    char *end;
    int siglen;

    if (!s_size || !s_sha || !s_sig || nw != 3) {
        snprintf(reply, n, "usage: fw begin size=<bytes> sha256=<hex> sig=<hex>");
        return 0;
    }
    uint32_t max = ops->max_size(ops->ctx);
    if (!max) {
        snprintf(reply, n, "no OTA flash layout: flash this firmware once over USB");
        return 0;
    }
    unsigned long size = strtoul(s_size, &end, 10);
    if (*end || *s_size < '0' || *s_size > '9' || size == 0 || size > max) {
        snprintf(reply, n, "size must be 1..%u bytes", (unsigned)max);
        return 0;
    }
    if (unhex(s_sha, sha, sizeof sha) != 32 || (siglen = unhex(s_sig, sig, sizeof sig)) < 8) {
        snprintf(reply, n, "bad sha256 or sig (hex expected)");
        return 0;
    }
    if (ops->sig_check(ops->ctx, sha, sig, (size_t)siglen)) {
        snprintf(reply, n, "signature does not match this unit's firmware key");
        return 0;
    }
    if (u->active) {
        ops->flash_abort(ops->ctx);
    }
    fwup_init(u);
    if (ops->flash_begin(ops->ctx, (uint32_t)size)) {
        snprintf(reply, n, "could not prepare the update slot");
        return 0;
    }
    ops->hash_start(ops->ctx);
    u->active = 1;
    u->size = (uint32_t)size;
    memcpy(u->sha, sha, sizeof sha);
    snprintf(reply, n, "ready for %lu bytes", size);
    return 1;
}

/** @brief `fw end`: everything arrived and matches what was signed. */
static int finish(fwup_t *u, const fwup_ops_t *ops, char *reply, size_t n)
{
    uint8_t sha[32];

    if (!u->active) {
        snprintf(reply, n, u->failed ? "update failed; start again with fw begin" : "no update in progress");
        return 0;
    }
    if (u->got != u->size) {
        snprintf(reply, n, "only %u of %u bytes arrived", (unsigned)u->got, (unsigned)u->size);
        return 0;
    }
    ops->hash_finish(ops->ctx, sha);
    u->active = 0;
    if (memcmp(sha, u->sha, sizeof sha) != 0) {
        ops->flash_abort(ops->ctx);
        u->failed = 1;
        snprintf(reply, n, "image does not match its signature; nothing changed");
        return 0;
    }
    if (ops->flash_finish(ops->ctx)) {
        u->failed = 1;
        snprintf(reply, n, "not a valid firmware image; nothing changed");
        return 0;
    }
    u->done = 1;
    snprintf(reply, n, "verified; reboot to start it");
    return 1;
}

int fwup_cmd(fwup_t *u, const fwup_ops_t *ops, char **w, int nw, char *reply, size_t n)
{
    if (nw == 0) {
        char st[120];
        ops->status(ops->ctx, st, sizeof st);
        snprintf(reply, n, "%s update=%s", st,
                 u->active ? "receiving" : u->done ? "ready-to-reboot" : u->failed ? "failed" : "idle");
        return 1;
    }
    if (strcmp(w[0], "begin") == 0) {
        return begin(u, ops, w + 1, nw - 1, reply, n);
    }
    if (nw == 1 && strcmp(w[0], "end") == 0) {
        return finish(u, ops, reply, n);
    }
    if (nw == 1 && strcmp(w[0], "abort") == 0) {
        fwup_abort(u, ops);
        reply[0] = 0;
        return 1;
    }
    snprintf(reply, n, "usage: fw | fw begin ... | fw end | fw abort");
    return 0;
}

int fwup_data(fwup_t *u, const fwup_ops_t *ops, const uint8_t *p, size_t len, char *err, size_t n)
{
    const char *why = NULL;

    if (!u->active) {
        snprintf(err, n, u->failed ? "update already failed" : "no update in progress");
        return -1;
    }
    if (len <= FWUP_HDR) {
        why = "empty chunk";
    } else {
        uint32_t off = (uint32_t)p[0] << 24 | (uint32_t)p[1] << 16 | (uint32_t)p[2] << 8 | p[3];
        size_t k = len - FWUP_HDR;
        if (off != u->got) {
            why = "chunk out of order";
        } else if (k > u->size - u->got) {
            why = "more data than announced";
        } else if (ops->flash_write(ops->ctx, p + FWUP_HDR, k)) {
            why = "flash write failed";
        } else {
            ops->hash_update(ops->ctx, p + FWUP_HDR, k);
            u->got += (uint32_t)k;
            return 0;
        }
    }
    snprintf(err, n, "%s at %u", why, (unsigned)u->got);
    fwup_abort(u, ops);
    u->failed = 1;
    return -1;
}

void fwup_abort(fwup_t *u, const fwup_ops_t *ops)
{
    if (u->active) {
        ops->flash_abort(ops->ctx);
    }
    fwup_init(u);
}

int fwup_should_fall_back(int trial)
{
    return trial > FWUP_TRIAL_BOOTS;
}
