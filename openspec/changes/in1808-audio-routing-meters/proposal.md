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
card, add an `Аудио` / `Видео` mode toggle in the expanded row header, and
replace only the right-hand Matrix tile while Audio mode is active. Audio routing
is diagnostic/read-only; this change does not authorize audio-route mutation.

## What Changes

- Add an IN1808-only Audio mode to the expanded room Matrix row.
- Keep `Общая информация` unchanged while swapping only the right-hand tile.
- Use the approved modern DMP visual language for compact vertical segmented
  dBFS meters.
- Show all relevant IN1808 audio meter points, including DP/HDMI/TP inputs,
  Aux, Mic/Line inputs, File Player, HDMI/DTP/analog/line outputs, and
  model-applicable amplifier outputs.
- Combine a stereo pair into one displayed meter using the louder channel
  (`max(left_dbfs, right_dbfs)`) while retaining left/right component evidence.
- Show DSP routing as a read-only matrix (Variant B): routing remains channel
  accurate, while stereo groups receive one combined meter.
- Read the current physical audio source with the documented read-only `1# Change: IN1808 audio routing meters

## Why

`Extron IN1808` is already a supported exact Matrix device, but the room Matrix
surface currently exposes only video routing/status. Real hardware investigation
now establishes enough IN1808 DSP behavior to add a focused read-only Audio mode:
audio channel names can be read, live meter values can be acquired across the
300xx/400xx/600xx DSP domains, and the DSP mix-point address space accepts the
expected 200xx grid while rejecting addresses immediately outside the observed
bounds.

The product decision is to keep the existing IN1808 row and General information
card, add an `Аудио` / `Видео` mode toggle in the expanded row header, and
replace only the right-hand Matrix tile while Audio mode is active. Audio routing
is diagnostic/read-only; this change does not authorize audio-route mutation.

## What Changes

- Add an IN1808-only Audio mode to the expanded room Matrix row.
- Keep `Общая информация` unchanged while swapping only the right-hand tile.
- Use the approved modern DMP visual language for compact vertical segmented
  dBFS meters.
- Show all relevant IN1808 audio meter points, including DP/HDMI/TP inputs,
  Aux, Mic/Line inputs, File Player, HDMI/DTP/analog/line outputs, and
  model-applicable amplifier outputs.
- Combine a stereo pair into one displayed meter using the louder channel
  (`max(left_dbfs, right_dbfs)`) while retaining left/right component evidence.

  command so `Program L/R` is explicitly linked to DP/HDMI/TP/Aux input 1..9.
- Read audio channel names through the IN1808 Audio Name SIS family and preserve
  deterministic fallback labels when a name is unavailable.
- Start IN1808 audio live metering only when Audio mode is active; stop it on
  return to Video, row collapse, room/search/context replacement, or shutdown.
- Because meter-update state scope is not documented as connection-local,
  cleanup SHALL stop polling but SHALL NOT send `*0` under this change.
- Extend the existing Matrix application/session owner rather than creating a
  parallel handler/controller/session lane.
- Keep existing video Matrix routing semantics unchanged: IN1808 video route
  authority remains `1%` / `<I>*1%`.
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

## Expected Result

An operator expands an IN1808 row and initially sees the existing video Matrix
dashboard. The row offers `Аудио`; selecting it changes that same control to
`Видео`, leaves General information intact, and replaces only the right-hand
tile with live audio meters plus a read-only DSP routing matrix. Returning to
Video restores the existing video tile and retires the Audio live subcontext.
