from __future__ import annotations


def chunked(items, size: int):
    bucket = []
    for item in items:
        bucket.append(item)
        if len(bucket) >= size:
            yield bucket
            bucket = []
    if bucket:
        yield bucket
