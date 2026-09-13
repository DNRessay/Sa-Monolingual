import os
from pathlib import Path

import config as cfg
import fetch as fetch_mod
from common import upload_file

BUCKET = os.environ["DATA_BUCKET"]


def handler(event, context):
    """
    event: {"lang": "zu", "source": "madlad400", "skip": 0, "chunk": 200000}
    returns: {"lang", "source", "count", "next_skip", "exhausted"}

    Step Functions re-invokes this with skip=next_skip until exhausted=true or
    an iteration cap is hit -- see aws/statemachine.asl.json.
    """
    lang = event["lang"]
    source_name = event["source"]
    skip = int(event.get("skip", 0))
    chunk = int(event.get("chunk", 200_000))

    src = next((s for s in cfg.SOURCES if s["name"] == source_name), None)
    if src is None or lang not in src["configs"]:
        return {"lang": lang, "source": source_name, "count": 0, "next_skip": skip, "exhausted": True}

    tmp_dir = Path("/tmp/raw") / lang / source_name
    tmp_dir.mkdir(parents=True, exist_ok=True)
    part_name = f"part-{skip:012d}.jsonl"
    local_path = tmp_dir / part_name

    if src["kind"] == "hf":
        count, exhausted = fetch_mod.fetch_hf(src, lang, limit=chunk, skip=skip, out_path=local_path)
    else:
        # small fixed-size archives -- always a single pass, ignore skip
        count = fetch_mod.fetch_url(src, lang, limit=chunk, out_path=local_path)
        exhausted = True

    if count > 0:
        upload_file(BUCKET, local_path, f"raw/{lang}/{source_name}/{part_name}")

    return {
        "lang": lang,
        "source": source_name,
        "count": count,
        "next_skip": skip + count,
        "exhausted": exhausted or count == 0,
    }
