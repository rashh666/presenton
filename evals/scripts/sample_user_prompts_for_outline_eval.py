#!/usr/bin/env python3
"""
Reproducibly sample rows from evals/data/user-prompts/Best.csv and Poor.csv for outline evals.

Example:
  uv run python evals/scripts/sample_user_prompts_for_outline_eval.py --seed 42 --best 5 --poor 5
  uv run python evals/scripts/sample_user_prompts_for_outline_eval.py --seed 42 --best 5 --poor 5 --print-yaml-vars
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

_EVALS = Path(__file__).resolve().parents[1]
BEST_CSV = _EVALS / "data" / "user-prompts" / "Best.csv"
POOR_CSV = _EVALS / "data" / "user-prompts" / "Poor.csv"


def load_best_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            text = (r.get("prompt_text") or "").strip()
            if not text:
                text = (r.get("workflow_description") or "").strip()
            if not text:
                continue
            rows.append(
                {
                    "id": r.get("id", "").strip(),
                    "prompt_text": text,
                    "audience_category": (r.get("audience_category") or "").strip(),
                }
            )
    return rows


def load_poor_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            text = (r.get("poor_prompt") or "").strip()
            if not text:
                continue
            rows.append({"id": str(r.get("id", "")).strip(), "poor_prompt": text})
    return rows


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--best", type=int, default=5, help="How many rows to sample from Best.csv")
    p.add_argument("--poor", type=int, default=5, help="How many rows to sample from Poor.csv")
    p.add_argument("--print-json", action="store_true", help="Print sampled rows as JSON")
    p.add_argument(
        "--print-yaml-vars",
        action="store_true",
        help="Print minimal YAML snippets (content blocks) for hand-paste into promptfoo tests",
    )
    args = p.parse_args()

    best_all = load_best_rows(BEST_CSV)
    poor_all = load_poor_rows(POOR_CSV)
    if len(best_all) < args.best:
        print(f"Not enough Best rows: have {len(best_all)}, need {args.best}", file=sys.stderr)
        return 1
    if len(poor_all) < args.poor:
        print(f"Not enough Poor rows: have {len(poor_all)}, need {args.poor}", file=sys.stderr)
        return 1

    rng = random.Random(args.seed)
    best_pick = rng.sample(best_all, args.best)
    poor_pick = rng.sample(poor_all, args.poor)

    out = {
        "seed": args.seed,
        "best": best_pick,
        "poor": poor_pick,
    }
    if args.print_json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    elif args.print_yaml_vars:
        print("# --- Best (content = library prompt_text) ---")
        for row in best_pick:
            bid = row["id"]
            print(f"\n# best {bid}")
            print(f"library_id: {bid}")
            print("prompt_tier: best")
            print("content: |")
            for line in row["prompt_text"].splitlines():
                print(f"  {line}")
            if row.get("audience_category"):
                print("additional_context: |")
                print(f"  Audience category (library metadata): {row['audience_category']}.")
        print("\n# --- Poor (content = user-typed vague prompt only) ---")
        for row in poor_pick:
            pid = row["id"]
            print(f"\n# poor {pid}")
            print(f"library_id: poor-{pid}")
            print("prompt_tier: poor")
            print("content: |")
            for line in row["poor_prompt"].splitlines():
                print(f"  {line}")
    else:
        print(f"Sampled {args.best} best + {args.poor} poor (seed={args.seed})")
        print("\nBest ids:", ", ".join(r["id"] for r in best_pick))
        print("Poor ids:", ", ".join(r["id"] for r in poor_pick))
        print("\nRe-run with --print-json or --print-yaml-vars for full text.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
