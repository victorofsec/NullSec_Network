# Cryptography

## Protocol version 1

NullSec Network’s private-message design aims to keep message content out of the server’s intentional plaintext data flow. It uses only Web Crypto API implementations supplied by the browser.

### Identity generation

On the first authenticated page, the browser calls `crypto.subtle.generateKey` for ECDH on P-256 with the extractable argument set to `false`. Web Crypto keeps the private key non-extractable while allowing export of the public half. IndexedDB stores the private `CryptoKey` using structured cloning alongside the exported public JWK. The application sends only that public JWK to the authenticated user’s profile. Conversation pages reuse the same shared initialization promise, preventing concurrent generation of competing identities.

There is one identity per NullSec username and browser storage profile. No private-key export, escrow, recovery, multi-device transfer or server backup is implemented.

### Shared key derivation

For users `A` and `B`:

1. Import the contact’s P-256 public JWK.
2. Compute 256 ECDH bits from the local private key and contact public key.
3. Import those bits as HKDF key material.
4. Compute the salt as `SHA-256(UTF8("NullSecNetwork-v1|" + sort(A,B).join("|")))`.
5. Use HKDF-SHA-256 with info `UTF8("private-message")` to derive a non-extractable 256-bit AES-GCM key.

Both directions use the same derived AES key. Direction is authenticated separately.

### Message encryption

For every message, the browser creates a new 12-byte IV with `crypto.getRandomValues`. AES-256-GCM encrypts UTF-8 plaintext with a 128-bit authentication tag. Additional authenticated data is:

`UTF8("NullSecNetwork-v1|" + sender_username + "|" + recipient_username)`

Ciphertext (including the GCM tag) and IV are Base64-encoded for JSON transport. The server adds identity from the authenticated session and URL, protocol version and timestamp. It does not accept sender or recipient identity from the JSON body.

### Fingerprints and changes

The fingerprint is SHA-256 of the uncompressed raw P-256 public key, shown as grouped hexadecimal. The browser remembers the last contact fingerprint in local storage. If the served key changes, sending is disabled and a prominent warning asks the user to compare the new value over a separate trusted channel before accepting it.

Fingerprint comparison is manual and optional. A first-use key can be substituted by a malicious server or network attacker controlling TLS. HTTPS protects transport but does not make the application server a trusted identity authority.

## Failure and deletion semantics

Deleting browser site data destroys the private key. Changing devices or browser profiles creates another key. Previous ciphertext generally becomes unreadable after key loss or identity replacement. The server cannot reset or reconstruct a private key. This is an intended consequence of not having server-side key escrow.

## Non-claims

The design has not been professionally audited. It is not the Signal protocol. In particular, a long-lived ECDH identity does not provide per-message forward secrecy, a ratchet, post-compromise security, deniability or multi-device consistency. The server supplies executable JavaScript and can replace it for future sessions. Use a mature audited messenger where the risk requires those properties.
