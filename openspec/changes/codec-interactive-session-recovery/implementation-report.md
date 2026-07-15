# Implementation Evidence

## Scope

- Change: `codec-interactive-session-recovery`
- Branch: `agent/codec-interactive-session-recovery`
- Architecture baseline: `a8a5fae389158d6fcb6ac36c58af9064f61983fe`
- Implementation date: 2026-07-15
- Hardware access: authorized operator-performed Huawei TE20 QA; no device
  identifiers, credentials, or session material were recorded.

## Delivered behavior

- Added typed login-authentication, established-session invalidation, transport,
  protocol, command, and indeterminate-command outcomes. Codec credential retry
  authority now comes only from the structured authentication category.
- Added request-scoped monotonic credential plans and a shared model-specific
  saved-profile-first transport policy, including TE20 runtime HTTPS support.
- Normalized TE20, TE40, Bar 310, and Polycom handler session boundaries and
  cleanup. Bar 310 presentation now sends once and performs one authoritative
  readback.
- Added a single-lane interactive session controller with context generations,
  duplicate-poll suppression, dequeue-time stale-work rejection, bounded
  recovery, and redacted public signals.
- Added read-only replay and state-changing readback/reconciliation so relative
  and toggle-like controls are never blindly applied twice.
- Routed CodecScreen live audio, sleep/Wake, volume, mute/gain, presentation,
  and Huawei call logs through background controller work. Polycom call logs and
  diagnostic refresh remain intentionally separate.
- Added deterministic shutdown and session artifact cleanup for screen/model/IP/
  credential lifecycle changes.

## Architecture compatibility

Implementation did not discover a change to the approved four-model matrix,
transport ordering, credential ownership rules, or conservative typed failure
classifier. `architecture-report.md` therefore remains unchanged.

## Automated evidence

Runtime and dependency restoration:

```text
node --version                                      -> v20.19.0
npm --version                                       -> 10.8.2
npm ci                                              -> 79 packages, 0 vulnerabilities
Python                                              -> CPython 3.12 project interpreter
```

Focused offline tests were run in isolated processes to avoid sharing Qt
application lifetime between otherwise independent test modules:

```text
credential/controller/handler contracts             -> 21 passed
CodecScreen offscreen                                -> 19 passed
credential retry ownership and worker outcomes       -> 40 passed
UI state                                             -> 4 passed
hardware-log and general redaction                    -> 27 passed
Focused total                                        -> 111 passed
```

Full regression and OpenSpec validation:

```text
python -m unittest discover -s tests -p "test_*.py"  -> 167 passed
.\openspec.cmd validate codec-interactive-session-recovery --strict
                                                     -> valid
.\openspec.cmd validate --all --strict               -> 7 passed, 0 failed
git diff --check                                     -> clean
```

The initial ad-hoc focused command placed multiple Qt application-owning test
modules in one manually ordered interpreter and exposed cross-module Qt
lifetime contamination. The repository's canonical discovery run passed, and
the focused evidence above was rerun in isolated processes; no production
behavior or mandatory check failed.

## Code-review remediation evidence

Independent review of published head
`22cd1b14dc968b6457797b0145a6b339cea0174c` returned `CHANGES REQUIRED` for
three bounded contract violations. The remediation preserves the approved
design and changes only `core/interactive_session.py`,
`gui/screens/codec_screen.py`, and their regression tests:

- one private operation budget is created at dequeue and is consumed by either
  a locally disconnected matching cache or later typed recovery; once consumed,
  a subsequent recoverable failure is terminal and cannot reconnect again;
- TE20, TE40, and Polycom mute/unmute descriptors now use opposite authoritative
  `Muted`/`Unmuted` desired states, while Bar 310 retains numeric gain policy;
- duplicate ownership is keyed by generation and duplicate key, with the exact
  operation ID as owner, so an old operation cannot release a new generation's
  marker.

Focused review-remediation tests were isolated by Qt application type:

```text
InteractiveSessionController, session/handler contracts -> 27 passed
CodecScreen offscreen mute descriptors                  -> 21 passed
credential fallback and worker retry ownership          -> 24 passed
Focused total                                           -> 72 passed
```

The canonical full offline suite was rerun after the production and regression
test changes:

```text
python -m unittest discover -s tests -p "test_*.py"      -> 175 passed
.\openspec.cmd validate codec-interactive-session-recovery --strict
                                                         -> valid
.\openspec.cmd validate --all --strict                   -> 7 passed, 0 failed
git diff --check                                         -> clean
```

## Security evidence

Synthetic credential, cookie, Session ID, CSRF, SSH, terminal, dialog, and
worker-output redaction paths are covered by the focused 27-test redaction
group and the full suite. Controller signals expose only operation/context
metadata, stable categories, safe messages, selected credential index, and
transport profile; they never expose candidate credential values or raw caught
exception text.

## Operator hardware evidence

On 2026-07-15 the operator confirmed the current Huawei TE20 build on live
equipment. The reported reproduction path, including microphone Mute control
and its delayed status refresh, worked after the follow-up fix: the field
remained a semantic `Muted`/`Unmuted` state instead of being overwritten by
numeric gain value `0`. No secrets or device identifiers were included in the
observation.

No TE40, Bar 310, or Polycom hardware observations were provided; this is not
treated as an offline acceptance failure because those devices were not
reported as available for this opt-in QA pass.

Post-implementation operator fixes were initially checked narrowly: the
default-IP text-only correction passed `git diff --check` without a test run,
and the TE20 mute readback correction passed 25 focused handler/CodecScreen
tests. Both fixes are included in the later 175-test review-remediation run
recorded above. Independent validation must still rerun all mandatory commands
against the final published SHA.
