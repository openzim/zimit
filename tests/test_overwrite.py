import pathlib

import pytest

from zimit.zimit import run

TEST_DATA_DIR = pathlib.Path(__file__).parent / "data"


def test_overwrite_flag_behaviour(tmp_path):
    zim_output = "overwrite-test.zim"
    output_path = tmp_path / zim_output

    # 1st run → creates file
    result = run(
        [
            "--seeds",
            "https://example.com",
            "--warcs",
            str(TEST_DATA_DIR / "example-response.warc"),
            "--output",
            str(tmp_path),
            "--zim-file",
            zim_output,
            "--name",
            "overwrite-test",
        ]
    )
    assert result in (None, 100)
    assert output_path.exists()

    # 2nd run, no overwrite → should fail
    with pytest.raises(SystemExit) as exc:
        run(
            [
                "--seeds",
                "https://example.com",
                "--warcs",
                str(TEST_DATA_DIR / "example-response.warc"),
                "--output",
                str(tmp_path),
                "--zim-file",
                zim_output,
                "--name",
                "overwrite-test",
            ]
        )
    assert exc.value.code == 2

    # 2nd run, no overwrite → should fail
    with pytest.raises(SystemExit) as exc:
        run(
            [
                "--seeds",
                "https://example.com",
                "--output",
                str(tmp_path),
                "--zim-file",
                zim_output,
                "--name",
                "overwrite-test",
            ]
        )
    assert exc.value.code == 2

    # 3rd run, with overwrite → should succeed
    result = run(
        [
            "--seeds",
            "https://example.com",
            "--warcs",
            str(TEST_DATA_DIR / "example-response.warc"),
            "--output",
            str(tmp_path),
            "--zim-file",
            zim_output,
            "--name",
            "overwrite-test",
            "--overwrite",
        ]
    )
    assert result in (None, 100)
    assert output_path.exists()
