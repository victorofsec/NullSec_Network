# Threat Model

## Goals

- Keep honest-server database contents and routine HTTP request bodies from containing private-message plaintext.
- Detect accidental corruption through AES-GCM authentication.
- Make contact public-key changes visible after first use.
- Enforce authenticated ownership and block boundaries on the server.
- Reduce common web risks with CSRF protection, auto-escaping, strict CSP, local static assets and secure production cookies.

## Protected assets

Private-message plaintext and local ECDH private keys are the primary protected assets. Account credentials, sessions, public posts, reports and social relationships also require ordinary web-application protection.

## Considered attackers

- A reader of a copied SQLite database sees ciphertext and metadata, not private-message plaintext.
- A network observer is constrained by correctly configured HTTPS but sees traffic timing and volume.
- Another authenticated user is constrained by Django authorization and block checks.
- Stored public content is untrusted and is escaped by Django; client-rendered message text uses DOM `textContent`, never `innerHTML`.
- Basic automated abuse is slowed by per-session or per-account limits.

## Out of scope or incompletely mitigated

- **Malicious/compromised server:** the server serves the JavaScript and can modify it to capture future plaintext or keys. Reproducible review and deployment discipline help operationally but do not remove this trust.
- **Endpoint compromise:** malware, a hostile browser extension, developer tools access, or injected same-origin code may read plaintext while displayed or before encryption.
- **Traffic analysis:** participants, dates, IP logs, size, frequency, unread counters and read cursors are not hidden. Likes and Seen history are also server-visible.
- **First-use substitution:** fingerprints provide trust-on-first-use only until users compare them out of band.
- **Key loss:** local storage deletion permanently removes the private key and can destroy access to history.
- **Cryptographic evolution:** there is no double ratchet, forward secrecy, post-compromise security, key transparency or multi-device protocol.
- **Availability:** a free single-worker instance and SQLite can be exhausted or unavailable. Rate limits are not DDoS protection.
- **Administration:** an instance operator can remove public posts and accounts through Django admin and can see reports and metadata.
- **Legal guarantees:** encryption does not determine legal obligations. Operators and users must understand their jurisdiction.

## Data classification

Public posts, usernames, display names and biographies are public plaintext. Email (if supplied), password hashes, sessions, follows, blocks and reports are server-private operational data. Message sender, recipient, time, IV, protocol version and ciphertext are server-visible. Private-message plaintext and private keys are intended to exist only at endpoints.

## Recommended operation

Use a unique stable secret key, force HTTPS, protect the hosting account with strong authentication, update Django/Python, limit admin access, keep encrypted/restricted backups, review security reports and disclose the application’s limitations to users.
