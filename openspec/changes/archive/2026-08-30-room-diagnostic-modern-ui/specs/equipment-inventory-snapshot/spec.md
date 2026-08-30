## ADDED Requirements

### Requirement: Room-name search is room-id preserving, distinguishable, and deterministic

The storage-independent `EquipmentInventory` runtime boundary SHALL provide a room-name search operation equivalent to `find_rooms_by_name(query)` for application autocomplete and direct room selection. This query SHALL NOT change canonical schema version 4 and SHALL perform no device/network I/O.

The search SHALL use only canonical records whose `room_id` is non-null and whose `room_name` is nonblank. The query and candidate names SHALL be compared after the existing canonical text normalization plus Unicode `casefold()`. A nonblank query matches when its complete normalized/casefolded text is a substring of a normalized/casefolded canonical `room_name`.

Matching SHALL NOT use fuzzy similarity, edit distance, transliteration, token guessing, device model text, address, VIP state, IP, `device_kind`, `source_model`, or registry order.

Search identity SHALL remain exact canonical `room_id`. Every matching room ID SHALL appear at most once even when several records or several differing names under that room ID match. Distinct room IDs SHALL remain distinct results even when their display names are identical.

For one matched room ID, the search projection SHALL derive presentation evidence independently and deterministically from canonical room records in ascending canonical `record_id` order:

```text
display_name     = first nonblank room_name
display_address  = first nonblank room_address, or null
```

A room MAY match because of another nonblank name present on a later record; this SHALL NOT change room identity or rewrite canonical records.

Autocomplete SHALL expose a deterministic `selection_label` or equivalent display string for each result. The label SHALL begin with `display_name`; when `display_address` is available it SHALL append that address as display-only disambiguation, for example `Переговорная — ул. ..., д. ...`. If two or more distinct room IDs in the same current result set still produce the same normalized name/address label, the application/inventory presentation projection SHALL append a neutral deterministic result discriminator such as `Вариант 1`, `Вариант 2` according to the already-defined deterministic result ordering. The discriminator SHALL NOT become room identity and SHALL NOT be persisted as canonical data.

Raw canonical `room_id` MAY remain hidden from ordinary operator presentation. Regardless of the displayed label, authority SHALL remain the exact result `room_id` bound to the current inventory snapshot.

Results SHALL be deterministic and ordered by casefolded `display_name`, then casefolded `display_address` with null sorting consistently, and then canonical `room_id`. Blank/empty normalized query SHALL return an empty result collection.

The runtime inventory implementation SHALL maintain an immutable room-search projection/index or equivalent precomputed structure so normal autocomplete queries do not repeatedly reconstruct room identity or normalize the complete canonical record set on every keystroke.

#### Scenario: Partial room name returns one room

- **GIVEN** canonical room ID `room-305` has nonblank room name `Переговорная 305`
- **WHEN** the application searches for `говорная 30`
- **THEN** the result contains `room-305`
- **AND** no device network I/O occurs

#### Scenario: Same room has several name values

- **GIVEN** records under one canonical `room_id` contain more than one nonblank `room_name`
- **WHEN** the query matches any one of those names
- **THEN** that room ID appears exactly once
- **AND** its display name is the first nonblank room name in canonical record order

#### Scenario: Same room name belongs to different room IDs with different addresses

- **GIVEN** two distinct canonical room IDs have the same `display_name`
- **AND** their first usable canonical room addresses differ
- **WHEN** that name is searched
- **THEN** both room IDs remain separate results
- **AND** their selection labels include the respective addresses so the operator can distinguish them
- **AND** the inventory does not merge them by display text

#### Scenario: Same room name and address still remain distinguishable

- **GIVEN** two or more distinct room IDs in one result set have equal normalized display name and display address
- **WHEN** autocomplete labels are produced
- **THEN** each result receives a deterministic neutral result discriminator in the display label
- **AND** each label still maps to exactly one canonical room ID
- **AND** the discriminator is not canonical identity or persisted room metadata

#### Scenario: Search does not use address or device model to create matches

- **GIVEN** a query appears only in a room address or device model text and not in any canonical room name
- **WHEN** room-name search runs
- **THEN** that evidence does not create a room match
- **AND** address may only decorate an already matched room result

#### Scenario: Blank search is empty

- **WHEN** room-name search receives only blank/whitespace text
- **THEN** it returns an empty result collection
- **AND** it creates no fallback or network activity
