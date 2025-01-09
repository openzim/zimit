import glob
import json
import os
from pathlib import Path

from warcio import ArchiveIterator
from zimscraperlib.zim import Archive


def test_is_file():
    """Ensure ZIM file exists"""
    assert os.path.isfile("/output/tests_en_onepage.zim")


def test_zim_main_page():
    """Main page specified, http://website.test.openzim.org/http-return-codes.html,
    was a redirect to https
    Ensure main page is the redirected page"""

    main_entry = Archive("/output/tests_en_onepage.zim").main_entry
    assert main_entry.is_redirect
    assert (
        main_entry.get_redirect_entry().path
        == "website.test.openzim.org/http-return-codes.html"
    )


def test_zim_scraper():
    """Check content of scraper metadata"""

    zim_fh = Archive("/output/tests_en_onepage.zim")
    scraper = zim_fh.get_text_metadata("Scraper")
    assert "zimit " in scraper
    assert "warc2zim " in scraper
    assert "Browsertrix-Crawler " in scraper


def test_files_list():
    """Check that expected files are present in the ZIM at proper path"""
    zim_fh = Archive("/output/tests_en_onepage.zim")
    for expected_entry in [
        "_zim_static/__wb_module_decl.js",
        "_zim_static/wombat.js",
        "_zim_static/wombatSetup.js",
        "website.test.openzim.org/http-return-codes.html",
        "website.test.openzim.org/200-response",
        "website.test.openzim.org/201-response",
        "website.test.openzim.org/202-response",
        "website.test.openzim.org/301-external-redirect-ok",
        "website.test.openzim.org/301-internal-redirect-ok",
        "website.test.openzim.org/302-external-redirect-ok",
        "website.test.openzim.org/302-internal-redirect-ok",
        "website.test.openzim.org/307-external-redirect-ok",
        "website.test.openzim.org/307-internal-redirect-ok",
        "website.test.openzim.org/308-external-redirect-ok",
        "website.test.openzim.org/308-internal-redirect-ok",
        "website.test.openzim.org/http-return-codes.html",
        "website.test.openzim.org/icons/favicon.ico",
        "website.test.openzim.org/icons/site.webmanifest",
        "website.test.openzim.org/internal_redirect_target.html",
        "www.example.com/",
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
    assert json.loads(Path("/output/crawl.json").read_bytes()) == {
        "crawled": 35,
        "pending": 0,
        "pendingPages": [],
        "total": 35,
        "failed": 18,
        "limit": {"max": 0, "hit": False},
    }

    assert json.loads(Path("/output/warc2zim.json").read_bytes()) == {
        "written": 8,
        "total": 8,
    }

    assert json.loads(Path("/output/stats.json").read_bytes()) == {
        "done": 8,
        "total": 8,
        "limit": {"max": 0, "hit": False},
    }
