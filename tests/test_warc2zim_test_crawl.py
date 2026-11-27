import io
import subprocess
from pathlib import Path

from warcio.warcwriter import WARCWriter

from zimit import zimit as zimit_module
from zimit.constants import EXIT_CODE_WARC2ZIM_TEST_CRAWL_FAILED
from zimit.zimit import run

TEST_DATA_DIR = Path(__file__).parent / "data"
COLLECTION = "test-collection"


def empty_warc_bytes() -> bytes:
    """A syntactically valid WARC with no response record, so warc2zim considers
    it unprocessable"""
    buffer = io.BytesIO()
    writer = WARCWriter(buffer, gzip=False)
    writer.write_record(
        writer.create_warcinfo_record(filename=None, info={"software": "test"})
    )
    return buffer.getvalue()


def make_fake_crawl(monkeypatch, warc_bytes_by_call: list[bytes]):
    """Replace the crawler subprocess call with a fake that drops a prepared WARC
    file into the collection directory the crawler would normally have created,
    one entry of warc_bytes_by_call per expected call (in order)."""
    calls: list[list[str]] = []

    def fake_run(args, check=False):  # noqa: ARG001, FBT002
        calls.append(args)
        cwd = Path(args[args.index("--cwd") + 1])
        archive_dir = cwd / "collections" / COLLECTION / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        warc_bytes = warc_bytes_by_call[len(calls) - 1]
        (archive_dir / "data.warc").write_bytes(warc_bytes)
        return subprocess.CompletedProcess(args=args, returncode=0)

    monkeypatch.setattr(zimit_module.subprocess, "run", fake_run)
    return calls


def test_failing_test_crawl_blocks_full_crawl(tmp_path, monkeypatch):
    calls = make_fake_crawl(monkeypatch, [empty_warc_bytes()])

    zim_file = "test-crawl-failure.zim"
    result = run(
        [
            "--seeds",
            "https://example.com",
            "--collection",
            COLLECTION,
            "--output",
            str(tmp_path),
            "--zim-file",
            zim_file,
            "--name",
            "test-crawl-failure",
        ]
    )

    assert result == EXIT_CODE_WARC2ZIM_TEST_CRAWL_FAILED
    # the full crawl must never have been triggered
    assert len(calls) == 1
    assert not (tmp_path / zim_file).exists()


def test_successful_test_crawl_allows_full_crawl(tmp_path, monkeypatch):
    good_warc_bytes = (TEST_DATA_DIR / "example-response.warc").read_bytes()
    calls = make_fake_crawl(monkeypatch, [good_warc_bytes, good_warc_bytes])

    zim_file = "test-crawl-success.zim"
    result = run(
        [
            "--seeds",
            "https://example.com",
            "--collection",
            COLLECTION,
            "--output",
            str(tmp_path),
            "--zim-file",
            zim_file,
            "--name",
            "test-crawl-success",
        ]
    )

    assert result in (None, 0)
    # both the test crawl and the full crawl must have been triggered
    assert len(calls) == 2
    assert (tmp_path / zim_file).exists()
