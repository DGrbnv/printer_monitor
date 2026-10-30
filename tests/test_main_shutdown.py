import pytest

import src.main as main_module
from src.models import PrinterState


class FakeConfig:
    def __init__(self, path):
        self.log_file = "log.txt"
        self.printers = {"P1": {"url": "http://printer"}}
        self.spoolman_url = "http://spool"
        self.spoolman_cache_ttl_seconds = 0
        self.spoolman_error_ttl_seconds = 0
        self.telegram = {"bot_token": "token", "chat_id": "chat"}
        self.telegram_retries = 0
        self.state_file = "state.json"
        self.db_file = "events.db"
        self.monitoring = {
            "startup_message": False,
            "shutdown_message": True,
        }
        self.interval = 1


class FakePrinter:
    def __init__(self, name, url):
        self.name = name
        self.url = url


class FakeTelegram:
    def __init__(self, *args, **kwargs):
        self.messages = []

    def send(self, text):
        self.messages.append(text)


class FakeStateManager:
    def __init__(self, path):
        self.save_calls = 0

    def load(self, printer_names):
        return {name: PrinterState() for name in printer_names}

    def save(self, states):
        self.save_calls += 1


class FakeEventLogger:
    def __init__(self, path):
        self.path = path


def test_shutdown_saves_state_and_sends_message(monkeypatch):
    saved_state_mgr = FakeStateManager("state.json")
    telegram = FakeTelegram()

    class FakeMonitor:
        def __init__(self, *args, **kwargs):
            pass

        def process(self, printer):
            raise KeyboardInterrupt()

    monkeypatch.setattr(main_module, "Config", FakeConfig)
    monkeypatch.setattr(main_module, "PrinterAPI", FakePrinter)
    monkeypatch.setattr(main_module, "TelegramBot", lambda *args, **kwargs: telegram)
    monkeypatch.setattr(main_module, "StateManager", lambda *args, **kwargs: saved_state_mgr)
    monkeypatch.setattr(main_module, "EventLogger", FakeEventLogger)
    monkeypatch.setattr(main_module, "Monitor", FakeMonitor)
    monkeypatch.setattr(main_module, "setup_logging", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_module, "cleanup_logs", lambda *args, **kwargs: None)

    main_module.main()

    assert saved_state_mgr.save_calls >= 1
    assert telegram.messages == ["🔴 <b>Мониторинг принтеров остановлен</b>"]


def test_exception_saves_state(monkeypatch):
    saved_state_mgr = FakeStateManager("state.json")

    class FakeMonitor:
        def __init__(self, *args, **kwargs):
            pass

        def process(self, printer):
            raise RuntimeError("boom")

    monkeypatch.setattr(main_module, "Config", FakeConfig)
    monkeypatch.setattr(main_module, "PrinterAPI", FakePrinter)
    monkeypatch.setattr(main_module, "TelegramBot", FakeTelegram)
    monkeypatch.setattr(main_module, "StateManager", lambda *args, **kwargs: saved_state_mgr)
    monkeypatch.setattr(main_module, "EventLogger", FakeEventLogger)
    monkeypatch.setattr(main_module, "Monitor", FakeMonitor)
    monkeypatch.setattr(main_module, "setup_logging", lambda *args, **kwargs: None)
    monkeypatch.setattr(main_module, "cleanup_logs", lambda *args, **kwargs: None)

    with pytest.raises(RuntimeError, match="boom"):
        main_module.main()

    assert saved_state_mgr.save_calls >= 1
