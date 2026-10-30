import json
from unittest.mock import mock_open, patch

from src.models import PrinterState
from src.state_manager import StateManager


def test_load_defaults_for_nulls(tmp_path):
    path = tmp_path / "states.json"
    raw = {
        "P1": {
            "last_state": None,
            "last_filename": None,
            "start_filament_mm": None,
            "seen_idle": None,
            "ended": None,
            "last_filament_mm": None,
            "last_print_duration": None,
            "last_progress": None,
            "start_time": None,
            "current_event_id": None,
            "connection_state": None,
            "offline_since": None,
            "last_seen": None,
        }
    }
    path.write_text(json.dumps(raw), encoding="utf-8")

    manager = StateManager(str(path))
    states = manager.load(["P1"])

    state = states["P1"]
    assert state.last_state is None
    assert state.last_filename is None
    assert state.start_filament_mm == 0.0
    assert state.seen_idle is False
    assert state.ended is False
    assert state.last_filament_mm == 0.0
    assert state.last_print_duration == 0
    assert state.last_progress is None
    assert state.start_time is None
    assert state.current_event_id is None
    assert state.connection_state == "online"
    assert state.last_seen is None


def test_save_load_roundtrip(tmp_path):
    path = tmp_path / "states.json"
    manager = StateManager(str(path))
    state = PrinterState(
        last_state="printing",
        last_filename="test.gcode",
        start_filament_mm=12.5,
        seen_idle=True,
        ended=False,
        last_filament_mm=50.0,
        last_print_duration=120,
        last_progress=45.0,
        start_time="2024-01-02T03:04:05",
        current_event_id=7,
        connection_state="offline",
        offline_since="2024-01-02T03:10:00",
        last_seen="2024-01-02T03:09:00",
    )
    manager.save({"P1": state})

    loaded = manager.load(["P1"])["P1"]

    assert loaded.last_state == "printing"
    assert loaded.last_filename == "test.gcode"
    assert loaded.start_filament_mm == 12.5
    assert loaded.seen_idle is True
    assert loaded.ended is False
    assert loaded.last_filament_mm == 50.0
    assert loaded.last_print_duration == 120
    assert loaded.last_progress == 45.0
    assert loaded.start_time == "2024-01-02T03:04:05"
    assert loaded.current_event_id == 7
    assert loaded.connection_state == "offline"
    assert loaded.offline_since == "2024-01-02T03:10:00"
    assert loaded.last_seen == "2024-01-02T03:09:00"


def test_save_skips_when_unchanged(tmp_path, monkeypatch):
    path = tmp_path / "states.json"
    manager = StateManager(str(path))
    state = PrinterState(last_state="printing", last_filename="test.gcode")
    manager.save({"P1": state})

    def fail_open(*args, **kwargs):
        raise AssertionError("Expected no write for unchanged snapshot")

    monkeypatch.setattr("builtins.open", fail_open)

    manager.save({"P1": state})


def test_save_writes_on_change(tmp_path):
    path = tmp_path / "states.json"
    manager = StateManager(str(path))
    state = PrinterState(last_state="printing", last_filename="test.gcode")
    manager.save({"P1": state})

    state.last_filename = "new.gcode"

    mocked_open = mock_open()
    with patch("builtins.open", mocked_open):
        manager.save({"P1": state})

    assert mocked_open.called


def test_load_infers_offline_state_from_legacy_data(tmp_path):
    path = tmp_path / "states.json"
    raw = {"P1": {"offline_since": "2024-01-02T03:10:00"}}
    path.write_text(json.dumps(raw), encoding="utf-8")

    manager = StateManager(str(path))
    state = manager.load(["P1"])["P1"]

    assert state.connection_state == "offline"
