# device-diagnostics-and-control Delta

## MODIFIED Requirements

### Requirement: Limited device control
The GUI SHALL expose as network-capable device controls only operations implemented by the selected device path: codec presentation, audio/microphone operations, supported SIP server actions, Extron routing to output 1, Aten outlet on/off/reboot actions, Aten bulk on/off actions, Extron IPL T PCS4i outlet on/off actions, and Extron IPL T PCS4i bulk on/off actions. Unsupported device actions SHALL not be reported as successful.

A reviewed fixed common dashboard MAY retain a visible local-only affordance for an unsupported codec operation only when the unified exact-model registration explicitly marks that network capability unsupported and the click is resolved locally before room interaction admission. Such an affordance SHALL NOT be represented as an available/supported device capability, SHALL NOT invalidate LIVE, acquire a handler/session, select credentials, create a mutation generation or perform device network I/O, and SHALL only produce the approved non-secret informational result. This local-only presentation exception does not authorize arbitrary unsupported controls on other surfaces.

PCS4i REBOOT SHALL remain unsupported and SHALL NOT be exposed to the operator as an individual or bulk operation.

#### Scenario: Extron routing action
- **WHEN** an operator selects an actionable Extron input/output-1 cell with a connected handler
- **THEN** the handler is asked to route that input to output 1 and the screen schedules a status refresh

#### Scenario: Aten outlet action
- **WHEN** an operator confirms an `on`, `off`, or `reboot` action for an Aten outlet
- **THEN** the application executes the matching handler action through the background PDU command path, reports its outcome, and refreshes after success

#### Scenario: PCS4i outlet action
- **WHEN** an operator confirms an `on` or `off` action for a PCS4i outlet from 1 through 4
- **THEN** the application executes the matching PCS4i handler action through the background PDU command path and reports its outcome

#### Scenario: PCS4i reboot is not available
- **GIVEN** selected device is Extron IPL T PCS4i
- **WHEN** `PDUScreen` renders supported outlet controls
- **THEN** ON is available
- **AND** OFF is available
- **AND** REBOOT is not available to the operator

#### Scenario: Unsupported SIP update
- **WHEN** a codec handler does not implement SIP server update
- **THEN** the operation reports an unsupported or failed outcome rather than claiming the setting changed

#### Scenario: Fixed codec dashboard shows unsupported affordance
- **GIVEN** the fixed room codec dashboard contains a visual control whose exact-model network capability is explicitly unsupported
- **WHEN** the operator activates that affordance while the common room lock matrix otherwise permits input
- **THEN** the application reports locally that the operation is unsupported
- **AND** the operation is not represented as a supported device capability
- **AND** no handler/session/credential/network interaction begins

#### Scenario: Bulk action uses supported individual capability
- **GIVEN** the selected PDU model supports individual ON and OFF operations
- **WHEN** the shared PDU screen renders bulk controls
- **THEN** bulk ON is available only from the ON capability
- **AND** bulk OFF is available only from the OFF capability
- **AND** no PCS4i REBOOT or bulk REBOOT control is exposed

#### Scenario: Unsupported bulk action is rejected
- **GIVEN** a PDU model does not support the requested individual operation
- **WHEN** a matching bulk operation is submitted programmatically
- **THEN** application dispatch rejects it before handler acquisition
- **AND** no PDU network I/O is started

### Requirement: Model-specific interactive codec session paths

The shared interactive controller SHALL preserve the supported transports, session artifacts, and operation boundaries of Huawei TE20, Huawei TE40, CloudLink Bar 310, CloudLink Box 310, and Polycom RPG 310. A model SHALL use only its supported functions, and functions on a separate worker path SHALL remain separate unless explicitly listed.

CloudLink Bar 310 and CloudLink Box 310 SHALL continue to use the same reviewed `CloudLinkBar310Handler` implementation while retaining exact assigned application model in operation context. Shared protocol capability SHALL NOT authorize Bar/Box aliasing, credential sharing, successful-index/profile sharing, or model switching during recovery.

For the CloudLink 310 family, one application-selected credential SHALL bind one handler generation for the exact model/IP/credential context. That generation MAY own:

```text
modern read subcontext
legacy compatibility/control subcontext
```

The modern read subcontext SHALL be established through `POST /v1/login/session` followed by `POST /v1/login/account`, retain cookies/token in memory only, and service only operations explicitly approved for the modern context. Modern action.cgi compatibility in this change is limited to the exact live-verified read-only requests `WEB_GetVersionInfoAPI`, `WEB_GetSystemMacAddrAPI`, and `WEB_GetMailboxDataAPI`.

Existing unverified read-only action.cgi operations, including audio, line/SIP, presentation, and camera reads, SHALL remain on the existing legacy compatibility path unless a later approved change proves their modern compatibility. The Box-specific live-meter read `WEB_GetCurrentAudioParam` is an explicit member of that legacy compatibility path in this change and is not added to the modern action.cgi allowlist. Existing supported state-changing action.cgi operations SHALL remain on the legacy compatibility/control path and retain their existing mutation-safety rules.

CloudLink microphone-gain network capability is an explicit exception: for exact Bar 310 and Box 310 it SHALL remain unavailable/disabled because authoritative target selection and reconciliation are not established. The application/controller SHALL reject that network operation before device I/O. The fixed common room codec dashboard MAY retain its `−`/`+` microphone visual affordances, but for Bar/Box those affordances SHALL resolve locally as unsupported before room interaction admission and SHALL NOT be represented as a supported network capability. Neither local affordance changes nor presentation state authorize gain I/O.

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

#### Scenario: Unverified action.cgi read remains legacy-compatible
- **WHEN** CloudLink refresh or interactive work needs existing audio, line/SIP, presentation, camera, or another read-only action.cgi operation not live-verified on modern auth
- **THEN** this change does not migrate that operation to the modern context
- **AND** its existing legacy compatibility path remains authoritative until separately approved

#### Scenario: Box live meter remains legacy-compatible
- **GIVEN** exact model is `CloudLink Box 310`
- **WHEN** live metering executes `WEB_GetCurrentAudioParam`
- **THEN** the request uses the existing legacy compatibility subcontext
- **AND** this change does not require modern `X-Access-Token` or modern body-token routing for that endpoint

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

#### Scenario: Polycom interactive controls
- **WHEN** Polycom performs volume, mute, or presentation work
- **THEN** its serialized shared handler uses HTTPS:443 login and the same credential for its lazy SSH:22 control session
- **AND** failure of either sub-session follows bounded interactive recovery

#### Scenario: Polycom call log remains separate
- **WHEN** operator loads Polycom call log
- **THEN** the existing short-lived Polycom call-log worker remains owner
- **AND** it is not routed through Huawei/shared call-log session path

## ADDED Requirements

### Requirement: Room codec dashboard data uses one typed model-neutral presentation projection

For every current exact codec registration, the room diagnostic/application boundary SHALL expose a model-neutral codec presentation projection sufficient for the fixed dashboard slots without making raw model-specific parser text or standalone Qt widgets into shared presentation authority.

The projection SHALL distinguish usable current evidence from absence/unknown and SHALL provide safe values where current approved diagnostic evidence exists for:

```text
model
mac_address
serial_number
platform
software_version
microphone
camera
call_status
presentation_status
sip_h323_registration
microphone_level
microphone_volume
microphone_mute_state
speaker_volume
speaker_mute_state
```

`microphone_volume` and `speaker_volume` SHALL be optional comparable numeric values. `microphone_mute_state` and `speaker_mute_state` SHALL be typed states equivalent to `MUTED | UNMUTED | UNKNOWN`; they SHALL NOT share one untagged scalar slot with numeric volume. An exact-model adapter MAY derive speaker mute state from numeric zero/non-zero only where that model's approved contract defines zero as muted. Shared Qt code SHALL NOT infer mute from display strings.

A model MAY legitimately have no current evidence for one or more slots. Absence SHALL remain absence and presentation SHALL render `Нет данных`; this change SHALL NOT add protocol reads solely to make every slot non-empty.

Existing typed `CallActivity` remains the model-neutral call-activity authority where applicable. Shared room presentation SHALL prefer typed/structured normalization where one exists and SHALL NOT derive shared semantic status by substring matching localized/model-specific call strings.

#### Scenario: Current model lacks platform evidence
- **GIVEN** the exact codec diagnostic snapshot has no current approved platform evidence
- **WHEN** model-neutral codec presentation is projected
- **THEN** `platform` remains unavailable
- **AND** no parser default, model string or standalone UI label is substituted as device evidence

#### Scenario: Numeric volume and mute state remain distinct
- **GIVEN** current accepted codec evidence proves a numeric speaker volume and a mute state
- **WHEN** model-neutral projection is built
- **THEN** numeric volume remains numeric authority for relative target construction
- **AND** mute state remains typed desired-state/readback authority
- **AND** neither value overwrites or stringifies the other into one ambiguous slot

### Requirement: Current codec room-control support matrix is a fixed acceptance oracle

The unified exact-model registration SHALL remain the sole runtime capability authority. For the current `master` baseline, implementation and tests SHALL nevertheless prove these exact expected capability declarations; this table is an OpenSpec/test oracle and SHALL NOT become a second runtime registry:

| Exact model | speaker_adjust | speaker_mute | microphone_adjust | microphone_mute | reboot |
| --- | --- | --- | --- | --- | --- |
| `Huawei TE20` | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | UNSUPPORTED |
| `Huawei TE40` | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | UNSUPPORTED |
| `CloudLink Bar 310` | SUPPORTED | SUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| `CloudLink Box 310` | SUPPORTED | SUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| `Polycom RPG 310` | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | UNSUPPORTED |

The matrix reflects current approved source/contracts: all five have proven speaker absolute volume/readback; TE20/TE40/Polycom microphone control is mute-state rather than numeric gain; CloudLink microphone gain remains prohibited and no separate approved room microphone-mute mutation binding is established; no current codec has an approved typed reboot plus reconciliation contract.

Speaker mute support for all five SHALL be implemented only as the approved volume-zero/restore desired-state policy defined below; it does not imply a separate raw speaker-mute wire command.

If current approved source changes before implementation such that this matrix is no longer true, the OpenSpec architecture SHALL be reviewed/updated before implementation silently changes capability applicability.

#### Scenario: Current codec registration matrix is checked
- **WHEN** composition tests inspect the five current exact codec registrations
- **THEN** every operation matches the table above
- **AND** runtime resolution still comes from the unified registry rather than this test-oracle table

### Requirement: Codec room-control adapters reuse approved typed operations and explicitly reject unsupported operations

The room codec-control capability SHALL reuse existing approved safe codec operation/readback semantics where available rather than duplicating protocol command grammar in the room GUI. Each exact codec registration SHALL bind an application/core codec-control adapter (or equivalent existing exact-registry-owned binding) that can answer operation support before network acquisition and can construct the typed desired-state/readback operation for supported controls.

Standalone `CodecScreen` demonstrates some existing safe speaker/microphone semantics but is not itself a room capability authority. A room adapter MAY reuse the same underlying application/core operation definitions only when the exact model supports the required method/readback contract and matches the fixed current-baseline support oracle above. A standalone widget branch, handler attribute probe or visually present button SHALL NOT silently promote support.

A model without a proven numeric microphone-adjust contract SHALL declare `microphone_adjust` unsupported rather than reinterpret mute/state as gain. Reboot SHALL remain unsupported for the current five-codec baseline; this change SHALL NOT invent one.

#### Scenario: Microphone has mute but no numeric gain contract
- **GIVEN** exact model is TE20, TE40 or Polycom RPG 310
- **WHEN** its room codec-control capability is composed
- **THEN** `microphone_mute` is supported
- **AND** `microphone_adjust` is unsupported
- **AND** shared GUI code does not reinterpret mute state as a numeric gain range

#### Scenario: CloudLink microphone controls remain network-unsupported
- **GIVEN** exact model is CloudLink Bar 310 or CloudLink Box 310
- **WHEN** its room codec-control capability is composed
- **THEN** `microphone_adjust` and `microphone_mute` are both unsupported for room mutation
- **AND** the fixed visual affordances may still use the local informational path defined by presentation/lifecycle contracts

### Requirement: Codec audio mutation authority separates current numeric value, mute state and restore evidence

A supported room codec audio desired-state operation SHALL use the same exact model/IP credential and transport safety boundaries as existing codec interaction. Before sending, the adapter SHALL validate the requested absolute target against its exact model operation range/state contract. Invalid, missing or contradictory targets SHALL fail before state-changing I/O.

Room-owned speaker restore authority SHALL be scoped to the exact current room generation and record. The application/core layer MAY remember the last accepted current non-zero `speaker_volume` for that exact row as a restore target. Widget-local `last_unmuted_volume`, requested values, ACKs, defaults, minimum values, another row's value, or fabricated `1` SHALL NOT become restore authority.

For a volume-zero speaker mute model:

```text
current accepted speaker_volume > 0 + mute intent
    -> desired absolute target 0
    -> current accepted non-zero value may remain the restore target

current accepted speaker_volume == 0 + unmute intent + proven restore target
    -> desired absolute target = proven restore target

current accepted speaker_volume == 0 + unmute intent + no proven restore target
    -> local unavailable result
    -> zero mutation/network I/O
```

A newly accepted non-zero authoritative speaker value MAY replace the prior restore target for the same current row/generation. Collapse/re-render does not make widget history authoritative; new room generation/context invalidation clears old restore authority.

For TE20/TE40/Polycom microphone mute, the desired target SHALL be typed `MUTED` or `UNMUTED` and reconciliation SHALL compare the typed current microphone mute state. Numeric microphone gain SHALL not be fabricated from that state.

Readback/reconciliation SHALL compare model-neutral normalized current state with the exact desired target. A command return value, ACK, HTTP success, SSH/Telnet prompt, empty error, or user-facing string SHALL NOT by itself confirm final audio state.

For relative-button intent represented as an absolute target, retry/fallback safety SHALL follow the existing relative-as-absolute operation contract: a structured authentication rejection may advance credentials only when the operation is proven not delivered under the applicable mutation-safety gate; after possible delivery, the operation SHALL NOT be blindly repeated with another credential.

#### Scenario: Desired target is outside exact model range
- **WHEN** a codec-control adapter receives an absolute audio target outside its exact approved model range
- **THEN** the operation fails closed before handler/session acquisition or state-changing send
- **AND** authoritative row data is unchanged

#### Scenario: Speaker unmute has no restore evidence
- **GIVEN** current accepted speaker volume is zero
- **AND** the exact row/generation has no accepted non-zero restore target
- **WHEN** the operator requests speaker unmute
- **THEN** no default/minimum/`1` target is invented
- **AND** no room mutation or device I/O starts
- **AND** a safe local unavailable result is shown

#### Scenario: Send appears successful but readback differs
- **WHEN** a supported audio mutation send returns apparent success
- **AND** mandatory readback does not prove the desired normalized state
- **THEN** the operation remains unconfirmed/failed under the room mutation contract
- **AND** the desired value is not written optimistically into authoritative row state

### Requirement: Room call-log preview uses one typed newest-first chronology authority

Automatic inline call-log preview and the detailed call-log window SHALL consume the same application-owned `CallHistorySnapshot` (or an equivalent typed normalized result preserving the same contract) for the exact model. This change SHALL NOT create a second parser/schema solely for the three-row preview.

The normalized result SHALL establish chronology before presentation. Records SHALL already be ordered newest-first using typed comparable `start_at` evidence. A record with no parseable/comparable `start_at` SHALL sort after every record with proven chronology. Ordering among equal timestamps or records lacking chronology SHALL preserve deterministic normalized acceptance/source order; presentation SHALL NOT sort localized `start_display` strings lexicographically and SHALL NOT guess missing timestamps.

The preview SHALL take the first three records of that accepted newest-first normalized result. All five current codec call-log adapters SHALL preserve/use this model-neutral chronology contract.

If acquisition/normalization cannot prove records, the preview result is unavailable/empty rather than fabricated. Safe display timestamp text may remain present for a record whose typed chronology is unavailable, but that text SHALL NOT promote the record ahead of timestamped records or become sorting authority.

#### Scenario: Preview and detailed window receive the same accepted result
- **GIVEN** a current call-log auxiliary acquisition is accepted for an exact codec row
- **WHEN** inline preview and detailed presentation consume it
- **THEN** both derive from the same normalized full result bound to that row/generation
- **AND** the preview does not run a separate model parser or alter record meaning

#### Scenario: Missing timestamp does not become newest
- **GIVEN** accepted normalized call records include records with typed `start_at` and one record with only unparseable/missing chronology
- **WHEN** preview ordering is established
- **THEN** all records with proven timestamps are ordered newest-first ahead of the unknown-chronology record
- **AND** no display-string sort or guessed timestamp is used
