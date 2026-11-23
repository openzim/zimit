import io

from warcio.statusandheaders import StatusAndHeaders
from warcio.warcwriter import WARCWriter
from zimscraperlib.rewriting.url_rewriting import REPLAY_MARKER
from zimscraperlib.zim import Archive

from zimit.constants import NORMAL_WARC2ZIM_EXIT_CODE
from zimit.zimit import run


def test_trailing_slash_revisit_redirect(tmp_path):
    warc_path = tmp_path / "trailing-slash.warc"
    with warc_path.open("wb") as output:
        writer = WARCWriter(output, gzip=True)
        home_html = b"<html><head><title>Blog</title></head><body>Home</body></html>"
        writer.write_record(
            writer.create_warc_record(
                "https://example.com/blog",
                "response",
                http_headers=StatusAndHeaders(
                    "HTTP/1.1 200 OK",
                    [
                        ("Content-Type", "text/html; charset=utf-8"),
                        ("Content-Length", str(len(home_html))),
                    ],
                ),
                payload=io.BytesIO(home_html),
            )
        )
        writer.write_record(
            writer.create_revisit_record(
                "https://example.com/blog/",
                "sha1:3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ",
                "https://example.com/blog/",
                "2026-01-01T00:00:00Z",
                http_headers=StatusAndHeaders(
                    "HTTP/1.1 301 Moved Permanently",
                    [("Location", "/blog")],
                ),
            )
        )

    zim_file = "trailing-slash.zim"
    result = run(
        [
            "--seeds",
            "https://example.com/blog",
            "--warcs",
            str(warc_path),
            "--output",
            str(tmp_path),
            "--zim-file",
            zim_file,
            "--name",
            "trailing-slash",
            "--title",
            "Blog",
            "--zim-lang",
            "eng",
        ]
    )
    assert result in (None, NORMAL_WARC2ZIM_EXIT_CODE)

    archive = Archive(tmp_path / zim_file)
    target = archive.get_entry_by_path(REPLAY_MARKER + "example.com/blog")
    assert not target.is_redirect

    redirect = archive.get_entry_by_path(REPLAY_MARKER + "example.com/blog/")
    assert redirect.is_redirect
    assert redirect.get_redirect_entry().path == REPLAY_MARKER + "example.com/blog"
