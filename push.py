import json
import os

from config import CLEAN, HF_REPO, LANGS, LANG_NAMES


def count(path):
    n = 0
    with path.open(encoding="utf-8") as f:
        for _ in f:
            n += 1
    return n


def push_lang(lang, repo=HF_REPO, private=False, shard_rows=500_000):
    from datasets import Dataset

    path = CLEAN / f"{lang}.jsonl"
    if not path.exists():
        print(f"! nothing to push for {lang}")
        return 0

    total = count(path)
    if total == 0:
        print(f"! {lang} is empty")
        return 0

    print(f"{lang}: {total} rows -> {repo}:{lang}")

    def gen():
        with path.open(encoding="utf-8") as f:
            for line in f:
                yield json.loads(line)

    ds = Dataset.from_generator(gen)
    ds.push_to_hub(repo, config_name=lang, private=private, max_shard_size="400MB")
    return total


def main(langs, repo, private):
    if not os.environ.get("HF_TOKEN"):
        raise SystemExit("set HF_TOKEN first")
    report = {}
    for lang in langs:
        try:
            report[lang] = push_lang(lang, repo, private)
        except Exception as e:
            print(f"! {lang}: {type(e).__name__}: {e}")
    print("\nlanguage  rows")
    for lang, n in report.items():
        print(f"{LANG_NAMES[lang]:<12} {n:>12,}")
    return report


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--langs", nargs="*", default=LANGS)
    p.add_argument("--repo", default=HF_REPO)
    p.add_argument("--private", action="store_true")
    a = p.parse_args()
    main(a.langs, a.repo, a.private)
