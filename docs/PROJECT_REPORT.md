# Project Report

## Abstract

NullSec Network is a compact social-network implementation designed around two objectives: self-hosting on a no-cost PythonAnywhere account and preventing an honest application server from intentionally receiving private-message plaintext. The result combines conventional public social features with browser-side authenticated encryption, using a deployment model suitable for an academic demonstration and small community instance.

## Context and motivation

Mainstream social systems are operationally complex and often centralized. This project asks what useful subset can remain inspectable and deployable by one person: accounts, profiles, follows, a public text timeline, moderation primitives and private conversation. Restricting the stack to Django, SQLite, WSGI and standard browser APIs removes paid infrastructure and build-chain dependencies.

The project also responds to debate around generalized client-side scanning, often associated with proposals labelled “Chat Control.” Its position is that lawful private communication is a legitimate security goal and that inspecting content on the endpoint before encryption changes an end-to-end encryption promise. This is stated as a serious technical and policy position, not legal advice or support for illegal activity.

## Requirements analysis

The free-tier target rules out persistent workers, WebSockets, managed queues and paid databases. Five-second HTTP polling gives acceptable small-scale message delivery within ordinary request/response WSGI. Text-only content removes file-storage, malware-scanning and quota concerns. Django authentication, forms, ORM and templates provide a narrow dependency surface; the sole declared package is Django 5.2.

Privacy requirements split the product into two clear classes. Public posts are deliberately plaintext. Private messages are opaque envelopes whose sender and recipient come from authenticated server context. This prevents a misleading interface from suggesting that all social data is encrypted.

## Implementation

The data model uses Django’s built-in user and session system. One-to-one profiles hold display data and a public JWK. Unique constraints prevent duplicate follows, blocks and reports. Indexed timestamps and participant pairs support paginated feeds and incremental conversation retrieval.

All state-changing HTML actions are POST requests with CSRF tokens. JSON writes also require Django’s CSRF cookie/header flow. Views validate lengths, types, protocol version and permissions. Blocks apply in either direction to key and message endpoints. Django templates escape public content, and the cryptographic client creates DOM nodes and sets `textContent` for decrypted user data.

The CSP forbids third-party and inline scripts, object embedding, images and framing. Production configuration refuses to start without an environment secret, disables debugging, uses secure cookies, redirects HTTPS and enables HSTS. Operators must manually set the real PythonAnywhere hostname.

## Cryptographic design

The browser creates a non-extractable P-256 ECDH private key and stores the `CryptoKey` in IndexedDB. Its public JWK is the only identity-key material sent to Django. ECDH shared output is passed through HKDF-SHA-256 with version and participant binding, then used as an AES-256-GCM key. A random 96-bit IV is generated for each message; protocol version and direction are authenticated as context. The server stores only opaque encrypted envelopes and metadata.

SHA-256 public-key fingerprints offer manual comparison. Local trust-on-first-use state exposes later key changes and requires explicit acknowledgement before sending. This is useful but weaker than authenticated key directories or safety-number ceremonies in mature protocols.

## Verification strategy

The Django suite covers account creation, profile creation, access control, ownership deletion, reporting, block enforcement, like uniqueness and ranking, Seen-history isolation, unread notifications, validated read cursors, conversation ordering, public-key validation, the exact private-message schema, encrypted-envelope persistence, rate limiting, pagination/security headers and absence of `innerHTML` in shipped JavaScript. Django system checks, migration-drift checks and `collectstatic` verify packaging.

Cryptographic interoperability still requires browser testing because Django tests do not execute Web Crypto. Review should use two accounts in separate browser profiles, compare fingerprints, exchange messages, reload, simulate a key replacement and then clear site data to confirm documented failure behaviour.

## Ethics, legality and independence

NullSec Network is independent and not officially affiliated with another entity called NullSec. It is a general-purpose communication tool. Instance operators should publish rules, review reports, obey applicable law and avoid claiming that encryption eliminates moderation or legal responsibilities. Public post reporting supports local moderation without pretending that the server can inspect private plaintext.

## Limitations and future research

The strongest limitation is delivery of cryptographic code by the same server from which the user seeks content confidentiality. A malicious deployment can change that code. The long-lived static ECDH model lacks forward secrecy and post-compromise recovery. Local-only identity makes recovery and multiple devices intentionally difficult. Polling increases metadata and request load. SQLite constrains write concurrency.

Future academic work could examine signed reproducible clients, key transparency, QR-based verification, a carefully designed ratchet, accessible encrypted export, improved local abuse controls and formal protocol analysis. Those changes should not be presented as complete until independently reviewed.

## Conclusion

Within its explicit scope, NullSec Network demonstrates a complete zero-paid-service social application with meaningful content privacy against an honest server and database reader. Its value depends on precise claims: it is functional, small and inspectable, but neither audited nor equivalent to established secure messengers.
