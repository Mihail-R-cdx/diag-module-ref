## ADDED Requirements

### Requirement: Expanded IN1808 row switches only the right tile between Video and Audio

For exact `Extron IN1808`, the expanded room Matrix row SHALL retain the
existing `Общая информация` card unchanged and SHALL add one mode control in
the row header aligned with the existing model/status content.

The default expanded mode is Video and the control text is `Аудио`. Selecting
it changes the local mode to Audio and the same control text to `Видео`.
Selecting `Видео` returns to the existing video Matrix presentation.

Only the right-hand expanded tile changes between modes. The mode switch SHALL
not create another room row, another top-level screen, or another General
information card.

Other exact Matrix models SHALL not show this IN1808 Audio-mode control.

#### Scenario: Operator enters Audio mode

- **GIVEN** exact current row is `Extron IN1808` and is expanded in Video mode
- **WHEN** the operator activates `Аудио`
- **THEN** `Общая информация` remains the same left card
- **AND** only the right tile changes to the IN1808 Audio presentation
- **AND** the same header control now reads `Видео`

#### Scenario: Operator returns to Video

- **GIVEN** an expanded IN1808 row is in Audio mode
- **WHEN** the operator activates `Видео`
- **THEN** the existing video Matrix right tile is restored
- **AND** the mode control returns to `Аудио`
- **AND** the left General-information presentation is unchanged

### Requirement: IN1808 Audio presentation uses Variant B routing with modern segmented meters

The IN1808 Audio right tile SHALL use Variant B: the primary diagnostic
presentation combines read-only DSP routing with compact live meters.

It SHALL expose all approved input/source meter groups (DP/HDMI/TP, Aux,
Mic/Line and File Player) and all approved output meter groups
(HDMI/TP-DTP/DTP-analog/Line Out and exact-variant amplifier outputs).

The tile SHALL also show the current physical Program source from mandatory
read-only `1$` metadata. Accepted input 1..9 evidence binds that named
DP/HDMI/TP/Aux source to both `Program L` and `Program R`; unavailable
evidence is shown as UNKNOWN and is not guessed from video `1%`.

Numeric meters SHALL use the same modern vertical 20-segment dBFS visual
language already approved for room Audio DSP meters. The legacy standalone
horizontal Audio DSP presentation is not the visual authority.

Stereo meter groups SHALL show one meter using the louder L/R level while
routing remains channel-accurate: L/R route subchannels are not collapsed into
one boolean cell.

The routing grid SHALL visibly distinguish ACTIVE, INACTIVE and UNKNOWN with a
non-color semantic/accessibility representation. Audio route cells are
read-only and non-actionable.

The source/output labels for the 200xx grid come from the adopted
`IN1808_PRODSP_PROFILE_MAPPING`, not runtime-discovered identity. The surface
SHALL expose safe non-interactive metadata equivalent to
`Карта каналов: профиль IN1808` through caption/tooltip/accessibility text so
the mapping basis is not represented as cell-by-cell hardware discovery.

#### Scenario: Stereo meter and routing evidence coexist

- **GIVEN** one stereo audio group has two current component meter values
- **AND** its L/R route crosspoints are independently available
- **WHEN** the Audio tile renders
- **THEN** one combined logical meter shows the louder component level
- **AND** routing remains represented by the independent channel/crosspoint evidence
- **AND** no click on a route cell emits a routing mutation intent

#### Scenario: Route evidence is unknown

- **GIVEN** one current Audio route cell is UNKNOWN
- **WHEN** the grid renders
- **THEN** the cell is visibly non-authoritative and distinct from ACTIVE/INACTIVE
- **AND** it cannot be used as mutation authority

### Requirement: IN1808 Audio names and variant capability remain truthful

Where accepted Audio Name evidence is available, the Audio presentation SHALL
use it for the corresponding stable logical channel. Missing names use
deterministic semantic fallback labels.

Variant-dependent amplifier channels SHALL be shown only when exact current
IN1808 wire-variant evidence establishes the capability. The GUI SHALL not
infer amplifier channels from available width, a prior row, a generic IN1808
substring, or a stale snapshot.

#### Scenario: Base IN1808 has no amplifier capability

- **GIVEN** exact current accepted IN1808 variant evidence establishes no amplifier
- **WHEN** the Audio tile renders
- **THEN** no amplifier meter/routing column is fabricated
- **AND** the remaining channel identities/order stay unchanged

### Requirement: IN1808 Audio failure is isolated from accepted Matrix presentation

Failure to acquire or update optional IN1808 Audio diagnostics SHALL affect the
Audio tile only when the current Matrix/General-information snapshot remains
accepted.

The Audio tile SHALL clear unavailable current meter/routing evidence and show
a safe no-data/error state. It SHALL NOT fabricate a meter, route, name, or
audio value and SHALL NOT relabel the whole row as failed solely because the
Audio live capability failed.

Returning to Video SHALL still expose the last accepted current video Matrix
presentation under its existing currentness/staleness rules.

#### Scenario: Audio polling fails after Matrix diagnostics succeeded

- **GIVEN** current IN1808 General information and video Matrix evidence are accepted
- **AND** Audio mode later encounters a protocol/transport failure
- **WHEN** the failure is presented
- **THEN** current unavailable Audio evidence is cleared/shown as no-data
- **AND** General information remains unchanged
- **AND** the accepted video Matrix snapshot is not rewritten as an Audio failure