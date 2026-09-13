import os
from pathlib import Path

import boto3

import process as process_mod
from common import download_file_if_exists, upload_file, delete_prefix

BUCKET = os.environ["DATA_BUCKET"]
_s3 = boto3.client("s3")


def _stream_shards(lang, tmp_dir, counter):
    """Yields (source_name, local_path) one at a time, downloading each just
    before it's needed. The caller deletes each file once it's been consumed
    (see after_shard below) -- this is what keeps peak /tmp usage to roughly
    one shard's size instead of an entire language's raw volume, which can
    exceed Lambda's 10GB ephemeral storage for high-resource languages."""
    prefix = f"raw/{lang}/"
    paginator = _s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            rel = key[len(prefix):].lstrip("/")
            if not rel:
                continue
            # Lambda fetch writes raw/{lang}/{source}/part-*.jsonl
            parts = rel.split("/")
            source = parts[0] if len(parts) > 1 else Path(rel).stem
            local_path = tmp_dir / rel
            local_path.parent.mkdir(parents=True, exist_ok=True)
            _s3.download_file(BUCKET, key, str(local_path))
            counter["n"] += 1
            yield source, local_path


def handler(event, context):
    """
    event: {"lang": "zu", "max_out": 0}   # max_out=0 means no cap
    returns: {"lang", "kept", "shards_downloaded", "raw_shards_deleted"}
    """
    lang = event["lang"]
    max_out = int(event.get("max_out", 0)) or None

    tmp_raw = Path("/tmp/raw") / lang
    tmp_clean = Path("/tmp/clean")
    tmp_state = Path("/tmp/state")
    for d in (tmp_raw, tmp_clean, tmp_state):
        d.mkdir(parents=True, exist_ok=True)

    process_mod.RAW = Path("/tmp/raw")
    process_mod.CLEAN = tmp_clean
    process_mod.STATE = tmp_state

    # reuse a previously-built exclusion cache if we have one, instead of
    # re-streaming the parallel corpus every single invocation
    exclude_key = f"state/exclude.{lang}.npy"
    download_file_if_exists(BUCKET, exclude_key, tmp_state / f"exclude.{lang}.npy")

    shard_count = {"n": 0}

    def _after_shard(path):
        try:
            Path(path).unlink(missing_ok=True)
        except Exception:
            pass

    kept = process_mod.process_lang(
        lang, skip_langid=False, skip_exclusion=False, max_out=max_out,
        shard_iter=_stream_shards(lang, tmp_raw, shard_count),
        after_shard=_after_shard,
    )

    clean_path = tmp_clean / f"{lang}.jsonl"
    uploaded = clean_path.exists()
    if uploaded:
        upload_file(BUCKET, clean_path, f"clean/{lang}.jsonl")

    cache_path = tmp_state / f"exclude.{lang}.npy"
    if cache_path.exists():
        upload_file(BUCKET, cache_path, exclude_key)

    # Raw shards are only ever needed until this point. Delete them now rather
    # than waiting on the bucket's lifecycle rule -- only once the clean file
    # genuinely made it to S3.
    raw_deleted = 0
    if uploaded:
        raw_deleted = delete_prefix(BUCKET, f"raw/{lang}/")

    return {
        "lang": lang, "kept": kept,
        "shards_downloaded": shard_count["n"],
        "raw_shards_deleted": raw_deleted,
    }
