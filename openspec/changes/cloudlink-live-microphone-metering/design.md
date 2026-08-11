# Design: CloudLink live microphone metering

## Context

The application already supports exact diagnostic identities `CloudLink Bar 310` and `CloudLink Box 310` through the shared CloudLink 310 handler/worker family. Ordinary codec refresh is one-shot diagnostic status work. Separately, PDU room enrichment resolves exactly one related codec and uses a dedicated serialized read-only related-codec session independent from the selected codec page.

The requested live signal is telemetry, not configuration or control. It therefore needs a repeated read-only lifecycle similar in cadence and presentation to DMP 64 Plus, without merging DMP protocol code or ownership into the CloudLink path.

The supplied protocol evidence is model-specific:

```text
Bar 310
GET /v1/mediacontrol/mic/current-volume
-> data.curMicVouumeList[]
-> each entry may contain deviceId and curVolume

Box 310
POST action.cgi?ActionID=WEB_GetCurrentAudioParam
-> existing authenticated CloudLink session / CSRF request context
-> data contains mic*ValueIndex, micArray*ValIdx, and unrelated audio-input fields
```

The supplied Box HAR also shows repeated `WEB_GetCurrentAudioParam` requests in the web audio-monitor path. The sample endpoint, not any unrelated audio input or setup response, is authority for the meter value. No captured IP, credential, token, cookie, or raw HAR artifact is repository evidence and none is to be committed.

Current PDU architecture has two contracts that must be changed deliberately:

1. related-codec resources are currently closed on terminal status success;
2. VIP is currently required to be the first line of the PDU room/codec block.

A live PDU meter cannot satisfy either contract without an explicit OpenSpec delta.

## Goals

1. Normalize Bar 310 and Box 310 live microphone observations into one narrow canonical sample.
2. Poll one sample per second without overlapping requests for one current meter context.
3. Keep zero distinct from unavailable data.
4. Keep live telemetry optional so meter failure does not erase ordinary codec status or accepted PDU success.
5. Preserve application-owned credential/profile authority and typed failure semantics.
6. Keep all blocking network I/O and cleanup off the Qt GUI thread.
7. Reject stale work before handler acquisition and network I/O where applicable and reject all stale callbacks.
8. Reuse the PDU related-codec session lane rather than opening a second simultaneous PDU-related session merely for the meter.
9. Render the same meter semantics on the codec page and as the top row of the PDU related-codec block.
10. Keep the capability closed to exact Bar 310 and Box 310 identities.

## Non-goals

- Do not change the equipment inventory schema, PDU-to-room resolution, or related-codec selection rules.
- Do not infer CloudLink support from free-form source text.
- Do not add TE20, TE40, Polycom, DMP, Biamp, Matrix, or PDU outlet metering through this capability.
- Do not move credential candidate selection or successful-index memory into a handler, worker, screen, or meter parser.
- Do not treat meter success as credential-success evidence.
- Do not add state-changing audio commands.
- Do not put the live sample into ordinary CloudLink `get_status()` required or optional status collection.
- Do not create a generic multi-device polling manager.
- Do not expose individual microphone channels in the GUI in this change.
- Do not commit HAR files, production IP addresses, credentials, tokens, cookies, or captured response bodies.

## Decision 1: Supported identities and canonical sample are closed

The capability supports exactly:

```text
CloudLink Bar 310
CloudLink Box 310
```

The protocol boundary produces an optional canonical sample equivalent to:

```text
raw_level: non-negative numeric observation
available: true
```

or an unavailable outcome with no numeric `raw_level`.

Presentation normalization is:

```text
display_ceiling = 20
fraction = clamp(raw_level / 20, 0.0, 1.0)
```

A real observed `0` is available silence and produces an empty 0% bar. Missing, malformed, unsuccessful, or otherwise unavailable sample data produces an unavailable meter state and SHALL NOT be converted to numeric zero. Values above 20 remain valid raw observations but are display-clamped to 100%.

The ceiling of 20 is an explicitly temporary product assumption in this change. Changing its semantic scale requires a later reviewed change or separately approved calibration update.

## Decision 2: Bar 310 extraction uses every returned microphone line

Bar 310 live sampling uses exactly:

```text
GET /v1/mediacontrol/mic/current-volume
```

The response must be successful under the established CloudLink request contract. After the existing double-JSON decoding boundary, `data["curMicVouumeList"]` must be a list.

Every Mapping element in that list is eligible regardless of `deviceId`. A valid element contributes `curVolume` only when it is numeric and non-negative. The canonical raw level is the maximum valid `curVolume` from the complete list.

The implementation SHALL NOT assume `deviceId` range `0..17`, exclude `deviceId == 18`, select a preferred device, or use list position as channel authority. Empty lists, lists with no valid numeric `curVolume`, and malformed payloads are unavailable samples rather than zero.

## Decision 3: Box 310 extraction uses a closed microphone-only field set

Box 310 live sampling uses exactly the established-session action:

```text
POST action.cgi?ActionID=WEB_GetCurrentAudioParam
```

The request reuses the existing authenticated CloudLink handler/session and its approved session/CSRF request material. This change creates no new credential source, login flow, or public token transport.

Only these exact decoded data fields contribute to the meter:

```text
mic1ValueIndex
mic2ValueIndex
mic3ValueIndex
mic4ValueIndex

micArray1_01ValIdx
micArray1_02ValIdx
micArray1_03ValIdx
micArray2_01ValIdx
micArray2_02ValIdx
micArray2_03ValIdx
micArray3_01ValIdx
micArray3_02ValIdx
micArray3_03ValIdx
```

A present value contributes only when numeric and non-negative. The canonical raw level is the maximum valid value across this closed set.

The implementation SHALL NOT scan arbitrary keys by substring and SHALL NOT include:

```text
trs*
rca*
hdmi*
blueToothIn*
uac*
m220w_porwer_hint
```

or another unreviewed audio-input field. Missing fields are simply absent observations; if no valid microphone field is observed, the sample is unavailable rather than zero.

The supplied HAR contains other audio-monitor setup/read calls. They do not own the canonical level. If real-device implementation proves that a separate non-mutating setup handshake is strictly required before `WEB_GetCurrentAudioParam` can return authoritative samples, that handshake may be encapsulated inside the model-specific meter session only after its safety and cleanup behavior are covered by tests; it SHALL NOT become a source of the meter value or a new authentication authority.

## Decision 4: Live metering is separate from ordinary codec status

The one-second meter loop SHALL NOT be added to `CloudLinkBar310Handler.get_status()` or make ordinary codec refresh long-lived.

The application/composition layer owns a focused CloudLink meter context for the current codec page. It captures at least:

```text
model
ip_address
meter generation / operation identity
credential-context revision or equivalent opaque identity
accepted credential/profile identity required to acquire the handler
```

The implementation may use a focused CloudLink-specific controller or an equivalent composition-owned boundary. It SHALL NOT create a generic controller for unrelated devices.

The meter begins only for an exact supported current CloudLink model/IP after the normal diagnostic context has been accepted. It stops when model changes, IP changes, the codec page/context is deactivated or replaced, relevant credential context changes, repeat diagnostic refresh supersedes the context, or the application shuts down.

## Decision 5: One-second polling is serialized and stale-safe

The target cadence is one sample cycle per second, matching the application DMP meter cadence selected by the product requirement. Vendor web-UI cadence is not authority to poll faster.

For one active meter context:

- there is at most one live sample request in flight;
- a new sample is not started while the previous sample operation is unfinished;
- the next cycle is scheduled from completion/elapsed cadence so slow I/O cannot create overlap;
- queued stale work is rejected before handler acquisition and before first network I/O where separable;
- currentness is checked before each new sample request and before publication;
- stale result, error, completion, profile, or credential metadata cannot update the current context;
- cleanup executes on the network/session-owning background lane.

No currentness decision depends on reading Qt widgets from a background worker.

## Decision 6: Sample-local failure is optional; terminal session failure stays typed

A successful session with an endpoint-local unsuccessful response, malformed sample payload, or sample-specific command/protocol problem produces an unavailable meter sample for that cycle. The next scheduled cycle may retry the read on the still-authoritative session. Already accepted codec/PDU status is unchanged.

Structured authentication rejection, established-session invalidation, or transport/session failure is not silently downgraded to a harmless parse miss. Existing typed failure and bounded read-only recovery policy remains authoritative. The meter may attempt only the already approved bounded same-context recovery; it SHALL NOT create an unbounded one-second reconnect/login loop.

If bounded recovery cannot restore the meter session, the meter remains unavailable until a new authoritative diagnostic/enrichment context starts. Such meter failure SHALL NOT:

- fail or clear already accepted ordinary codec status;
- change an accepted PDU refresh into failure;
- advance credentials from user-facing text or HTTP-status string heuristics;
- persist a new successful credential index or connection profile;
- open an automatic modal error merely because optional live telemetry is unavailable.

Secrets remain redacted from logs, signals, public errors, and presentation payloads.

## Decision 7: Codec-page rendering is a meter, not a numeric parameter

For exact Bar 310 or Box 310 context, the codec `Параметры и управление` card contains:

```text
...
Статус микрофона
Уровень микрофонов   [horizontal live meter]
Журнал звонков
```

The meter uses the same user-visible semantics as the existing DMP meter: horizontal progress indication, no numeric text overlay, normal active style for available samples, and a visually distinct inactive/unavailable state when no sample is authoritative.

The row is hidden for unsupported codec models. Rebuilding codec-owned widgets must not create duplicate meter rows or leak old callbacks into newly created widgets.

## Decision 8: PDU enrichment extends its existing dedicated related-codec lane

PDU metering does not reuse or interfere with the selected codec page session. `PDURoomCodecEnrichmentController` remains owner of the exact resolved related-codec model/IP/enrichment generation and its dedicated serialized session lane.

For a resolved exact Bar 310 or Box 310:

```text
accepted PDU refresh
-> exact room/codec resolution
-> dedicated related-codec session activation
-> initial normalized call/presentation status read
-> publish codec diagnostic SUCCESS
-> retain the same current related-codec session context
-> start serialized 1-second microphone sample cycles
```

Initial related-codec status success is therefore terminal for the status operation but not terminal for the CloudLink meter child lifecycle. The session is retained only while the exact PDU enrichment generation, codec model/IP, credential context, and inventory-derived resolution remain current.

For unsupported related codecs, current one-shot status behavior and terminal cleanup remain unchanged.

A live-meter sample result extends PDU presentation with optional microphone-meter availability/raw/fraction fields without replacing call/presentation values or changing `codec_diagnostic_status`. Sample-local unavailability affects only the meter.

## Decision 9: PDU meter precedes VIP without weakening VIP authority

For a resolved supported CloudLink related codec, the existing `Комната и связанный кодек` block begins with:

```text
Уровень микрофонов   [horizontal live meter]
VIP                  <existing VIP presentation>
...
```

The meter is the top overall row. VIP remains the first room-context row and retains the existing `ДА/НЕТ/НЕТ ДАННЫХ/КОНФЛИКТ ДАННЫХ` semantics and prominent styling.

Until a supported related codec is resolved, or when the exact related codec is unsupported, the meter row is hidden and existing PDU room/codec presentation remains unchanged.

PDU supersession clears/hides the old meter at the same boundary that clears the existing related-codec presentation. A stale sample can never restore an old bar after a new PDU refresh/model/IP/credential/inventory context becomes authoritative.

## Decision 10: Testing proves protocol, lifecycle, and presentation boundaries

Regression coverage must use synthetic payloads and fake handlers/sessions only. Tests must cover:

- Bar max over all list entries including `deviceId == 18`;
- Bar malformed/empty/no-valid-sample cases;
- Box exact included field set and exact exclusion of non-microphone audio fields;
- valid zero versus unavailable;
- raw values `0`, values inside `0..20`, exactly `20`, and above `20`;
- one-second scheduling without overlapping sample operations;
- cancellation before acquisition/I/O and stale callback rejection;
- sample-local failure followed by a later cycle;
- bounded terminal session failure behavior without credential-memory changes;
- codec row ordering, visibility, meter rendering, rebuild/no-duplicate behavior;
- PDU initial status success followed by continued CloudLink metering on the same dedicated lane;
- unsupported related codec retaining one-shot cleanup;
- PDU top-row meter ordering and VIP immediately below it;
- PDU supersession/credential/inventory/shutdown cleanup;
- no modal/PDU-success regression from optional meter failure;
- redaction and absence of captured HAR/IP/token data from fixtures.

## Archive applicability

This change modifies existing `pdu-room-codec-enrichment` requirements and adds a new root capability. Independent validation must therefore perform the repository-required disposable archive-applicability check in its clean detached validation worktree before any `READY FOR ARCHIVE` decision.
