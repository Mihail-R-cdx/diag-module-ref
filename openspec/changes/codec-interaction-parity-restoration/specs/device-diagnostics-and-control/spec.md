## MODIFIED Requirements

### Requirement: Current codec room-control support matrix is a fixed acceptance oracle

The unified exact-model registration SHALL remain the sole runtime capability authority. Implementation and tests SHALL prove these exact network-capability declarations:

| Exact model | speaker_adjust | speaker_mute | microphone_adjust | microphone_mute | reboot |
| --- | --- | --- | --- | --- | --- |
| `Huawei TE20` | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | UNSUPPORTED |
| `Huawei TE40` | SUPPORTED | SUPPORTED | **SUPPORTED** | SUPPORTED | UNSUPPORTED |
| `Huawei TE50` | SUPPORTED | SUPPORTED | **SUPPORTED** | SUPPORTED | UNSUPPORTED |
| `CloudLink Bar 310` | SUPPORTED | SUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| `CloudLink Box 310` | SUPPORTED | SUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| `Polycom RPG 310` | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | UNSUPPORTED |

This table is an OpenSpec/test oracle and SHALL NOT become a second runtime registry.

TE40 numeric microphone gain is distinct from microphone mute. Its approved primary-input target is `MIC1`. User-facing configured gain range is `-12 dB .. +9 dB`, step `1 dB`; device/wire range is `0..21`, step `1`, with `gain_db = mic1Value - 12` and `mic1Value = gain_db + 12`.

Speaker mute support for all five SHALL continue to use only the approved volume-zero/restore desired-state policy and proven exact-row/generation restore evidence; it does not imply a separate raw speaker-mute wire command.

Polycom RPG 310 speaker adjustment SHALL use range `0..100`, step `2`. TE20/TE40 speaker adjustment SHALL use `0..21`, step `1`. Bar/Box speaker adjustment SHALL use `0..15`, step `1`.

Post-cycle LIVE capability is not inferred from this mutation table; it is advertised separately by the same exact-model registration. In this change Box 310 SHALL advertise no post-cycle LIVE binding.

#### Scenario: Current codec registration matrix is checked

- **WHEN** composition tests inspect the six current exact codec registrations
- **THEN** every operation matches the table above
- **AND** TE40 and TE50 expose microphone gain and microphone mute as separate supported operations
- **AND** Box 310 does not acquire a post-cycle LIVE capability by sharing a handler with Bar 310
- **AND** runtime resolution still comes from the unified registry rather than this test-oracle table

### Requirement: Codec room-control adapters reuse approved typed operations and explicitly reject unsupported operations

The room codec-control capability SHALL reuse existing approved safe codec operation/readback semantics rather than duplicate protocol command grammar in the room GUI. Each exact codec registration SHALL bind an application/core codec-control adapter, or equivalent registry-owned binding, that can answer operation support before network acquisition and construct typed desired-state/readback operations only for approved controls.

A standalone widget branch, handler attribute probe, accepted read-only field, shared handler type, or visually present button SHALL NOT silently promote a state-changing or LIVE capability.

`Huawei TE20` and `Polycom RPG 310` remain microphone-mute models with no approved numeric microphone-adjust mutation in this change. `Huawei TE40` and exact-model `Huawei TE50` support both independent numeric microphone gain and independent microphone mute under the approved TE40 contract. `CloudLink Bar 310` and `CloudLink Box 310` retain both microphone-adjust and separate microphone-mute mutation as unsupported.

Reboot SHALL remain unsupported for the current six-codec baseline.

#### Scenario: Microphone has mute but no numeric gain contract

- **GIVEN** exact model is `Huawei TE20` or `Polycom RPG 310`
- **WHEN** its room codec-control capability is composed
- **THEN** `microphone_mute` is supported
- **AND** `microphone_adjust` is unsupported
- **AND** shared GUI code does not reinterpret mute state as a numeric gain range

#### Scenario: CloudLink microphone controls remain network-unsupported

- **GIVEN** exact model is `CloudLink Bar 310` or `CloudLink Box 310`
- **WHEN** its room codec-control capability is composed
- **THEN** `microphone_adjust` and `microphone_mute` are both unsupported for room mutation
- **AND** fixed visual affordances may use only the existing local informational path
- **AND** no accepted numeric read evidence promotes either mutation capability

#### Scenario: TE40/TE50 numeric gain and mute are independent supported operations

- **GIVEN** exact model is `Huawei TE40` or `Huawei TE50`
- **WHEN** its room codec-control capability is composed
- **THEN** `microphone_adjust` is supported only through the approved `MIC1` gain contract
- **AND** `microphone_mute` remains separately supported
- **AND** changing gain never reuses `WEB_OpenMicAPI` / `WEB_CloseMicAPI`
- **AND** numeric gain value `0` is not interpreted as mute authority

### Requirement: Model-specific interactive codec session paths

The shared interactive controller SHALL preserve the supported transports, session artifacts, and operation boundaries of Huawei TE20, Huawei TE40, Huawei TE50, CloudLink Bar 310, CloudLink Box 310, and Polycom RPG 310. A model SHALL use only its supported functions, and functions on a separate worker path SHALL remain separate unless explicitly listed.

CloudLink Bar 310 and CloudLink Box 310 SHALL continue to use the same reviewed `CloudLinkBar310Handler` implementation while retaining exact assigned application model in operation context. Shared protocol capability SHALL NOT authorize Bar/Box aliasing, credential sharing, successful-index/profile sharing, model switching during recovery, or capability promotion from one exact model to the other.

For the CloudLink 310 family, one application-selected credential SHALL bind one handler generation for the exact model/IP/credential context. That generation MAY own:

```text
modern read subcontext
legacy compatibility/control subcontext
```

The modern read subcontext SHALL be established through `POST /v1/login/session` followed by `POST /v1/login/account`, retain cookies/token in memory only, and service only operations explicitly approved for the modern context. Modern action.cgi compatibility in this change is limited to the exact live-verified read-only requests `WEB_GetVersionInfoAPI`, `WEB_GetSystemMacAddrAPI`, and `WEB_GetMailboxDataAPI`.

Existing unverified read-only action.cgi operations, including audio, line/SIP, presentation, and camera reads, SHALL remain on the existing legacy compatibility path unless a later approved change proves their modern compatibility. Existing supported state-changing action.cgi operations SHALL remain on the legacy compatibility/control path and retain their existing mutation-safety rules.

The endpoint `WEB_GetCurrentAudioParam` remains classified as a legacy-compatibility endpoint for Box 310 protocol history, but **this change SHALL NOT advertise or execute it as a Box post-cycle LIVE capability**. The exact Box 310 application registration SHALL have no post-cycle LIVE binding. A future reviewed Box LIVE restoration MAY reuse that legacy transport boundary only after its own parser/normalization contract is approved.

CloudLink microphone-gain network capability is an explicit exception: for exact Bar 310 and Box 310 it SHALL remain unavailable/disabled because authoritative target selection and reconciliation are not established. The application/controller SHALL reject that network operation before device I/O. The fixed common room codec dashboard MAY retain its `−`/`+` microphone visual affordances, but for Bar/Box those affordances SHALL resolve locally as unsupported before room interaction admission and SHALL NOT be represented as a supported network capability.

The application SHALL NOT issue gain `PUT`/`POST /v1/mediacontrol/mic/devices`, use fixed device IDs, use first-HD-AI/first-plugged selection, use `gainVolume` as authoritative reconciliation, or infer gain support from a method/widget. Re-enabling gain requires a later approved contract.

Both CloudLink subcontexts belong to one handler generation and assigned credential. Model/IP/credential-context/generation invalidation SHALL supersede both. Handler/worker code SHALL NOT iterate credential candidates; application/composition remains credential-selection/fallback authority.

#### Scenario: CloudLink Bar 310 reviewed read uses modern context
- **GIVEN** exact model is `CloudLink Bar 310`
- **WHEN** an operation explicitly approved for the modern read context executes
- **THEN** it uses HTTPS:443 with the application-selected credential and modern session artifacts
- **AND** the context remains exactly `CloudLink Bar 310`

#### Scenario: CloudLink Bar 310 interactive session
- **GIVEN** the interactive context model is exactly `CloudLink Bar 310` with one application-selected credential
- **WHEN** Bar 310 performs supported interactive preparation, volume, mute, presentation, call-log, or other approved read work
- **THEN** it uses one exact Bar handler generation with the approved modern-read and legacy compatibility/control subcontexts
- **AND** call-log reads use the recovered shared in-memory modern token through `X-Access-Token`
- **AND** unverified reads and supported mutations retain their approved legacy compatibility/control path
- **AND** handler recovery does not select another credential or relabel the operation as Box 310

#### Scenario: CloudLink Box 310 reviewed read uses modern context
- **GIVEN** the exact application model is `CloudLink Box 310`
- **WHEN** an approved common modern read executes
- **THEN** it uses the shared handler modern read context
- **AND** exact Box identity remains unchanged
- **AND** recovery does not relabel or retry as Bar 310

#### Scenario: CloudLink Box 310 interactive session
- **GIVEN** the interactive context model is exactly `CloudLink Box 310`
- **WHEN** Box 310 performs an operation supported by the shared CloudLink 310 interactive capability
- **THEN** it uses HTTPS:443 through the same `CloudLinkBar310Handler` generation and the application-selected credential
- **AND** approved common modern reads use the modern read subcontext while legacy-compatible operations retain the legacy compatibility/control subcontext
- **AND** the interactive context remains exactly `CloudLink Box 310`
- **AND** recovery does not retry or relabel the operation as `CloudLink Bar 310`
- **AND** shared handler ownership does not imply or create a Box post-cycle LIVE binding

#### Scenario: Unverified action.cgi read remains legacy-compatible
- **WHEN** CloudLink refresh or interactive work needs existing audio, line/SIP, presentation, camera, or another read-only action.cgi operation not live-verified on modern auth
- **THEN** this change does not migrate that operation to the modern context
- **AND** its existing legacy compatibility path remains authoritative until separately approved

#### Scenario: Box live meter remains legacy-compatible
- **GIVEN** exact model is `CloudLink Box 310`
- **WHEN** current-change room interactive capabilities are composed
- **THEN** Box 310 advertises no post-cycle LIVE binding
- **AND** room LIVE performs no `WEB_GetCurrentAudioParam` request for Box 310
- **AND** the endpoint's legacy-compatibility transport classification remains dormant protocol knowledge for a future approved Box LIVE restoration
- **AND** this change does not require or authorize modern `X-Access-Token` or modern body-token routing for that deferred endpoint

#### Scenario: Existing CloudLink mutation stays on legacy control path
- **WHEN** Bar 310 or Box 310 performs an already supported mutation other than microphone gain, such as Wake, presentation mutation, supported mute semantics, speaker volume, or SIP configuration
- **THEN** the operation remains on its existing legacy compatibility/control path
- **AND** modern read evidence does not authorize migration or blind replay

#### Scenario: CloudLink microphone gain is disabled
- **GIVEN** exact model is `CloudLink Bar 310` or `CloudLink Box 310`
- **WHEN** user/application requests microphone-gain mutation through any network-capable boundary
- **THEN** the operation is unavailable/disabled before device network I/O
- **AND** no gain PUT/POST, fixed-ID target, first-HD-AI selection, or gain readback is attempted
- **AND** no ambiguous mutation result can trigger alternate-method replay

#### Scenario: CloudLink fixed gain affordance is local only
- **GIVEN** the fixed common room codec dashboard is rendering Bar 310 or Box 310
- **WHEN** the operator clicks visible microphone `−` or `+` while the room lock matrix otherwise permits input
- **THEN** the application resolves the affordance locally as unsupported
- **AND** no room mutation generation, handler/session acquisition or device I/O starts
- **AND** the network capability remains unavailable/disabled

#### Scenario: CloudLink generation is invalidated
- **WHEN** exact model, IP, relevant credential context, or generation is superseded
- **THEN** modern-read and legacy-compatibility/control resources are invalidated/closed
- **AND** stale callbacks cannot update the replacement context

#### Scenario: Huawei TE20 interactive session
- **WHEN** TE20 performs live audio, sleep/Wake, volume, mute, presentation, or call-log work
- **THEN** it uses saved-first HTTP:80 and runtime-supported HTTPS:443 candidates with one credential
- **AND** recovery replaces invalid Session ID, cookie, CSRF, and transport state as one handler unit

#### Scenario: Huawei TE40 interactive session
- **WHEN** TE40 performs live audio, sleep-related presentation preparation, volume, mute, presentation, or call-log work
- **THEN** it uses saved-first HTTPS:443 and HTTP:80 candidates with one credential
- **AND** recovery replaces invalid opener, cookie, Session ID, CSRF, and browser-session state as one handler unit

#### Scenario: Huawei TE50 keeps exact identity while reusing TE40 session behavior

- **GIVEN** the exact application model is `Huawei TE50`
- **WHEN** it performs a function covered by the approved TE40 contract
- **THEN** it uses the same approved TE40 transport/session behavior
- **AND** operation context, credential/profile memory, parser output, and presentation retain exact model identity `Huawei TE50`
- **AND** no loose Huawei-family or `TE*` model inference is admitted

#### Scenario: Polycom interactive controls
- **WHEN** Polycom performs volume, mute, or presentation work
- **THEN** its serialized shared handler uses HTTPS:443 login and the same credential for its lazy SSH:22 control session
- **AND** failure of either sub-session follows bounded interactive recovery

#### Scenario: Polycom call log remains separate
- **WHEN** operator loads Polycom call log
- **THEN** the existing short-lived Polycom call-log worker remains owner
- **AND** it is not routed through Huawei/shared call-log session path

## ADDED Requirements

### Requirement: Huawei TE50 is an exact-model reuse of the approved TE40 contract

`Huawei TE50` is an explicitly admitted exact application model in this change. By the product requirement's declared protocol equivalence, it SHALL reuse every approved TE40 protocol, capability, parser/normalization, presentation, call-log, Local Refresh, and currentness/cleanup contract covered by this change, including `WEB_GetCurrentAudioParam`, current-audio JSON-string decoding, `MicValueIndex`/`mic<N>ValueIndex`/`micArray<N>_<NN>ValIdx` aggregation, `0..220 -> 0..100%` microphone LIVE normalization, MIC1 configured gain/mutation, mute, speaker, camera, and lifecycle behavior.

This is exact-model registration reuse, not substring/family inference: `Huawei TE50` SHALL remain distinguishable from `Huawei TE40` in model resolution and operation context while reusing its approved implementation boundary. TE40 protocol evidence is hardware-backed; TE50 admission is based on declared product equivalence and requires exact-SHA TE50 hardware acceptance before that equivalence is treated as hardware-proven. `Huawei TE30` and `Huawei TE60` remain out of scope and SHALL NOT be inferred from this requirement.

#### Scenario: TE50 reuses the approved TE40 contract without widening the family

- **GIVEN** exact model resolution yields `Huawei TE50`
- **WHEN** a function covered by this change is composed
- **THEN** TE50 receives the corresponding approved TE40 behavior under exact TE50 identity
- **AND** `Huawei TE30` and `Huawei TE60` receive no capability merely from this reuse declaration
- **AND** TE50 hardware acceptance remains pending until tested on the exact implementation SHA

### Requirement: TE40 current-audio microphone LIVE aggregates hardware-backed microphone evidence

For exact `Huawei TE40`, both one-shot `WEB_GetCurrentAudioParam` evidence used to seed `monitor_mic_value` and true periodic `get_live_audio_status` evidence SHALL use the same exact-model current-audio microphone extractor. The approved TE40 microphone-level authority is `WEB_GetCurrentAudioParam`; `WEB_GetMonitorAudioParam` SHALL NOT remain a co-authority for either initial seed or true LIVE without separate hardware-backed contract evidence.

The successful current-audio response has the outer envelope `{ "success": 1, "data": "<JSON string>" }`; when `data` is a JSON string, the exact-model boundary SHALL decode it to an object before extraction. The extractor SHALL collect valid microphone candidates from present compatibility `MicValueIndex`, every present field whose name exactly matches `^mic\d+ValueIndex$`, and every present field whose name exactly matches `^micArray\d+_\d+ValIdx$`. A valid candidate is finite numeric evidence; booleans, null, malformed values, non-numeric strings, lists, and objects SHALL NOT be numeric candidates. The raw microphone level for the single room meter SHALL be `max(all valid microphone candidates)`. This is an application aggregation contract derived from observed TE40 telemetry; it does not assert that Huawei documents those fields as one vendor max-meter.

If there is no valid candidate, the microphone LIVE sample is unavailable and presentation SHALL render `Нет данных`, not observed zero. A valid candidate of numeric `0` is observed zero/silence. After aggregation, the existing TE40 Huawei monitor-audio normalization SHALL map raw `0..220` to `0..100%` and clamp only the presentation result according to its existing helper. `SpeakerValueIndex` SHALL NOT participate in the microphone aggregate or create a speaker LIVE capability.

The initial one-shot seed has lower authority than an accepted true LIVE sample, but both use this same extractor/aggregation contract. Exact `Huawei TE20` retains its existing `MicValueIndex`-only contract and SHALL NOT infer `micArray...` support from this TE40 evidence.

#### Scenario: TE40 current-audio authority serves initial seed and true LIVE

- **GIVEN** exact current model is `Huawei TE40`
- **WHEN** initial microphone seed or periodic true LIVE needs microphone-level evidence
- **THEN** the exact-model source is `WEB_GetCurrentAudioParam`
- **AND** the two paths use the same extractor
- **AND** `WEB_GetMonitorAudioParam` is not a co-authority for those TE40 microphone samples

#### Scenario: TE40 current-audio JSON string is decoded before extraction

- **GIVEN** `WEB_GetCurrentAudioParam` succeeds with `data` containing a JSON string object
- **WHEN** TE40 exact-model current-audio normalization runs
- **THEN** it decodes the string before selecting microphone candidates

#### Scenario: TE40 MicValueIndex remains a valid sole microphone candidate

- **GIVEN** a TE40 current-audio payload has valid `MicValueIndex = 41` and no valid matching individual or array field
- **WHEN** exact-model microphone extraction runs
- **THEN** raw microphone level is `41`

#### Scenario: TE40 individual microphone evidence supplies a level

- **GIVEN** a TE40 current-audio payload has `mic1ValueIndex = 37` and no greater valid microphone candidate
- **WHEN** exact-model microphone extraction runs
- **THEN** raw microphone level is `37`

#### Scenario: TE40 array evidence supplies microphone level when MicValueIndex is absent

- **GIVEN** a TE40 current-audio payload lacks `MicValueIndex` and has `micArray1_01ValIdx = 17`, `micArray1_02ValIdx = 83`, and `micArray1_03ValIdx = 41`
- **WHEN** exact-model microphone extraction runs
- **THEN** raw microphone level is `83`

#### Scenario: TE40 individual microphone values aggregate by maximum

- **GIVEN** a TE40 current-audio payload has valid `mic1ValueIndex = 37` and `mic2ValueIndex = 41`
- **WHEN** exact-model microphone extraction runs
- **THEN** raw microphone level is `41`

#### Scenario: TE40 multiple microphone arrays aggregate by maximum

- **GIVEN** a TE40 current-audio payload has valid `micArray1_03ValIdx = 37` and `micArray2_02ValIdx = 83`
- **WHEN** exact-model microphone extraction runs
- **THEN** raw microphone level is `83`

#### Scenario: TE40 aggregate retains the maximum across compatibility, individual, and array evidence

- **GIVEN** a TE40 current-audio payload has `MicValueIndex = 20`, `mic1ValueIndex = 37`, and `micArray1_01ValIdx = 70`
- **WHEN** exact-model microphone extraction runs
- **THEN** raw microphone level is `70`

#### Scenario: TE40 real individual and array evidence aggregates to the observed maximum

- **GIVEN** a decoded TE40 current-audio payload has `mic1ValueIndex = 37`, `micArray1_01ValIdx = 25`, `micArray1_02ValIdx = 12`, and `micArray1_03ValIdx = 37`
- **WHEN** exact-model microphone extraction runs
- **THEN** raw microphone level is `37`
- **AND** existing `0..220 -> 0..100%` presentation normalization produces its existing rounded approximately `17%` fill

#### Scenario: TE40 malformed microphone evidence is ignored

- **GIVEN** a TE40 current-audio payload has valid `micArray1_01ValIdx = 31` alongside matching individual/array fields that are null, boolean, malformed, infinite, or non-numeric strings
- **WHEN** exact-model microphone extraction runs
- **THEN** only valid finite numeric candidates participate
- **AND** raw microphone level is `31`

#### Scenario: TE40 unrelated audio inputs are excluded

- **GIVEN** a TE40 current-audio payload has valid `MicValueIndex = 20` and greater numeric `trs*`, `rca*`, `hdmi*`, `dvi*`, `dp*`, `pstn*`, or `sdi*` fields
- **WHEN** exact-model microphone extraction runs
- **THEN** raw microphone level remains `20`

#### Scenario: TE40 has no valid microphone candidate

- **GIVEN** a TE40 current-audio payload has no valid compatibility, individual, or array candidate
- **WHEN** exact-model microphone extraction runs
- **THEN** microphone LIVE is unavailable
- **AND** presentation renders `Нет данных` rather than numeric zero

#### Scenario: TE40 observed zero remains valid microphone evidence

- **GIVEN** a TE40 current-audio payload has a valid microphone candidate of numeric `0`
- **WHEN** exact-model microphone extraction runs
- **THEN** the raw microphone level is observed numeric `0`
- **AND** the normalized meter is available at `0%`

#### Scenario: TE40 speaker evidence does not affect microphone aggregate

- **GIVEN** a TE40 current-audio payload has valid `MicValueIndex = 20` and `SpeakerValueIndex = 220`
- **WHEN** exact-model microphone extraction runs
- **THEN** raw microphone level remains `20`
- **AND** no user-visible speaker LIVE meter is created

#### Scenario: TE40 initial seed and true LIVE share one extractor

- **GIVEN** equivalent TE40 one-shot and true LIVE current-audio payloads contain matching valid compatibility, individual, and array evidence
- **WHEN** each path extracts microphone level
- **THEN** each produces the same raw aggregate and normalization result
- **AND** accepted true LIVE takes precedence over the initial seed

#### Scenario: TE20 current contract is unchanged

- **GIVEN** exact current model is `Huawei TE20`
- **WHEN** it obtains initial or LIVE microphone evidence
- **THEN** its existing `MicValueIndex`-only source and extraction contract remains unchanged
- **AND** TE40 individual/array fields are not promoted into TE20 evidence

### Requirement: TE40 static status publishes canonical room evidence without additional I/O

The existing TE40 initial diagnostic snapshot SHALL publish canonical `microphone_status` from rich `mic_connection_status`, canonical `camera_status` from rich `camera_connection_status`, and canonical `uptime` from the already-read `runDay`/`runHour`/`runMin` presentation value when present. These fields remain distinct from microphone mute and require no additional request or polling.

Present numeric `mic1Value` is the authoritative configured-primary-gain source for `mic_volume`. Historical `micValue` may be used only as a compatibility fallback when `mic1Value` is absent; it SHALL not override present MIC1 evidence.

#### Scenario: TE40 initial snapshot preserves rich state and MIC1 gain

- **GIVEN** the existing initial TE40 diagnostic result contains rich microphone/camera connection evidence, `mic1Value = 18`, and formatted uptime `12 дней 4 часов 37 минут`
- **WHEN** exact parser normalization completes
- **THEN** canonical microphone status, camera status, uptime, and configured microphone volume `18` are available to room presentation
- **AND** no extra status request or uptime polling starts

### Requirement: TE40 MIC1 gain and mute evidence are independent read authorities

For exact `Huawei TE40`, static audio normalization SHALL preserve numeric microphone configuration evidence independently from mute evidence.

When the approved TE40 audio-status parser receives a present finite numeric `mic1Value` in wire domain `0..21`, the accepted room snapshot SHALL publish canonical numeric `microphone_volume` from that MIC1 value. Historical `micValue` MAY be a compatibility fallback only when `mic1Value` is absent; present `mic1Value` SHALL NOT be overridden by `micValue`. When authoritative `MicSwitch` or equivalent approved mute evidence is present, the same snapshot SHALL independently publish canonical `microphone_muted`.

For presentation and typed gain intent, TE40 SHALL use `gain_db = microphone_volume - 12`. Thus wire value `21` is `+9 dB`, `18` is `+6 dB`, and `0` is `-12 dB`.

A numeric value, including `0`, SHALL NOT be interpreted as mute evidence. Mute state SHALL NOT overwrite numeric gain evidence, and numeric gain evidence SHALL NOT overwrite mute state.

#### Scenario: TE40 static audio contains MIC1 gain and unmuted state

- **GIVEN** TE40 audio status contains numeric `mic1Value = 18`
- **AND** independent authoritative mute evidence says unmuted
- **WHEN** the room snapshot is accepted
- **THEN** `microphone_volume` is numeric `18`
- **AND** the model-specific display value is `+6 dB`
- **AND** `microphone_muted` is `false`
- **AND** neither value is derived from the other

#### Scenario: TE40 MIC1 zero is not mute authority

- **GIVEN** TE40 audio status contains numeric `mic1Value = 0`
- **AND** independent authoritative mute evidence says unmuted
- **WHEN** the room snapshot is accepted
- **THEN** `microphone_volume` remains numeric `0`
- **AND** its configured gain meaning is `-12 dB`
- **AND** `microphone_muted` remains `false`
- **AND** the application does not fabricate a muted state from the numeric value

#### Scenario: Present MIC1 gain wins over historical compatibility field

- **GIVEN** TE40 audio status contains `mic1Value = 18` and `micValue = 12`
- **WHEN** the room snapshot is accepted
- **THEN** `microphone_volume` remains numeric `18`
- **AND** the model-specific display value is `+6 dB`

#### Scenario: Historical micValue is fallback only when MIC1 is absent

- **GIVEN** TE40 audio status has no `mic1Value` and contains numeric `micValue = 18`
- **WHEN** the room snapshot is accepted
- **THEN** compatibility fallback may publish numeric `microphone_volume = 18`

### Requirement: TE40 microphone-gain mutation uses fresh full-state save and reconciliation

For exact `Huawei TE40`, room `microphone_adjust` SHALL control primary `MIC1` configured input gain only. Each operator `-` / `+` intent changes configured gain by exactly `1 dB`, clamped to `-12 dB .. +9 dB`, equivalent to wire target `0..21` step `1`.

The state-changing transport boundary is:

```text
POST action.cgi?ActionID=WEB_SaveAudioMicCtrlParams
```

A previously accepted room snapshot SHALL NOT be used as full-state save authority.

After the exact MUTATION owns the serialized room interaction lane and prior LIVE has retired through bounded cleanup, the mutation SHALL first perform a **fresh full TE40 audio-control read** through `WEB_InitAudioCtrlParamsAPI` using the approved exact-row/session context. An already-approved equivalent read MAY be used only if it returns the same complete mutation-required state.

The fresh mutation-local pre-write state SHALL include all non-secret save-state fields required by the native full-state payload:

```text
micall
mic1 .. mic18
mic1Value .. mic18Value
```

If that fresh state is missing, malformed, stale, not current for the exact row/generation, or lacks any required field, the save command SHALL NOT be submitted. This is a definite pre-submit failure: it SHALL NOT set `unconfirmed_after_command` or stale-due-command merely because the fresh read failed. Existing typed auth/session/connection failure rules still apply independently.

The outgoing save payload SHALL be constructed exclusively from that fresh pre-write state plus current required secret session/CSRF material. For a MIC1 gain intent, only target `mic1Value` may differ from the fresh baseline. Non-target `micall`, `micN`, and `micNValue` fields SHALL NOT come from older cache, GUI state, guessed defaults, zeros, or another model.

The mapping is:

```text
wire mic1Value = requested gain_db + 12
requested gain_db = wire mic1Value - 12
```

A successful response such as `{"success":1,"data":""}` is acknowledgement only.

After one accepted submit, reconciliation SHALL perform a fresh full audio-control read from the same approved authority. Final success requires all of:

```text
current exact row / room generation / operation currentness still matches
MIC1 target equals requested wire value
all preserved non-target micall / micN / micNValue fields equal the fresh pre-write baseline
```

The approved canonical `microphone_volume` projection MAY confirm the MIC1 target, but target confirmation does not substitute for collateral-state comparison. If the post-write read cannot expose sufficient full state to compare the preserved fields, success SHALL NOT be declared.

Missing/malformed/mismatched/stale readback, collateral mismatch, ambiguous send outcome, or cancellation after possible send SHALL follow the root blocked/unconfirmed mutation contract; no blind replay is permitted.

Microphone mute remains a separate desired-state operation and SHALL NOT change as a side effect of gain adjustment.

#### Scenario: TE40 gain plus uses a fresh full-state baseline

- **GIVEN** exact TE40 currently has accepted room `microphone_volume = 18`
- **WHEN** the operator confirms one microphone gain `+`
- **THEN** MUTATION first retires LIVE and obtains fresh full audio-control state
- **AND** the typed target is wire `mic1Value = 19`
- **AND** the outgoing full-state save is built only from that fresh baseline
- **AND** only target `mic1Value` differs from the fresh baseline

#### Scenario: TE40 fresh pre-write state is unavailable

- **GIVEN** a TE40 gain mutation owns the lane but fresh full audio-control state cannot be obtained completely
- **WHEN** mutation preparation evaluates the save
- **THEN** `WEB_SaveAudioMicCtrlParams` is not submitted
- **AND** no command ambiguity is created solely by that pre-submit failure
- **AND** bounded cleanup releases the lane subject to independent typed session/connection failure rules

#### Scenario: TE40 gain acknowledgement is not final authority

- **GIVEN** `WEB_SaveAudioMicCtrlParams` returns a successful acknowledgement
- **WHEN** mandatory post-write full-state read is missing, malformed, stale, or target MIC1 does not equal the requested target
- **THEN** requested gain is not published as confirmed
- **AND** root blocked/unconfirmed mutation safety applies
- **AND** the command is not blindly repeated

#### Scenario: TE40 collateral microphone state changed

- **GIVEN** fresh pre-write state records non-target microphone fields
- **AND** one gain save may have been delivered
- **WHEN** post-write full-state reconciliation shows any preserved non-target `micall`, `micN`, or `micNValue` field differs from that fresh baseline
- **THEN** the MIC1 mutation is not declared fully confirmed
- **AND** the row enters root blocked/unconfirmed state
- **AND** the application does not silently accept or replay the command

#### Scenario: TE40 gain minus at lower bound is local no-op

- **GIVEN** exact TE40 has current accepted `microphone_volume = 0`, equivalent to `-12 dB`
- **WHEN** the operator requests one microphone gain `-`
- **THEN** no below-range target is constructed
- **AND** no mutation/session/device I/O is started solely for that no-op
- **AND** mute state remains unchanged

### Requirement: TE40 camera normalization accepts zero-to-many camera records

For exact `Huawei TE40`, `WEB_GetLocalCameraList.itemList` or its approved equivalent SHALL be treated as a zero-to-many collection. The parser SHALL NOT require at least two entries before processing camera evidence.

Each present entry SHALL be interpreted independently. An active camera MAY use the existing approved port/type lookup to resolve model evidence. A valid single returned camera SHALL publish known camera status/model evidence when available and SHALL NOT become `Нет данных` solely because a second list entry is absent.

#### Scenario: TE40 returns exactly one camera record

- **GIVEN** TE40 camera-list data contains exactly one valid camera entry
- **WHEN** exact-model camera normalization runs
- **THEN** that entry is processed
- **AND** available camera state/model evidence is published
- **AND** the parser does not require `len(itemList) >= 2`

### Requirement: CloudLink Box 310 post-cycle microphone LIVE is deferred and unavailable in this change

Current authorized Bar 310 evidence belongs to Bar and SHALL NOT be used as a Box parser contract. Earlier Box hardware evidence is insufficient to define a complete LIVE parser. Therefore this change explicitly removes Box microphone LIVE from its implementation/acceptance scope rather than asking implementation to choose envelope, roles, aggregation, or normalization.

The unified exact-model registration for `CloudLink Box 310` SHALL advertise no post-cycle LIVE binding. Room interaction SHALL perform zero Box microphone LIVE polling, including zero `WEB_GetCurrentAudioParam` requests admitted as LIVE. Exact Box identity and all approved non-LIVE capabilities remain unchanged.

A future reviewed Box LIVE restoration change is required before this capability may become supported. That future change must establish response envelope/container, microphone record selection/device-role semantics, numeric validity, aggregation, normalization, unavailable/error semantics, lifecycle currentness, and exact Box identity.

Earlier `{deviceId, curVolume}` observations remain discovery evidence only. No `max(all curVolume)` rule is approved here. The current Bar fixed-field `mic*ValueIndex` schema is not Box evidence.

#### Scenario: Box registration has no LIVE binding

- **GIVEN** exact model is `CloudLink Box 310`
- **WHEN** unified room capabilities are composed
- **THEN** no post-cycle LIVE binding is advertised
- **AND** shared `CloudLinkBar310Handler` type does not promote Box LIVE
- **AND** no Box room LIVE request is admitted

#### Scenario: Box non-LIVE interaction remains supported where separately approved

- **GIVEN** exact model is `CloudLink Box 310`
- **WHEN** diagnostics, speaker control, call-log preview/detail, or Local Refresh use their existing approved capabilities
- **THEN** those operations remain available under their own exact-row lifecycle contracts
- **AND** absence of Box LIVE does not relabel the model as Bar 310

#### Scenario: Future Box LIVE needs a new reviewed contract

- **WHEN** a later change proposes to re-enable Box microphone LIVE
- **THEN** it cannot infer the parser from Bar fields or the earlier pair shape alone
- **AND** it must supply the complete transport-edge to normalized-meter contract before capability is advertised
