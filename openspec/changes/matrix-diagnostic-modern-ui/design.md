# Design: Modern Matrix/IN1804 room presentation

## Context

MIH-9 established the common room shell and exact-row accordion. MIH-10 independently modernized Audio DSP inside that shell. MIH-11 owns the Matrix/Extron IN1804 expanded room presentation and the minimum room-safe route interaction needed for the approved Matrix table.

Current `master` has three Matrix concerns that must remain separated:

1. **Accepted Matrix evidence**
   - `ExtronIN1804Handler.get_full_status()` collects existing device/routing evidence.
   - `ExtronIN1804DataParser.parse()` publishes normalized Matrix data.
   - Current legacy behavior is not fully fail-closed: constructor/parser defaults can synthesize eight inputs or input 1, and failed HDCP reads can collapse to zero.

2. **Standalone Matrix lifecycle**
   - `MatrixScreen` owns standalone presentation and emits `routeRequested`.
   - `MatrixController` owns standalone background refresh/route/session/currentness.
   - This standalone screen/controller pair is not room authority.

3. **Room Matrix lifecycle**
   - `RoomDiagnosticTreeWidget` owns room presentation only.
   - `RoomReadOnlyPresentation._build_matrix()` is the current Matrix room projection.
   - unified dispatch registers exact `Extron IN1804` with `matrix_one_shot` and `matrix_room_live`, but no room mutation binding.
   - `RoomInteractionCoordinator` owns one serialized room lane including generic `MUTATION` and `RECONCILIATION` semantics.

The redesign must preserve those ownership boundaries while tightening Matrix evidence before it is allowed to authorize room routing.

## Goals

- Match the approved Matrix reference hierarchy/field placement inside the foundation accordion.
- Keep the Matrix table visually dominant and operator-readable.
- Preserve truthful accepted evidence; never fabricate reference values or legacy defaults as device evidence.
- Show HDCP as presence only: `есть`, `нет`, `Нет данных`.
- Add exact-row room routing to output 1 through existing application-owned mutation safety with explicit confirmation.
- Ensure missing/malformed route readback can never confirm a state-changing route.
- Preserve current Matrix live/local-refresh and standalone behavior except where fail-closed normalization removes fabricated defaults.
- Keep dark/light presentation geometry stable and GUI network I/O off the Qt GUI thread.

## Non-goals

- No redesign of the common room header/shell.
- No Audio DSP/codec/PDU redesign.
- No new protocol reads for MAC, serial, firmware, uptime, HDCP version, reboot, or expanded-screen navigation.
- No HDCP version display.
- No standalone Matrix screen promotion into room mode.
- No `Открыть расширенный экран` affordance in the room Matrix dashboard.
- No second room route lane or direct widget-to-handler call.
- No mutation retry after possible route delivery.
- No change to Matrix SIS route command syntax (output 1 only).

## Decision 1: The room exact-row surface is the normative Matrix target

The modern Matrix content is rendered by the current room path under `RoomDiagnosticTreeWidget`. `MatrixScreen` remains a standalone consumer/lifecycle.

Implementation may extract a presentation-only Matrix dashboard widget, but room mode remains acceptance authority. Such a widget may consume accepted data and emit safe local intents; it cannot own credentials, handlers, sessions, request generations, currentness, or device I/O.

The common accordion header is unchanged. MIH-11 starts below that header.

`Открыть расширенный экран` SHALL NOT be rendered in MIH-11: no enabled control, disabled placeholder, navigation signal, or acceptance requirement exists for it.

## Decision 2: Three-card Matrix dashboard hierarchy

At the foundation baseline viewport (`1440 x 900` logical pixels), expanded Matrix content is one horizontal dashboard with this order:

```text
+-------------------------+--------------------------------------------------+--------------------+
| Общая информация       | Матрица (входы и коммутация)                    | Быстрые действия   |
| narrow                  | dominant                                         | narrow             |
+-------------------------+--------------------------------------------------+--------------------+
```

Approximate content-width shares:

```text
General information: 24-28%
Matrix table:        50-56%
Quick actions:       18-22%
```

The central Matrix card remains dominant. Exact pixel dimensions and gaps use foundation/theme tokens. At `1180 x 720`, controlled reflow/scrolling is allowed if semantic order and action meaning remain reachable and unchanged. Theme switching is presentation-only and performs no Matrix I/O.

## Decision 3: General information card uses fixed visual slots and truthful evidence

Rows always render in this order:

```text
Модель
MAC-адрес
Серийный номер
Версия прошивки
Температура
Время работы
```

Deterministic accepted-key aliases may map existing accepted evidence to those slots, but presentation cannot infer values from unrelated fields, model text, logs, prior snapshots, or reference artwork. Missing fields render `Нет данных`.

On the change base, MAC, serial, firmware, and uptime are not authoritative Matrix evidence. MIH-11 does not add new protocol reads to fill them.

## Decision 4: Table order is normative and rows require proven input authority

The central table semantic order is:

```text
[input ordinal] | Сигнал | HDCP | Входы | [accepted output-1 name / Main Output]
```

Baseline width targets:

```text
ordinal       7-9%
Сигнал       18-21%
HDCP         16-18%
Входы        25-29%
output       26-30%
```

Rows are created only from a **proven accepted current input count/order**. The visual reference's eight rows are illustrative only.

Current legacy `self.inputs_num = 8` / parser fallback `data.get('inputs_num', 8)` SHALL NOT establish accepted input authority. Input count is known only when existing model/capability evidence positively establishes the supported exact Matrix input count. If count is unproven, normalized count remains UNKNOWN/absent and the room presentation SHALL NOT fabricate eight rows or enable route intents for an unproven ordinal.

The output header uses the first accepted output name when present/non-empty; otherwise `Main Output`.

## Decision 5: Existing Matrix reads are normalized fail-closed before presentation/reconciliation

MIH-11 explicitly includes normalization-only corrections in `handlers/extron/in1804.py` and `core/parser.py`. It does not add a new SIS command.

### Input count

- recognized existing model/capability evidence -> positive accepted count;
- missing/unrecognized model/count evidence -> UNKNOWN/absent;
- constructor or parser default `8` is not device evidence;
- per-input arrays produced only from an unproven legacy default cannot authorize table rows or route intents.

### Current connection

`current_connection` is an optional accepted input ordinal. It is established only by a successfully parsed existing connection readback that identifies one valid input within the proven accepted input range.

```text
valid parse + valid input -> N
empty response            -> None / UNKNOWN
malformed response        -> None / UNKNOWN
out-of-range response     -> None / UNKNOWN
failed read               -> None / UNKNOWN
```

`get_connections()` SHALL NOT append input 1 when the response contains no parseable route. `ExtronIN1804DataParser.parse()` SHALL NOT use input 1 when the connection list is empty.

A route readback parser SHALL parse the protocol response intentionally rather than concatenate unrelated digits into a synthetic input number.

### HDCP presence

The room column represents current **input HDCP presence**, not HDCP version, input authorization configuration, or output HDCP state.

A dedicated normalized per-input tri-state projection SHALL be derived from the existing input HDCP status read:

```text
recognized present -> True
recognized absent  -> False
failed/malformed/unrecognized/missing -> None
```

Failure must never be collapsed into false merely to fill the table. Existing `input_hdcp_auth` configuration and `output_hdcp` evidence are not presentation authority for this column.

## Decision 6: Signal, HDCP presence, and route cells preserve non-color meaning

### Signal

Signal presentation uses accepted `signal_status` and must distinguish confirmed absence from unknown. Color is supplementary only.

```text
confirmed signal present -> `есть`
confirmed signal absent  -> `нет сигнала`
unknown                  -> `Нет данных`
```

### HDCP

```text
hdcp_present is True  -> `есть`
hdcp_present is False -> `нет`
hdcp_present is None  -> `Нет данных`
```

No `2.2`, `1.4`, other version/status token, authorization value, or output HDCP value is displayed in the room `HDCP` column.

### Route/output

```text
current_connection == input N -> `активен`
known different current input -> `не выбран`
current_connection is UNKNOWN -> `Нет данных`
```

Local click/hover/confirmation/ACK state never changes authoritative route styling before reconciliation accepts a truthful snapshot.

## Decision 7: Matrix route is a safe exact-row intent with explicit confirmation

A non-active output cell may become actionable only when all are true:

- current row is exact `Extron IN1804`;
- row is current expanded record with usable connected state;
- row is not stale/degraded/blocked/unconfirmed;
- unified registration declares approved Matrix mutation/reconciliation bindings;
- room lane permits mutation;
- input ordinal is within the proven accepted input authority.

Presentation emits only a non-secret immutable intent equivalent to:

```text
MatrixRoomRouteIntent(output_num=1, input_num=N)
```

The active cell is a no-op. Composition revalidates exact `record_id`, shows an explicit confirmation dialog, and only on confirmation calls `RoomInteractionCoordinator.confirm_mutation()`. Cancel changes no lifecycle state and performs no I/O.

## Decision 8: Unified registration owns Matrix room mutation capability

No parallel model list is introduced. The exact `Extron IN1804` registration adds explicit room bindings equivalent to:

```text
mutation_binding_key       = matrix_room_route
reconciliation_binding_key = matrix_room_route_reconcile
cleanup_binding_key         = existing room cleanup authority
```

Existing `matrix_one_shot`, `matrix_room_live`, and local-refresh acquisition remain authorities. Startup/composition fails closed if declared mutation capability lacks mutation/reconciliation/cancellation/cleanup hooks.

## Decision 9: Matrix mutation uses one exact credential attempt and one send

The background route adapter receives immutable exact-row context, validated output 1/input N intent, and exactly one application-selected credential candidate/index per attempt. Handler/worker never chooses or iterates candidates.

Only structured authentication rejection proven before route delivery may authorize application-owned candidate advance after cleanup. Once route send is invoked or delivery is ambiguous, no candidate advance or replay is allowed. Public strings never authorize fallback.

## Decision 10: Route ACK is non-authoritative; reconciliation requires truthful requested-input readback

ACK/success from route send is only delivery evidence. It cannot update accepted `current_connection`, visible active route, or final success memory.

Reconciliation performs current exact-row read-only Matrix acquisition. Success is authoritative only when fail-closed normalized evidence establishes:

```text
current_connection == requested input_num
```

A different input, `None`, malformed/failed evidence, or other UNKNOWN result fails reconciliation unconfirmed. This rule is especially important for requested Input 1: no legacy default may convert missing readback into confirmation.

On failed/unconfirmed reconciliation, prior cache is stale/unconfirmed, row network actions/live remain blocked, and top full Refresh is required. On confirmed reconciliation, the full accepted snapshot may atomically replace row cache; eligible live resumes only after cleanup/currentness checks.

## Decision 11: Model-specific cleanup remains inside the one room lane

Composition may generalize PDU-specific dispatch plumbing or add a Matrix-specific sibling, but SHALL preserve one serialized room lane and model-specific owners. Matrix cancellation targets Matrix ownership, PDU cancellation remains PDU-specific, and neither acquires the other's resources.

## Decision 12: Quick actions contain only approved controls

The right `Быстрые действия` card contains:

### `Обновить статус`
Enabled only when existing exact-row Local Refresh is allowed. It emits existing Local Refresh intent and creates no second refresh path.

### `Перезагрузить устройство`
Visible for layout fidelity but disabled/non-actionable because approved IN1804 capability has no reboot mutation. It emits no signal, worker, handler call, or device request.

`Открыть расширенный экран` is absent from the room dashboard.

## Decision 13: Existing live/local refresh and standalone routing remain regression-free

MIH-11 does not replace existing `matrix_room_live` or `matrix_one_shot` acquisition. Confirmed mutation retires current Matrix live through the existing bounded lifecycle before send. Eligible live may resume only after confirmed reconciliation and cleanup/currentness checks.

Standalone `MatrixScreen`/`MatrixController` routing remains separate. Tightened normalization may remove fabricated defaults but does not rewire standalone routing through room state.

## Failure-state table

| Event | Room Matrix result |
| --- | --- |
| Click active route | no mutation |
| Confirmation Cancel | no lifecycle change, no I/O |
| Stale/superseded intent before acquisition | reject/no I/O |
| Live cleanup timeout before send | route not sent |
| Structured auth rejection before delivery | candidate may advance after cleanup |
| Route send ACK/success | start reconciliation; cache unchanged |
| Route send ambiguous/unknown outcome | blocked/unconfirmed; no replay/fallback; full Refresh required |
| Reconciliation reads requested input | accept new full snapshot; normal lifecycle may resume |
| Reconciliation reads different input | blocked/unconfirmed; prior cache stale; full Refresh required |
| Reconciliation has empty/malformed/UNKNOWN route evidence | blocked/unconfirmed; never synthesize Input 1; full Refresh required |
| Late callback from superseded context | ignored |

## Testing strategy

### Normalization

- missing/unrecognized model/count does not become 8 accepted inputs;
- empty connection list normalizes `current_connection` to UNKNOWN, not 1;
- successful connection response without a parseable input normalizes to UNKNOWN;
- out-of-range connection normalizes to UNKNOWN;
- requested Input 1 plus failed/empty/malformed readback cannot reconcile successfully;
- HDCP input presence has present/absent/unknown states;
- HDCP read failure/malformed response does not become `нет`.

### Presentation

- exact three-card order at baseline;
- general-info row order and no-data behavior;
- data-driven **proven** input count; no hard-coded/default eight;
- exact table column order and dynamic output header;
- signal + non-color cue;
- HDCP displays only `есть` / `нет` / `Нет данных` and never a version token;
- route active/non-active/no-data states;
- dark/light baseline/minimum behavior;
- reboot disabled;
- `Открыть расширенный экран` absent;
- Local Refresh uses existing intent.

### Intent/currentness and registry

- only non-active eligible output cell emits route intent;
- unproven input count exposes no actionable fabricated input;
- stale/non-current row emits/accepts no mutation;
- confirmation cancel performs zero device I/O;
- exact Extron registration owns Matrix mutation/reconciliation bindings with no parallel model list.

### Mutation safety

- live retires before route owner starts;
- no acquisition before currentness/cleanup gate;
- pre-delivery typed auth rejection may advance one approved candidate;
- after route send invocation no automatic replay/candidate advance;
- at most one route send per confirmed mutation attempt;
- ACK does not update accepted route state;
- reconciliation must match requested input from truthful normalized evidence;
- mismatch/UNKNOWN blocks row and requires full Refresh;
- stale callbacks cannot update replacement context.

### Regression

- existing PDU mutation/reconciliation unchanged;
- existing Matrix room live/local Refresh unchanged;
- standalone Matrix routing remains functional and separate;
- common accordion one-expanded-row behavior unchanged;
- theme toggle does not perform I/O.

## Manual visual acceptance

At `1440 x 900` in dark and light themes verify:

- left General information / center Matrix / right Quick actions hierarchy;
- exact field order;
- central table visually dominant;
- input number compact;
- Signal, HDCP, input name, and output columns readable without baseline clipping;
- HDCP is presence-only and never shows a version;
- route state understandable without color;
- reboot visibly disabled;
- `Открыть расширенный экран` is absent;
- shared foundation header/room/network regions remain unchanged.

Screenshots are local validation evidence and are not repository artifacts by default.
