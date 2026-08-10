## ADDED Requirements

### Requirement: Repository-local archive output is normalized after successful upstream archive

The tracked repository-local `openspec.cmd` wrapper SHALL keep the pinned repository-local OpenSpec CLI as the authority that applies archive deltas. For an invocation whose first command token is `archive`, the wrapper SHALL run archive-specific compatibility processing around that upstream command. It SHALL NOT implement requirement merging itself and SHALL NOT patch installed files under `node_modules`.

#### Scenario: Successful archive receives compatibility processing

- **WHEN** `./openspec.cmd archive <change> --yes` invokes the pinned upstream archive and the upstream command succeeds
- **THEN** the repository-local archive compatibility postprocessor runs before the wrapper reports success
- **AND** semantic requirement application remains the result produced by the pinned upstream OpenSpec command

#### Scenario: Non-archive command is invoked

- **WHEN** the wrapper receives a command whose first command token is not `archive`
- **THEN** it forwards that command through the existing pinned repository-local OpenSpec path without archive preflight or EOF normalization
- **AND** it preserves the upstream command result and exit status

### Requirement: Archive preflight protects pre-existing root specification work

Before invoking upstream archive, the archive compatibility path SHALL verify that `openspec/specs/` contains no pre-existing tracked modifications, staged modifications, or untracked files. If the root-spec tree is not clean, the wrapper SHALL fail before upstream archive and SHALL NOT normalize or overwrite that work.

Ignored local artifacts outside the root-spec tree SHALL NOT make this preflight fail.

#### Scenario: Root specification is already modified

- **GIVEN** a tracked or staged root specification under `openspec/specs/` differs from `HEAD`
- **WHEN** repository-local archive is requested
- **THEN** the wrapper fails before invoking upstream archive
- **AND** the pre-existing root specification bytes remain unchanged

#### Scenario: Untracked root specification exists

- **GIVEN** an untracked file exists under `openspec/specs/`
- **WHEN** repository-local archive is requested
- **THEN** the wrapper fails before invoking upstream archive
- **AND** it does not treat the untracked file as archive-generated output

### Requirement: Only archive-generated root specification files are normalization targets

After a successful upstream archive that began with a clean root-spec tree, the compatibility layer SHALL derive the post-archive root-spec change set from Git and SHALL select only existing `openspec/specs/**/spec.md` files that are changed relative to `HEAD` or newly created by the archive.

The compatibility layer SHALL NOT normalize files outside `openspec/specs/`, SHALL NOT normalize archived change artifacts under `openspec/changes/archive/`, and SHALL NOT rewrite deleted paths.

#### Scenario: Archive modifies an existing root specification

- **GIVEN** the root-spec tree was clean before archive
- **AND** successful upstream archive changes `openspec/specs/example/spec.md`
- **WHEN** compatibility processing discovers archive-generated output
- **THEN** that root specification is eligible for EOF normalization

#### Scenario: Archive creates a new root specification

- **GIVEN** the root-spec tree was clean before archive
- **AND** successful upstream archive creates a new untracked `openspec/specs/new-capability/spec.md`
- **WHEN** compatibility processing discovers archive-generated output
- **THEN** that new root specification is eligible for EOF normalization

#### Scenario: Unrelated file changes outside the root-spec tree

- **WHEN** compatibility processing runs after archive
- **THEN** it does not modify the unrelated file
- **AND** the unrelated file remains available to ordinary repository checks

### Requirement: EOF normalization is minimal, deterministic, and idempotent

For each selected archive-generated root specification, the compatibility layer SHALL remove only excess terminal empty or whitespace-only lines and SHALL leave exactly one terminal line terminator. It SHALL preserve all bytes/text before the terminal blank-line region, including requirement content, scenario content, internal blank lines, indentation, and trailing whitespace attached to a non-empty content line.

The normalizer SHALL preserve an observable terminal line-ending convention (`LF` or `CRLF`). When a file contains no observable line ending, it SHALL use `LF` for the single terminal line terminator. Re-running normalization on already normalized output SHALL make no further change.

#### Scenario: Upstream archive emits multiple blank lines at EOF

- **GIVEN** an archive-generated root specification ends with two or more terminal line terminators or whitespace-only blank lines
- **WHEN** EOF normalization runs
- **THEN** the file ends with exactly one terminal line terminator
- **AND** no preceding semantic content is changed

#### Scenario: Root specification already has one clean terminal line terminator

- **GIVEN** an archive-generated root specification already ends with exactly one clean terminal line terminator
- **WHEN** EOF normalization runs
- **THEN** the file bytes remain unchanged

#### Scenario: Internal blank lines are present

- **GIVEN** a root specification contains blank lines between requirements or scenarios
- **WHEN** EOF normalization runs
- **THEN** those internal blank lines remain unchanged

#### Scenario: Final content line has trailing whitespace

- **GIVEN** the final non-empty content line contains trailing spaces or tabs
- **WHEN** EOF normalization runs
- **THEN** that trailing whitespace is not silently removed
- **AND** ordinary `git diff --check` remains able to report it

#### Scenario: CRLF root specification is normalized

- **GIVEN** the selected root specification uses `CRLF` line endings at its terminal content boundary
- **WHEN** excess terminal blank lines are normalized
- **THEN** the resulting single terminal line terminator remains `CRLF`

### Requirement: Failed upstream archive is never postprocessed into apparent success

If the pinned upstream archive command returns a non-zero exit code, the repository-local wrapper SHALL NOT run EOF normalization. It SHALL preserve the upstream failure as a failed wrapper result and SHALL NOT attempt to hide, clean up, or reinterpret partial upstream output.

#### Scenario: Upstream archive fails

- **WHEN** the pinned upstream `archive` command exits non-zero
- **THEN** EOF normalization does not run
- **AND** the wrapper returns a non-zero result reflecting archive failure
- **AND** any partial upstream changes remain visible for diagnosis rather than being rewritten by the compatibility layer

### Requirement: Archive success remains gated by repository whitespace validation

After a successful upstream archive and EOF normalization, the wrapper SHALL run repository `git diff --check`. The wrapper SHALL report success only if that check succeeds. The normalizer SHALL NOT suppress, ignore, or globally rewrite other whitespace errors.

This wrapper-level check supplements rather than replaces the mandatory post-archive checks required by `RULES.md`.

#### Scenario: EOF defect is the only archive whitespace problem

- **GIVEN** upstream archive produces only excess terminal blank lines in selected root specifications
- **WHEN** normalization removes that excess and `git diff --check` runs
- **THEN** the wrapper may complete successfully

#### Scenario: Another whitespace defect remains

- **GIVEN** archive output or another repository diff still contains a whitespace error after EOF normalization
- **WHEN** `git diff --check` runs
- **THEN** the wrapper returns non-zero
- **AND** the compatibility layer does not rewrite that unrelated defect into success

### Requirement: Archive compatibility uses only tracked repository tooling and existing runtime dependencies

The compatibility implementation SHALL be tracked in the repository, SHALL use the repository-supported Node runtime and standard-library/Git facilities, and SHALL add no new npm runtime or development dependency solely for EOF normalization. `npm ci` SHALL continue to restore the pinned OpenSpec dependency without requiring a patch to installed third-party files.

#### Scenario: Dependencies are restored on a clean workstation

- **WHEN** a supported Node environment runs `npm ci`
- **THEN** the pinned OpenSpec dependency is restored normally
- **AND** repository-local archive normalization remains available from tracked wrapper/helper files
- **AND** no manual edit under `node_modules` is required

#### Scenario: Future upstream OpenSpec already emits clean EOF output

- **GIVEN** a future separately reviewed dependency change causes upstream archive to emit exactly one terminal line terminator
- **WHEN** the repository-local normalizer runs
- **THEN** normalization is a no-op for already-clean root specs
- **AND** semantic archive output remains unchanged
