from pathlib import Path

import boto3

_s3 = boto3.client("s3")


def upload_file(bucket, local_path, key):
    _s3.upload_file(str(local_path), bucket, key)


def download_file_if_exists(bucket, key, local_path):
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _s3.download_file(bucket, key, str(local_path))
        return True
    except Exception:
        return False


def download_prefix(bucket, prefix, local_dir):
    """Mirrors every object under s3://bucket/prefix into local_dir. Returns count."""
    local_dir = Path(local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)
    paginator = _s3.get_paginator("list_objects_v2")
    n = 0
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            rel = key[len(prefix):].lstrip("/")
            if not rel:
                continue
            dest = local_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            _s3.download_file(bucket, key, str(dest))
            n += 1
    return n
