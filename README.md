# NullSec Network

NullSec Network is a small open-source social network for public text posts and end-to-end encrypted private messages. It is deliberately designed to run on one free PythonAnywhere web app: Python 3.13, Django 5.2, SQLite, WSGI, server-rendered templates and local vanilla JavaScript.

> **Français — résumé.** NullSec Network est un réseau social léger et auto-hébergeable. Les publications sont publiques et stockées en clair, tandis que les messages privés sont chiffrés dans le navigateur avant tout envoi. Le projet défend la confidentialité des communications légales et s’oppose au scan généralisé côté client associé aux propositions dites « Chat Control ». Il est indépendant, sans affiliation officielle avec un autre groupe appelé NullSec, non audité et ne prétend pas remplacer Signal.

## Why this project exists

Small communities should be able to inspect, fork and operate their own social software without buying managed databases, queues or cloud storage. NullSec Network demonstrates that useful privacy properties can fit into a modest, understandable deployment.

The project supports lawful private communication and opposes generalized client-side scanning proposals commonly grouped under the political label “Chat Control.” The exact proposals and legal status evolve, so this repository makes a factual engineering point rather than giving legal advice: scanning content on an endpoint before encryption changes the privacy and security model of end-to-end encrypted communication. NullSec Network neither facilitates nor condones illegal content.

This project is independent and has no official affiliation with any other group or organization named NullSec.

## Features

- Registration, login/logout, editable display name and biography
- User search, follows, blocks, public text posts and deletion
- One-like-per-user engagement, like-ranked feeds and account-scoped, server-visible Seen history
- Post reporting for the local instance administrator
- Private browser-encrypted conversations, unread badges and activity ordering with five-second HTTP polling
- Public-key fingerprints and key-change warnings
- Responsive dark interface with no CDN, external API, uploaded media or attachment support
- Pagination, SQLite indexes and simple per-account/session rate limits

After login, the root URL and Django authentication redirect open the private-conversation list. Public feeds remain available from the navigation. The bundled NullSec logo is used as a subtle same-origin background pattern; no remote visual asset is loaded.

## Architecture

The single WSGI process renders Django templates and handles ordinary forms plus two same-origin JSON endpoints. SQLite stores application data. Static CSS and JavaScript are served locally. There are no WebSockets, background workers, scheduled jobs, external network calls or permanent processes.

Private-message plaintext exists in the sender and recipient browser UI. The server intentionally receives and stores only sender, recipient, Base64 ciphertext, Base64 IV, protocol version and timestamp. It still sees communication metadata. See [Architecture](docs/ARCHITECTURE.md), [Cryptography](docs/CRYPTOGRAPHY.md) and [Threat model](docs/THREAT_MODEL.md).

## Cryptography summary

On the first authenticated page in each browser profile, Web Crypto generates an ECDH P-256 identity. The private `CryptoKey` is non-extractable and stored in IndexedDB; only its public JWK is uploaded. This makes the account reachable for encrypted messages after its first successful login, without requiring it to open a conversation first. For a conversation, ECDH output enters HKDF-SHA-256 with participant-bound salt and protocol-specific info, producing an AES-256-GCM key. Every message uses a fresh random 12-byte IV and direction-bound additional authenticated data. SHA-256 fingerprints of the raw public keys are displayed and a locally remembered contact fingerprint triggers a warning if it changes.

**Important:** clearing site data, losing the browser profile or changing device destroys the local private key and can make old messages permanently unreadable. There is no recovery or escrow. Key changes also make messages encrypted under an earlier identity unreadable.

## Limits

This is a functional privacy-focused application, not an audited cryptographic product. It does not claim Signal-equivalent security. It has no forward secrecy, post-compromise security, multi-device synchronization, key backup, automatic trusted identity verification, traffic-analysis resistance or protection against a malicious server changing the JavaScript it serves. XSS, browser compromise, endpoint malware and account takeover remain serious threats. Metadata is not encrypted. Read the threat model before use.

**High-risk use warning:** do not use this unaudited prototype as the sole communication channel for journalistic sources, whistleblowers or extremely confidential information. Likes, Seen history, read cursors, participants and timing are server-visible metadata. Choose a mature audited messenger and a complete operational-security process for such work.

## Local installation (Python 3.13)

```bash
git clone https://github.com/YOUR_ACCOUNT/NullSec_Network.git
cd NullSec_Network
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
export NULLSEC_DEBUG=True
export NULLSEC_SECRET_KEY='local-development-only-change-me'
export NULLSEC_ALLOWED_HOSTS='localhost,127.0.0.1'
python manage.py migrate
python manage.py test
python manage.py runserver
```

Use `http://127.0.0.1:8000/`. Web Crypto is available on localhost as a secure context. Production must use HTTPS.

An optional `.env.example` is provided for local convenience. Django does not load `.env` files itself, so copy and source it in the shell before running commands:

```bash
cp .env.example .env
# Edit .env and replace the sample secret, then:
set -a
source .env
set +a
python manage.py migrate
python manage.py runserver
```

`.env` is ignored by Git. On PythonAnywhere, keep using the private WSGI environment configuration documented below; do not commit production secrets and do not add `python-dotenv`.

## Forking and publishing on GitHub

Use GitHub’s **Fork** button, then:

```bash
git clone https://github.com/YOUR_ACCOUNT/NullSec_Network.git
cd NullSec_Network
git remote add upstream https://github.com/ORIGINAL_OWNER/NullSec_Network.git
git fetch upstream
```

To publish a new repository instead:

```bash
git init
git add .
git commit -m "Initial NullSec Network release"
git branch -M main
git remote add origin https://github.com/YOUR_ACCOUNT/NullSec_Network.git
git push -u origin main
```

## Free PythonAnywhere deployment

The public address is based on the **actual PythonAnywhere username**, not the repository name:

- US system: `https://USERNAME.pythonanywhere.com`
- EU system: `https://USERNAME.eu.pythonanywhere.com`

If `nullsec` is available as an account name on the selected system, the US address would be `https://nullsec.pythonanywhere.com`; availability is not guaranteed.

Open a Bash console on PythonAnywhere and run (replace every placeholder):

First, on **Account → System image**, select the current `innit` image if `python3.13` is not available in the console. Then run:

```bash
git clone https://github.com/YOUR_ACCOUNT/NullSec_Network.git ~/NullSec_Network
cd ~/NullSec_Network
python3.13 -m venv ~/.virtualenvs/nullsec
source ~/.virtualenvs/nullsec/bin/activate
python -m pip install -r requirements.txt
export NULLSEC_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"
export NULLSEC_ALLOWED_HOSTS='USERNAME.pythonanywhere.com'
export NULLSEC_CSRF_TRUSTED_ORIGINS='https://USERNAME.pythonanywhere.com'
export NULLSEC_DEBUG=False
python manage.py migrate
python manage.py test
python manage.py collectstatic --noinput
```

For the EU system, use `USERNAME.eu.pythonanywhere.com` in both variables. Save the generated secret somewhere private before closing the console; it must remain stable.

On the PythonAnywhere **Web** tab:

1. Create a new manual-configuration web app using Python **3.13**.
2. Set **Virtualenv** to `/home/USERNAME/.virtualenvs/nullsec`.
3. Open the WSGI configuration file and replace its contents with the following, inserting the real username, hostname and previously generated secret:

```python
import os
import sys

project_home = "/home/USERNAME/NullSec_Network"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.environ["DJANGO_SETTINGS_MODULE"] = "nullsec_network.settings"
os.environ["NULLSEC_SECRET_KEY"] = "PASTE_THE_STABLE_RANDOM_SECRET_HERE"
os.environ["NULLSEC_ALLOWED_HOSTS"] = "USERNAME.pythonanywhere.com"
os.environ["NULLSEC_CSRF_TRUSTED_ORIGINS"] = "https://USERNAME.pythonanywhere.com"
os.environ["NULLSEC_DEBUG"] = "False"

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

For EU, change both host strings to `USERNAME.eu.pythonanywhere.com`. Do not commit this WSGI file or its secret.

4. Under **Static files**, add URL `/static/` and directory `/home/USERNAME/NullSec_Network/staticfiles`.
5. Enable **Force HTTPS** on the Web tab. HTTPS is required by Web Crypto and secure cookies.
6. Press **Reload USERNAME.pythonanywhere.com** (or the EU hostname).

For later updates:

```bash
cd ~/NullSec_Network
git pull --ff-only
source ~/.virtualenvs/nullsec/bin/activate
export NULLSEC_SECRET_KEY='THE_SAME_STABLE_SECRET'
export NULLSEC_ALLOWED_HOSTS='USERNAME.pythonanywhere.com'
export NULLSEC_CSRF_TRUSTED_ORIGINS='https://USERNAME.pythonanywhere.com'
export NULLSEC_DEBUG=False
python manage.py migrate
python manage.py test
python manage.py collectstatic --noinput
```

Then reload the web app from the Web tab. SQLite’s `db.sqlite3` is intentionally excluded from Git; back it up separately and restrict access to the account.

The Django admin is available at `/admin/` for moderation. Create a dedicated superuser with `python manage.py createsuperuser`, use a long unique password, keep `DEBUG=False`, require HTTPS, and never register private-message ciphertext in the admin.

## Free-tier compatibility checklist

- One PythonAnywhere web worker: yes
- Python 3.13 / Django 5.2 / SQLite / WSGI: yes
- Permanent process or background task: none
- Outbound Internet access at runtime: none
- Redis, paid database, storage or service: none
- WebSocket/ASGI/Channels: none
- Build tool or Node dependency: none

## License

MIT. See [LICENSE](LICENSE).
