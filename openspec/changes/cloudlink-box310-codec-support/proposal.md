# Change: cloudlink-box310-codec-support

## Why

The application supports `CloudLink Bar 310`, but it does not recognize or dispatch the distinct Huawei VCS codec model `CloudLink Box 310`. The Box 310 uses the same management protocol and supported command semantics as the existing Bar 310 implementation, so adding support must extend exact model identity without creating a second independent protocol implementation.

The current architecture intentionally uses closed exact registries. The equipment importer recognizes only reviewed canonical `diagnostic_model` values, application dispatch accepts only exact registered models, and the Bar 310 handler/worker/parser path currently validates one exact Bar identity. Adding Box 310 therefore requires an explicit reviewed change rather than runtime alias guessing or fuzzy fallback.

## What Changes

- Add exact canonical inventory model `CloudLink Box 310`.
- Recognize Box 310 from the existing deterministic component recognizer using exact components `cloudlink`, `box`, and `310` in either approved model-text evidence field.
- Add `CloudLink Box 310` to the application closed dispatch registry and codec equipment-page registry.
- Route `CloudLink Box 310` to the same existing `cloudlink_bar_310` diagnostic lifecycle and connection-profile policy as `CloudLink Bar 310`.
- Reuse the existing `CloudLinkBar310Handler` protocol implementation and Bar 310 command semantics instead of cloning the handler or command map.
- Preserve distinct product identity: Bar 310 displays/validates as `Huawei CloudLink Bar 310`; Box 310 displays/validates as `Huawei CloudLink Box 310`.
- Bind the expected handler/parser identity from the already assigned exact application model. The handler, worker, parser, interactive session, related-codec status path, and existing supported codec actions must not infer or switch the product model from response text or failures.
- Extend all currently supported Bar 310 codec operations that depend on exact model routing, including ordinary refresh, supported interactive operations, related-codec read-only enrichment, and the existing SIP-server action, to Box 310 through the shared protocol implementation.
- Keep credential selection, successful credential-index memory, and connection-profile memory model-bound. Supporting the same protocol does not authorize implicit credential sharing or fallback between Bar 310 and Box 310.
- Keep existing Bar 310 behavior unchanged.

## Impact

Affected specifications:

- `equipment-inventory-snapshot`
- `diagnostic-application-shell`
- `request-lifecycle-and-recovery`

Expected implementation areas:

- `tools/import_equipment_inventory.py`
- `docs/equipment-inventory-runbook.md`
- `gui/diagnostic_dispatch.py`
- `gui/equipment_pages.py`
- `gui/main_window.py`
- `core/codec_connection_profiles.py`
- `core/interactive_session.py`
- `core/related_codec_status.py`
- `core/workers/codec_polling.py`
- `core/workers/codec_actions.py`
- `handlers/huawei/bar310.py`
- `core/parser.py`
- focused synthetic tests for inventory recognition, dispatch, shared Bar/Box protocol behavior, interactive/related-codec routing, and regression coverage

This change does not add a new transport protocol, new device commands, new credential fallback policy, new retry policy, a new GUI page, production inventory data, or Graphify artifacts.
