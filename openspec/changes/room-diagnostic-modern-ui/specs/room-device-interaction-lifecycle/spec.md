## MODIFIED Requirements

### Requirement: Top room controls and context changes supersede interaction safely

Top full Refresh SHALL remain the from-scratch room recovery action. When allowed, it SHALL invalidate the old room interaction generation, stop/cancel read-only activity, clear room tree/header/cache presentation, resolve the current target-search context against current inventory/fallback rules, and execute the resulting room cycle again as a first connection. It SHALL NOT preserve a prior expanded secondary row or reuse old per-record cache as current state.

For an unchanged room-name query that still has multiple matches, top full Refresh MAY reuse the currently selected exact `room_id` only when that selection is still current for the same query revision, current inventory snapshot/candidate set, and current room-search result. Otherwise it SHALL require a new explicit selection and SHALL perform no device I/O from the stale candidate.

During auxiliary read, top full Refresh SHALL remain available and SHALL act as the global supersession action after bounded cleanup/abandonment. During Local Refresh, target-search editing, Password, top full Refresh, accordion switching/collapse, and incompatible network/state-changing actions SHALL remain blocked until its terminal cleanup/release boundary. During a confirmed state-changing command through its mandatory reconciliation terminal boundary, top full Refresh, target-search editing, Password, and incompatible accordion/network actions SHALL remain blocked.

Editing the target-search text in post-cycle idle/live state SHALL immediately invalidate current room/live/pending-start authority, invalidate any room-name selection, and clear room presentation. Editing alone SHALL start no network I/O. Returning the field text to the previous value SHALL NOT resurrect the prior generation or prior stale selection.

`Пароль` remains an IP-target/model-wide configuration action rather than a room-name or secondary-row credential editor. It MAY be exposed through an application `Действия` menu. Cancel and Save-without-effective-change SHALL preserve the current room/live state. A real effective credential-chain change SHALL invalidate exact-row sessions/live, clear current room/tree/cache state, and require a new diagnostic start.

Theme switching is presentation-only and SHALL NOT be treated as a target/context change: it SHALL NOT invalidate room generations, stop live, clear caches, or start device I/O.

#### Scenario: Auxiliary read is superseded by top Refresh

- **GIVEN** an auxiliary read is active
- **WHEN** top full Refresh is requested
- **THEN** the auxiliary context loses authority and is cancelled/retired
- **AND** the new full room cycle starts only under the new room generation after current target resolution
- **AND** late auxiliary callbacks cannot update it

#### Scenario: Target search is edited after room completion

- **WHEN** the operator changes the target-search text
- **THEN** the current room interaction/tree/cache authority and any room-name selection are invalidated immediately
- **AND** no replacement device I/O begins until Enter/top Refresh creates a new current context

#### Scenario: Old room selection cannot survive query edit

- **GIVEN** a multi-result room-name query has an exact selected room ID
- **WHEN** the search field is edited and later returned to the old visible text
- **THEN** the old selected room does not regain authority automatically
- **AND** current room resolution/selection is required again

#### Scenario: Theme toggle does not supersede room interaction

- **GIVEN** a room is connected and an allowed live lifecycle is active
- **WHEN** the operator switches between dark and light themes
- **THEN** current exact-row authority and live lifecycle remain unchanged
- **AND** no device network I/O is started by theme switching
