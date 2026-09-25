# Hardware validation: Extron matrix model expansion

## Evidence status

- **SOFTWARE REVALIDATION REQUIRED:** the earlier software/independent validation
  predates the 2026-09-23 hardware/UI architecture remediation and no longer
  authorizes archive for the updated change.
- **READ-ONLY HARDWARE EVIDENCE RECORDED:** IN1804 and IN1808 retain prior partial
  evidence. Captured post-remediation evidence exists for IN1608 xi and DTP
  CrossPoint 86 4K; operator-attested post-remediation read-only QA is recorded
  for IN1806 and DTP CrossPoint 108 4K. All four remediation fixtures are
  `PARTIAL`, not `PASS`.
- **POST-REMEDIATION HARDWARE PASS:** none. Fixtures without a
  post-remediation run are explicitly `NOT RUN`; historical failures are not
  carried forward as a current implementation failure without a current run.

Only these hardware result values may be recorded: `PASS`, `PARTIAL`, `FAIL`,
`NOT RUN`, and `BLOCKED`. For the current permitting hardware gate, `PASS`
requires every applicable **Phase A read-only** check **and** authoritative,
non-empty values for all five `Общая информация` fields: model, MAC address,
serial number, firmware version, and temperature. If even one required
field remains `Нет данных`, missing, stale, malformed, synthetic, or unproven,
the run is not `PASS`. Phase B route mutation is
separate, optional, and non-permitting; it is not required for a read-only
hardware PASS and SHALL NOT be performed without explicit operational approval.

`PARTIAL` means only a documented subset of read-only checks was observed,
including a run that cannot yet establish all five mandatory General-information
fields without contradicting the profile. `FAIL` means observed hardware
contradicts the implementation/approved profile or a required field cannot be
acquired as implemented and requires remediation/retest. `BLOCKED` means a
present device could not be exercised for an external reason.

## Mandatory General-information hardware gate

For every hardware model evaluated for PASS, capture and verify all five fields:

```text
Модель
MAC-адрес
Серийный номер
Версия прошивки
Температура
```

`Модель` must match accepted exact identity/canonical profile. MAC and serial must come from current canonical room/inventory evidence. If either is absent, the fixture cannot receive complete-refresh or hardware PASS; no device fallback is approved.
Firmware and temperature must be observed from the approved exact SIS reads. Values must be non-empty and plausible for the device; placeholders,
model-as-serial substitution, synthetic zero, stale cache, or copied values do not
count. A missing exact command/source is a capability gap requiring architecture/
implementation follow-up, not permission to mark PASS.

## General-information acquisition/evidence matrix

This table mirrors the closed pre-implementation authority in `design.md`.

| Profile group | Model | MAC | Serial | Firmware | Temperature | General-information readiness |
| --- | --- | --- | --- | --- | --- | --- |
| IN1804 | PROVEN `1I` | REQUIRED canonical inventory | REQUIRED canonical inventory | PROVEN `Q` | PROVEN `W20STAT` | READY FOR IMPLEMENTATION |
| IN1806 / IN1808 | PROVEN `1I` | REQUIRED canonical inventory | REQUIRED canonical inventory | PROVEN `Q` | PROVEN `W20STAT` | READY FOR IMPLEMENTATION |
| IN1608 xi | PROVEN closed `1I` | REQUIRED canonical inventory | REQUIRED canonical inventory | PROVEN `Q` | PROVEN `W20STAT` | READY FOR IMPLEMENTATION |
| DTP CrossPoint 84 | PROVEN `I` | REQUIRED canonical inventory | REQUIRED canonical inventory | PROVEN `Q` | PROVEN `S` | READY FOR IMPLEMENTATION |
| DTP CrossPoint 82/84/86/108 4K | PROVEN exact `N` | REQUIRED canonical inventory | REQUIRED canonical inventory | PROVEN `Q` | PROVEN `S` | READY FOR IMPLEMENTATION |
| XTP CrossPoint 1600/3200 | DEFERRED | n/a | n/a | n/a | n/a | NOT IN SUPPORTED SCOPE |
| XTP II CrossPoint 1600/3200/6400 | DEFERRED | n/a | n/a | n/a | n/a | NOT IN SUPPORTED SCOPE |

## Model capability and evidence matrix

“Unavailable” means the approved profile must not send a speculative read, not
that a blank value should be invented. `Yes` is an expected capability to
exercise during hardware QA. Route mutation shown in the table is informational
for the optional Phase B only.

| Model | Inventory / identity | Topology | Signal / input HDCP | Output HDCP / auth | Input / output names / temp | Route read / optional mutation | Hardware status | Evidence / required retest |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Extron IN1804 | Canonical / `1I` | fixed 4x1 | Yes / legacy mapping | Yes / Yes | Yes / Yes / Yes | `!` / `<I>*1!` | PARTIAL | Prior read-only evidence recorded temp `59`, input HDCP `0,1,0,1`, signal `0*1*0*1`, and route-read PASS. No positive HDCP `2` case observed. |
| Extron IN1806 | Canonical / exact `IN1806`, part number `60-1663-01` | fixed 6x1 | Yes / legacy mapping | Yes / Yes | Yes / Yes / Yes | `1%` / `<I>*1%` | PARTIAL | Post-remediation read-only QA was operator-attested on real hardware: the current remediation behaved normally and no new protocol/profile/routing/UI contradiction was observed. The attestation has no captured raw responses or complete Phase A/five-field record, so it is not `PASS`; no route mutation occurred. |
| Extron IN1808 | Canonical / `1I` | fixed 8x1 | Yes / legacy mapping | Yes / Yes | Yes / Yes / Yes | `1%` / `<I>*1%` | PARTIAL | Prior read-only evidence was collected with the legacy combined AV route read. Post-remediation retest must prove `1%` video polling, including a breakaway-safe case where practical. No positive HDCP `2` case observed. Loop Out remains deferred. |
| Extron IN1608 xi | Canonical / exact closed `1I` aliases | fixed 8x1 | Yes / modern mapping | Yes / Yes | Yes / unavailable / Yes | `&` / `<I>&` | PARTIAL | Post-remediation evidence confirms closed identity, firmware, temperature, signal framing, and video-only `&` route readback; see the dated record below. The complete Phase A/five-field record is not captured, so this is not `PASS`. |
| DTP CrossPoint 84 | Canonical / documented DTP identity | fixed 8x4 | Yes / modern mapping | `WO<N>HDCP` / unavailable | Yes / Yes / REQUIRED-PROVE | `<O>%` / `<I>*<O>%` | NOT RUN | DTP canonical route is video-only; optional untie is `0*<O>%`. Capture actual `0LS` framing when available. |
| DTP CrossPoint 82 4K | Canonical / part number `N` | fixed 8x2 | Yes / modern mapping | `WO<N>HDCP` / unavailable | Yes / Yes / REQUIRED-PROVE | `<O>%` / `<I>*<O>%` | NOT RUN | DTP canonical route is video-only; optional untie is `0*<O>%`. Capture actual `0LS` framing when available. |
| DTP CrossPoint 84 4K | Canonical / part number `N` | fixed 8x4 | Yes / modern mapping | `WO<N>HDCP` / unavailable | Yes / Yes / REQUIRED-PROVE | `<O>%` / `<I>*<O>%` | NOT RUN | Must remain distinct from non-4K DTP 84; optional untie is `0*<O>%`. |
| DTP CrossPoint 86 4K | Canonical / part number `N` | fixed 8x6 | Yes / modern mapping | `WO<N>HDCP` / unavailable | Yes / Yes / REQUIRED-PROVE | `<O>%` / `<I>*<O>%` | PARTIAL | Post-remediation evidence confirms the exact `N` identity, firmware, temperature, and all six video route reads without `1!`; see the dated record below. Canonical inventory lacks serial evidence, so it cannot be `PASS`. |
| DTP CrossPoint 108 4K | Canonical / exact part number `N` aliases including `60-1381-12` | fixed 10x8 | Yes / modern mapping | `WO<N>HDCP` / unavailable | Yes / Yes / REQUIRED-PROVE | `<O>%` / `<I>*<O>%` | PARTIAL | Post-remediation read-only QA was operator-attested on real hardware: the current remediation behaved normally and no new identity/routing/profile/UI contradiction was observed. The attestation has no captured raw responses or complete Phase A/five-field record, so it is not `PASS`; no route mutation occurred. Historical `N -> 60-1381-12` remains historical evidence, not a newly captured response. |

## 2026-09-25 post-remediation read-only evidence

These observations are read-only and contain no route mutation. They reconcile
the implementation evidence only; they do not replace the complete Phase A gate.

### Operator-attested runs without captured raw values

- **IN1806:** a post-remediation read-only run was performed on real hardware.
  The operator attested that the current remediation behaved normally, with no
  new protocol, profile, routing, or UI contradiction. No raw command/response
  pair, MAC, serial, firmware, temperature, or complete five-field record was
  supplied for this run. Status: `PARTIAL`.
- **DTP CrossPoint 108 4K:** a post-remediation read-only run was performed on
  real hardware. The operator attested that the current remediation behaved
  normally, with no new identity, routing, profile, or UI contradiction. No raw
  command/response pair, MAC, serial, firmware, temperature, or complete
  five-field record was supplied for this run. Status: `PARTIAL`. The exact
  historical `N -> 60-1381-12` observation is not newly captured evidence.

### IN1608 xi captured evidence

- `1I` returned `IN1608 xi IPCP SA`, which resolves through the closed exact
  alias to canonical `IN1608 xi`.
- `Q` returned `2.45`; `W20STAT` returned `36`; and `W0LS` returned
  `0*0*0*1*0*0*0*0`.
- `&` returned `01`. The current profile/parser normalizes this as video
  `routes[1] == 1`; no combined `!` polling was used.
- The room GUI projected a canonical-inventory serial value with one trailing
  underscore. This is an inventory/reference-data issue, not device or SIS
  parser evidence; it is deferred to MIH-29. The implementation must not strip
  that value with `rstrip` or any equivalent normalization.
- Status: `PARTIAL`. The recorded evidence does not establish every applicable
  Phase A check and the complete five-field current record, so it cannot be
  promoted to `PASS`.

### DTP CrossPoint 86 4K captured evidence

- `N` returned `60-1382-01`, identifying the exact DTP CrossPoint 86 4K
  profile; `Q` returned `2.01`.
- `S` returned `12.125 57.000 0 0`, whose approved DTP status parser takes as
  temperature `57`.
- Video route reads returned `1% -> 6`, `2% -> 4`, `3% -> 7`, `4% -> 7`,
  `5% -> 7`, and `6% -> 7`. No legacy `1!` route poll was used.
- Current canonical inventory has no serial evidence for this fixture. Device
  and inventory reconciliation is deferred to MIH-29; no device serial fallback
  is approved.
- Status: `PARTIAL`, because the required canonical serial and the complete
  Phase A/five-field record are not available. It is not a `PASS`.

## Phase A — read-only hardware procedure

This is the mandatory current hardware gate. For every physically available
model selected for retest:

1. Verify inventory conversion resolves the expected canonical
   `diagnostic_model` without changing the source-model evidence.
2. Connect through the normal application/handler path and capture the exact
   identity response; verify it matches the inventory expectation.
3. Establish the complete five-field General-information tuple under the source rules above. Inventory MAC and serial are mandatory. Firmware/temperature use the approved exact SIS profile. Do not mark the run PASS if any required field is missing.
4. Read the remaining profile-approved capabilities, topology, signal presence, input HDCP, output HDCP, HDCP authorization, names, and all applicable routes. Optional unavailable/unproven fields remain unavailable; do not issue a trial command.
5. Where practical, compare parsed state with the device Web UI or known current state. Record raw request/response pairs with firmware version and device serial/asset reference, omitting credentials.

XTP and XTP II are deferred and are not hardware-PASS targets in this change. Do not run them merely to satisfy this change's permitting gate.

For DTP, capture the real `0LS` response exactly, including whether it is bare,
`Frq00*`-prefixed, space-separated, or contiguous. Verify DTP CrossPoint 84's
documented identity path and the 4K models' exact part-number path. Read every
applicable canonical video route with `<O>%`; do not use `<O>!` as a DTP
read-only query. A framing variance or unexpected response is evidence for
review, not permission to change parsing or command semantics.

For IN1806, exercise only the approved read-only commands for its exact six-input
profile and verify inputs 7 and 8 are not fabricated. Record exact `1I` identity,
part number `60-1663-01` where queried, and all supported current status fields.
Read the canonical Matrix route with `1%`; do not use `1!` for polling. Where
operationally observable without mutation, verify the read remains valid when audio
is in breakaway from video.

For IN1808, exercise only the approved read-only commands `1I`, `W20STAT`,
`WI<N>VNAM`, `WO<N>VNAM`, `W0LS`, `WE<N>HDCP`, `WI<N>HDCP`,
`WO<N>HDCP`, and `1%`; do not use `1!` for Matrix polling and do not model Loop Out as a second main route. Where operationally observable without mutation, verify `1%` remains authoritative while audio is in breakaway.

For IN1608 xi, use `1I`, `W20STAT`, `W<N>NI`, `W0LS`, `WE<N>HDCP`,
`WI<N>HDCP`, `WO<N>HDCP`, and `&`. Do not use combined-selection `!` for Matrix polling. The exact hardware-observed
`IN1608 xi IPCP SA` identity must resolve closed to canonical `IN1608 xi`.
Do not probe an unproven IN1608 xi output-name read.

## Phase B — optional controlled mutation procedure

Phase B is a separate, optional operational exercise. It is **not required** for
the current read-only hardware permitting gate, `PASS`, independent validation,
or archive readiness. Do not run it unless route switching is explicitly
authorized and operationally safe, including an approved restoration route.

Before mutation, record the accepted route state, exact target output, target
input, and restoration route. Send one route change only. Transport success or
ACK is not authoritative; read the exact target output and accept success only
when:

```text
routes[target_output] == requested_input
```

For IN1806/IN1808, this optional operation is video-only: set `<I>*1%` and reconcile with `1%`. For IN1608 xi, set `<I>&` and reconcile with `&`. Do not change or infer audio ties for these presentation-switcher profiles. IN1804 remains on its separate legacy compatibility profile.

For DTP, this optional operation is video-only: set `<I>*<O>%`, reconcile with
`<O>%`, and use `0*<O>%` only for an explicitly authorized video untie.
Do not change or infer audio ties.

XTP/XTP II are deferred from production support; Phase B SHALL NOT route-switch them under this change.

Restore the original route if a mutation was actually authorized and performed,
then verify the same targeted readback. If a failure occurs after possible send,
do not replay automatically. Preserve raw evidence and record the optional
mutation result separately from the mandatory Phase A read-only status.
