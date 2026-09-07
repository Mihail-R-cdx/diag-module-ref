# Change: Restore codec interaction parity after room UI redesign

## Why

The room codec redesign preserved most protocol handlers but replaced the working codec-screen interaction composition with a new room lifecycle and dashboard. Real-device user testing after the redesign shows that presentation-only fixes landed while important codec behavior still regressed: call-log loading, microphone-value presentation, live microphone/audio telemetry, Local Refresh, and multiple button actions still fail, error, or remain locked/hung.

A forensic comparison against `c442152077dd8aa6251f1d8be9fc98b765406dbd` (the `master` revision immediately before `codec-diagnostic-modern-ui`) shows that proven protocol/handler code largely remains present. The retained `gui/screens/codec_screen.py` is therefore a behavioral oracle for already-supported operations, not a GUI to restore.

Key regressions include:

- automatic codec call-log preview competes with the same serialized room lane used by LIVE and can retire freshly started CloudLink metering;
- TE20/TE40 pre-redesign `get_live_audio_status` polling was not carried into the new room codec dashboard;
- the dashboard can render controls whose exact-model capability registry rejects them;
- Polycom speaker step regressed from the proven value `2` to the current generic value `1`;
- microphone parser evidence is not normatively mapped to the canonical fields consumed by the common dashboard, allowing real `mic_volume` data to become `Нет данных`;
- speaker mutation/refresh now crosses heavier lifecycle boundaries than the proven targeted operation + readback path;
- offline snapshot/mocked tests previously passed without proving the real parser/session/device path.

## What Changes

- Keep the current common room codec dashboard and current exact-model registry as application authority.
- Make an exact-model capability matrix normative before implementation for TE20, TE40, CloudLink Bar 310, CloudLink Box 310, and Polycom RPG 310.
- Preserve the pre-redesign behavior at `c442152...` for operations proven to work, including Polycom speaker step `2`, without weakening current exact-row/security/currentness rules.
- Add a normative parser/normalization contract from model-specific microphone evidence to canonical accepted room evidence and then to the common dashboard.
- Restore CloudLink Bar/Box live microphone metering while changing automatic inline call-log preview so it never retires active LIVE merely to enrich the card.
- Restore TE20/TE40 model-specific live-audio status behavior through a room-owned live binding.
- Keep intentionally unsupported operations unavailable: CloudLink microphone gain is not re-enabled; reboot is not invented as a room network capability merely because the new dashboard shows a button.
- Make explicit call-log opening use the proven fresh model-specific retrieval path independently from automatic preview.
- Restore supported codec audio readback/control parity using targeted authoritative readback where available while preserving the current root fail-closed restore-authority rule for speaker unmute.
- Ensure every codec user action reaches bounded terminal cleanup and cannot leave GUI/lifecycle locks permanently stuck.
- Add composition/parser integration regression coverage that starts at the transport edge; manually prebuilt canonical snapshots are insufficient sole evidence.
- Make hardware-backed acceptance on the exact published implementation SHA a required independent-validation gate for every affected codec model.

## Explicit defect families

The change tracks these user-visible actions separately so a fix on one model/action cannot be mistaken for full parity:

- `Обновить статус`;
- explicit `Журнал звонков` / `Развернуть`;
- CloudLink live microphone bar;
- TE20/TE40 live microphone/speaker audio;
- speaker `-` / `+` and speaker mute;
- supported microphone mute;
- misleading CloudLink microphone `-` / `+` affordances where gain is not a network capability;
- misleading `Перезагрузить устройство` affordance where reboot is not a network capability.

Presentation control, SIP fix, and TE20 Wake are not new functionality in this change; existing approved behavior must not regress, but they are not used to expand scope without a reproduced defect.

## Hardware gate

All five affected codec models are confirmed `AVAILABLE` for post-implementation real-device validation: Huawei TE20, Huawei TE40, CloudLink Bar 310, CloudLink Box 310, and Polycom RPG 310.

`AVAILABLE` is an architecture input only: it means the device can be provided after implementation. It is not evidence that the fix is already verified. Every applicable affected scenario must still pass on the exact published implementation SHA before independent implementation validation may issue a permitting verdict. Offline tests cannot replace this hardware gate.

## Non-Goals

- Reverting the room codec visual redesign.
- Replacing working Huawei/Polycom handlers solely because the new GUI is broken.
- Introducing a second model/capability authority beside `diagnostic_dispatch`.
- Allowing concurrent authoritative room network owners.
- Re-enabling CloudLink microphone-gain mutation without separate authoritative target/readback proof.
- Inventing reboot support that was not proven by the pre-redesign room behavior/current root contract.
- Inventing speaker-unmute restore targets when current exact-row restore evidence is absent.
- Redesigning Matrix, PDU, or Audio DSP surfaces.

## Behavioral Oracle

Primary pre-redesign reference:

`c442152077dd8aa6251f1d8be9fc98b765406dbd`

Current baseline at change creation:

`754099722ec14d4b9aa0516e0e085387fd0e727b`

The oracle is behavioral rather than visual: the new UI may look different, but supported codec actions SHALL preserve successful model-specific request/readback semantics and cleanup behavior unless current device evidence proves that behavior invalid.

## Affected Specs

- `device-diagnostics-and-control`
- `room-device-interaction-lifecycle`
- `codec-call-log-usage-statistics`
- `diagnostic-ui-presentation`
