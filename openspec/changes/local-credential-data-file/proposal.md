# Change: Local credential data file

## Why

The local plain-text device-password store is currently named `credentials.local.json`.
The desired operator-facing filesystem name is the neutral `data.local.json`.
The rename is intentionally limited to the local JSON filenames; credential-provider
semantics, schema, ownership, fallback policy, and secret-handling rules remain unchanged.

## What Changes

- Rename the canonical untracked runtime store from `credentials.local.json` to
  `data.local.json`.
- Rename the tracked safe template from `credentials.example.json` to
  `data.example.json`.
- Keep the retired `credentials.local.json` filename ignored as a secret-bearing
  legacy filename so an old workstation file cannot become accidentally trackable.
- Do not read or fall back to the retired filename at runtime. `data.local.json`
  is the single canonical provider path after implementation.
- Update safe missing-file guidance, tests, ignore rules, and operator documentation
  to the new names.
- Normalize every current root requirement that still names the retired runtime file: use `data.local.json` where the canonical path matters and durable `local credential store` / `provider storage` wording where the requirement is only about ownership. Archived OpenSpec history remains untouched.
- Preserve all internal credential terminology such as `CredentialProvider`,
  `JsonCredentialProvider`, credential profiles, candidate ordering, and redaction.

## Out of Scope

- Changing the JSON schema or profile names.
- Encrypting the local store or introducing a new secure provider.
- Changing credential fallback/retry ownership.
- Renaming Python credential classes/modules merely because the filesystem name changes.
- Editing archived OpenSpec history.

## Expected Result

Operators create `data.local.json` from `data.example.json` in the application
root. The application reads only that canonical file, while both the new local file
and the retired secret-bearing legacy filename remain protected from accidental Git
publication.
