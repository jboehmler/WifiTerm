/**
 * @file tls.h
 * @brief The one TLS server session (mbedTLS), with the client certificate required (R12).
 * @details Only one session exists at a time; a second connection is closed before TLS (no
 *          RAM for two). The ESP has no clock, so certificate dates are checked against a
 *          lower-bound time (see clock in bridge.c): "not yet valid" is ignored, "expired" is enforced.
 */
#ifndef TLS_H
#define TLS_H

#include <stddef.h>
#include <stdint.h>

/** @brief Load the embedded CA, server certificate and key; set up the config. @return 0 on success. */
int tls_init(void);

/**
 * @brief Run the TLS handshake on an accepted socket.
 * @param fd Socket from accept(); owned by tls.c from here on, even on failure.
 * @param timeout_ms Handshake time limit.
 * @return 0 when the session is up (client certificate verified).
 */
int tls_start(int fd, unsigned timeout_ms);

/** @brief Socket of the session, for select(). @return fd, or -1 if no session. */
int tls_fd(void);

/** @brief Nonzero if decrypted bytes are waiting (read them even if select() says nothing). */
int tls_pending(void);

/**
 * @brief Read decrypted bytes without waiting.
 * @return Bytes read (> 0), 0 if nothing is available, or < 0 if the session ended.
 */
int tls_read(uint8_t *buf, size_t n);

/**
 * @brief Send all bytes, waiting (up to @p timeout_ms) while the client is slow.
 * @return 0 on success, < 0 if the session failed.
 */
int tls_write(const uint8_t *buf, size_t n, unsigned timeout_ms);

/** @brief End the session and close its socket. */
void tls_close(void);

#endif /* TLS_H */
