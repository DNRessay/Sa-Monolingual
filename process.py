import json
import re
import unicodedata

import numpy as np

from config import (
    RAW, CLEAN, STATE, GLOTLID, STRICT_LANGID, PARALLEL_REPO,
    MIN_WORDS, MAX_WORDS, MIN_CHARS, MAX_CHARS,
    MIN_ALPHA_RATIO, MAX_DIGIT_RATIO,
    LANGID_THRESHOLD, LANGID_THRESHOLD_STRICT,
)

URL_RE = re.compile(r"https?://\S+|www\.\S+|\S+@\S+\.\S+")
WS_RE = re.compile(r"\s+")
SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀ-ÖØ-ÞĐŊŠŽ])|\n+")
PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
BAD_RE = re.compile(r"(\|\s*\|)|(\.{4,})|(-{5,})|(<[^>]+>)")

_lid = None


def _load_lid():
    global _lid
    if _lid is None:
        import fasttext
        from huggingface_hub import hf_hub_download
        path = hf_hub_download("cis-lmu/glotlid", "model.bin")
        _lid = fasttext.load_model(path)
    return _lid


def normalize(text):
    text = unicodedata.normalize("NFKC", text)
    text = URL_RE.sub(" ", text)
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    return WS_RE.sub(" ", text).strip()


def dedup_key(s):
    s = PUNCT_RE.sub("", s.lower())
    return WS_RE.sub(" ", s).strip()


def hash64(s):
    import hashlib
    return int.from_bytes(hashlib.blake2b(s.encode("utf-8"), digest_size=8).digest(), "big")


def split_sentences(text):
    for part in SENT_RE.split(text):
        part = part.strip()
        if part:
            yield part


def quality_ok(s):
    if not (MIN_CHARS <= len(s) <= MAX_CHARS):
        return False
    words = s.split()
    if not (MIN_WORDS <= len(words) <= MAX_WORDS):
        return False
    if BAD_RE.search(s):
        return False
    alpha = sum(c.isalpha() for c in s)
    digit = sum(c.isdigit() for c in s)
    if alpha / len(s) < MIN_ALPHA_RATIO:
        return False
    if digit / len(s) > MAX_DIGIT_RATIO:
        return False
    if len(set(words)) / len(words) < 0.4:
        return False
    return True


def langid_ok(model, s, label, threshold):
    labels, probs = model.predict(s.replace("\n", " "), k=1)
    return labels[0] == f"__label__{label}" and probs[0] >= threshold


def build_exclusion(lang, configs=None):
    """Hashes of sentences already used in the parallel corpus, so we don't repeat them."""
    from datasets import load_dataset

    STATE.mkdir(parents=True, exist_ok=True)
    cache = STATE / f"exclude.{lang}.npy"
    if cache.exists():
        return np.load(cache)

    hashes = []
    for cfg in configs or [f"{lang}-en", f"en-{lang}", lang]:
        try:
            ds = load_dataset(PARALLEL_REPO, cfg, split="train", streaming=True)
        except Exception:
            continue
        for row in ds:
            val = row.get(lang) or row.get("target") or row.get("tgt")
            if not val and "translation" in row:
                val = row["translation"].get(lang)
            if val:
                hashes.append(hash64(dedup_key(normalize(val))))
        break

    arr = np.array(sorted(set(hashes)), dtype=np.uint64)
    np.save(cache, arr)
    print(f"  exclusion set for {lang}: {len(arr)} sentences from {PARALLEL_REPO}")
    return arr


def in_exclusion(arr, h):
    if arr.size == 0:
        return False
    i = np.searchsorted(arr, np.uint64(h))
    return i < arr.size and arr[i] == np.uint64(h)


def process_lang(lang, skip_langid=False, skip_exclusion=False, max_out=None,
                  shard_iter=None, after_shard=None):
    """
    shard_iter: optional iterable of (source_name, local_path) pairs already
    downloaded to disk. When given, RAW/lang is never scanned -- this lets a
    caller stream one shard down (e.g. from S3) at a time instead of mirroring
    an entire language locally first, which can exceed Lambda's /tmp limit for
    high-resource languages. Falls back to scanning RAW/lang when omitted, for
    local/Colab use.
    after_shard: optional callback(local_path) invoked once a shard's lines
    are fully consumed, so the caller can delete it immediately and keep peak
    disk usage to one shard at a time.
    """
    CLEAN.mkdir(parents=True, exist_ok=True)
    out_path = CLEAN / f"{lang}.jsonl"

    label = GLOTLID[lang]
    threshold = LANGID_THRESHOLD_STRICT if lang in STRICT_LANGID else LANGID_THRESHOLD
    model = None if skip_langid else _load_lid()
    exclude = np.array([], dtype=np.uint64) if skip_exclusion else build_exclusion(lang)

    seen = set()
    kept = 0
    stats = {}

    if shard_iter is None:
        src_dir = RAW / lang
        if not src_dir.exists():
            print(f"! no raw data for {lang}")
            return 0

        def _default_iter():
            for shard in sorted(src_dir.rglob("*.jsonl")):
                # local CLI writes flat files (source.jsonl); the Lambda fetch
                # path writes numbered parts under a source/ subdirectory
                source = shard.parent.name if shard.parent != src_dir else shard.stem
                yield source, shard

        shard_iter = _default_iter()

    with out_path.open("w", encoding="utf-8") as out:
        for source, shard in shard_iter:
            s_kept = stats.get(source, 0)
            with open(shard, encoding="utf-8") as f:
                for line in f:
                    try:
                        text = json.loads(line)["text"]
                    except Exception:
                        continue
                    for sent in split_sentences(text):
                        sent = normalize(sent)
                        if not quality_ok(sent):
                            continue
                        h = hash64(dedup_key(sent))
                        if h in seen:
                            continue
                        if in_exclusion(exclude, h):
                            continue
                        if model and not langid_ok(model, sent, label, threshold):
                            continue
                        seen.add(h)
                        out.write(json.dumps(
                            {"text": sent, "lang": lang, "source": source},
                            ensure_ascii=False) + "\n")
                        kept += 1
                        s_kept += 1
                        if max_out and kept >= max_out:
                            stats[source] = s_kept
                            print(f"  {lang}: {kept} (cap reached)")
                            if after_shard:
                                after_shard(shard)
                            return kept
            stats[source] = s_kept
            print(f"  {source}: {s_kept} so far")
            if after_shard:
                after_shard(shard)

    print(f"{lang}: {kept} unique sentences -> {out_path}")
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / f"{lang}.stats.json").write_text(json.dumps(stats, indent=2))
    return kept


if __name__ == "__main__":
    import argparse
    from config import LANGS

    p = argparse.ArgumentParser()
    p.add_argument("--langs", nargs="*", default=LANGS)
    p.add_argument("--skip-langid", action="store_true")
    p.add_argument("--skip-exclusion", action="store_true")
    p.add_argument("--max", type=int, default=None)
    a = p.parse_args()
    for lang in a.langs:
        process_lang(lang, a.skip_langid, a.skip_exclusion, a.max)
