import src.monitor as monitor_module
from src.models import PrinterState
from src.monitor import Monitor


class FlakyPrinter:
    def __init__(self, name="P1", failures=1):
        self.name = name
        self.calls = 0
        self.failures = failures

    def get_status(self):
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError("offline")
        return {
            "print_stats": {"state": "idle", "filename": ""},
            "display_status": {"progress": 0.0},
        }


class StablePrinter:
    def __init__(self, name="P1"):
        self.name = name
        self.calls = 0

    def get_status(self):
        self.calls += 1
        return {
            "print_stats": {"state": "idle", "filename": ""},
            "display_status": {"progress": 0.0},
        }


class FakeSpoolman:
    def __init__(self):
        self.calls = 0
        self.last_error = False

    def get_spool_for_printer(self, printer_name):
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("spoolman down")
        self.last_error = False
        return {"remaining_weight": 100.0, "remaining_length": 1000.0}

    @staticmethod
    def filament_name(spool):
        return "Test PLA"


class FakeTelegram:
    def send(self, text):
        pass


class FakeEventLogger:
    def log_start(self, printer, filename, started_at):
        return 1

    def log_end(
        self,
        event_id,
        printer,
        filename,
        status,
        filament_name,
        filament_grams,
        duration_seconds,
        ended_at,
        error_reason,
    ):
        pass


def test_status_backoff_increases_and_resets(monkeypatch):
    current = {"value": 0.0}

    def fake_monotonic():
        return current["value"]

    monkeypatch.setattr(monitor_module.time, "monotonic", fake_monotonic)

    printer = FlakyPrinter(failures=2)
    spoolman = FakeSpoolman()
    telegram = FakeTelegram()
    logger = FakeEventLogger()
    states = {"P1": PrinterState()}
    monitor = Monitor([printer], spoolman, telegram, states, logger)

    monitor.process(printer)
    assert printer.calls == 1
    assert monitor._status_backoff["P1"]["delay"] == 1.0

    current["value"] = 0.5
    monitor.process(printer)
    assert printer.calls == 1

    current["value"] = 1.1
    monitor.process(printer)
    assert printer.calls == 2
    assert monitor._status_backoff["P1"]["delay"] == 2.0

    current["value"] = 3.2
    monitor.process(printer)
    assert printer.calls == 3
    assert "P1" not in monitor._status_backoff


def test_spoolman_backoff_skips_until_success(monkeypatch):
    current = {"value": 0.0}

    def fake_monotonic():
        return current["value"]

    monkeypatch.setattr(monitor_module.time, "monotonic", fake_monotonic)

    printer = StablePrinter()
    spoolman = FakeSpoolman()
    telegram = FakeTelegram()
    logger = FakeEventLogger()
    states = {"P1": PrinterState()}
    monitor = Monitor([printer], spoolman, telegram, states, logger)

    current["value"] = 0.0
    monitor.process(printer)
    assert spoolman.calls == 1
    assert monitor._spoolman_backoff["P1"]["delay"] == 1.0

    current["value"] = 0.5
    monitor.process(printer)
    assert spoolman.calls == 1

    current["value"] = 1.1
    monitor.process(printer)
    assert spoolman.calls == 2
    assert "P1" not in monitor._spoolman_backoff
