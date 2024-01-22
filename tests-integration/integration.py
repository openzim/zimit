import glob
import json
import os

import libzim.reader
from warcio import ArchiveIterator


def get_zim_main_entry(zimfile):
    zim_fh = libzim.reader.Archive(zimfile)
    return zim_fh.main_entry


def test_is_file():
    """Ensure ZIM file exists"""
    assert os.path.isfile("/output/isago.zim")


def test_zim_main_page():
    """Main page specified, http://isago.rskg.org/, was a redirect to https
    Ensure main page is the redirected page"""

    main_entry = get_zim_main_entry("/output/isago.zim")
    assert main_entry.is_redirect
    assert main_entry.get_redirect_entry().path == "isago.rskg.org/"


def test_user_agent():
    """Test that mobile user agent was used

    Check is done in WARC request records with custom Zimit and email suffix
    """

    found = False
    for warc in glob.glob("/output/.tmp*/collections/crawl-*/archive/*.warc.gz"):
        with open(warc, "rb") as fh:
            for record in ArchiveIterator(fh):
                if record.rec_type == "request":
                    print(record.http_headers)  # noqa: T201
                    ua = record.http_headers.get_header("User-Agent")
                    if ua:
                        assert "Mozilla" in ua
                        assert ua.endswith(" +Zimit test@example.com")
                        found = True

    # should find at least one
    assert found


def test_stats_output():
    with open("/output/crawl.json") as fh:
        assert json.loads(fh.read()) == {
            "crawled": 5,
            "pending": 0,
            "pendingPages": [],
            "total": 5,
            "failed": 0,
            "limit": {"max": 0, "hit": False},
        }
    with open("/output/warc2zim.json") as fh:
        assert json.loads(fh.read()) == {
            "written": 8,
            "total": 8,
        }
    with open("/output/stats.json") as fh:
        assert json.loads(fh.read()) == {
            "done": 8,
            "total": 8,
            "limit": {"max": 0, "hit": False},
        }
