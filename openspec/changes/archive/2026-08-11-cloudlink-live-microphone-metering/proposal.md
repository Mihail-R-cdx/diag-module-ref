# Change: cloudlink-live-microphone-metering

## Why

CloudLink Bar 310 and CloudLink Box 310 expose live microphone-level observations in their web APIs, but the diagnostic application does not currently poll or display those observations. The operator therefore cannot see whether room microphones are producing signal while viewing either the codec page or the PDU page that already resolves and diagnoses the related room codec.

The existing Extron DMP 64 Plus page establishes the desired presentation pattern: a continuously moving horizontal meter updated once per second. CloudLink metering must preserve the existing codec and PDU success contracts: a missing or temporarily malformed live sample is optional telemetry and must not erase normal codec status or convert an accepted PDU refresh into a failure.

The two CloudLink 310 models expose different raw payloads, so the protocol boundary must normalize them into one narrow canonical microphone-level sample before GUI rendering. The live lifecycle must also remain stale-safe, background-only for network I/O, and independent from the existing ordinary codec status refresh.

## What Changes

- Add a CloudLink 310 live microphone-meter capability for exact models `CloudLink Bar 310` and `CloudLink Box 310`.
- For Bar 310, read `GET /v1/mediacontrol/mic/current-volume`, decode `curMicVouumeList`, and use the maximum valid `curVolume` across every array element regardless of `deviceId`.
- For Box 310, read `WEB_GetCurrentAudioParam` through the existing authenticated CloudLink session and use the maximum value from the closed microphone-only field set: `mic1ValueIndex` through `mic4ValueIndex` and the nine `micArray*_0*ValIdx` fields. TRS, RCA, HDMI, Bluetooth, UAC, power-hint, and other non-microphone fields are excluded.
- Normalize both models to one optional raw level and one display fraction using a temporary fixed display ceiling of `20`: `0` is valid silence, `20` is full scale, and values above `20` are display-clamped to full scale.
- Poll at a one-second cadence with no overlapping sample requests for one current meter context.
- Keep live-meter acquisition outside ordinary CloudLink `get_status()` so meter unavailability cannot invalidate otherwise successful codec diagnostics.
- Treat endpoint-local unsuccessful/malformed live samples as unavailable telemetry and attempt the next scheduled sample; never manufacture zero from absence.
- Preserve typed authentication/session/transport handling and existing application-owned credential policy. Meter success is not new credential-success evidence.
- Add `Уровень микрофонов` to the codec `Параметры и управление` card after `Статус микрофона` and before `Журнал звонков`, rendered as a horizontal meter with the same visual semantics as the existing DMP meter and no numeric overlay.
- Extend PDU related-codec enrichment so a resolved Bar 310 or Box 310 can continue live microphone metering after the initial related-codec status succeeds.
- Add the same meter as the top row of the PDU `Комната и связанный кодек` block. VIP remains the first room-context row immediately below the meter and retains its existing prominent treatment.
- Hide the live-meter row when the exact current codec or resolved related codec is not one of the two supported CloudLink 310 models.
- Invalidate live metering immediately when its authoritative model/IP/credential/PDU-enrichment context is superseded; stale queued work must be dropped before handler acquisition and I/O where applicable, and stale callbacks must not update either screen.
- Add synthetic regression coverage for both model payloads, zero/unavailable distinction, range normalization, cadence/non-overlap, stale suppression, codec presentation, PDU presentation, and cleanup.

## Impact

Affected specifications:

- new `cloudlink-live-microphone-metering`
- modified `pdu-room-codec-enrichment`

Expected implementation areas include:

- `handlers/huawei/bar310.py` or a focused CloudLink meter protocol helper
- a focused application-owned CloudLink meter lifecycle/controller boundary
- `gui/screens/codec_screen.py`
- `gui/pdu_room_codec_enrichment.py`
- `gui/screens/pdu_screen.py`
- application composition wiring
- focused synthetic meter and PDU-enrichment tests

This change does not alter equipment-inventory identity or codec selection, supported diagnostic-model recognition, ordinary codec status required-core semantics, DMP protocol/OIDs, PDU outlet operations, Matrix behavior, state-changing codec operations, credential source/storage, or Graphify artifacts.
