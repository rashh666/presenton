# Presenton evals

[Promptfoo](https://www.promptfoo.dev/) runs tests against a **Python provider** (`provider.py`) that calls the same outline / structure / slide prompts as production (`messages_builder.py` + `prompts/*.txt`).

## What runs today

The default config only loads **outline** tests. Other suites live in the repo so you can wire them in when you are ready.

| Eval area | In `promptfooconfig.yaml` now |
|-----------|-------------------------------|
| Outline generation | ✓ |
| Structure (layout selection) | — |
| Slide content | — |
| Integration (outline → structure → slides) | — |

---

## Prerequisites

### 1. Promptfoo (CLI)

Install globally so `promptfoo` is on your `PATH`:

```bash
npm install -g promptfoo
```

If you prefer not to install globally, use `npx promptfoo@latest` instead of `promptfoo` in the commands below.

### 2. Python environment (required for `provider.py`)

The provider uses **Python 3.11** and dependencies from `evals/pyproject.toml` (notably `llmai`). From the **repo root**:

```bash
cd evals
uv sync
source .venv/bin/activate
export PROMPTFOO_PYTHON="$PWD/.venv/bin/python"
```

On Windows (PowerShell): `.\.venv\Scripts\Activate.ps1` — on Windows you can set `PROMPTFOO_PYTHON` to the full path of `.venv\Scripts\python.exe` instead.

**Important:** Promptfoo runs the Python provider with the interpreter in **`PROMPTFOO_PYTHON`** when set (recommended). Otherwise it uses whatever `python3` is on your `PATH`, so activate the venv above or exports will not match the env where `llmai` is installed.

### 3. API keys and model settings

`promptfooconfig.yaml` sets `LLM` and `OPENAI_MODEL` for the default setup. You must export the matching API key in your shell (see `llm_env.py` for other providers).

**OpenAI (default in config):**

```bash
export OPENAI_API_KEY="sk-..."
# Optional overrides (see llm_env.py):
# export PRESENTON_MODEL="gpt-4o"
```

If you change `LLM` in the config or in the shell (e.g. `anthropic`), set the corresponding key (`ANTHROPIC_API_KEY`, etc.) instead.

You can also load keys from the app’s `userConfig.json` via `env_sync` if `USER_CONFIG_PATH` / `APP_DATA_DIRECTORY` point at your Presenton data directory—same behavior as the server.

---

## Run evaluations

Always run from the **`evals/`** directory so relative paths in the config resolve.

```bash
cd evals
source .venv/bin/activate   # if not already active
export PROMPTFOO_PYTHON="$PWD/.venv/bin/python"
export OPENAI_API_KEY="sk-..."
promptfoo eval -c promptfooconfig.yaml --no-cache --no-share
```

- **`-c` / `--config`** — Path to your config file. Use it when the file is not named `promptfooconfig.yaml` or when you keep multiple configs (e.g. `promptfooconfig.structure.yaml`).
- **`--no-cache`** — Skips disk cache so you see fresh model outputs.
- **`--no-share`** — Avoids uploading results to promptfoo cloud (good default for private keys).

Validate the config and provider wiring without calling the model (as far as `validate config` allows):

```bash
cd evals
export PROMPTFOO_PYTHON="$PWD/.venv/bin/python"
promptfoo validate config -c promptfooconfig.yaml
```

### Smaller runs

```bash
promptfoo eval -c promptfooconfig.yaml --filter-pattern '\[(best|poor)\]' --no-cache
promptfoo eval -c promptfooconfig.yaml --filter-pattern '\[best\]' --no-cache
promptfoo eval -c promptfooconfig.yaml --filter-pattern '\[poor\]' --no-cache
```

---

## View results in the browser

After an `eval`, start the local UI (latest results by default):

```bash
cd evals
export PROMPTFOO_PYTHON="$PWD/.venv/bin/python"
promptfoo view
```

Useful flags:

- **`promptfoo view -y`** — Skip prompts and open the browser.
- **`promptfoo view -n`** — Do not auto-open a browser tab.
- **`promptfoo view -p 15500`** — Pick a port (default is `15500`).

There is no separate “evaluation” subcommand name—**`eval`** runs tests and **`view`** opens them.

---

## How it works

1. **`promptfooconfig.yaml`** — Declares env defaults, the stub prompt, the custom provider, optional `defaultTest` assertions, and the **`tests:`** list (YAML files under `tests/`).
2. **`provider.py`** — For each test case, promptfoo passes `vars` into the provider. The `stage` variable selects the pipeline:
   - **`outline`** — User brief → structured outline JSON.
   - **`structure`** — Needs `outline_slides_json` (and related vars); picks per-slide layouts.
   - **`slide_content`** — Needs `slide_markdown`, `response_schema_json`, etc.
   - **`integration`** — Full chain; needs `layout_json` and runs outline → structure → per-slide content (see comments in `provider.py`).

3. **Assertions** — Defined per test or via `defaultTest` (e.g. “valid JSON”). `llm-rubric` assertions need a grader model/API access as promptfoo documents.

### Evaluating structure, slide content, or integration

The YAML suites already exist:

| Path | `stage` in tests | Notes |
|------|------------------|--------|
| `tests/outline/core.yaml` | `outline` | Default config includes this only. |
| `tests/structure/*.yaml` | `structure` | Requires `outline_slides_json` (and `n_slides` / layout keys as in each file). |
| `tests/slide-content/unit.yaml` | `slide_content` | Requires slide markdown + response schema vars. |
| `tests/integration/flow.yaml` | `integration` | End-to-end; rubrics should target **`rendered_slide_bodies`** when grading final slide content. |

To run them, add the corresponding `file://tests/...` entries under **`tests:`** in your config (or a copy of the config you pass with **`-c`**). You can keep a second file, e.g. `promptfooconfig.full.yaml`, that lists outline + structure + slide + integration, and switch with `-c`.

---

## Repo layout

| Path | Purpose |
|------|---------|
| `promptfooconfig.yaml` | Default entrypoint: env, provider, assertions, **outline-only** `tests` list |
| `provider.py` | Builds LLM messages from each test’s `vars` and `stage` |
| `tests/outline/core.yaml` | Twelve outline tests (six from `Best.csv`, six from `Poor.csv`) |
| `tests/structure/` | Layout selection given `outline_slides_json` |
| `tests/slide-content/` | Per-slide structured content |
| `tests/integration/` | End-to-end outline → structure → slide |
| `data/user-prompts/` | `Best.csv` / `Poor.csv` — source library text for curated outline tests |
| `schemas/layouts/` | Canonical layout JSON; tests use `layout_json: file://schemas/layouts/...` |
| `prompts/` | System/user templates + `provider_placeholder.txt` |

Shared Python modules (`contracts.py`, `messages_builder.py`, …) live next to `provider.py` and are importable because the provider adds this directory to `sys.path`.

---

## Outline `vars` contract

See the header comment in `tests/outline/core.yaml`. Values align with `servers/fastapi/models/generate_presentation_request.py`, tone/verbosity enums, plus eval-only `stage` and `web_search` for the provider.
