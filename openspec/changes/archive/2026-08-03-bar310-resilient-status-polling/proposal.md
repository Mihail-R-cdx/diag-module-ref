# Change: bar310-resilient-status-polling

## Why

The current CloudLink Bar 310 refresh path gathers several useful device fields and then iterates every remaining entry in the handler command map, including configuration endpoints that are not part of ordinary status polling. A later unsupported, malformed, or temporarily unavailable endpoint can therefore raise after model, version, MAC, SIP, audio, and camera data were already collected.

`CloudLinkBar310Handler.get_status()` catches every exception and returns an empty mapping. `HuaweiBar310Worker` then parses that empty mapping, adds only technical connection metadata, and emits it through the success result signal. The GUI receives no canonical display fields, the typed failure classification is lost, established-session recovery cannot run correctly, and a failed refresh can be treated as a successful credential/profile outcome.

Presentation and sleep endpoints are also queried without populating the canonical `presentation` and `sleep_mode` fields consumed by the parser, so successful device responses can still be replaced by false default states.

## What Changes

- Replace command-map enumeration with an explicit reviewed CloudLink Bar 310 read-only status plan.
- Make `get_version` the required core identity request for a successful refresh.
- Treat MAC, audio, line/SIP, call, presentation, sleep, camera, and HD-AI microphone reads as optional status enrichment.
- Exclude configuration endpoints and every state-changing endpoint from ordinary status polling.
- Preserve structured `AuthenticationError`, `SessionInvalidError`, and `ConnectionError` failures instead of converting them to `{}`.
- Treat a required-core command or payload failure as a typed refresh failure.
- Isolate optional endpoint command/protocol failures so they omit only unavailable fields and do not erase already collected status.
- Do not manufacture semantic defaults such as `Off`, `Stop`, `No Call`, or zero volume when the corresponding optional endpoint was unavailable.
- Normalize presentation and sleep responses through shared parsing helpers used by both full refresh and interactive readback.
- Reject empty, non-mapping, or core-less Bar 310 payloads at the worker/parser boundary before adding `ip_address` or `connection_profile` metadata.
- Emit a worker error, perform cleanup, and emit completion without a success result when the payload is unusable.
- Add focused synthetic regression coverage for partial status, typed terminal failures, empty-result rejection, presentation/sleep normalization, and signal cleanup lifecycle.

## Impact

Affected specification:

- `request-lifecycle-and-recovery`

Expected implementation areas:

- `handlers/huawei/bar310.py`
- `core/workers/codec_polling.py`
- `core/parser.py`
- `tests/test_bar310_status_polling.py`

This change does not alter credential candidate ownership or order, successful credential memory authority, connection-profile retry order, interactive operation serialization, stale callback rules, GUI layout, equipment inventory, model recognition, other codec handlers, PDU/Matrix/audio-DSP behavior, or Graphify artifacts.
