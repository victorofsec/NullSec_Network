# Architecture

## Design constraints

NullSec Network targets a free PythonAnywhere web app. Its runtime is one Python 3.13 WSGI application using Django 5.2 and one local SQLite file. Django templates produce all pages; local vanilla CSS and JavaScript add presentation and browser cryptography. Nothing requires an always-running process.

## Components

1. **Browser:** renders HTML, stores the non-extractable ECDH private `CryptoKey` in IndexedDB, stores observed contact fingerprints in local storage, encrypts outgoing private-message text and decrypts incoming ciphertext.
2. **Django WSGI application:** authenticates sessions, validates forms and JSON, enforces ownership/block rules, renders pages, exposes key and ciphertext endpoints, and applies security headers.
3. **SQLite:** stores Django authentication/session data, profiles, follows, blocks, public posts, reports, public JWKs and encrypted message records.
4. **Local static directory:** contains one stylesheet and two scripts. `collectstatic` copies them for PythonAnywhere’s static-file mapping.

## Request flows

Public features use ordinary CSRF-protected forms. Lists use 20-row pages and `select_related` where profiles are displayed. Indexed columns cover post timelines and both directions of message retrieval.

Private conversations use `GET /api/keys/`, `POST /api/keys/`, `GET|POST /api/messages/<username>/` and a validated read-cursor endpoint. Polling requests at most 100 records newer than the last observed numeric ID every five seconds. The API never accepts a plaintext property. Server-side message validation accepts only `ciphertext`, `iv` and protocol version 1, then supplies authenticated sender, recipient and creation time. A separate conversation-state table stores last activity, unread count and read cursor so the encrypted-message table remains unchanged. These values are metadata, not end-to-end encrypted content.

Public feeds annotate posts with unique like counts and rank by count, creation time and ID. A user cannot like their own post. Seen records remove acknowledged posts from active feeds and supply a private server-side history ordered by acknowledgement time.

## Authorization boundaries

- Login is required for all social and message functions.
- Only an author may delete their post.
- Users cannot follow or message themselves.
- A block in either direction prevents profile visibility where appropriate, public-key lookup and private-message access.
- Creating a block removes follows in both directions.
- Reports are unique per reporter and post; a repeated report updates its reason.
- Private messages are selected only through a query constrained to the authenticated user and named contact.

## Security headers and production settings

The application sends a CSP limited to same-origin scripts, styles, fonts, connections and the bundled logo; objects and frames are disabled. It also sends Permissions Policy, clickjacking, MIME-sniffing and referrer protections. Production settings require an environment-provided secret, use secure SameSite cookies, redirect to HTTPS and enable HSTS. Template auto-escaping is retained, and JavaScript adds user content only with `textContent`.

## Capacity model

SQLite is suitable for a small instance and a single worker, not high write concurrency. Search is capped at 50 results and session-limited to 20 attempts/minute; publishing is limited to five posts/minute/account; private sending is limited to 30 messages/minute/account. These database/session limits are simple abuse friction, not a distributed denial-of-service defense.

## Deployment properties

The runtime does not make outbound requests. Git and package installation need network access only during deployment. There are no uploads, media processors, queues, scheduled tasks, WebSockets, email integrations or cloud services.
