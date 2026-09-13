"""Builds the JSON input for a Step Functions execution.

Run from the repo root:
    python aws/generate_pairs.py --out stepfunctions-input.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import SOURCES, LANGS  # noqa: E402


def build(langs=None):
    langs = langs or LANGS
    pairs = [
        {"lang": lang, "source": src["name"]}
        for lang in langs
        for src in SOURCES
        if lang in src["configs"]
    ]
    return {"pairs": pairs, "langs": langs}


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--langs", nargs="*", default=None)
    p.add_argument("--out", default="stepfunctions-input.json")
    a = p.parse_args()

    data = build(a.langs)
    Path(a.out).write_text(json.dumps(data, indent=2))
    print(f"{len(data['pairs'])} (lang, source) pairs, {len(data['langs'])} languages -> {a.out}")
