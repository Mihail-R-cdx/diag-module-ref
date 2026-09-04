# Design: codec-diagnostic-ui-stability

## Context

The modern room codec dashboard is a presentation over existing application-owned room diagnostic authority. The baseline codec models are:

```text
Huawei TE20
Huawei TE40
CloudLink Bar 310
CloudLink Box 310
Polycom RPG 310
```

Existing approved boundaries remain authoritative:

- exact row authority is room generation + canonical `record_id` + exact `diagnostic_model` + exact IP + current operation token;
- one application-owned serialized room interaction lane owns `LIVE`, `LOCAL_REFRESH`, `AUXILIARY_READ`, `MUTATION`, and `RECONCILIATION`;
- unified exact-model registration is the capability authority;
- presentation owns no credentials, handler/session objects, retries, timers, request generations, or blocking I/O;
- call-log reads are read-only auxiliary work and existing Huawei/Polycom retrieval ownership remains authoritative;
- state-changing commands are incomplete until accepted readback/reconciliation;
- stale work is rejected before handler acquisition/I/O where separable and again before publication;
- typed failures take precedence over public strings;
- CloudLink live microphone metering is approved only for exact `CloudLink Bar 310` and `CloudLink Box 310`.

This change corrects presentation/stability defects inside those boundaries. It does not create widget-owned fixes or new protocol capability.

## Goals

1. Make call-history preview, direction, duration, and usage-statistics semantics consistent across all five baseline codecs.
2. Preserve fresh explicit detailed-journal acquisition while allowing the automatic room-card preview to use its own accepted snapshot.
3. Make the mandatory one-attempt-per-expansion-epoch automatic preview contract testable.
4. Make `CloudLink Box 310` a mandatory end-to-end call-history/statistics regression oracle.
5. Remove `Платформа`, codec-local `Отладка`, and any speaker-volume scale/bar from the modern codec dashboard.
6. Define a normative display-only speaker-volume percentage mapping from the existing exact-model registry ranges.
7. Make microphone meter capability/data availability explicit.
8. Correct speaker mutation and Local Refresh stability without adding parallel lifecycle ownership.

## Non-goals

- New codec protocol discovery or new device support.
- New CloudLink auth/session behavior.
- New live microphone polling for TE20, TE40, or Polycom RPG 310.
- Reworking 30/90-day/100-record usage-statistics product rules.
- Replacing the detailed call-log window hierarchy.
- Changing non-codec Debug behavior.
- Replacing canonical/raw speaker-volume mutation authority with GUI percentage state.
- Assuming the root cause of MIH-23 before reproduction evidence exists.

## Decisions

### 1. One normalized call-history record contract, but acquisition epochs remain distinct

All five model-specific adapters SHALL normalize source records into one application-level call-history record contract before presentation.

This change adds typed direction:

```text
CallDirection = INCOMING | OUTGOING | UNKNOWN
```

The visible semantic mapping is deterministic:

```text
INCOMING -> incoming semantic icon/cue with non-color/accessibility meaning `Входящий`
OUTGOING -> outgoing semantic icon/cue with non-color/accessibility meaning `Исходящий`
UNKNOWN  -> neutral direction cue with non-color/accessibility meaning `Направление неизвестно`
```

The concrete glyph/Qt asset MAY vary, but the semantic role binding SHALL NOT be swapped. Presentation SHALL render direction only from `CallDirection` and SHALL NOT infer it from icon color, localized source text, model name, peer formatting, record position, or vendor branch.

Machine-readable duration semantics remain those of the current root specification. Accepted completed non-negative duration is rendered for every baseline model. Missing/unparseable duration remains visible as unavailable and follows the existing partial-calculation warning contract; active records remain `Активный` and contribute zero until completed.

The automatic room-card preview and an explicit detailed-journal opening MAY therefore show snapshots from different acquisition epochs. What is shared is the normalized record type, chronology semantics, direction/duration semantics, and statistics calculation contract — not a cross-open cache.

### 2. Automatic room preview admission remains mandatory exactly once per eligible expansion epoch

The existing root lifecycle requirement remains unchanged and authoritative.

For every eligible codec expansion epoch, the application SHALL admit exactly one automatic call-history preview intent through the existing serialized `AUXILIARY_READ` lane. Duplicate Qt expansion notifications, re-render, resize, repaint, theme changes, or rebuilding the same already-expanded row SHALL NOT admit a second intent.

If the row is expanded before the automatic room cycle is terminal, application authority retains the current expansion epoch and admits its one preview intent after the cycle becomes terminal if that exact row/epoch remains current and eligible. Pre-terminal expansion itself performs no device I/O.

If another lifecycle owns or is retiring from the lane when the automatic preview intent is admitted, the preview remains application-owned pending work behind the existing lifecycle/handoff boundary. It SHALL NOT be silently dropped merely because the lane is busy, and it SHALL NOT acquire a handler/session concurrently. A later stale, cancelled, superseded, or failed-currentness/cleanup gate MAY prevent device I/O.

### 3. Explicit detailed journal always starts a fresh serialized acquisition

The existing call-log freshness policy is preserved:

```text
room-card automatic preview
    -> may render its accepted automatic-preview snapshot

explicit `Развернуть` / explicit detailed journal opening
    -> always starts a fresh serialized exact-row `AUXILIARY_READ`
```

An accepted automatic-preview snapshot SHALL NOT substitute for the required explicit read. Once the fresh explicit acquisition has accepted data, the detailed dialog, its latest-record presentation, and its statistics use that fresh accepted acquisition result. Expanding/collapsing sections inside the already-open detailed dialog continues to reuse that same explicit-load data without another request, exactly as the root spec requires.

No cross-open call-history cache or second reader is introduced.

`CloudLink Box 310` is a mandatory end-to-end regression from exact registry identity through approved retrieval/session path, normalization, room preview, fresh explicit journal load, and statistics.

### 4. `Платформа` and codec-local Debug are presentation-only removals

The modern `Состояние` card no longer renders `Платформа`, but implementation SHALL NOT delete or stop collecting internal `platform` evidence merely for this change.

The modern codec dashboard SHALL expose no `Отладка` affordance. Existing accumulated log/terminal data and Debug presentation for other approved device families remain unchanged. No hidden codec alternate network/debug path is added.

### 5. Speaker percentage has one normative application-owned conversion

The application projection adds:

```text
speaker_volume_percent: Optional[int]  # 0..100 when authoritative
```

The exact-model registry already owns the canonical speaker bounds. Current approved baseline ranges are:

```text
Huawei TE20          0..21
Huawei TE40          0..21
CloudLink Bar 310    0..15
CloudLink Box 310    0..15
Polycom RPG 310      0..100
```

For accepted numeric `speaker_volume = V`, registry minimum `MIN`, and maximum `MAX`, percentage SHALL be calculated only when `MAX > MIN` and `MIN <= V <= MAX`:

```text
scaled  = 100 * (V - MIN) / (MAX - MIN)
percent = floor(scaled + 0.5)
```

This is nearest-integer rounding with half values rounded upward for this non-negative closed range. No runtime clamping is allowed: out-of-range, malformed, stale, or missing evidence yields no accepted percentage and presentation shows `Нет данных`.

Current acceptance oracles include:

```text
TE20/TE40:       0 -> 0%, 10 -> 48%, 21 -> 100%
Bar310/Box310:   0 -> 0%,  7 -> 47%, 15 -> 100%
Polycom RPG310:  0 -> 0%, 42 -> 42%, 100 -> 100%
```

The mapping is produced in application/adapter projection using the existing unified registry; no second range table or Qt-owned conversion is permitted. Canonical/raw `speaker_volume` and existing model-specific mutation target conversion remain mutation/reconciliation authority. A requested target or send/ACK does not update accepted percentage until current exact-row reconciliation/status evidence is accepted.

### 6. Speaker controls have no presentation-owned pending lifecycle

A supported `−`/`+` click enters only the existing exact-row `MUTATION` -> mandatory `RECONCILIATION` lifecycle. Presentation MAY derive disabled/busy state from that lifecycle but SHALL NOT own an independent pending timer/flag, retry owner, credential fallback, or direct status request.

Unsupported actions remain local informational affordances with zero room network admission/I/O. Ambiguous send/result or failed reconciliation follows the existing blocked/unconfirmed contract and SHALL NOT be cleared by blind resend or optimistic percentage.

### 7. Microphone meter capability and runtime availability are separate

Current modern-room live-meter capability remains:

| Exact model | Capability |
| --- | --- |
| Huawei TE20 | `UNSUPPORTED` |
| Huawei TE40 | `UNSUPPORTED` |
| CloudLink Bar 310 | `SUPPORTED` |
| CloudLink Box 310 | `SUPPORTED` |
| Polycom RPG 310 | `UNSUPPORTED` |

For supported Bar/Box rows, accepted numeric zero is observed silence, an accepted current sample renders the approved fill, and absence of a current accepted sample renders `Нет данных`. For unsupported rows, the permanent slot renders `Не поддерживается` and performs zero meter network activity. This change does not modify CloudLink endpoint/session contracts.

### 8. Local Refresh architecture is fixed; defect root cause is not assumed

`Обновить статус` remains an alias of the one exact-row `LOCAL_REFRESH` lifecycle. The architecture prohibits a second codec-specific refresh owner, direct widget-to-handler dispatch, duplicate current-operation error presentation, string-based failure reclassification, stale cache mutation, and stale-row modal publication regardless of the eventual defect location.

Before implementation changes, MIH-23 SHALL be reproduced separately for TE20, TE40, Bar 310, Box 310, and Polycom RPG 310. Evidence SHALL classify the failing boundary as either common lifecycle/composition or model-specific adapter/typed-failure behavior. Implementation SHALL correct the proven root cause inside the approved ownership boundary rather than assume duplicate callbacks are the cause.

Presentation terminal semantics remain:

```text
ACCEPTED_SUCCESS
ACCEPTED_TERMINAL_FAILURE
STALE_OR_SUPERSEDED
CANCELLED
```

- accepted success publishes accepted exact-row usable data and no error modal;
- accepted terminal failure follows the existing row failure contract and emits at most one non-secret current-operation error presentation;
- stale/superseded/cancelled outcomes mutate no current cache and emit no current-row error modal.

Queued stale work remains rejectable before handler acquisition/I/O where separable.

### 9. Credentials, retries, secrets, and GUI thread remain unchanged

Application/composition remains credential selection/fallback authority; handler/worker never iterates credentials; candidate advancement requires structured authentication failure; transport/session recovery remains separate; publication rechecks currentness; network I/O stays off the Qt GUI thread; secrets never enter public errors, dialogs, logs, normalized records, or test snapshots.

## Risks / Trade-offs

### Risk: percentage becomes mutation authority

Mitigation: percentage is display-only; canonical/raw state plus approved mutation/reconciliation remains authoritative.

### Risk: missing preview is "fixed" by a second reader

Mitigation: exactly-one automatic admission is mandatory through the existing serialized auxiliary lane; no widget-owned network owner is allowed.

### Risk: explicit journal shows stale automatic-preview data

Mitigation: explicit opening always starts a fresh serialized acquisition and never treats the automatic preview snapshot as a substitute.

### Risk: Local Refresh fix targets an assumed cause

Mitigation: model-by-model reproduction/classification is an implementation gate before code changes.

### Risk: archive delta conflicts with current roots

Mitigation: the change uses `MODIFIED Requirements`; independent validation must perform the required disposable archive-applicability check before `READY FOR ARCHIVE`.

## Validation Strategy

Implementation validation SHALL include:

- call-history parity for all five baseline codecs;
- exactly-one automatic preview admission per expansion epoch, including pre-terminal expansion, duplicate Qt notifications, busy/retiring lane, row switch, stale/cancelled gates, and no concurrent I/O;
- fresh explicit `Развернуть` acquisition even when automatic preview data already exists;
- Box 310 end-to-end preview plus fresh detailed/statistics regression;
- normalized `INCOMING`/`OUTGOING`/`UNKNOWN` plus visible semantic cue-role mapping tests;
- completed/active/missing-duration cases;
- dashboard tests proving `Платформа` and codec `Отладка` are absent without deleting internal data/non-codec Debug;
- speaker-percent min/max/intermediate/zero and out-of-range/no-data cases for each distinct approved range;
- volume mutation lifecycle tests for supported/unsupported, reconciliation success, ambiguous/failed reconciliation, stale completion, and no presentation-owned pending state;
- microphone-meter tests for Bar/Box supported data/zero/no-data and TE20/TE40/Polycom unsupported with zero meter I/O;
- Local Refresh model-by-model reproduction evidence before fixes, then success/failure/stale/cancelled regression tests at the proven boundary;
- GUI-thread/non-blocking and stale-before-I/O coverage;
- full offline test suite;
- `git diff --check` and `git diff --cached --check`;
- repository-local `.\openspec.cmd validate codec-diagnostic-ui-stability --strict` and `.\openspec.cmd validate --all --strict`.

## Open Questions

None at product-contract level. The MIH-23 Local Refresh root cause is intentionally not presumed; model-by-model reproduction/classification is a required implementation evidence gate, not an unresolved architecture choice.
