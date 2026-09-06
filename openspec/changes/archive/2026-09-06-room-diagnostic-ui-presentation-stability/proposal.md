# Change: Stabilize room diagnostic presentation lifecycle

## Why

The approved room diagnostics shell and device-family dashboards are already merged, but five follow-up GUI defects show that room presentation state is not consistently scoped across `render()` / background refresh boundaries:

- current canonical VIP metadata does not produce the approved visible VIP indication reliably;
- Audio DSP local gain/mute placeholder popup lifetime is coupled to channel selection/disposable widget lifetime instead of the current hover + expanded-row context;
- the equipment tree loses the operator's scroll position when the same authoritative room/session is re-rendered;
- the network tree does not provide truthful user disclosure and loses user disclosure state across background re-render;
- collapse/current-row replacement can leave an obsolete Audio popup context alive.

These are presentation-lifecycle defects, not five new device capabilities. They SHOULD be corrected in one reviewed change so the fixes share one explicit context/invalidation model and do not create GUI-owned application/device authority.

## What Changes

- Introduce an explicit room-presentation context boundary keyed by the current `RoomDiagnosticSessionIdentity` already produced by application authority.
- Preserve only safe room-local user presentation state across same-identity background re-render: equipment viewport/scroll state and network disclosure state; retain the already-approved Audio channel selection semantics without making it popup authority.
- Reset room-local presentation state on a real `RoomDiagnosticSessionIdentity` replacement or explicit presentation clear; state restoration is presentation-only and emits no room/device interaction intent.
- Make known-switch rows in the existing network summary tree truthfully disclose their current canonical attached room-equipment rows, while preserving the existing switch summary semantics and keeping those visual children non-authoritative.
- Preserve each known switch row's user-selected expanded/collapsed state across same-identity background re-render and reset it on a new room/session identity.
- Replace selected/pinned Audio popup lifetime with a single presentation-owned hover coordinator whose target is safe identity only: current room/session identity + current expanded Audio `record_id` + `section` + `oid`.
- Keep the Audio popup visible while the pointer is over the active source scale or its popup, switch immediately when another current scale is entered, and close when neither surface owns hover.
- Invalidate/hide the Audio popup synchronously on Audio row collapse, current expanded-row replacement, room/session identity replacement, target disappearance, or presentation clear; stale hide/reposition callbacks cannot reopen or hide a newer target.
- Preserve the popup across a same-context destructive re-render only by re-resolving/revalidating the safe target against the rebuilt current expanded Audio presentation; disposable widget references never survive rebuild.
- Restore the already-required clear VIP indication directly from current canonical `session.room_vip`; no second VIP state is introduced.

## Capabilities

### Modified capabilities

- `diagnostic-ui-presentation`
  - define context-scoped scroll/disclosure preservation for same-room/session re-render;
  - make the network summary tree genuinely disclosable without creating topology authority;
  - replace Audio selected/pinned popup lifetime with hover + current-expanded-row lifetime;
  - preserve the existing canonical VIP presentation requirement as the regression oracle.

### Unchanged authoritative capabilities

- `room-device-interaction-lifecycle`
  - remains the authority for exact current row/context, interaction admission, handler/session ownership, stale-result rejection, credentials, and serialized network work; this change adds no lifecycle owner there.

## Impact

### Production areas expected to be touched during implementation

Implementation is expected to be localized primarily to the current room presentation (`gui/room_diagnostic_tree.py`), theme/component presentation only if needed for the VIP/disclosure affordance, and focused GUI regression tests. Application/controller/protocol code SHOULD remain unchanged unless current source has materially changed before implementation and architecture is re-reviewed.

### Explicit non-goals

This change SHALL NOT:

- redesign Audio/Matrix/Codec/PDU dashboards beyond the five tracked presentation defects;
- change device/protocol semantics or supported-device capability;
- move exact-row, room, network-topology, credential, handler/session, request-generation, retry, or device-I/O authority into Qt presentation state;
- make scroll/disclosure/hover state canonical room/device state;
- make a network summary/child row a routing or target authority;
- allow popup target state to substitute for the current expanded row or `RoomInteractionContext`;
- enable the currently disabled Audio DSP gain/mute placeholders or create a mutation path;
- start network I/O from render, hover, scrolling, disclosure restoration, popup timers, or VIP rendering;
- use string heuristics instead of typed failures/currentness evidence;
- expose credentials/secrets in presentation state, logs, errors, tooltips, or tests;
- use Graphify as authority or validation evidence.

## Change base

This change is authored against current `master`:

`fcf066b9046d78a864e957a927626981a77c2691`

At architecture reconnaissance time there was no `agent/room-diagnostic-ui-presentation-stability` branch and no PR for this change. Publishing these approved design artifacts on the dedicated feature branch is permitted when explicitly authorized; production code/tests remain out of scope until the architecture gate is complete.
