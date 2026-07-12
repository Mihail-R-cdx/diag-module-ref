# Local device credentials

The first credential provider uses a plain-text, **unencrypted** local JSON
file. It is intentionally a small migration step, not a secure vault.

## Setup

1. Copy `credentials.example.json` to `credentials.local.json` in the
   application root (beside `main.py`).
2. Replace only the placeholders with credentials approved for that
   workstation. Choose `username_password`, `password`, or `unauthenticated`
   for each named profile.
3. Map each device model in `device_profiles` to its profile. A request uses an
   explicit profile when supplied; otherwise it uses the selected model's map.
   Direct caller/test credentials take priority over either source.

`credentials.local.json` is ignored by Git. Never add, commit, email, or copy
it through Git. On every new PC, create a fresh local file from the example;
Git does not create, retrieve, or transfer it.

## Plain-text limitations

The JSON provider does not encrypt its file. Limit its filesystem permissions
to the local operator, do not place it in shared folders, and exclude it from
untrusted synchronization and backup locations. Use your organization's local
workstation and backup policy. A future secure provider (for example Windows
Credential Manager) can replace this provider without changing workers or
handlers.

## Incident guidance

For a suspected prior exposure, inspect tracked history with value-safe
commands such as `git log --all -- <path>` and report paths/categories only.
If an operational credential is confirmed, remove it from current code and
rotate it under the incident process. Any Git-history rewrite requires separate
approval; do not rewrite history as part of normal migration work.
