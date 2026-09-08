# Change: Restore codec interaction parity after room UI redesign

## Why

The room codec redesign preserved most protocol handlers but replaced the working codec-screen interaction composition with a new room lifecycle and dashboard. Real-device user testing after the redesign shows that presentation-only fixes landed while important codec behavior still regressed: call-log loading, microphone-value presentation, live microphone/audio telemetry, Local Refresh, camera presentation, and multiple button actions still fail, error, or remain locked/hung.

A forensic comparison against `c442152077dd8aa6251f1d8be9fc98b765406dbd` (the `master` revision immediately before `codec-diagnostic-modern-ui`) shows that proven protocol/handler code largely remains present. The retained `gui/screens/codec_screen.py` is therefore a behavioral oracle for already-supported operations, not a GUI to restore.

Hardware acceptance of published implementation `467f2cbb502f698476f047d277052bf5ccb55147` subsequently proved that some assumptions in the first approved architecture were themselves incomplete or wrong. That SHA remains a historical pre-hardware implementation baseline and is not a permitting hardware-acceptance candidate after these findings.

Key regressions and hardware-discovered contract corrections include:

- every supported codec must automatically acquire and display the three most recent calls after the initial room diagnostic becomes usable; the previous LIVE-priority automatic-preview skip is no longer acceptable product behavior;
- TE20/TE40 pre-redesign `get_live_audio_status` polling was not carried into the new room codec dashboard consistently, and TE40 hardware shows the live microphone/speaker evidence should feed dedicated level meters rather than duplicate textual `Live ...` rows;
- TE40 exposes independent numeric microphone gain evidence through `micValue` as well as independent mute evidence through `MicSwitch`; treating TE40 microphone control as mute-only is incorrect;
- the exact TE40 microphone-gain write protocol must be recovered/verified before implementation rather than guessed, while readback remains numeric `micValue` and mute remains a separate operation;
- TE40 camera parsing currently requires at least two `itemList` entries, causing a valid one-camera installation to render `Нет данных`; camera parsing must accept zero-to-many entries and process each present camera independently;
- CloudLink Box 310 hardware shows `WEB_GetCurrentAudioParam` microphone evidence as records containing `deviceId` and `curVolume`; the fixed-field `mic1ValueIndex` / `micArray...` assumption is invalid and must be replaced by Box-specific extraction plus maximum valid `curVolume` normalization;
- the dashboard can render controls whose exact-model capability registry rejects them;
- Polycom speaker step regressed from the proven value `2` to the current generic value `1`;
- microphone parser evidence is not normatively mapped to the canonical fields consumed by the common dashboard, allowing real values to become `Нет данных`;
- speaker mutation/refresh now crosses heavier lifecycle boundaries than the proven targeted operation + readback path;
- offline snapshot/mocked tests previously passed without proving the real parser/session/device path.

## What Changes

- Keep the current common room codec dashboard and current exact-model registry as application authority.
- Amend the exact-model capability matrix for TE40 so microphone gain and microphone mute are distinct supported capabilities; do not infer the same change for TE20 or Polycom without separate evidence.
- Require TE40 numeric `micValue` normalization into canonical `microphone_volume` while preserving `MicSwitch`/mute normalization independently.
- Require protocol-discovery evidence for the TE40 microphone-gain setter (ActionID/method, payload, range and authoritative readback) before production implementation; implementation SHALL NOT invent or guess the write endpoint.
- Require TE40 camera parsing to accept and normalize `WEB_GetLocalCameraList.itemList` with zero, one, or many entries instead of requiring two entries.
- Replace the expansion/LIVE-priority automatic call-preview policy with one fresh initial call-history acquisition after the room diagnostic is accepted and before the first LIVE start for each supported current codec row; publish at most the three newest normalized calls inline.
- Keep explicit `Развернуть` / detailed journal as a separate fresh operator acquisition; when LIVE is active, explicit detail may retire and later resume LIVE through the existing bounded lifecycle.
- Restore TE20/TE40 model-specific live-audio status behavior through a room-owned live binding and present `MicValueIndex` / `SpeakerValueIndex` as dedicated microphone/speaker level meters rather than redundant textual live rows.
- Correct CloudLink Box 310 live microphone extraction for the hardware-observed `{deviceId, curVolume}` record shape while keeping Box protocol identity separate from Bar 310.
- Preserve the pre-redesign behavior at `c442152...` for operations proven to work, including Polycom speaker step `2`, without weakening current exact-row/security/currentness rules.
- Add a normative parser/normalization contract from model-specific microphone evidence to canonical accepted room evidence and then to the common dashboard.
- Keep intentionally unsupported operations unavailable: CloudLink microphone gain is not re-enabled; reboot is not invented as a room network capability merely because the new dashboard shows a button.
- Restore supported codec audio readback/control parity using targeted authoritative readback where available while preserving the current root fail-closed restore-authority rule for speaker unmute.
- Ensure every codec user action reaches bounded terminal cleanup and cannot leave GUI/lifecycle locks permanently stuck.
- Add composition/parser integration regression coverage that starts at the transport edge; manually prebuilt canonical snapshots are insufficient sole evidence.
- Re-run architecture review, implementation validation, and exact-SHA hardware acceptance after this amendment; prior offline PASS on `467f2cbb...` does not satisfy the amended contract.

## Explicit defect families

The change tracks these user-visible actions separately so a fix on one model/action cannot be mistaken for full parity:

- `Обновить статус`;
- automatic three-call inline preview after initial connection;
- explicit `Журнал звонков` / `Развернуть`;
- CloudLink live microphone bar, including Box-specific live parsing;
- TE20/TE40 live microphone/speaker level meters;
- TE40 numeric microphone gain `-` / `+` and independent microphone mute;
- TE40 camera detection/presentation for one-or-more returned camera records;
- speaker `-` / `+` and speaker mute;
- supported microphone mute;
- misleading CloudLink microphone `-` / `+` affordances where gain is not a network capability;
- misleading `Перезагрузить устройство` affordance where reboot is not a network capability.

Presentation control, SIP fix, and TE20 Wake are not new functionality in this change; existing approved behavior must not regress, but they are not used to expand scope without a reproduced defect.

## Hardware gate

All five affected codec models are confirmed `AVAILABLE` for post-implementation real-device validation: Huawei TE20, Huawei TE40, CloudLink Bar 310, CloudLink Box 310, and Polycom RPG 310.

`AVAILABLE` is an architecture input only: it means the device can be provided after implementation. It is not evidence that the amended fix is already verified. Every applicable affected scenario must still pass on the exact published post-amendment implementation SHA before independent implementation validation may issue a permitting verdict. Offline tests cannot replace this hardware gate.

Hardware observations collected against `467f2cbb502f698476f047d277052bf5ccb55147` are architecture-discovery evidence only. They invalidate conflicting assumptions but do not satisfy final acceptance for a later implementation SHA.

## Non-Goals

- Reverting the room codec visual redesign.
- Replacing working Huawei/Polycom handlers solely because the new GUI is broken.
- Introducing a second model/capability authority beside `diagnostic_dispatch`.
- Allowing concurrent authoritative room network owners.
- Inferring TE20/TE30/TE50/TE60 microphone-gain support from TE40 without separate evidence; broader Huawei TE-family model expansion is outside this amendment.
- Re-enabling CloudLink microphone-gain mutation without separate authoritative target/readback proof.
- Inventing reboot support that was not proven by the pre-redesign room behavior/current root contract.
- Inventing speaker-unmute restore targets when current exact-row restore evidence is absent.
- Redesigning Matrix, PDU, or Audio DSP surfaces.

## Behavioral Oracle

Primary pre-redesign reference:

`c442152077dd8aa6251f1d8be9fc98b765406dbd`

Current baseline at change creation:

`754099722ec14d4b9aa0516e0e085387fd0e727b`

Hardware-discovery baseline that triggered this amendment:

`467f2cbb502f698476f047d277052bf5ccb55147`

The oracle is behavioral rather than visual: the new UI may look different, but supported codec actions SHALL preserve successful model-specific request/readback semantics and cleanup behavior unless current device evidence proves that behavior invalid. Current real-device evidence takes precedence over a conflicting historical assumption, but a newly discovered state-changing protocol must be explicitly verified before implementation rather than guessed.

## Affected Specs

- `device-diagnostics-and-control`
- `room-device-interaction-lifecycle`
- `codec-call-log-usage-statistics`
- `diagnostic-ui-presentation`
