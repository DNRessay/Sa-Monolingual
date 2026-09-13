import argparse

import fetch
import process
import push
from config import LANGS, HF_REPO, LANG_NAMES


def main():
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=["fetch", "process", "push", "all", "report"])
    p.add_argument("--langs", nargs="*", default=LANGS)
    p.add_argument("--sources", nargs="*", default=None)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--max", type=int, default=None)
    p.add_argument("--repo", default=HF_REPO)
    p.add_argument("--force", action="store_true")
    p.add_argument("--skip-langid", action="store_true")
    p.add_argument("--skip-exclusion", action="store_true")
    p.add_argument("--private", action="store_true")
    a = p.parse_args()

    if a.stage in ("fetch", "all"):
        fetch.run(a.langs, a.sources, a.limit, a.force)
    if a.stage in ("process", "all"):
        for lang in a.langs:
            process.process_lang(lang, a.skip_langid, a.skip_exclusion, a.max)
    if a.stage in ("push", "all"):
        push.main(a.langs, a.repo, a.private)
    if a.stage == "report":
        from config import CLEAN
        print(f"{'language':<12}{'rows':>14}  target 1M")
        for lang in a.langs:
            f = CLEAN / f"{lang}.jsonl"
            n = push.count(f) if f.exists() else 0
            print(f"{LANG_NAMES[lang]:<12}{n:>14,}  {'ok' if n >= 1_000_000 else 'short'}")


if __name__ == "__main__":
    main()
