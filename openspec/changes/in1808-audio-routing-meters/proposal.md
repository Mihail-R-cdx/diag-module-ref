# Change: IN1808 audio routing meters

## Why

`Extron IN1808` is already a supported exact Matrix device, but the room Matrix
surface currently exposes only video routing/status. Real hardware investigation
now establishes enough IN1808 DSP behavior to add a focused read-only Audio mode:
audio channel names can be read, live meter values can be acquired across the
300xx/400xx/600xx DSP domains, and the DSP mix-point address space accepts the
expected 200xx grid while rejecting addresses immediately outside the observed
bounds.

The product decision is to keep the existing IN1808 row and General information
card, add an explicit action-labelled mode control in the expanded row header
(`Переключить на аудио` / `Переключить на видео`), and replace only the
right-hand Matrix tile while Audio mode is active. Audio routing
is diagnostic/read-only; this change does not authorize audio-route mutation.

## What Changes

- Add an IN1808-only Audio mode to the expanded room Matrix row.
- Keep `Общая информация` unchanged while swapping only the right-hand tile.
- Use the approved modern DMP segmented level-meter visual language: horizontal
  meters for logical inputs and vertical meters for logical outputs. Keep the
  numeric level visible, but omit the literal `dBFS` unit suffix from all
  visible IN1808 Audio meter text; unavailable numeric evidence renders as `—`.
- Show all relevant IN1808 audio meter points, including DP/HDMI/TP inputs,
  Aux, Mic/Line inputs, File Player, HDMI/DTP/analog/line outputs, and
  model-applicable amplifier outputs.
- Combine a stereo pair into one displayed meter using the louder channel
  (`max(left_dbfs, right_dbfs)`) while retaining left/right component evidence.
- Show DSP routing as a read-only matrix (Variant B): underlying 8 x 12
  routing evidence remains channel-accurate, while the room UI groups stereo
  L/R rows and columns into one compact logical matrix cell.
- Read the current physical audio source with the documented read-only `1$`
  command so `Program L/R` is explicitly linked to DP/HDMI/TP/Aux input 1..9.
- Read audio channel names through the IN1808 Audio Name SIS family and preserve
  deterministic fallback labels when a name is unavailable.
- Switch the right tile to the Audio layout immediately on the first
  `Переключить на аудио` click, before waiting for controller availability or device I/O;
  neutral placeholders make the mode change visible while Audio acquisition
  starts in the background.
- Acknowledge that accepted click locally by disabling the same mode control
  while the target Audio layout is being committed. Re-enable it as soon as
  the Audio layout is visibly committed, with a 10-second fail-safe maximum;
  controller/device completion is not part of this UI acknowledgement.
- Align horizontal input meters to logical routing rows and vertical output
  meters to logical routing columns in one shared grid; remove duplicated
  meter labels and `VALID`/`INVALID` text.
- Start IN1808 audio live metering only when Audio mode is active; stop it on
  return to Video, row collapse, room/search/context replacement, or shutdown.
- Because meter-update state scope is not documented as connection-local,
  cleanup SHALL stop polling but SHALL NOT send `*0` under this change.
- Extend the existing Matrix application/session owner rather than creating a
  parallel handler/controller/session lane.
- Keep existing video Matrix routing semantics unchanged: IN1808 video route
  authority remains `1%` / `<I>*1%`.
- For exact `Extron IN1808` only, replace the long sequential read-only Video
  full-status fan-out with the hardware-proven guarded batch: standalone exact
  `1I`, then one serialized sacrificial-`1I` + 30-query read-only batch, then
  a matching post-batch `1I`. Hardware evidence confirms that the first
  in-batch payload is omitted while all 30 required payloads remain ordered.
  Production requires the exact aggregate-echo + 30-useful-payload shape and
  field-specific parsing. Because the SIS payloads are untagged, the change
  explicitly accepts the residual possibility of an indistinguishable
  same-grammar stale/delayed/duplicate payload only as a bounded risk for
  read-only diagnostic evidence; the batch grants no mutation authority.
- Reuse the already accepted current room `matrix_one_shot` Video snapshot when
  exact-IN1808 `matrix_room_live` starts. LIVE bootstrap SHALL NOT launch a
  second full Video refresh, and an accepted `Переключить на аудио` action
  SHALL NOT schedule one either. The Matrix LIVE controller may remain
  transport-lazy until Audio or another independently admitted Matrix operation
  actually needs I/O.
- When Audio is selected and LIVE has no connected Matrix session yet, establish
  that session with only the minimum exact-IN1808 identity/variant verification
  required to authorize the Audio profile; do not re-read firmware, temperature,
  HDCP, Video names, signal presence, or `1%` merely to enter Audio mode.
- Isolate audio failures from the accepted Matrix/General-information snapshot:
  an audio failure produces an Audio no-data/error state rather than relabeling
  the whole device as failed when current Matrix diagnostics remain accepted.

## Out of Scope

- Changing IN1808 audio routing, mix-point gain, mute, volume, phantom power,
  presets, DSP configuration, or other audio state.
- Reusing the DMP 64 Plus wire protocol profile verbatim.
- Adding Audio mode to IN1804, IN1806, IN1608 xi, DTP CrossPoint, or other Matrix
  models.
- Redesigning the standalone `MatrixScreen`.
- Changing the existing IN1808 video-routing mutation contract.
- Guessing unsupported amplifier paths for an IN1808 variant whose exact wire
  identity does not establish that amplifier capability.
- Adding a second room interaction lane, second persistent Matrix session, or
  handler-owned credential fallback.
- Generalizing IN1808 Video batching to IN1804, IN1806, IN1608 xi, DTP
  CrossPoint, or another Matrix profile without separate protocol evidence.
- Re-polling the complete Video snapshot solely because exact-IN1808 room LIVE
  starts or because the operator switches from Video presentation to Audio.

## Expected Result

An operator expands an IN1808 row and initially sees the existing video Matrix
dashboard. The first `Переключить на аудио` click is acknowledged locally by
temporarily disabling that same mode control while the target presentation is
committed. The same interaction changes the control to `Переключить на видео`,
leaves General information intact, and renders the complete Audio layout with
neutral/loading evidence before any device result is required. Once that Audio
layout is visibly committed the control is enabled again; a 10-second fail-safe
prevents a stuck disabled control if the presentation transition cannot
complete.

The accepted Video snapshot from the completed room one-shot remains the Video
authority. Starting IN1808 LIVE and selecting Audio do not poll that same Video
snapshot again. A legitimate future full Video refresh uses the hardware-proven exact-IN1808
guarded batch instead of the old sequential fan-out. Its correlation authority
is deliberately bounded: all detectable count/framing/parser/identity ambiguity
fails closed, while an indistinguishable same-grammar stale/delayed substitution
remains an explicit read-only diagnostic limitation and grants no mutation
authority. Selecting Audio begins Audio acquisition
directly on the lazy LIVE owner, with only a minimum
standalone exact-identity/variant check if a new transport session must be
established. Returning to Video restores the existing video tile and retires the
Audio live subcontext.
