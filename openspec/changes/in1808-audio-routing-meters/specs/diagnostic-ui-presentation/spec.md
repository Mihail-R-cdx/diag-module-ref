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
- **AND** the same synchronous UI action changes the right tile to the complete
  IN1808 Audio layout before any controller/device result is required
- **AND** unavailable meters initially show neutral `— dBFS` evidence and
  route cells show neutral/unknown placeholders rather than the old Video tile
- **AND** the same header control immediately reads `Видео`
- **AND** temporary Matrix-controller busy state is handled in the background
  without requiring a second operator click

#### Scenario: Operator returns to Video

- **GIVEN** an expanded IN1808 row is in Audio mode
- **WHEN** the operator activates `Видео`
- **THEN** the existing video Matrix right tile is restored
- **AND** the mode control returns to `Аудио`
- **AND** the left General-information presentation is unchanged

### Requirement: IN1808 Audio presentation uses one aligned logical routing grid

The IN1808 Audio right tile SHALL use the hardware-QA-refined Variant B
presentation: one compact logical routing grid with meters physically aligned to
the same row/column geometry.

The visible input rows SHALL be exactly:

```text
Program L/R
Mic/Line 1
Mic/Line 2
Line In 3
Line In 4
File Player L/R
```

The visible output columns SHALL be exactly the applicable subset of:

```text
HDMI 1A
TP/DTP 1B
DTP Analog
Line Out 1
Line Out 2
Line Out 3
Line Out 4
Amplifier
```

`Amplifier` appears only for an exact amplifier-capable IN1808 variant.

The UI SHALL group raw L/R route evidence only for presentation:

- Program L/R uses raw routing rows 0 and 1;
- File Player L/R uses raw routing rows 6 and 7;
- HDMI 1A uses raw columns 0 and 1;
- TP/DTP 1B uses raw columns 2 and 3;
- DTP Analog uses raw columns 4 and 5;
- SA Amplifier uses raw columns 10 and 11;
- MA70 Amplifier uses raw column 10.

Mic/Line 1/2, Line In 3/4 and Line Out 1..4 remain one raw row/column each.

The underlying channel-accurate 8 x 12 routing snapshot SHALL remain available
unchanged. Grouping SHALL be presentation-only.

For one grouped logical routing cell:

- at least one applicable ACTIVE component -> filled dot;
- all applicable components known INACTIVE -> hollow dot;
- no ACTIVE component plus one or more UNKNOWN components -> neutral UNKNOWN
  marker.

The visible grid SHALL NOT render the words `ACTIVE`, `INACTIVE`, `VALID`
or `INVALID`. Route cells remain read-only/non-actionable. Tooltip or
accessibility metadata SHOULD expose component states for a grouped cell.

#### Scenario: Stereo route evidence is compacted without rewriting raw evidence

- **GIVEN** a logical stereo row or column contains multiple raw crosspoints
- **WHEN** the Audio routing surface renders
- **THEN** the visible intersection is one grouped dot/unknown marker
- **AND** its state follows the grouped semantics above
- **AND** the original per-channel routing evidence remains unchanged
- **AND** no click can emit an Audio mutation

### Requirement: IN1808 Audio meters align exactly with logical routing rows and columns

The input-meter rail, routing grid and output-meter header SHALL share one
logical sizing model rather than independent visual layouts.

Input meters SHALL be horizontal and SHALL be placed to the left of the
corresponding logical routing row. Their vertical center SHALL match the row
center.

Output meters SHALL be vertical and SHALL be placed above the corresponding
logical routing column. Their horizontal center SHALL match the column center.

The top-left region above the input/row-label rail SHALL remain empty because it
does not correspond to an output column.

Input/output names SHALL be rendered once in the routing row/column headers.
Meter widgets SHALL NOT repeat those names. Numeric dBFS SHALL remain visible;
`VALID`/`INVALID` captions SHALL not be shown.

Routing data rows SHALL be compact and uniform; the target is approximately
half the vertical size of the hardware-tested pre-refinement implementation,
subject to font/accessibility minimums. Meter bars MAY become narrower to keep
the alignment exact.

All meter widgets retain the modern 20-segment Audio DSP visual language.
Stereo logical meters continue to display max(L,R) while preserving component
evidence internally.

#### Scenario: Output meter aligns to its routing column

- **GIVEN** an applicable logical output column
- **WHEN** the Audio tile lays out its output meter and routing grid
- **THEN** the meter centerline equals the routing-column centerline
- **AND** no duplicate output label is rendered below or beside the meter

#### Scenario: Input meter aligns to its routing row

- **GIVEN** an applicable logical input row
- **WHEN** the Audio tile lays out its input meter and routing grid
- **THEN** the horizontal meter centerline equals the routing-row centerline
- **AND** no duplicate input label is rendered by the meter widget

### Requirement: Program L/R meter follows the current physical audio source

The visible `Program L/R` input meter SHALL use the approved physical source
selected by mandatory read-only `1$`.

For `1$ = 1..9`, the Program meter uses the corresponding DP/HDMI/TP/Aux
300xx meter group and applies the approved stereo max(L,R) display rule.
If the Program source or its meter evidence is unavailable, the Program meter
SHALL show `— dBFS` and SHALL NOT infer a source from video `1%`.

The physical DP/HDMI/TP/Aux groups remain normalized evidence; they are not
rendered as separate routing rows in this compact matrix view.

#### Scenario: Program source is known

- **GIVEN** `1$` identifies HDMI 3
- **AND** current HDMI 3 left/right meter evidence is available
- **WHEN** the Audio tile renders Program L/R
- **THEN** its horizontal meter uses the HDMI 3 logical meter level
- **AND** the row remains labelled `Program L/R`
- **AND** video `1%` is not consulted for this choice

#### Scenario: Program source is unknown

- **WHEN** `1$` is UNKNOWN or the selected source meter is unavailable
- **THEN** Program L/R shows `— dBFS`
- **AND** the UI does not guess another physical input

### Requirement: IN1808 Audio presentation discloses mapping basis without visual noise

The routing surface SHALL expose safe non-interactive metadata equivalent to
`Карта каналов: профиль IN1808` through caption, tooltip, or accessibility
text so the adopted `IN1808_PRODSP_PROFILE_MAPPING` is not presented as
hardware-cross-checked discovery.

The mapping-basis disclosure SHALL not reintroduce per-cell
`ACTIVE`/`INACTIVE` text or meter `VALID`/`INVALID` captions.

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