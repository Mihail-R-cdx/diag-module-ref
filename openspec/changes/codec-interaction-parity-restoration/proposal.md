# Change: Restore codec interaction parity after room UI redesign

## Why

The room codec redesign preserved most protocol handlers but replaced the working codec-screen interaction composition with a new room lifecycle and dashboard. User testing on real codecs after the redesign shows that presentation-only fixes landed, while important codec behavior still regressed: call log loading, microphone-volume presentation, live microphone/audio telemetry, and multiple button actions still fail, error, or remain locked/hung.

A forensic comparison against `c442152077dd8aa6251f1d8be9fc98b765406dbd` (the `master` revision immediately before `codec-diagnostic-modern-ui`) shows that the proven pre-redesign protocol/handler code largely remains present. The legacy `gui/screens/codec_screen.py` also remains available as a behavioral oracle. The change therefore treats this as an interaction-parity regression, not as a new protocol-discovery project.

Key observed architectural regressions include:

- automatic codec call-log preview is requested immediately after row expansion and competes with the same serialized room lane used by LIVE, so preview admission can retire freshly started CloudLink live metering;
- TE20/TE40 pre-redesign `get_live_audio_status` polling was not carried into the new room codec dashboard;
- the new dashboard renders controls whose exact-model capability registry rejects them, producing misleading affordances and user-visible errors;
- speaker-volume mutation now crosses a heavier mutation/shutdown/full-refresh lifecycle instead of the proven targeted operation + authoritative readback path;
- offline regression tests proved synthetic snapshots and coordinator transitions but did not prove the real handler/session path that user-visible codec behavior depends on.

## What Changes

- Keep the current common room codec dashboard and current exact-model registry as application authority.
- Use the pre-redesign codec interaction behavior at `c442152...` as the required behavioral oracle for already-supported operations; do not re-invent working Huawei/Polycom requests without evidence that the old path itself is broken.
- Restore CloudLink Bar 310 / Box 310 live microphone metering without allowing automatic call-log preview to starve or permanently retire LIVE.
- Restore TE20/TE40 model-specific live-audio status behavior through a room-owned live binding rather than through the reusable legacy widget.
- Restore exact-model codec audio readback/control parity for operations that were already supported before redesign, while keeping intentionally unsupported operations (including CloudLink microphone gain unless separately proven/approved) unavailable as network capabilities.
- Make explicit call-log opening use the proven model-specific retrieval path and remain functional independently from automatic preview presentation.
- Ensure every codec user action reaches a bounded terminal state and releases UI/lifecycle locks on success, ordinary failure, cancellation, timeout, and connection loss.
- Add integration-level regression coverage that executes the real composition/controller/interactive-session boundary with model handlers substituted only at the transport edge; snapshot-only tests are insufficient acceptance evidence.
- Require real-device acceptance for each affected codec defect before the corresponding defect can be considered closed.

## Non-Goals

- Reverting the room codec visual redesign.
- Replacing current Huawei/Polycom handlers solely because the new GUI is broken.
- Introducing a second model/capability authority beside `diagnostic_dispatch`.
- Allowing concurrent authoritative room network owners.
- Re-enabling CloudLink microphone-gain mutation without separate authoritative target/readback proof.
- Redesigning Matrix, PDU, or Audio DSP surfaces.

## Behavioral Oracle

Primary pre-redesign reference:

`c442152077dd8aa6251f1d8be9fc98b765406dbd`

Current baseline at change creation:

`754099722ec14d4b9aa0516e0e085387fd0e727b`

The oracle is behavioral rather than visual: the new UI may look different, but supported codec actions SHALL preserve the successful model-specific request/readback semantics and cleanup behavior that existed before the codec room redesign unless current device evidence proves that behavior invalid.

## Affected Specs

- `device-diagnostics-and-control`
- `room-device-interaction-lifecycle`
- `codec-call-log-usage-statistics`
- `diagnostic-ui-presentation`
