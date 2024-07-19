import glob
import json
import os

from warcio import ArchiveIterator
from zimscraperlib.zim import Archive


def test_is_file():
    """Ensure ZIM file exists"""
    assert os.path.isfile("/output/isago.zim")


def test_zim_main_page():
    """Main page specified, http://isago.rskg.org/, was a redirect to https
    Ensure main page is the redirected page"""

    main_entry = Archive("/output/isago.zim").main_entry
    assert main_entry.is_redirect
    assert main_entry.get_redirect_entry().path == "isago.rskg.org/"


def test_zim_scraper():
    """Main page specified, http://isago.rskg.org/, was a redirect to https
    Ensure main page is the redirected page"""

    zim_fh = Archive("/output/isago.zim")
    scraper = zim_fh.get_text_metadata("Scraper")
    assert "zimit " in scraper
    assert "warc2zim " in scraper
    assert "Browsertrix crawler " in scraper


def test_files_list():
    """Check that expected files are present in the ZIM at proper path"""
    zim_fh = Archive("/output/isago.zim")
    for expected_entry in [
        "_zim_static/__wb_module_decl.js",
        "_zim_static/wombat.js",
        "_zim_static/wombatSetup.js",
        "isago.rskg.org/",
        "isago.rskg.org/a-propos",
        "isago.rskg.org/conseils",
        "isago.rskg.org/faq",
        "isago.rskg.org/static/favicon256.png",
        "isago.rskg.org/static/tarifs-isago.pdf",
        "maxcdn.bootstrapcdn.com/bootstrap/4.0.0/css/bootstrap.min.css",
    ]:
        assert zim_fh.get_content(expected_entry)


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
            "written": 7,
            "total": 7,
        }
    with open("/output/stats.json") as fh:
        assert json.loads(fh.read()) == {
            "done": 7,
            "total": 7,
            "limit": {"max": 0, "hit": False},
        }
