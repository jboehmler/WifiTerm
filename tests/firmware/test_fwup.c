/**
 * @file test_fwup.c
 * @brief Host tests for fwup.c (signed firmware update protocol), with fake flash, hash and
 *        signature check.
 */
#include <stdio.h>
#include <string.h>

#include "fwup.h"

static int g_pass, g_fail;

/** @brief Count one check; print it and the reply if it failed. */
static void check(int ok, const char *what, const char *reply)
{
    if (ok) {
        g_pass++;
    } else {
        g_fail++;
        printf("FAIL: %s (%s)\n", what, reply);
    }
}

/** @brief Fake platform: a RAM "slot", a toy hash, and a signature that is "30 <hash[0]>". */
typedef struct {
    uint8_t slot[4096];
    uint32_t written, max;
    uint8_t acc[32];
    size_t pos; /**< Bytes hashed so far (the toy hash depends on position). */
    int began, finished, aborted, fail_write, fail_finish;
} fake_t;

static uint32_t f_max(void *c) { return ((fake_t *)c)->max; }
static int f_sig(void *c, const uint8_t h[32], const uint8_t *s, size_t n)
{
    (void)c;
    return n >= 8 && s[0] == 0x30 && s[1] == h[0] ? 0 : -1;
}
static int f_begin(void *c, uint32_t size) { fake_t *f = c; (void)size; f->began++; f->written = 0; return 0; }
static int f_write(void *c, const uint8_t *p, size_t n)
{
    fake_t *f = c;
    if (f->fail_write || f->written + n > sizeof f->slot) return -1;
    memcpy(f->slot + f->written, p, n);
    f->written += (uint32_t)n;
    return 0;
}
static int f_finish(void *c) { fake_t *f = c; f->finished++; return f->fail_finish ? -1 : 0; }
static void f_abort(void *c) { ((fake_t *)c)->aborted++; }
static void f_hstart(void *c) { fake_t *f = c; memset(f->acc, 0, 32); f->pos = 0; }
static void f_hupdate(void *c, const uint8_t *p, size_t n)
{
    fake_t *f = c;
    for (size_t i = 0; i < n; i++, f->pos++) f->acc[f->pos % 32] = (uint8_t)(f->acc[f->pos % 32] * 31 + p[i] + 1);
}
static void f_hfinish(void *c, uint8_t out[32]) { memcpy(out, ((fake_t *)c)->acc, 32); }
static void f_status(void *c, char *b, size_t n) { (void)c; snprintf(b, n, "running=ota_0 fw=test next=ota_1"); }

/** @brief The toy hash of a whole image, as hex, and the matching fake signature. */
static void sign(fake_t *f, const uint8_t *img, size_t n, char *sha_hex, char *sig_hex)
{
    uint8_t h[32];
    f_hstart(f);
    f_hupdate(f, img, n);
    f_hfinish(f, h);
    for (int i = 0; i < 32; i++) sprintf(sha_hex + 2 * i, "%02x", h[i]);
    sprintf(sig_hex, "30%02x0102030405060708", h[0]);
}

/** @brief Run "fw <text>" (split on spaces). */
static int fw(fwup_t *u, const fwup_ops_t *ops, const char *text, char *reply, size_t n)
{
    static char line[600];
    char *w[8];
    int nw = 0;
    strncpy(line, text, sizeof line - 1);
    for (char *t = strtok(line, " "); t && nw < 8; t = strtok(NULL, " ")) w[nw++] = t;
    return fwup_cmd(u, ops, w, nw, reply, n);
}

/** @brief Send one FW frame with @p k bytes of @p img at offset @p off. */
static int chunk(fwup_t *u, const fwup_ops_t *ops, const uint8_t *img, uint32_t off, size_t k, char *err)
{
    uint8_t p[FWUP_HDR + 512];
    p[0] = (uint8_t)(off >> 24); p[1] = (uint8_t)(off >> 16); p[2] = (uint8_t)(off >> 8); p[3] = (uint8_t)off;
    memcpy(p + FWUP_HDR, img + off, k);
    return fwup_data(u, ops, p, FWUP_HDR + k, err, 60);
}

int main(void)
{
    fake_t f = {.max = 3000};
    fwup_ops_t ops = {&f, f_max, f_sig, f_begin, f_write, f_finish, f_abort, f_hstart, f_hupdate, f_hfinish, f_status};
    fwup_t u;
    char reply[200], err[60], sha[65], sig[40], cmd[300];
    uint8_t img[1000];

    for (int i = 0; i < 1000; i++) img[i] = (uint8_t)(i * 7 + 3);
    img[0] = 0xE9;
    sign(&f, img, sizeof img, sha, sig);
    fwup_init(&u);

    check(fw(&u, &ops, "", reply, sizeof reply) == 1 && strstr(reply, "update=idle"), "status idle", reply);
    check(fw(&u, &ops, "end", reply, sizeof reply) == 0, "end without begin", reply);
    check(chunk(&u, &ops, img, 0, 100, err) == -1, "chunk without begin", err);

    /* Bad begin: missing keys, sizes, hex, signature. None of them erase anything. */
    check(fw(&u, &ops, "begin size=1000", reply, sizeof reply) == 0, "begin missing keys", reply);
    snprintf(cmd, sizeof cmd, "begin size=5000 sha256=%s sig=%s", sha, sig);
    check(fw(&u, &ops, cmd, reply, sizeof reply) == 0 && strstr(reply, "1..3000"), "begin too big", reply);
    snprintf(cmd, sizeof cmd, "begin size=-1 sha256=%s sig=%s", sha, sig);
    check(fw(&u, &ops, cmd, reply, sizeof reply) == 0, "begin negative", reply);
    snprintf(cmd, sizeof cmd, "begin size=1000 sha256=%.62s sig=%s", sha, sig);
    check(fw(&u, &ops, cmd, reply, sizeof reply) == 0, "begin short sha", reply);
    snprintf(cmd, sizeof cmd, "begin size=1000 sha256=%s sig=30zz0102030405060708", sha);
    check(fw(&u, &ops, cmd, reply, sizeof reply) == 0, "begin bad sig hex", reply);
    snprintf(cmd, sizeof cmd, "begin size=1000 sha256=%s sig=3000010203040506070809", sha);
    check(fw(&u, &ops, cmd, reply, sizeof reply) == 0 && strstr(reply, "signature"), "begin wrong signature", reply);
    check(f.began == 0, "nothing erased by a rejected begin", "");
    f.max = 0;
    snprintf(cmd, sizeof cmd, "begin size=1000 sha256=%s sig=%s", sha, sig);
    check(fw(&u, &ops, cmd, reply, sizeof reply) == 0 && strstr(reply, "USB"), "begin without OTA layout", reply);
    f.max = 3000;

    /* Good update in 300-byte chunks. */
    check(fw(&u, &ops, cmd, reply, sizeof reply) == 1 && f.began == 1, "begin", reply);
    check(fw(&u, &ops, "", reply, sizeof reply) == 1 && strstr(reply, "update=receiving"), "status receiving", reply);
    check(chunk(&u, &ops, img, 0, 300, err) == 0, "chunk 1", err);
    check(fw(&u, &ops, "end", reply, sizeof reply) == 0 && strstr(reply, "300 of 1000"), "end too early", reply);
    check(chunk(&u, &ops, img, 300, 300, err) == 0 && chunk(&u, &ops, img, 600, 300, err) == 0 &&
              chunk(&u, &ops, img, 900, 100, err) == 0,
          "chunks 2-4", err);
    check(fw(&u, &ops, "end", reply, sizeof reply) == 1 && f.finished == 1 && strstr(reply, "reboot"), "end", reply);
    check(memcmp(f.slot, img, sizeof img) == 0 && f.written == sizeof img, "slot holds the image", "");
    check(fw(&u, &ops, "", reply, sizeof reply) == 1 && strstr(reply, "ready-to-reboot"), "status ready", reply);

    /* Out of order, too much data, write failure: each drops the update. */
    check(fw(&u, &ops, cmd, reply, sizeof reply) == 1, "begin again", reply);
    check(chunk(&u, &ops, img, 300, 100, err) == -1 && strstr(err, "out of order"), "out of order", err);
    check(f.aborted == 1 && fw(&u, &ops, "end", reply, sizeof reply) == 0, "dropped after out of order", reply);
    check(chunk(&u, &ops, img, 0, 100, err) == -1, "no chunks after a failure", err);
    check(fw(&u, &ops, "", reply, sizeof reply) == 1 && strstr(reply, "update=failed"), "status failed", reply);
    check(fw(&u, &ops, cmd, reply, sizeof reply) == 1, "begin after failure", reply);
    for (uint32_t off = 0; off < 1000; off += 250) chunk(&u, &ops, img, off, 250, err);
    check(chunk(&u, &ops, img, 999, 1, err) == -1 && strstr(err, "out of order"), "extra chunk", err);
    check(fw(&u, &ops, cmd, reply, sizeof reply) == 1, "begin", reply);
    f.fail_write = 1;
    check(chunk(&u, &ops, img, 0, 100, err) == -1 && strstr(err, "flash write"), "write failure", err);
    f.fail_write = 0;

    /* Tampered image: right length, wrong bytes. */
    check(fw(&u, &ops, cmd, reply, sizeof reply) == 1, "begin for tamper test", reply);
    img[500] ^= 1;
    for (uint32_t off = 0; off < 1000; off += 500) chunk(&u, &ops, img, off, 500, err);
    int fin = f.finished;
    check(fw(&u, &ops, "end", reply, sizeof reply) == 0 && strstr(reply, "does not match") && f.finished == fin,
          "tampered image refused", reply);
    img[500] ^= 1;

    /* Image the platform rejects (e.g. bad header). */
    check(fw(&u, &ops, cmd, reply, sizeof reply) == 1, "begin", reply);
    for (uint32_t off = 0; off < 1000; off += 500) chunk(&u, &ops, img, off, 500, err);
    f.fail_finish = 1;
    check(fw(&u, &ops, "end", reply, sizeof reply) == 0 && strstr(reply, "not a valid"), "invalid image", reply);
    f.fail_finish = 0;

    /* Abort and session end. */
    check(fw(&u, &ops, cmd, reply, sizeof reply) == 1, "begin", reply);
    int ab = f.aborted;
    check(fw(&u, &ops, "abort", reply, sizeof reply) == 1 && f.aborted == ab + 1, "abort", reply);
    check(fw(&u, &ops, "bogus", reply, sizeof reply) == 0, "unknown sub-command", reply);

    /* Trial boots. */
    check(!fwup_should_fall_back(0) && !fwup_should_fall_back(1) && !fwup_should_fall_back(FWUP_TRIAL_BOOTS) &&
              fwup_should_fall_back(FWUP_TRIAL_BOOTS + 1),
          "fall back after the trial boots", "");

    printf("%d passed, %d failed\n", g_pass, g_fail);
    return g_fail != 0;
}
