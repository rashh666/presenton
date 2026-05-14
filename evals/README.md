# Presenton evals

Promptfoo + Python provider (`provider.py`) calling the same outline / structure / slide prompts as production (`prompts_*.py` + `prompts/*.txt`).

## Layout

| Path | Purpose |
|------|---------|
| `promptfooconfig.yaml` | **Single** config: env, provider, default assertions, and all test suites |
| `provider.py` | Builds LLM messages from each test’s `vars` (`stage`, `content`, …) |
| `tests/outline/` | Outline: `core.yaml` (regressions), `user-prompts.yaml` (CSV-derived scenarios) |
| `tests/structure/` | Layout selection given `outline_slides_json` |
| `tests/slide-content/` | Per-slide structured content |
| `tests/integration/` | End-to-end outline → structure → slide (same order as `presentation.py`); grade **`rendered_slide_bodies`** only for quality rubrics |
| `data/user-prompts/` | `Best.csv` / `Poor.csv` for sampling and outline realism tests |
| `scripts/` | Helpers (e.g. `sample_user_prompts_for_outline_eval.py`) |
| `schemas/layouts/` | Canonical `PresentationLayoutModel` JSON; tests use `layout_json: file://schemas/layouts/...` |
| `prompts/` | System/user templates + `provider_placeholder.txt` (promptfoo stub) |

Python modules at the eval root (`contracts.py`, `messages_builder.py`, …) stay importable by `provider.py` (`sys.path` includes this directory).

## Run

From repo root (or `evals/`):

```bash
cd evals
export OPENAI_API_KEY=...   # or keys for LLM in userConfig / env
npx promptfoo@latest eval -c promptfooconfig.yaml --no-cache --no-share
```

Validate only:

```bash
npx promptfoo@latest validate config -c promptfooconfig.yaml
```

### Focused runs

```bash
npx promptfoo@latest eval -c promptfooconfig.yaml --filter-pattern '\[outline\]' --no-cache
npx promptfoo@latest eval -c promptfooconfig.yaml --filter-pattern 'user-prompt-lib' --no-cache
npx promptfoo@latest eval -c promptfooconfig.yaml --filter-pattern '\[integration\]' --no-cache
```

### Integration output shape

`stage: integration` returns JSON with `outline`, `structure`, `slides` (per-slide metadata + `content`), and **`rendered_slide_bodies`**: an array of only the final structured slide dicts (what production would store as slide `content` plus embedded `__speaker_note__`). Assertions and `llm-rubric` prompts should reference **`rendered_slide_bodies`** so scores reflect the finished deck, not intermediate outline/structure text.

## Sample CSV rows for new outline cases

```bash
python3 evals/scripts/sample_user_prompts_for_outline_eval.py --seed 42 --best 5 --poor 5 --print-json
```

## Outline `vars` contract

See the header in `tests/outline/core.yaml`. Values align with `servers/fastapi/models/generate_presentation_request.py`, `enums/tone.py`, and `enums/verbosity.py`, plus eval-only `stage` and provider `web_search`.
