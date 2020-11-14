import os
import glob

import libzim.reader
from warcio import ArchiveIterator

def get_zim_article(zimfile, path):
    zim_fh = libzim.reader.File(zimfile)
    return zim_fh.get_article(path).content.tobytes()

def test_is_file():
    """ Ensure ZIM file exists"""
    assert os.path.isfile("/output/isago.zim")

def test_zim_main_page():
    """ Main page specified, http://isago.ml/, was a redirect to https
        Ensure main page is the redirected page"""

    assert b'"https://isago.ml/"' in get_zim_article("/output/isago.zim", "A/index.html")

def test_user_agent():
    """ Test that mobile user agent was used in WARC request records with custom Zimit and email suffix"""

    #result = get_zim_article("/output/isago.zim", "H/isago.ml/")
    #print(result)
    for warc in glob.glob("/output/.tmp*/collections/capture/archive/*.warc.gz"):
        with open(warc, "rb") as fh:
            for record in ArchiveIterator(fh):
                if record.rec_type == "request":
                    print(record.http_headers)
                    ua = record.http_headers.get_header("User-Agent")
                    if ua:
                        assert "iPhone" in ua
                        assert ua.endswith(" +Zimit test@example.com")
                        return

    # not found
    assert False
