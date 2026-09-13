import io
import json
import os
import tarfile
import time
import gzip

import requests

from config import RAW, STATE, SOURCES


def _state_path(lang, source):
    STATE.mkdir(parents=True, exist_ok=True)
    return STATE / f"{lang}.{source}.done"


def _out_path(lang, source):
    d = RAW / lang
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{source}.jsonl"


def fetch_hf(src, lang, limit=None, skip=0, out_path=None):
    """Streams up to `limit` rows starting at `skip`. Returns (count, exhausted).

    exhausted=True means the underlying stream ended before `limit` was reached
    (or no limit was given at all) -- the caller doesn't need to come back for more.
    """
    from datasets import load_dataset

    cfg = src["configs"].get(lang)
    if cfg is None:
        return 0, True

    kwargs = {"streaming": True, "split": src.get("split", "train")}
    if src.get("trust"):
        kwargs["trust_remote_code"] = True
    if src.get("data_dir_tpl"):
        kwargs["data_dir"] = src["data_dir_tpl"]

    ds = load_dataset(src["repo"], **kwargs) if cfg == "default" else load_dataset(src["repo"], cfg, **kwargs)
    if skip:
        ds = ds.skip(skip)

    field = src["field"]
    out = out_path or _out_path(lang, src["name"])
    n = 0
    exhausted = True
    with open(out, "w", encoding="utf-8") as f:
        for row in ds:
            text = row.get(field)
            if not text:
                for alt in ("text", "content", "raw_content", "sentence", "document"):
                    text = row.get(alt)
                    if text:
                        break
            if not text:
                continue
            f.write(json.dumps({"text": text}, ensure_ascii=False) + "\n")
            n += 1
            if limit and n >= limit:
                exhausted = False  # stream may have more; we stopped because of the cap
                break
    return n, exhausted


def _iter_leipzig_sentences(blob):
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        for m in tar.getmembers():
            if not m.name.endswith("-sentences.txt"):
                continue
            fh = tar.extractfile(m)
            if fh is None:
                continue
            for line in io.TextIOWrapper(fh, encoding="utf-8", errors="ignore"):
                parts = line.rstrip("\n").split("\t", 1)
                if len(parts) == 2 and parts[1].strip():
                    yield parts[1].strip()


def fetch_url(src, lang, limit=None, out_path=None):
    """One-shot: these are small fixed-size archives, no skip/resume needed."""
    urls = src["configs"].get(lang) or []
    out = out_path or _out_path(lang, src["name"])
    n = 0
    with open(out, "w", encoding="utf-8") as f:
        for url in urls:
            try:
                r = requests.get(url, timeout=300)
                r.raise_for_status()
            except Exception as e:
                print(f"  ! {url}: {e}")
                continue
            blob = r.content
            if url.endswith(".tar.gz"):
                it = _iter_leipzig_sentences(blob)
            elif url.endswith(".gz"):
                it = (l.strip() for l in gzip.decompress(blob).decode("utf-8", "ignore").splitlines())
            else:
                it = (l.strip() for l in blob.decode("utf-8", "ignore").splitlines())
            for s in it:
                if not s:
                    continue
                f.write(json.dumps({"text": s}, ensure_ascii=False) + "\n")
                n += 1
                if limit and n >= limit:
                    return n
    return n


def run(langs, only=None, limit=None, force=False):
    """Local/Colab CLI driver -- single pass per (lang, source), no chunking."""
    totals = {}
    for lang in langs:
        for src in SOURCES:
            if only and src["name"] not in only:
                continue
            if lang not in src["configs"]:
                continue
            marker = _state_path(lang, src["name"])
            if marker.exists() and not force:
                print(f"= {lang}/{src['name']} already fetched")
                continue
            print(f"> {lang}/{src['name']}")
            t0 = time.time()
            try:
                if src["kind"] == "hf":
                    n, _ = fetch_hf(src, lang, limit)
                else:
                    n = fetch_url(src, lang, limit)
            except Exception as e:
                print(f"  ! failed: {type(e).__name__}: {e}")
                continue
            marker.write_text(str(n))
            totals[(lang, src["name"])] = n
            print(f"  {n} records in {time.time() - t0:.0f}s")
    return totals


if __name__ == "__main__":
    import argparse
    from config import LANGS

    p = argparse.ArgumentParser()
    p.add_argument("--langs", nargs="*", default=LANGS)
    p.add_argument("--sources", nargs="*", default=None)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--force", action="store_true")
    a = p.parse_args()
    run(a.langs, a.sources, a.limit, a.force)
