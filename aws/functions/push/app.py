import os
from pathlib import Path

import push as push_mod
from common import download_file_if_exists

BUCKET = os.environ["DATA_BUCKET"]


def handler(event, context):
    """
    event: {"lang": "zu"}
    returns: {"lang", "rows", "pushed"}
    """
    lang = event["lang"]

    tmp_clean = Path("/tmp/clean")
    tmp_clean.mkdir(parents=True, exist_ok=True)
    push_mod.CLEAN = tmp_clean

    local_path = tmp_clean / f"{lang}.jsonl"
    found = download_file_if_exists(BUCKET, f"clean/{lang}.jsonl", local_path)
    if not found:
        return {"lang": lang, "rows": 0, "pushed": False}

    if not os.environ.get("HF_TOKEN"):
        raise RuntimeError("HF_TOKEN is not set on this function")

    rows = push_mod.push_lang(lang, repo=push_mod.HF_REPO, private=False)
    return {"lang": lang, "rows": rows, "pushed": rows > 0}
