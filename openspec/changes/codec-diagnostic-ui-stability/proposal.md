# Change: Stabilize codec diagnostic UI behavior

## Why

The modern room codec dashboard is now the approved presentation for `Huawei TE20`, `Huawei TE40`, `CloudLink Bar 310`, `CloudLink Box 310`, and `Polycom RPG 310`, but several user-visible behaviors are not yet consistent with the approved room interaction and model-neutral diagnostic contracts.

Observed product gaps are concentrated in one architecture-connected surface:

- call-history preview/statistics are not reliably available with the same semantics on all five codecs, duration/direction presentation is inconsistent, and `CloudLink Box 310` requires an explicit end-to-end regression oracle;
- the codec dashboard still exposes presentation elements that are no longer desired (`Платформа` and codec-local `Отладка`);
- speaker volume presentation/control can remain unavailable or appear stuck instead of showing accepted current percentage and completing through the existing mutation/reconciliation lifecycle;
- microphone level needs explicit `supported` / `unsupported` / `no-data` presentation semantics without expanding protocol capability by inference;
- codec `Обновить статус` can surface an erroneous/duplicate error path instead of reflecting the single exact-row `LOCAL_REFRESH` result.

These are not independent redesigns. They share the same exact-row authority, unified model registration, serialized interaction lane, typed-failure rules, and stale-result rejection boundary. They SHOULD therefore be corrected in one reviewed stability change so the implementation cannot fix symptoms by creating parallel GUI-owned network paths.

## What Changes

- Tighten normalized codec call-history presentation so all five supported codec models use one typed direction/duration/statistics contract, including automatic room-card preview and the existing detailed journal flow.
- Require end-to-end regression coverage for the exact `CloudLink Box 310` call-history/statistics path.
- Remove the `Платформа` row from the modern room codec `Состояние` card while retaining platform data internally where existing diagnostics still provide it.
- Remove the codec-dashboard `Отладка` affordance only; approved Debug presentation for other device families remains unchanged.
- Remove any speaker-volume meter/scale from the modern codec dashboard and render accepted current speaker volume as a model-neutral percentage between `−` and `+`.
- Keep speaker mutation target/reconciliation authority separate from that display percentage and require volume controls to complete only through the existing serialized `MUTATION` -> `RECONCILIATION` lifecycle.
- Make modern room microphone-meter presentation explicit: the current approved live meter is `SUPPORTED` only for `CloudLink Bar 310` and `CloudLink Box 310`; supported models with no accepted current sample show `Нет данных`; `Huawei TE20`, `Huawei TE40`, and `Polycom RPG 310` show `Не поддерживается` and perform no meter I/O because this change does not approve a new meter protocol for them.
- Tighten codec Local Refresh completion so `Обновить статус` remains an alias of the existing exact-row `LOCAL_REFRESH` lifecycle and stale/cancelled/superseded outcomes cannot display an error for the current row.

## Capabilities

### Modified capabilities

- `diagnostic-ui-presentation`
  - remove `Платформа` from the modern codec state card;
  - remove speaker-volume scale/bar and show accepted percentage in the speaker control row;
  - expose explicit microphone-meter supported/unsupported/no-data presentation semantics.
- `room-device-interaction-lifecycle`
  - make codec Debug a presentation-visibility exception like the already-approved modern PDU exception;
  - tighten codec Local Refresh and volume-control completion/stale-result behavior without creating a second network owner.

### Extended capabilities

- `codec-call-log-usage-statistics`
  - add typed direction parity, duration/statistics parity, initial room-preview acceptance, and exact Box 310 regression requirements while preserving existing acquisition ownership and product-limit semantics.
- `device-diagnostics-and-control`
  - add a display-only accepted `speaker_volume_percent` projection and exact baseline semantics for codec audio presentation; existing raw/canonical mutation state remains authoritative for control/reconciliation.

## Impact

### Production areas expected to be touched during implementation

Implementation is expected to affect only the current room codec composition/presentation, codec application projection/normalization, existing call-history adapters/normalization where evidence is currently missing or mapped incorrectly, and focused regression tests. Exact files are implementation details and SHALL be selected from current source after reading `RULES.md` and these approved specs.

### Explicit non-goals

This change SHALL NOT:

- redesign the common room shell or another device-family dashboard;
- add new supported codec models;
- create new credential selection/fallback behavior;
- move handler/session/network ownership into Qt presentation code;
- add a second call-log reader, Local Refresh owner, volume mutation owner, retry loop, or live-meter poller;
- infer authentication from public strings such as `auth`, `401`, or `403`;
- add live microphone-meter protocol support for TE20, TE40, or Polycom RPG 310 without a later separately approved protocol contract;
- remove platform data from handlers/parsers/model-neutral diagnostics merely because the modern codec dashboard stops rendering it;
- remove Debug capability from non-codec device families;
- change CloudLink Bar/Box approved meter endpoints, session boundaries, or credential rules;
- alter Graphify artifacts or make Graphify part of validation evidence.

## Change base

This change is authored against current `master`:

`705daee00cd51cd1f4dfd100238f9bcdc33d01ec`

Because this change explicitly replaces legacy call-log, Debug, state-card, and audio-card requirements where scenario identities no longer describe approved behavior, while retaining `MODIFIED Requirements` only where their scenario identities remain truthful, independent validation SHALL include the repository-required disposable archive-applicability check before `READY FOR ARCHIVE`.
