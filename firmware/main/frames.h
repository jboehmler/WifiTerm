/**
 * @file frames.h
 * @brief WiFi Terminal protocol v1 framing: `type | len | payload` (docs/protocol.md).
 * @details Portable C99, no ESP headers, so the same file is unit-tested on the PC with gcc.
 *          Wire format: 1-byte type, 2-byte big-endian length, then 0..1024 payload bytes.
 */
#ifndef FRAMES_H
#define FRAMES_H

#include <stddef.h>
#include <stdint.h>

/** @brief Lowest protocol version this firmware speaks. */
#define PROTO_MIN 1
/** @brief Highest protocol version this firmware speaks. */
#define PROTO_MAX 1
/** @brief Largest payload allowed in one frame. */
#define FRAME_MAX_PAYLOAD 1024
/** @brief Header size: type byte plus 16-bit length. */
#define FRAME_HEADER_LEN 3
/** @brief Largest encoded frame. */
#define FRAME_MAX_LEN (FRAME_HEADER_LEN + FRAME_MAX_PAYLOAD)

/** @brief Frame type codes. */
typedef enum {
    FRAME_HELLO = 0x01, /**< Version and capability exchange, first frame each way. */
    FRAME_DATA = 0x02,  /**< Bytes to or from the RS-232 device. */
    FRAME_CMD = 0x03,   /**< Command, client to ESP: "<seq> <text>". */
    FRAME_RESP = 0x04,  /**< Reply, ESP to client: "<seq> OK|ERR <text>". */
    FRAME_EVENT = 0x05, /**< Unsolicited notice from the ESP. */
    FRAME_PING = 0x06,  /**< Keepalive request. */
    FRAME_PONG = 0x07,  /**< Keepalive reply, same payload as the PING. */
    FRAME_LOG = 0x08,   /**< ESP log lines, after "log on". */
} frame_type_t;

/** @brief Result of feeding bytes to the decoder. */
typedef enum {
    FRAME_NEED_MORE = 0, /**< No complete frame yet. */
    FRAME_READY = 1,     /**< A frame is complete; read it with frame_decoder_type/payload. */
    FRAME_BAD = -1,      /**< Header announced a payload over FRAME_MAX_PAYLOAD; drop the session. */
} frame_status_t;

/**
 * @brief Incremental decoder state. Holds at most one frame, so it needs no heap.
 * @details Usage: call frame_decoder_feed() with received bytes; each FRAME_READY result
 *          means one frame is available until the next feed call.
 */
typedef struct {
    uint8_t hdr[FRAME_HEADER_LEN];       /**< Header bytes collected so far. */
    size_t hdr_got;                      /**< Number of header bytes collected. */
    uint16_t len;                        /**< Payload length from the header. */
    size_t got;                          /**< Payload bytes collected. */
    uint8_t payload[FRAME_MAX_PAYLOAD + 1]; /**< Payload, plus a NUL so text payloads are C strings. */
} frame_decoder_t;

/** @brief Reset a decoder to empty. @param d Decoder. */
void frame_decoder_init(frame_decoder_t *d);

/**
 * @brief Consume bytes until one frame completes or the input runs out.
 * @param d Decoder.
 * @param data Received bytes.
 * @param len Number of bytes in @p data.
 * @param used Set to how many bytes were consumed; call again with the rest.
 * @return FRAME_READY, FRAME_NEED_MORE or FRAME_BAD.
 */
frame_status_t frame_decoder_feed(frame_decoder_t *d, const uint8_t *data, size_t len, size_t *used);

/** @brief Type of the completed frame. @param d Decoder. @return Type code. */
static inline uint8_t frame_decoder_type(const frame_decoder_t *d) { return d->hdr[0]; }

/** @brief Payload of the completed frame, NUL-terminated. @param d Decoder. @return Payload. */
static inline const uint8_t *frame_decoder_payload(const frame_decoder_t *d) { return d->payload; }

/** @brief Payload length of the completed frame. @param d Decoder. @return Length. */
static inline size_t frame_decoder_len(const frame_decoder_t *d) { return d->len; }

/**
 * @brief Encode one frame into @p out.
 * @param out Destination, at least FRAME_HEADER_LEN + @p len bytes.
 * @param type Frame type.
 * @param payload Payload bytes (may be NULL when @p len is 0).
 * @param len Payload length, at most FRAME_MAX_PAYLOAD.
 * @return Encoded length, or 0 if @p len is too large.
 */
size_t frame_encode(uint8_t *out, uint8_t type, const void *payload, size_t len);

/**
 * @brief Encode a RESP frame "<seq> OK|ERR <text>".
 * @param out Destination, FRAME_MAX_LEN bytes.
 * @param seq Sequence number of the command being answered.
 * @param ok Nonzero for OK, zero for ERR.
 * @param text Reply text (may be empty or NULL); truncated to fit.
 * @return Encoded length.
 */
size_t frame_encode_resp(uint8_t *out, unsigned seq, int ok, const char *text);

/**
 * @brief Split a CMD payload "<seq> <text>".
 * @param payload NUL-terminated CMD payload.
 * @param seq Set to the sequence number.
 * @param text Set to point at the command text inside @p payload (may be empty).
 * @return 0 on success, -1 if there is no valid sequence number (1..65535).
 */
int frame_parse_cmd(const char *payload, unsigned *seq, const char **text);

/**
 * @brief Pick the protocol version from a client HELLO "proto=<min>-<max> ...".
 * @param payload NUL-terminated HELLO payload.
 * @return Highest version both sides speak, or 0 if there is none.
 */
int frame_choose_proto(const char *payload);

#endif /* FRAMES_H */
