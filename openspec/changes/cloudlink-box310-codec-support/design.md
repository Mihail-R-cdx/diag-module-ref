# Design: CloudLink Box 310 codec support

## Context

The current exact model path is deliberately split into two identities:

```text
inventory/application model: CloudLink Bar 310
handler/display model:        Huawei CloudLink Bar 310
```

Application composition resolves only canonical `diagnostic_model` values. `CloudLink Bar 310` is present in the importer registry, application dispatch registry, codec page registry, codec transport-profile policy, interactive handler factory, related-codec resolver/adapter, and model-specific application branches. The existing Bar polling path then constructs `CloudLinkBar310Handler`; the handler, worker, and parser currently require the exact handler/display identity `Huawei CloudLink Bar 310`.

`CloudLink Box 310` is a distinct supported product identity but uses the same management protocol and supported operations as Bar 310. The architecture must therefore add a second exact model identity while keeping one protocol implementation.

## Goals

1. Recognize `CloudLink Box 310` deterministically from inventory evidence.
2. Dispatch Box 310 to the codec page and the existing Bar 310 protocol lifecycle.
3. Reuse the existing Bar 310 endpoint, transport, parsing, failure, retry, and interactive-operation semantics.
4. Preserve the correct product identity in validated raw status and GUI presentation.
5. Preserve exact application-owned credential and connection-profile ownership per model/IP.
6. Preserve Bar 310 behavior and regression coverage unchanged.
7. Make direct diagnostics and PDU related-codec enrichment both support Box 310.

## Non-goals

- Do not add, remove, or change Bar/Box HTTP endpoints or command payloads.
- Do not clone `CloudLinkBar310Handler`, its command map, parser logic, or polling plan into a second Box-specific implementation.
- Do not add fuzzy runtime aliases or substring dispatch.
- Do not infer Bar versus Box from a device-provided free-form model string.
- Do not retry a failed Box operation as Bar or a failed Bar operation as Box.
- Do not share or copy credentials automatically between the two exact model keys.
- Do not change credential fallback, successful-index persistence, interactive recovery, transport retry, stale-operation acceptance, or state-changing replay policy.
- Do not add a GUI page or redesign `CodecScreen`.
- Do not change production inventory data or Graphify artifacts.

## Decision 1: Keep two exact product identities over one protocol family

The approved exact identities SHALL be:

| Purpose | Bar 310 | Box 310 |
| --- | --- | --- |
| canonical inventory/application model | `CloudLink Bar 310` | `CloudLink Box 310` |
| handler/parser/display model | `Huawei CloudLink Bar 310` | `Huawei CloudLink Box 310` |
| screen | `codec` | `codec` |
| diagnostic lifecycle route | `cloudlink_bar_310` | `cloudlink_bar_310` |
| default transport profile | HTTPS 443 | HTTPS 443 |

Application composition remains the authority that assigns the exact canonical model. A shared immutable mapping or equivalent focused helper MAY translate the assigned application model to its expected handler/display identity. That mapping SHALL contain only the two reviewed identities above; it SHALL NOT perform substring, fuzzy, response-based, or failure-based recognition.

The product identity passed into the shared protocol implementation is public non-secret operation context. It is not credential evidence and cannot authorize credential fallback.

## Decision 2: Inventory recognition adds one non-overlapping exact rule

The importer closed reviewed registry SHALL add:

```text
CloudLink Box 310
  required: cloudlink + box + 310
```

The existing rule remains:

```text
CloudLink Bar 310
  required: cloudlink + bar + 310
```

The existing component normalization, independent evaluation of `Модель` and `Наименование`, distinct-union cardinality, ambiguity handling, and safe diagnostics remain unchanged. `box` and `bar` are distinct exact components; neither is an alias for the other.

Examples:

```text
Huawei CloudLink Box 310 -> CloudLink Box 310
CloudLink-Box-310        -> CloudLink Box 310
cloudlink_box310         -> CloudLink Box 310
CloudLink Bar 310        -> CloudLink Bar 310
CloudLink Box 610        -> unmapped
Box 310                  -> unmapped because cloudlink is required
```

The expected kind for `CloudLink Box 310` is `video_codec`, matching the existing authoritative source-type consistency model. Recognition still does not override `Тип модели -> device_kind`.

## Decision 3: Dispatch adds Box as a distinct registry entry sharing the Bar lifecycle

The application closed dispatch registry SHALL contain a separate exact entry:

```text
CloudLink Box 310 -> codec -> cloudlink_bar_310
```

The existing Bar entry remains:

```text
CloudLink Bar 310 -> codec -> cloudlink_bar_310
```

The codec equipment-page registry SHALL include both exact canonical models. Fallback model choices and credential-configuration resolution therefore expose Box 310 as its own selectable exact model while still assigning the same codec page and shared lifecycle route.

No runtime component may collapse the accepted canonical model to `CloudLink Bar 310`. The exact accepted model remains part of request freshness, credential keying, successful-index memory, connection-profile memory, interactive context identity, and stale callback checks.

## Decision 4: Parameterize identity at the shared Bar protocol boundary

`CloudLinkBar310Handler` remains the single protocol implementation for both products. It SHALL receive or otherwise be constructed with one already validated expected handler/display identity derived from the assigned exact application model.

For ordinary polling:

```text
assigned CloudLink Bar 310
    -> shared Bar protocol worker/handler
    -> raw model == Huawei CloudLink Bar 310
    -> parsed Модель == Huawei CloudLink Bar 310

assigned CloudLink Box 310
    -> same shared Bar protocol worker/handler
    -> raw model == Huawei CloudLink Box 310
    -> parsed Модель == Huawei CloudLink Box 310
```

The handler SHALL continue to manufacture the canonical handler/display model from trusted assigned context rather than copy a free-form response label. The worker and parser SHALL validate against the expected identity for that operation, not merely accept either family member. A mismatched identity is a protocol/parser contract failure; it does not trigger model switching.

The lifecycle delta SHALL modify the existing root requirements `CloudLink Bar 310 required core evidence is exact` and `CloudLink Bar 310 parser and worker success require exact usable canonical status`. Those requirements SHALL no longer hard-code Bar identity as the only successful identity; they SHALL parameterize exact success by the trusted expected identity derived from the assigned Bar or Box application model. The new family requirement is complementary and SHALL NOT exist as a contradictory parallel contract.

All existing Bar polling decisions remain shared and unchanged: required version gate, explicit optional status plan, endpoint ownership/precedence, optional endpoint isolation, typed terminal failures, presentation/sleep normalization, zero preservation, cleanup, and redaction.

## Decision 5: Every existing Bar model gate that represents protocol capability becomes a Bar/Box family gate

Exact-model branches that exist only to select Bar protocol capability SHALL accept both reviewed application models and route them to the same implementation. This includes:

- ordinary codec refresh and credential-attempt restart;
- codec transport-profile ordering;
- interactive-session handler acquisition and supported Bar interactive operations;
- PDU room resolver related-codec support, related-codec status support, and Bar call/presentation normalization;
- the existing SIP-server action where Bar 310 is already supported.

These are closed family gates, not aliases. Prefer one shared constant/helper for the approved Bar/Box family where it reduces duplicated exact-name conditionals. Do not broaden unrelated Huawei, Polycom, TE20, or TE40 behavior.

## Decision 6: Credentials and saved success remain exact-model scoped

Protocol equivalence does not imply credential equivalence.

The application SHALL resolve credential candidates for the exact accepted canonical model:

```text
CloudLink Bar 310 -> Bar model credential chain
CloudLink Box 310 -> Box model credential chain
```

A deployment MAY explicitly configure the same credential profile for both model names, but application code SHALL NOT silently copy, alias, or fall back from one model's credential candidates to the other model.

Successful credential index and saved connection profile remain keyed by the exact model and IP. Success for Box 310 cannot become Bar 310 success evidence, and vice versa.

## Decision 7: Related-codec enrichment treats Box as the same protocol family but preserves Box identity

The pure room resolver's closed supported-related-codec set SHALL include exact `CloudLink Box 310`, so a unique video-codec record with that canonical model may resolve normally. This is an exact support entry; the resolver SHALL NOT infer Box support from `device_kind`, `source_model`, or similarity to Bar 310.

When room resolution returns exact `codec_diagnostic_model = CloudLink Box 310`, the enrichment controller SHALL keep that exact model in its context, resolve Box credentials, order the same HTTPS:443 profile, acquire the shared Bar protocol handler with Box identity, and use the same call/presentation command semantics as Bar 310.

Accepted presentation continues to report `codec_diagnostic_model = CloudLink Box 310`. No resolver, enrichment component, or status adapter may replace it with Bar 310 merely because the protocol implementation is shared.

## Decision 8: Regression boundary

Synthetic tests SHALL prove at least:

1. importer recognition for `CloudLink Box 310` across case/separator/compact forms;
2. boundary negatives and Bar/Box distinction;
3. dispatch and page registration for Box 310 with lifecycle `cloudlink_bar_310`;
4. Bar 310 dispatch remains unchanged;
5. Box polling uses `CloudLinkBar310Handler` semantics but validates/displays `Huawei CloudLink Box 310`;
6. Bar polling still validates/displays `Huawei CloudLink Bar 310`;
7. identity mismatch is rejected rather than silently rewritten;
8. Box uses the existing HTTPS:443 profile policy;
9. room resolution, interactive handler acquisition, and related-codec status use the shared Bar protocol capability for Box while preserving exact Box identity;
10. Box and Bar credential/success/profile contexts remain distinct;
11. existing Bar status-polling regression suite still passes;
12. no production inventory, credential file, or Graphify artifact is introduced.

## Implementation shape

A preferred implementation shape is:

```text
exact application model
    -> closed Bar/Box identity mapping
    -> shared lifecycle route cloudlink_bar_310
    -> existing Bar protocol implementation
    -> expected exact handler/display identity
```

The implementation may place the small family/identity mapping in an existing focused codec module or a new focused pure module if that removes duplicated literals cleanly. It must not create a generic alias engine or new model-guessing layer.
