# Design: room-diagnostic-ui-presentation-stability

## Context

Current room presentation is rebuilt repeatedly from one application-owned `RoomDiagnosticSession`. `RoomDiagnosticTreeWidget.render(session)` currently rebuilds the network and equipment trees, while `MainWindow` calls that render path on current background session updates. The application/controller layer already rejects stale/superseded sessions and keeps network work off the Qt GUI thread.

Current ownership is therefore intentionally split:

```text
application/session authority
    RoomDiagnosticSessionIdentity
    room metadata / room_vip
    canonical records and accepted diagnostic evidence
    expanded_record_id
    exact current row/context for network operations
    interaction locks/currentness

room presentation-local state
    viewport/scroll position
    network disclosure
    existing Audio selected-channel visual state
    Audio hover/popup presentation state
```

`RoomDiagnosticSessionIdentity` is the existing application-produced presentation-context key. It contains the inventory snapshot, room generation, source identity/IP, and room ID. This change consumes that immutable identity; it does not create a new room/session identity or make the widget authoritative for it.

The current root `diagnostic-ui-presentation` spec already requires `room_vip == true` to have a clear badge/indicator and false/null not to render as VIP true. Current source already projects `session.room_vip` into a `roomVipBadge`; MIH-14 is therefore a presentation regression against an existing root contract, not a reason to add a second VIP domain field.

The current root network contract intentionally renders compact switch summaries, but MIH-18 now requires real tree disclosure. This change minimally revises that presentation contract: known-switch summary rows become disclosure parents for the same canonical attached room records already used to compute port/count summaries. No new switch/device topology source is introduced.

The current root Audio contract permits local controls for a `hovered channel or a selected/pinned channel`. MIH-15 explicitly changes that product behavior: channel selection remains a separate local visual feature, but it no longer pins popup visibility.

## Goals

1. Give same-room/session background re-render an explicit, safe presentation-state snapshot/restore boundary.
2. Preserve equipment viewport/scroll position across same-identity background re-render without persisting it as canonical state.
3. Make network disclosure truthful, user-controlled, and stable across same-identity background re-render.
4. Make Audio popup lifetime follow actual hover plus the current expanded Audio row, not selection or stale disposable widgets.
5. Make collapse/current-row/session replacement synchronously revoke obsolete popup context.
6. Restore the approved visible VIP indication solely from canonical current room metadata.
7. Preserve all existing application/network/credential/currentness/threading authority.

## Non-goals

- A general-purpose persistent UI-preferences subsystem.
- Persisting state across application restart.
- Persisting room presentation state across a new `RoomDiagnosticSessionIdentity`.
- Replacing `expanded_record_id` with a presentation-owned current row.
- Changing automatic diagnostic acquisition or any device-family protocol.
- Enabling Audio DSP gain/mute mutation.
- Reworking Audio selection semantics beyond decoupling selection from popup visibility.
- Inventing unattached switches or topology evidence absent from canonical room records.
- Reworking the approved Audio/Matrix/Codec/PDU dashboard geometry.

## Decisions

### 1. `RoomDiagnosticSessionIdentity` is the room presentation-context boundary

The room widget SHALL keep at most one active presentation context keyed by the exact current `session.identity`.

For an incoming render:

```text
incoming identity == active presentation identity
    -> same-context render
    -> snapshot safe local presentation state
    -> rebuild from authoritative session data
    -> restore/revalidate only safe state

incoming identity != active presentation identity
    -> context replacement
    -> revoke popup/transient state
    -> discard prior scroll/disclosure state
    -> rebuild with defaults from the new authoritative session
```

`clear_presentation()` is an unconditional revocation boundary equivalent to no active presentation context.

No local state snapshot may contain credentials, handler/session objects, workers/controllers, `RoomInteractionContext`, operation tokens used as network authority, secrets, accepted device data, or mutable `RoomDiagnosticSession` ownership.

### 2. State has three lifetimes; there is no single generic “persist everything” bucket

#### A. Authoritative application/session state — never duplicated as presentation authority

Examples:

- `session.identity`;
- `session.expanded_record_id`;
- `session.room_vip`;
- canonical room/network records;
- accepted device snapshots and interaction locks.

Render always consumes these from the current session.

#### B. Context-scoped room presentation state — survives same-identity re-render

The widget owns safe state such as:

```text
RoomPresentationState
    identity: RoomDiagnosticSessionIdentity
    equipment_viewport: visual-only anchor/fallback scroll position
    network_expanded_switch_keys: set of safe presentation switch keys
```

The existing Audio channel selection may remain implemented separately, but it follows the same already-approved current-room identity scoping and channel-pruning rules. It SHALL NOT be used to drive popup visibility.

`network_expanded_switch_keys` is presentation-only. For a canonical known switch it may use the exact canonical `switch_ip_address` only as a visual row key. A record-bound unknown-switch row has no disclosure child group and therefore no persisted expanded key. The key SHALL NOT be used for routing, handler acquisition, device access, or topology inference.

#### C. Transient Audio hover/popup state — current-expanded-row scoped

A popup target is safe presentation identity only:

```text
AudioPopupTarget
    room_identity
    record_id
    section
    oid
```

Runtime hover state may additionally track whether the pointer is currently inside the source scale or the one popup, plus a monotonic presentation-only hide/rebind epoch. Disposable QWidget pointers may be used only during the current render epoch and are never restored across rebuild.

This state is invalidated not only by room/session identity replacement, but also by current expanded-row replacement/collapse or disappearance of the exact channel target.

### 3. Equipment scroll restoration preserves the viewport, not canonical state

Before a same-context destructive rebuild, the presentation SHALL capture the equipment viewport. Preferred representation is a visual anchor:

```text
first visible canonical top-level record_id + pixel offset from viewport top
```

with the current vertical scrollbar value as a fallback.

After rebuild/layout, if the same identity is still current and the anchor record still exists, the widget restores the viewport relative to that record and clamps to the current scrollbar range. If the anchor disappeared during same-context evidence evolution, it falls back to the captured scrollbar value, also clamped. A new identity or `clear_presentation()` uses the normal default position and never imports the old anchor.

Using `record_id` here is only a visual anchor. It does not select the row, expand it, create a `RoomInteractionContext`, or admit network work.

Programmatic restoration SHALL NOT emit an interaction intent or mutate acquisition order. Background refresh remains data authority only; it does not choose the operator's scroll position.

### 4. Network disclosure uses the current summary rows as parents and canonical records as visual children

Known-switch summary rows retain the current three summary columns and deterministic grouping/port/count semantics. Each known-switch row SHALL additionally have one visual child per current canonical room-equipment record attached to that exact switch, ordered by canonical `record_id`.

A child is a presentation of existing evidence only. Minimum child semantics are:

```text
column 0 -> safe current equipment identity (diagnostic model / established display label; never invented switch identity)
column 1 -> that record's exact canonical switch_port or `Нет данных`
column 2 -> empty/neutral child value; the parent remains the device-count summary owner
```

The implementation MAY include an already-established safe device/IP cue in column 0 if it does not create a new authority or widen this change into a redesign.

Rows with unknown switch IP but known port remain record-bound top-level `Коммутатор не определён` rows as today. They SHALL NOT be grouped into a fictitious switch merely to create disclosure children.

User expansion/collapse changes only presentation-local `network_expanded_switch_keys`. On same-identity render, the newly rebuilt current switch rows restore those booleans after canonical data is repopulated. A background refresh SHALL NOT itself add or remove an expanded key except when the corresponding current canonical switch row no longer exists; identity replacement resets to the default collapsed state.

Disclosure restoration SHALL block/suppress any accidental user-action handling and SHALL perform zero device I/O.

### 5. One room-level Audio popup coordinator owns hover continuity

The current per-channel popup lifetime is too closely tied to disposable channel widgets. The implementation SHALL move lifetime coordination above disposable meter channels to the room presentation boundary (or an equivalent presentation-only coordinator owned by it).

There is exactly one active Audio local-controls popup target in the room presentation.

Channel widgets provide only presentation hover events/registration for safe channel identity; they do not become application/device target authority. The coordinator owns the single-shot hide bridge used to move from a narrow source scale into the popup.

State machine:

```text
ENTER current Audio scale A
    validate current session identity + expanded_record_id + row family + channel
    active_target = A
    show/reposition popup for A
    cancel pending hide

LEAVE scale A
    if pointer is not in popup -> schedule short presentation-only hide

ENTER popup for active_target
    cancel pending hide

LEAVE popup
    if pointer is not on active source scale -> schedule hide

ENTER current Audio scale B while A is active
    active_target = B immediately
    rebind label/position to B
    invalidate A's pending hide epoch

neither active source scale nor popup owns hover
    hide and clear active target
```

Channel selection is orthogonal: selected visual emphasis MAY persist under its existing root requirement, but selected state SHALL NOT keep the popup open after both hover surfaces are left.

### 6. Popup validity is rechecked against application-owned expanded-row evidence

A popup may be visible only if all are true:

- the popup target's `room_identity` equals the current `session.identity`;
- current `session.expanded_record_id` equals popup `record_id`;
- that current row still resolves to the Audio DSP presentation family;
- the exact `section + oid` exists in the current accepted presentation evidence;
- current hover ownership is still valid.

Collapse of the active Audio row, expansion of another row, session identity replacement, `clear_presentation()`, or channel disappearance SHALL synchronously revoke/hide the popup and advance its presentation epoch before disposable widgets are destroyed.

A delayed hide/reposition/rebind callback captures the presentation epoch and target identity. If either is no longer current, it is a no-op. Therefore an old timer cannot close a newly switched popup and cannot resurrect a popup after collapse/context replacement.

This check consumes `expanded_record_id` as evidence. It does not replace or compete with `room-device-interaction-lifecycle` exact-row authority.

### 7. Same-context rebuild may preserve popup continuity only by re-resolution, never by stale widget retention

A background update can currently destroy/recreate expanded Audio widgets. For a same-identity render, the coordinator MAY carry only the safe `AudioPopupTarget` plus hover ownership facts across the render transaction.

After rebuild it SHALL resolve the replacement scale by exact `record_id + section + oid` and re-check the current expanded row. Popup continuity is allowed only when current pointer hit-testing confirms the pointer remains over either:

- the replacement source scale for the same target; or
- the still-current room-owned popup.

Otherwise the popup closes. No old source QWidget pointer, old child presentation, or stale session object is retained to justify visibility.

This gives MIH-15 continuity during ordinary same-context refresh without allowing stale MIH-16 popup resurrection.

### 8. VIP remains a direct canonical projection

No new VIP state is stored in `RoomPresentationState`.

On every render:

```text
session.room_vip is True
    -> show the approved clear non-color VIP indicator/badge/icon with textual/accessibility meaning

session.room_vip is False or None
    -> do not present VIP true
```

Implementation may correct layout/icon styling/visibility so the existing indicator is plainly visible, but SHALL NOT infer VIP from room name, local UI history, device data, or another metadata field.

### 9. Restoration is side-effect-free and never enters the network lane

The following remain pure presentation events:

- scroll capture/restore;
- network disclosure capture/restore;
- Audio popup show/hide/reposition/rebind;
- VIP rendering;
- background presentation rebuild itself.

They SHALL emit no Local Refresh, auxiliary read, live, mutation, reconciliation, handler/session, credential, retry, worker, or protocol request.

If disabled Audio controls later become authorized by another approved change, any user intent from those controls must still be converted/revalidated by application composition against the exact current `RoomInteractionContext`. The popup's `AudioPopupTarget` remains insufficient authority by itself.

## Risks / Trade-offs

### Risk: UI-state cache becomes a second room/session authority

Mitigation: the cache is keyed by application-produced immutable identity, contains only safe visual state, and is discarded on identity replacement. Authoritative data is always rebuilt from the current session.

### Risk: network disclosure reintroduces topology inference

Mitigation: parent grouping and child membership use only the same canonical `switch_ip_address`, `switch_port`, and room records already used by the approved summary. Unknown-switch records remain ungrouped. Children are explicitly non-authoritative.

### Risk: popup survives collapse or a row switch

Mitigation: expanded-row equality is a mandatory visibility invariant and collapse/switch advances the popup epoch synchronously before old widgets can outlive their context.

### Risk: popup disappears on every background render

Mitigation: popup ownership is lifted above disposable channel widgets and same-context continuity is re-established only by safe target re-resolution plus current pointer hit-testing.

### Risk: old popup timer hides a newly selected hover target

Mitigation: every delayed callback is fenced by a presentation-only epoch + exact target identity.

### Risk: scroll restoration changes selection/interaction

Mitigation: viewport anchor restoration is visual-only, signal-suppressed, and cannot expand/select rows or create network intents.

## Validation Strategy

Implementation validation SHALL include:

- VIP true/false/null regression proving the visible indicator uses only current `session.room_vip`;
- equipment scroll/viewport preservation through repeated same-identity `render()` and background-style updates;
- identity replacement and `clear_presentation()` tests proving old scroll state is not restored;
- network known-switch parent disclosure with deterministic canonical children and unchanged summary ports/count;
- unknown-switch record rows staying ungrouped/non-disclosable;
- user network expand/collapse persistence through same-identity re-render and reset on identity replacement;
- proof that restoration does not emit room interaction/network signals;
- Audio scale -> popup hover bridge, popup -> outside close, A -> B target switching, and selected-channel-not-pinning tests;
- Audio collapse, another-row expansion, identity replacement, target disappearance, and stale timer epoch tests;
- same-identity Audio re-render while pointer remains on valid source/popup and re-render after pointer leaves;
- regression that Audio `-`, `+`, and `Mute` remain disabled and emit no mutation/network intent;
- regression that existing exact current row/application interaction ownership is unchanged;
- GUI-thread/network-owner regressions where currently applicable;
- focused GUI tests and full offline suite during implementation;
- repository-local `.\openspec.cmd validate room-diagnostic-ui-presentation-stability --strict` and `.\openspec.cmd validate --all --strict` during implementation/validation according to `RULES.md`;
- `git diff --check` and `git diff --cached --check` before publication.

## Open Questions

None at product-contract level. Concrete Qt helper/class placement may vary during implementation, but ownership, identity keys, invalidation conditions, disclosure content, and no-I/O constraints above are normative.
