import time

from zimit import zimit as zimit_module
from zimit.zimit import ConversionHeartbeat

HEARTBEAT_MESSAGE = "warc2zim is still running after"


class RecordingLogger:
    def __init__(self):
        self.messages: list[str] = []

    def info(self, message: str):
        self.messages.append(message)


def test_heartbeat_logs_while_conversion_is_running(monkeypatch):
    recorder = RecordingLogger()
    monkeypatch.setattr(zimit_module, "logger", recorder)

    with ConversionHeartbeat(interval=0.01):
        time.sleep(0.1)

    assert any(HEARTBEAT_MESSAGE in message for message in recorder.messages)


def test_heartbeat_stops_when_conversion_finishes(monkeypatch):
    recorder = RecordingLogger()
    monkeypatch.setattr(zimit_module, "logger", recorder)

    heartbeat = ConversionHeartbeat(interval=0.01)
    with heartbeat:
        time.sleep(0.1)

    thread = heartbeat._thread
    assert thread is not None
    assert not thread.is_alive()

    recorder.messages.clear()
    time.sleep(0.05)

    assert not any(HEARTBEAT_MESSAGE in message for message in recorder.messages)
