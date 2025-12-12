import pytest

from zimit import zimit as app

"""
 cleanup disabled because atexit hooks run at the very end of the Python process
 shutdown. By the time cleanup() is called, the logging module has already closed its
 file streams.
"""


@pytest.fixture(autouse=True)
def disable_zimit_cleanup(monkeypatch):
    monkeypatch.setattr(app, "cleanup", lambda: None)
