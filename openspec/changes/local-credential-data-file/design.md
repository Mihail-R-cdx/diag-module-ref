# Design: Local credential data file

## Context

Current root contracts and production bootstrap use the application-root file
`credentials.local.json`, with `credentials.example.json` as the tracked safe
template. The requested change is a filesystem naming change only.

## Canonical naming

After implementation:

```text
runtime local store    data.local.json
tracked safe template  data.example.json
retired secret file    credentials.local.json
```

`data.local.json` remains an unencrypted credential store despite its generic
filename. Its contents, schema, profile semantics, and security classification do
not change.

## Runtime resolution

`JsonCredentialProvider` continues to resolve its default path from the stable
application/project root rather than the process current working directory.

The provider SHALL read only `data.local.json` by default. It SHALL NOT probe,
auto-migrate, merge, or fall back to `credentials.local.json`. If only the retired
legacy file exists, normal missing-canonical-file handling applies before device I/O.

An explicitly injected path used by focused tests remains supported exactly as today.

## Repository protection

Implementation SHALL:

- ignore `data.local.json`;
- retain `credentials.local.json` in ignore/protection rules as a retired sensitive
  filename;
- replace the tracked `credentials.example.json` template with
  `data.example.json`;
- preserve the same non-operational placeholder schema in the renamed template;
- update Graphify/local-corpus exclusions where filename rules are explicit.

Keeping the legacy secret filename ignored is deliberate: renaming the runtime path
must not make an old workstation password file newly visible to Git.

## Compatibility and migration

This is a deliberate canonical rename, not a dual-source compatibility period.
Operators migrate manually by creating/copying the required local values into
`data.local.json`. Production code must not silently consume the legacy filename.

Safe error text SHALL reference `data.local.json` and `data.example.json` and
must not reveal credential/profile values.

## Unchanged architecture

The following remain unchanged:

- `CredentialProvider` / `JsonCredentialProvider` ownership;
- versioned JSON schema and `profiles` / `device_profiles` structure;
- explicit/profile/model source priority;
- application-owned ordered credential fallback;
- successful-index persistence rules;
- worker/handler one-candidate boundaries;
- redaction and no-secret-output requirements;
- plain-text local-store security limitations.
