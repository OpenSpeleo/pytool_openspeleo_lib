# openspeleo_lib Agent Instructions

## Project overview

`openspeleo_lib` reads, writes, validates, and converts cave-survey data, using
`openspeleo_core` for native functionality.

- `openspeleo_lib/models.py` and `interfaces/`: survey models and format
  adapters.
- `openspeleo_lib/interfaces/ariane/`: Ariane encoding, decoding, and mappings.
- `openspeleo_lib/geojson.py` and `geo_utils.py`: geographic conversion.
- `openspeleo_lib/commands/`: the `openspeleo` CLI, conversion, and TML
  validation.
- `tests/`: model, interface, GeoJSON, and command regression coverage.

Preserve the coordinate-safety contract documented in `README.md`: explicit
coordinates stay authoritative, discrepancies above 500 metres raise
`InconsistentShotCoordinatesError`, and failed CLI conversion must neither
create nor overwrite output. Do not guess coordinate corrections.

Some private fixtures require `ARTIFACT_ENCRYPTION_KEY` through the existing
test environment. Never print or commit the key or decrypted survey data; report
fixture coverage that could not run without it.

## Temporary agent files

Keep agent plans, task lists, TODO tracking, progress notes, review notes, and
scratch lessons outside the repository tree, including all submodules. Use a
unique task directory under `/tmp/` (for example, create one with
`mktemp -d /tmp/speleodb-task.XXXXXX`) or another OS temporary directory whose
resolved path is outside every checkout.

Never create or update these working files inside the checkout, even in ignored
directories such as `tasks/`, `todos/`, or `plans/`. Never stage or commit them.
Existing tracked task and lesson files are historical references; do not append
new work to them. Keep durable product and architecture documentation in
`docs/`, without embedding task checklists or linking to temporary files. Before
an authorized commit, inspect the staged filenames and exclude all agent working
files.

## Working rules

- Read the relevant source, tests, and configuration before editing. Keep
  changes focused and preserve public behavior unless the task requires changing
  it.
- Inspect staged and unstaged changes separately before and after work. Preserve
  unrelated user work, existing branches, and submodule revisions.
- Do not stage, commit, push, open a PR, tag, or publish without explicit user
  authorization. Never install Git hooks or configure `core.hooksPath`.
- Run commands from this repository's root unless stated otherwise. In the
  monorepo, also follow the integration root's `AGENTS.md`; keep this repository
  usable independently and keep product changes in their owning repository.
- For documentation-only changes, run `prek run prettier --files AGENTS.md` and
  whitespace checks. For behavior changes, run focused regression tests and the
  relevant full suite. Report commands, results, and any missing prerequisites.

## Python development and verification

Python support and dependencies are defined in `pyproject.toml`; the current
minimum is Python 3.11 and CI covers Python 3.11 through 3.14. Keep code
compatible with that range. Follow the configured Ruff rules, use existing
package constants and helpers, and add regression coverage at the affected
parser, model, or command boundary.

Run the standalone checks from this package directory:

```bash
uv sync --frozen --all-extras --dev
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv run prek run --all-files
```

Prek may apply fixes; inspect its diff and rerun affected checks. For test runs,
prefer the CI command `uv run pytest` over legacy Make targets that may require
extra tools or perform cleanup. Preserve test fixtures; put generated test
outputs in temporary directories.

## Dependencies and integration

Keep this package's `pyproject.toml` and `uv.lock` authoritative for standalone
use. Run `uv lock` here after dependency changes. When working in the monorepo,
also refresh the root integration lock and validate the root frozen sync as
directed by its `AGENTS.md`. Do not add a uv workspace or monorepo-only paths to
standalone dependency declarations.

This package uses Flit. Preserve its package layout, CLI entry points, and
module-owned version metadata. For packaging changes, run `uv run flit build`;
do not use cleanup targets as routine verification or change release workflows
without a task requirement.
