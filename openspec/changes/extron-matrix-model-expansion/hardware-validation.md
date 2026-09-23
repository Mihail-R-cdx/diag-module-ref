# Hardware validation: Extron matrix model expansion

## Evidence status

- **SOFTWARE REVALIDATION REQUIRED:** the earlier software/independent validation
  predates the 2026-09-23 hardware/UI architecture remediation and no longer
  authorizes archive for the updated change.
- **READ-ONLY HARDWARE EVIDENCE RECORDED:** IN1804 and IN1808 have prior partial
  read-only evidence; IN1608 xi, IN1806, DTP CrossPoint 86 4K, and DTP CrossPoint
  108 4K produced the pre-remediation observations recorded below.
- **POST-REMEDIATION HARDWARE PASS:** none yet. The affected available fixtures
  require read-only retest after implementation of section 26.

Only these hardware result values may be recorded: `PASS`, `PARTIAL`, `FAIL`,
`NOT RUN`, and `BLOCKED`. For the current permitting hardware gate, `PASS`
requires every applicable **Phase A read-only** check **and** authoritative,
non-empty values for all six `Общая информация` fields: model, MAC address,
serial number, firmware version, temperature, and uptime. If even one required
field remains `Нет данных`, missing, stale, malformed, synthetic, or unproven,
the run is not `PASS`. Phase B route mutation is
separate, optional, and non-permitting; it is not required for a read-only
hardware PASS and SHALL NOT be performed without explicit operational approval.

`PARTIAL` means only a documented subset of read-only checks was observed,
including a run that cannot yet establish all six mandatory General-information
fields without contradicting the profile. `FAIL` means observed hardware
contradicts the implementation/approved profile or a required field cannot be
acquired as implemented and requires remediation/retest. `BLOCKED` means a
present device could not be exercised for an external reason.

## Mandatory General-information hardware gate

For every hardware model evaluated for PASS, capture and verify all six fields:

```text
Модель
MAC-адрес
Серийный номер
Версия прошивки
Температура
Время работы
```

`Модель` must match accepted exact identity/canonical profile. MAC and serial must come from current canonical room/inventory evidence. If either is absent, the fixture cannot receive complete-refresh or hardware PASS; no device fallback is approved.
Firmware and temperature must be observed from the approved exact SIS reads; uptime must be observed from the approved SNMPv2c `sysUpTime.0` read. Values must be non-empty and plausible for the device; placeholders,
model-as-serial substitution, synthetic zero, stale cache, or copied values do not
count. A missing exact command/source is a capability gap requiring architecture/
implementation follow-up, not permission to mark PASS.

## General-information acquisition/evidence matrix

This table mirrors the closed pre-implementation authority in `design.md`.

| Profile group | Model | MAC | Serial | Firmware | Temperature | Uptime | General-information readiness |
| --- | --- | --- | --- | --- | --- | --- | --- |
| IN1804 | PROVEN `1I` | REQUIRED canonical inventory | REQUIRED canonical inventory | PROVEN `Q` | PROVEN `W20STAT` | PROVEN design: SNMPv2c `sysUpTime.0` | READY FOR IMPLEMENTATION |
| IN1806 / IN1808 | PROVEN `1I` | REQUIRED canonical inventory | REQUIRED canonical inventory | PROVEN `Q` | PROVEN `W20STAT` | PROVEN design: SNMPv2c `sysUpTime.0` | READY FOR IMPLEMENTATION |
| IN1608 xi | PROVEN closed `1I` | REQUIRED canonical inventory | REQUIRED canonical inventory | PROVEN `Q` | PROVEN `W20STAT` | PROVEN design: SNMPv2c `sysUpTime.0` | READY FOR IMPLEMENTATION |
| DTP CrossPoint 84 | PROVEN `I` | REQUIRED canonical inventory | REQUIRED canonical inventory | PROVEN `Q` | PROVEN `S` | PROVEN design: SNMPv2c `sysUpTime.0` | READY FOR IMPLEMENTATION |
| DTP CrossPoint 82/84/86/108 4K | PROVEN exact `N` | REQUIRED canonical inventory | REQUIRED canonical inventory | PROVEN `Q` | PROVEN `S` | PROVEN design: SNMPv2c `sysUpTime.0` | READY FOR IMPLEMENTATION |
| XTP CrossPoint 1600/3200 | DEFERRED | n/a | n/a | n/a | n/a | no approved source | NOT IN SUPPORTED SCOPE |
| XTP II CrossPoint 1600/3200/6400 | DEFERRED | n/a | n/a | n/a | n/a | no approved source | NOT IN SUPPORTED SCOPE |

For supported IN/DTP hardware, PASS additionally requires SNMP to be enabled and the deployment read-only community to be available through explicit password-only profile `matrix-snmp-read`. Missing monitoring configuration is BLOCKED, not permission to substitute local elapsed time or scrape an undocumented page.

## Model capability and evidence matrix

“Unavailable” means the approved profile must not send a speculative read, not
that a blank value should be invented. `Yes` is an expected capability to
exercise during hardware QA. Route mutation shown in the table is informational
for the optional Phase B only.

| Model | Inventory / identity | Topology | Signal / input HDCP | Output HDCP / auth | Input / output names / temp | Route read / optional mutation | Hardware status | Evidence / required retest |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Extron IN1804 | Canonical / `1I` | fixed 4x1 | Yes / legacy mapping | Yes / Yes | Yes / Yes / Yes | `!` / `<I>*1!` | PARTIAL | Prior read-only evidence recorded temp `59`, input HDCP `0,1,0,1`, signal `0*1*0*1`, and route-read PASS. No positive HDCP `2` case observed. |
| Extron IN1806 | Canonical / exact `IN1806`, part number `60-1663-01` | fixed 6x1 | Yes / legacy mapping | Yes / Yes | Yes / Yes / Yes | `1%` / `<I>*1%` | FAIL | Hardware banner identified `IN1806`, firmware `V1.04`, part number `60-1663-01`, while the pre-remediation application did not support the model. Post-remediation retest must prove video-only polling remains authoritative with audio breakaway and does not use `1!`. |
| Extron IN1808 | Canonical / `1I` | fixed 8x1 | Yes / legacy mapping | Yes / Yes | Yes / Yes / Yes | `1%` / `<I>*1%` | PARTIAL | Prior read-only evidence was collected with the legacy combined AV route read. Post-remediation retest must prove `1%` video polling, including a breakaway-safe case where practical. No positive HDCP `2` case observed. Loop Out remains deferred. |
| Extron IN1608 xi | Canonical / exact closed `1I` aliases | fixed 8x1 | Yes / modern mapping | Yes / Yes | Yes / unavailable / Yes | `&` / `<I>&` | FAIL | Hardware authenticated and returned `IN1608 xi IPCP SA`; pre-remediation exact resolver rejected that valid observed identity. Post-remediation retest must also prove video-only route polling and no combined `!` polling. |
| DTP CrossPoint 84 | Canonical / documented DTP identity | fixed 8x4 | Yes / modern mapping | `WO<N>HDCP` / unavailable | Yes / Yes / REQUIRED-PROVE | `<O>%` / `<I>*<O>%` | NOT RUN | DTP canonical route is video-only; optional untie is `0*<O>%`. Capture actual `0LS` framing when available. |
| DTP CrossPoint 82 4K | Canonical / part number `N` | fixed 8x2 | Yes / modern mapping | `WO<N>HDCP` / unavailable | Yes / Yes / REQUIRED-PROVE | `<O>%` / `<I>*<O>%` | NOT RUN | DTP canonical route is video-only; optional untie is `0*<O>%`. Capture actual `0LS` framing when available. |
| DTP CrossPoint 84 4K | Canonical / part number `N` | fixed 8x4 | Yes / modern mapping | `WO<N>HDCP` / unavailable | Yes / Yes / REQUIRED-PROVE | `<O>%` / `<I>*<O>%` | NOT RUN | Must remain distinct from non-4K DTP 84; optional untie is `0*<O>%`. |
| DTP CrossPoint 86 4K | Canonical / part number `N` | fixed 8x6 | Yes / modern mapping | `WO<N>HDCP` / unavailable | Yes / Yes / REQUIRED-PROVE | `<O>%` / `<I>*<O>%` | FAIL | Read-only poll returned names and `0LS`, then the old route poll sent `1!` and received `E13`. Post-remediation retest must prove `<O>%` readback; no mutation required. |
| DTP CrossPoint 108 4K | Canonical / exact part number `N` aliases including `60-1381-12` | fixed 10x8 | Yes / modern mapping | `WO<N>HDCP` / unavailable | Yes / Yes / REQUIRED-PROVE | `<O>%` / `<I>*<O>%` | FAIL | Hardware returned exact part number `60-1381-12`; the pre-remediation allowlist rejected it. Post-remediation identity and read-only poll retest required. |
| XTP CrossPoint 1600 | Canonical / `N`, `I`, `*N` | dynamic board-aware | Yes / modern mapping | `W0<N>HDCP` / unavailable | unavailable / unavailable / REQUIRED-PROVE | `<O>!` / `<I>*<O>!` | NOT RUN | First-generation AV-route profile only; preserve empty-slot IDs. |
| XTP CrossPoint 3200 | Canonical / `N`, `I`, `*N` | dynamic board-aware | Yes / modern mapping | `W0<N>HDCP` / unavailable | unavailable / unavailable / REQUIRED-PROVE | `<O>!` / `<I>*<O>!` | NOT RUN | First-generation AV-route profile only; preserve empty-slot IDs. |
| XTP II CrossPoint 1600 | Canonical / `N`, `I`, `*N` | dynamic board-aware | Yes / modern mapping | unavailable / Yes | unavailable / unavailable / REQUIRED-PROVE | `<O>!` / `<I>*<O>!` | NOT RUN | Output HDCP remains UNPROVEN/unavailable. |
| XTP II CrossPoint 3200 | Canonical / `N`, `I`, `*N` | dynamic board-aware | Yes / modern mapping | unavailable / Yes | unavailable / unavailable / REQUIRED-PROVE | `<O>!` / `<I>*<O>!` | NOT RUN | Output HDCP remains UNPROVEN/unavailable. |
| XTP II CrossPoint 6400 | Canonical / `N`, `I`, `*N` | dynamic board-aware | Yes / modern mapping | unavailable / Yes | unavailable / unavailable / REQUIRED-PROVE | `<O>!` / `<I>*<O>!` | NOT RUN | Output HDCP remains UNPROVEN/unavailable. |

## Phase A — read-only hardware procedure

This is the mandatory current hardware gate. For every physically available
model selected for retest:

1. Verify inventory conversion resolves the expected canonical
   `diagnostic_model` without changing the source-model evidence.
2. Connect through the normal application/handler path and capture the exact
   identity response; verify it matches the inventory expectation.
3. Establish the complete six-field General-information tuple under the source rules above. Inventory MAC and serial are mandatory. Firmware/temperature use the approved exact SIS profile and uptime uses SNMPv2c `sysUpTime.0` through `matrix-snmp-read`. Do not mark the run PASS if any required field is missing.
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

For XTP/XTP II, retain the separately approved AV-route profile and reconcile
according to that profile.

Restore the original route if a mutation was actually authorized and performed,
then verify the same targeted readback. If a failure occurs after possible send,
do not replay automatically. Preserve raw evidence and record the optional
mutation result separately from the mandatory Phase A read-only status.


## SNMP uptime read-only hardware procedure

For each remaining supported IN/DTP fixture:
1. confirm canonical inventory MAC and serial are non-empty;
2. confirm SNMP is enabled operationally on the device;
3. resolve dedicated `matrix-snmp-read` without logging its community value;
4. issue SNMPv2c GET for exactly `1.3.6.1.2.1.1.3.0` on UDP/161;
5. record the returned TimeTicks value and formatted uptime with the community redacted;
6. reject mismatched request-id/OID/type, non-zero error-status, malformed BER, extra varbinds or timeout as incomplete evidence;
7. compare with visible device uptime where available only as a plausibility check.

No SNMP mutation, walk or trap operation is permitted.