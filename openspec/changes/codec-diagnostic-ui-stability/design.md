# Design: codec-diagnostic-ui-stability

## Context

The modern room codec dashboard is a presentation over the existing room diagnostic/application authority. The five baseline codec models are:

```text
Huawei TE20
Huawei TE40
CloudLink Bar 310
CloudLink Box 310
Polycom RPG 310
```

The approved architecture already establishes the important ownership boundaries:

- exact row authority is immutable room generation + canonical `record_id` + exact `diagnostic_model` + exact IP + operation/currentness token;
- one application-owned serialized room interaction lane owns `LIVE`, `LOCAL_REFRESH`, `AUXILIARY_READ`, `MUTATION`, and `RECONCILIATION`;
- unified exact-model registration is capability authority;
- presentation does not own credentials, handler/session objects, retries, timers, request generations, or blocking I/O;
- call-log reads are read-only auxiliary work and existing Huawei/Polycom retrieval/lifecycle ownership remains authoritative;
- state-changing commands are not complete at send/ACK and require accepted readback/reconciliation;
- stale work is rejected before handler acquisition/I/O where separable and again before publication;
- typed failures take precedence over text heuristics;
- CloudLink live microphone metering is currently approved only for exact `CloudLink Bar 310` and `CloudLink Box 310`.

The implementation must correct stability/presentation gaps inside those boundaries rather than introduce widget-owned fixes.

## Goals

1. Make call-history preview, direction, duration, and usage-statistics behavior semantically consistent across the five baseline codecs.
2. Make `CloudLink Box 310` a mandatory end-to-end regression oracle for call history/statistics.
3. Simplify the modern codec dashboard by removing `Платформа`, codec-local `Отладка`, and any speaker-volume scale/bar.
4. Show accepted current speaker volume as a true percentage without making GUI percentage state mutation authority.
5. Make microphone meter capability and data availability unambiguous for all five baseline models.
6. Ensure speaker-volume controls and codec Local Refresh terminate through the already-approved serialized lifecycle and cannot remain stuck due to a second presentation-owned pending state.
7. Preserve stale-result, credential, secret-safety, GUI-thread, and mutation ambiguity contracts.

## Non-goals

- New codec protocol discovery or new device support.
- New CloudLink auth/session behavior.
- New live microphone polling for TE20, TE40, or Polycom RPG 310.
- Reworking the 30/90-day/100-record usage-statistics product rules.
- Redesigning the detailed call-log window hierarchy.
- Changing non-codec Debug behavior.
- Changing raw codec speaker-volume mutation semantics unless required to correctly project already-supported accepted state.
- Adding GUI-local retries to make controls appear responsive.

## Decisions

### 1. One normalized call-history record remains the source for preview, dialog, direction, duration, and statistics

The five model-specific adapters SHALL normalize source records into the same application-level call-history record contract before presentation.

This change adds typed direction:

```text
CallDirection = INCOMING | OUTGOING | UNKNOWN
```

and preserves machine-readable duration semantics already required by the root specification. Presentation SHALL render direction only from `CallDirection`; it SHALL NOT derive direction from icon color, localized text, model name, peer formatting, or whether one vendor happens to expose a field.

A completed record with accepted non-negative duration SHALL render duration for every baseline model. Missing/unparseable duration remains visible as unavailable and follows the existing partial-calculation warning contract; it is not silently replaced with zero. Active records remain `Активный` and contribute zero to usage as already approved.

The same accepted normalized snapshot SHALL drive:

- the three-row modern room preview;
- the existing detailed call-log presentation;
- duration display;
- direction cues;
- usage statistics.

No second parser or vendor-specific GUI branch is permitted.

### 2. Initial room call-history preview reuses existing `AUXILIARY_READ` authority

The modern room dashboard may automatically attempt call-history preview only through the application-owned room call-history auxiliary binding already defined by the room lifecycle. The presentation publishes intent/consumes accepted state; it never invokes a handler directly.

Automatic preview is accepted only for the exact current row/generation and must obey the serialized lane. If another lifecycle owns/retains the lane, preview waits, is skipped, or is superseded according to the existing lifecycle policy; it must not create concurrency merely to populate the card.

A later explicit `Развернуть` uses the current accepted snapshot if available; otherwise it uses the existing explicit serialized auxiliary acquisition. The change introduces no cross-open cache and no second reader.

`CloudLink Box 310` is a mandatory end-to-end regression case from exact model registration through retrieval/normalization to preview/dialog/statistics presentation.

### 3. `Платформа` is removed only from modern codec presentation

The modern `Состояние` card no longer renders a `Платформа` row. The field may remain in parser/handler/model-neutral diagnostic data because other code or diagnostics may legitimately use it.

Therefore implementation SHALL NOT delete or stop collecting `platform` merely to satisfy this presentation change. The presentation projection simply does not allocate/render that slot.

### 4. Codec-local Debug is a visibility exception, not a capability rewrite

The modern codec dashboard SHALL expose no `Отладка` affordance. This mirrors the already-approved PDU presentation exception.

The underlying local accumulated terminal/log data is not reclassified and no network behavior changes. Debug remains available wherever another approved device-family presentation still exposes it. No hidden codec alternate command/debug path is added.

### 5. Speaker display percentage is distinct from canonical mutation state

The application projection adds:

```text
speaker_volume_percent: Optional[int]  # 0..100 when authoritative
```

This field is display-only accepted evidence. It SHALL be produced from the exact model's accepted speaker-volume state using an explicit application/adapter mapping whose source semantics are already supported/proven for that model.

Rules:

- exact numeric `0` is valid accepted `0%`;
- values are presented only after normalization to the closed `0..100` range according to the model's approved semantics;
- absence, malformed evidence, stale evidence, or an unproven source-to-percent mapping yields no percentage and renders `Нет данных`;
- presentation SHALL NOT guess a range from one observed value, clamp an unknown wire scale into a percent, parse a localized string, or use widget history/defaults;
- the value displayed immediately after a click is not authoritative merely because the UI knows the requested target;
- accepted post-mutation percentage changes only when the existing reconciliation/accepted-state path publishes current exact-row evidence.

The existing canonical/raw `speaker_volume` state and model-specific target conversion remain mutation/reconciliation authority. `speaker_volume_percent` SHALL NOT be reverse-converted by the GUI into a wire target.

For each of the five baseline registrations, implementation tests SHALL prove the mapping from the already-supported current speaker-volume source into `speaker_volume_percent`, or prove the source is currently unavailable for that exact snapshot and retain `Нет данных` without inventing data.

### 6. Speaker control has no presentation-owned pending lifecycle

A `−` or `+` click is resolved through exact-model capability authority and the common room lock matrix.

If unsupported, the existing local informational path performs zero network I/O.

If supported and admitted, exactly one existing `MUTATION` -> `RECONCILIATION` lifecycle owns the operation. The presentation MAY show disabled/busy state derived from that lifecycle, but SHALL NOT maintain an independent pending flag/timer that can outlive or disagree with lifecycle authority.

The control becomes eligible again only from an accepted terminal lifecycle state for the same still-current usable row. Ambiguous send/result or failed reconciliation remains blocked/unconfirmed according to the existing mutation contract; the UI SHALL NOT clear uncertainty by blind resend.

### 7. The modern room microphone meter uses three explicit semantic states

The modern room `Аудио` card has a permanent microphone-level slot, but network support comes only from unified application capability authority and existing approved live bindings.

Current baseline semantics are:

| Exact model | Modern room live microphone meter |
| --- | --- |
| Huawei TE20 | `UNSUPPORTED` |
| Huawei TE40 | `UNSUPPORTED` |
| CloudLink Bar 310 | `SUPPORTED` |
| CloudLink Box 310 | `SUPPORTED` |
| Polycom RPG 310 | `UNSUPPORTED` |

For `SUPPORTED` Bar/Box rows:

- accepted numeric zero is valid observed silence and renders as 0 fill;
- an accepted current sample renders the approved normalized fill;
- no accepted current sample renders `Нет данных`/unavailable;
- a meter-cycle failure does not convert accepted ordinary codec status into failure.

For `UNSUPPORTED` TE20/TE40/Polycom rows:

- the permanent meter slot renders `Не поддерживается` with an inactive/non-authoritative indicator;
- rendering performs zero handler/session/credential/network activity;
- legacy/standalone methods or historical polling behavior do not implicitly approve modern room support.

This change does not modify CloudLink Bar/Box endpoint/session contracts in `cloudlink-live-microphone-metering`.

### 8. Codec Local Refresh has one completion/presentation path

`Обновить статус` remains an alias of the one exact-row `LOCAL_REFRESH` lifecycle.

The presentation consumes a typed terminal result classified by currentness:

```text
ACCEPTED_SUCCESS
ACCEPTED_TERMINAL_FAILURE
STALE_OR_SUPERSEDED
CANCELLED
```

- `ACCEPTED_SUCCESS`: atomically accepted row data is rendered; no error modal is shown.
- `ACCEPTED_TERMINAL_FAILURE`: the existing row failure transition is applied and at most one non-secret user-facing error presentation may be emitted for that accepted current operation.
- `STALE_OR_SUPERSEDED` and `CANCELLED`: no current-row error modal and no cache mutation are allowed.

The presentation SHALL NOT separately interpret worker/handler callbacks and then also react to application lifecycle completion. This prevents the current erroneous/duplicate error path and keeps stale old-row callbacks silent.

### 9. Credentials, retries, stale work, and GUI thread remain unchanged

All corrected flows remain within existing application/composition ownership:

- application selects credentials/fallback candidates;
- handler/worker never iterates credentials;
- credential advancement requires structured authentication failure;
- transport/session recovery remains separate from credential fallback;
- queued stale work is rejected before handler acquisition and I/O where separable;
- publication rechecks exact row/generation/currentness;
- no codec network operation blocks the Qt GUI thread;
- secrets never enter public errors, dialogs, logs, normalized presentation records, or test snapshots.

## Risks / Trade-offs

### Risk: display percentage is confused with mutation authority

Mitigation: `speaker_volume_percent` is explicitly display-only. Mutation/reconciliation remains based on the existing canonical model-specific volume state and target conversion.

### Risk: fixing missing call history creates a second automatic reader

Mitigation: automatic preview is explicitly routed through the existing serialized auxiliary binding and current snapshot; no widget-owned request path is permitted.

### Risk: unsupported microphone meter is accidentally treated as missing telemetry

Mitigation: capability state (`SUPPORTED`/`UNSUPPORTED`) is resolved before runtime data availability. `UNSUPPORTED` and `Нет данных` have different presentation semantics and different test oracles.

### Risk: removing Debug hides needed logs during validation

Mitigation: only the modern codec dashboard affordance is removed. Existing internal logs/test diagnostics remain available; no log source is deleted by this change.

### Risk: archive delta conflicts with current root requirements

Mitigation: this change intentionally uses `MODIFIED Requirements`. Before `READY FOR ARCHIVE`, independent validation must perform the repository-required disposable archive-applicability check against the then-current root specs.

## Validation Strategy

Implementation validation SHALL include:

- exact-model focused call-history tests for all five baseline codecs;
- explicit `CloudLink Box 310` end-to-end call-history/statistics regression coverage;
- typed incoming/outgoing/unknown direction and completed/active/missing-duration cases;
- modern dashboard structure tests proving `Платформа` and codec `Отладка` are absent without removing non-codec Debug;
- speaker percentage projection tests for each baseline codec and stale/missing evidence;
- volume mutation lifecycle tests for supported/unsupported, success reconciliation, ambiguous/failed reconciliation, stale completion, and no duplicate/presentation-owned pending state;
- microphone-meter tests for Bar/Box supported data and no-data, plus TE20/TE40/Polycom unsupported with zero meter I/O;
- Local Refresh success/failure/stale/cancelled tests with no duplicate or stale error modal;
- GUI-thread/non-blocking and stale-before-I/O coverage on affected paths;
- full offline test suite;
- `git diff --check`;
- `./openspec.cmd` is NOT an allowed substitute on non-Windows shells; repository validation SHALL use the exact repository-local command required by `RULES.md` in the supported project environment:
  `.\openspec.cmd validate codec-diagnostic-ui-stability --strict` and `.\openspec.cmd validate --all --strict`.

## Open Questions

None. Protocol capability expansion is intentionally out of scope; unsupported meter models remain unsupported until separately approved evidence exists.
