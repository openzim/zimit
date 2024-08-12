from pathlib import Path

import requests

from zimit.constants import REQUESTS_TIMEOUT


def download_file(url: str, fpath: Path):
    """Download file from url to fpath with streaming"""
    with requests.get(url, timeout=REQUESTS_TIMEOUT, stream=True) as resp:
        resp.raise_for_status()
        with open(fpath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
