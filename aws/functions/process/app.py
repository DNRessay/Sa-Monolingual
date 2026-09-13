import os
from pathlib import Path

import process as process_mod
from common import download_prefix, download_file_if_exists, upload_file

BUCKET = os.environ["DATA_BUCKET"]


def handler(event, context):
    """
    event: {"lang": "zu", "max_out": 0}   # max_out=0 means no cap
    returns: {"lang", "kept", "shards_downloaded"}
    """
    lang = event["lang"]
    max_out = int(event.get("max_out", 0)) or None

    tmp_raw = Path("/tmp/raw")
    tmp_clean = Path("/tmp/clean")
    tmp_state = Path("/tmp/state")
    for d in (tmp_raw, tmp_clean, tmp_state):
        d.mkdir(parents=True, exist_ok=True)

    # redirect the process module's paths onto /tmp for this invocation
    process_mod.RAW = tmp_raw
    process_mod.CLEAN = tmp_clean
    process_mod.STATE = tmp_state

    shards = download_prefix(BUCKET, f"raw/{lang}/", tmp_raw / lang)

    # reuse a previously-built exclusion cache if we have one, instead of
    # re-streaming the parallel corpus every single invocation
    exclude_key = f"state/exclude.{lang}.npy"
    download_file_if_exists(BUCKET, exclude_key, tmp_state / f"exclude.{lang}.npy")

    kept = process_mod.process_lang(lang, skip_langid=False, skip_exclusion=False, max_out=max_out)

    clean_path = tmp_clean / f"{lang}.jsonl"
    if clean_path.exists():
        upload_file(BUCKET, clean_path, f"clean/{lang}.jsonl")

    cache_path = tmp_state / f"exclude.{lang}.npy"
    if cache_path.exists():
        upload_file(BUCKET, cache_path, exclude_key)

    return {"lang": lang, "kept": kept, "shards_downloaded": shards}
