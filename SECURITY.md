# Security Policy

NullSec Network is a privacy-focused educational application. It has not been professionally audited and must not be represented as equivalent to Signal or another mature secure messenger.

## Supported version

Security fixes target the current `main` branch. Instance operators should follow upstream changes and apply security updates promptly.

## Reporting a vulnerability

Do not open a public issue for an unpatched vulnerability. Contact the repository owner through a private GitHub security advisory (“Security” → “Advisories” → “Report a vulnerability”). Include affected versions, reproduction steps, impact and any suggested mitigation. If private reporting is unavailable, ask the owner for a private channel without disclosing exploit details.

No bounty or response deadline is promised. Please avoid accessing other users’ data, disrupting a public instance, or retaining data beyond what is necessary to demonstrate the issue.

## Operator responsibilities

Keep Python and Django patched, protect the PythonAnywhere account, use a unique secret key, keep `DEBUG=False`, enforce HTTPS, review reports, back up SQLite securely, and review local law. Backups contain public content, account metadata, relationship metadata and private-message ciphertext.
