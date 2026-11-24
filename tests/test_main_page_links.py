import io

from warcio.statusandheaders import StatusAndHeaders
from warcio.warcwriter import WARCWriter
from zimscraperlib.rewriting.url_rewriting import REPLAY_MARKER
from zimscraperlib.zim import Archive

from zimit.constants import NORMAL_WARC2ZIM_EXIT_CODE
from zimit.zimit import run

SEED = "https://sacred-texts.com/"
HOME_PATH = REPLAY_MARKER + "sacred-texts.com/"
INDEX_PATH = REPLAY_MARKER + "sacred-texts.com/index.html"


def add_response(writer, url, payload):
    writer.write_record(
        writer.create_warc_record(
            url,
            "response",
            http_headers=StatusAndHeaders(
                "HTTP/1.1 200 OK",
                [
                    ("Content-Type", "text/html; charset=utf-8"),
                    ("Content-Length", str(len(payload))),
                ],
            ),
            payload=io.BytesIO(payload),
        )
    )


def test_main_page_links_use_replay_prefix(tmp_path):
    warc_path = tmp_path / "main-page.warc"
    home_html = (
        b"<html><head><title>Home</title></head><body>"
        b'<a href="index.html">Index</a>'
        b"</body></html>"
    )
    index_html = b"<html><head><title>Index</title></head><body>Index</body></html>"

    with warc_path.open("wb") as output:
        writer = WARCWriter(output, gzip=True)
        add_response(writer, SEED, home_html)
        add_response(writer, SEED + "index.html", index_html)

    zim_file = "main-page.zim"
    result = run(
        [
            "--seeds",
            SEED,
            "--warcs",
            str(warc_path),
            "--output",
            str(tmp_path),
            "--zim-file",
            zim_file,
            "--name",
            "main-page",
            "--title",
            "Main page",
            "--zim-lang",
            "eng",
        ]
    )
    assert result in (None, NORMAL_WARC2ZIM_EXIT_CODE)

    archive = Archive(tmp_path / zim_file)
    main_entry = archive.main_entry
    assert main_entry.is_redirect
    assert main_entry.get_redirect_entry().path == HOME_PATH
    assert archive.has_entry_by_path(HOME_PATH)
    assert archive.has_entry_by_path(INDEX_PATH)

    content = bytes(archive.get_entry_by_path(HOME_PATH).get_item().content).decode()
    assert 'href="index.html"' in content
    assert "wombatSetup.REPLAY_MARKER" in content
