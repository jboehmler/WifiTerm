/**
 * @file fwup.h
 * @brief Signed firmware update over the TLS link (NOTES I-25, John 2026-10-25: option 1).
 * @details The client sends, in one session:
 *          1. CMD `fw begin size=<n> sha256=<64 hex> sig=<hex>`: the signature (ECDSA P-256,
 *             DER) over the image's SHA-256 is checked against the public key built into the
 *             firmware BEFORE anything is erased. Then the spare slot is prepared.
 *          2. FW frames (type 0x09): 4-byte big-endian offset, then image bytes, in order.
 *          3. CMD `fw end`: length and SHA-256 must match what was signed; then the slot is
 *             checked, made the boot slot, and marked "on trial" (see ota.h).
 *          4. CMD `reboot`.
 *          `fw abort` (or the session ending) drops a half-done update; the running firmware
 *          is never touched. `fw` alone shows the slots. Portable C99, unit-tested on the PC:
 *          flash, hash and signature are reached through fwup_ops_t.
 */
#ifndef FWUP_H
#define FWUP_H

#include <stddef.h>
#include <stdint.h>

/** @brief Frame type of an image chunk (docs/protocol.md). */
#define FRAME_FW 0x09
/** @brief Bytes before the data in a FW frame (the offset). */
#define FWUP_HDR 4
/** @brief Longest signature accepted, bytes (ECDSA P-256 DER is at most 72). */
#define FWUP_SIG_MAX 80

/** @brief What fwup needs from the platform. Each int function returns 0 on success. */
typedef struct {
    void *ctx;                                            /**< Passed to every call. */
    uint32_t (*max_size)(void *ctx);                      /**< Spare slot size; 0 = no OTA layout. */
    int (*sig_check)(void *ctx, const uint8_t hash[32], const uint8_t *sig, size_t len); /**< Signature over hash. */
    int (*flash_begin)(void *ctx, uint32_t size);         /**< Prepare the spare slot. */
    int (*flash_write)(void *ctx, const uint8_t *p, size_t len); /**< Append to it. */
    int (*flash_finish)(void *ctx);                       /**< Check the image, set boot slot, start trial. */
    void (*flash_abort)(void *ctx);                       /**< Drop a half-written slot. */
    void (*hash_start)(void *ctx);                        /**< Start SHA-256. */
    void (*hash_update)(void *ctx, const uint8_t *p, size_t len); /**< Add bytes. */
    void (*hash_finish)(void *ctx, uint8_t out[32]);      /**< Result. */
    void (*status)(void *ctx, char *buf, size_t n);       /**< "running=ota_0 fw=0.2.0 next=ota_1". */
} fwup_ops_t;

/** @brief Update state (one per session; fwup_init() at session start). */
typedef struct {
    int active;          /**< `fw begin` accepted, image arriving. */
    int failed;          /**< A chunk failed; `fw end` refuses until the next `fw begin`. */
    int done;            /**< `fw end` succeeded: reboot to start the new firmware. */
    uint32_t size;       /**< Image size announced. */
    uint32_t got;        /**< Bytes received so far. */
    uint8_t sha[32];     /**< SHA-256 announced (and signed). */
} fwup_t;

/** @brief Reset to idle. @param u State. */
void fwup_init(fwup_t *u);

/**
 * @brief Handle an `fw ...` command.
 * @param u State. @param ops Platform.
 * @param w Words after "fw". @param nw Their count.
 * @param reply Reply text. @param n Its size.
 * @return 1 OK, 0 error (reply says why).
 */
int fwup_cmd(fwup_t *u, const fwup_ops_t *ops, char **w, int nw, char *reply, size_t n);

/**
 * @brief Handle one FW frame.
 * @param u State. @param ops Platform.
 * @param p Payload (offset + data). @param len Its length.
 * @param err Filled with the reason on failure (sent as EVENT `fw error <reason>`).
 * @param n Size of @p err.
 * @return 0 OK, -1 the update failed (and was dropped).
 */
int fwup_data(fwup_t *u, const fwup_ops_t *ops, const uint8_t *p, size_t len, char *err, size_t n);

/** @brief Drop a half-done update (session ended). @param u State. @param ops Platform. */
void fwup_abort(fwup_t *u, const fwup_ops_t *ops);

/**
 * @brief Boot-time trial check (NOTES I-25): decide whether to fall back.
 * @details `fw end` stores trial = 1. Each boot of the new firmware adds one; the first
 *          client session (HELLO) clears it. So the new firmware gets FWUP_TRIAL_BOOTS boots
 *          to accept a client before the next boot switches back to the previous slot.
 * @param trial Saved trial count, 0 = not on trial.
 * @return 1 to switch back to the other slot now, 0 to carry on (caller then saves trial + 1).
 */
int fwup_should_fall_back(int trial);

/** @brief Boots allowed on new firmware without a client session before falling back. */
#define FWUP_TRIAL_BOOTS 3

#endif /* FWUP_H */
