# bootstrap-openspec-baseline

Establish normative OpenSpec baseline for the existing diagnostic application without changing runtime behavior.

## Windows OpenSpec workflow

Install the pinned repository-local OpenSpec 1.6.0 dependency with `npm ci`.
Then run `./openspec.cmd list` and
`./openspec.cmd validate --all --strict`. The wrapper resolves
`node_modules/.bin/openspec.cmd` relative to itself, so it can be invoked from
another working directory and does not require a global OpenSpec installation.
