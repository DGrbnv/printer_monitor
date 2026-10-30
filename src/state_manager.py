import json
from dataclasses import asdict
from pathlib import Path
from .models import PrinterState


class StateManager:
    def __init__(self, path: str | None = None):
        base_dir = Path(__file__).resolve().parent.parent
        self.path = Path(path) if path else base_dir / "data" / "printer_states.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._last_snapshot = None

    @staticmethod
    def _serialize_states(states):
        return {k: asdict(v) for k, v in states.items()}

    def load(self, printer_names):
        if not self.path.exists():
            states = {
                name: PrinterState()
                for name in printer_names
            }
            self._last_snapshot = self._serialize_states(states)
            return states

        with open(self.path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        def coalesce_float(value, default=0.0):
            if value is None:
                return default
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        def coalesce_int(value, default=0):
            if value is None:
                return default
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        def coalesce_bool(value, default=False):
            if value is None:
                return default
            if isinstance(value, bool):
                return value
            return default

        states = {}
        for name in printer_names:
            data = raw.get(name, {})
            connection_state = data.get("connection_state")
            if connection_state not in {"online", "offline"}:
                connection_state = "offline" if data.get("offline_since") else "online"
            states[name] = PrinterState(
                last_state=data.get("last_state"),
                last_filename=data.get("last_filename"),
                start_filament_mm=coalesce_float(
                    data.get("start_filament_mm"),
                    0.0
                ),
                start_remaining_weight=coalesce_float(
                    data.get("start_remaining_weight"),
                    None
                ),
                start_spool_id=coalesce_int(
                    data.get("start_spool_id"),
                    None
                ),
                seen_idle=coalesce_bool(data.get("seen_idle"), False),
                ended=coalesce_bool(data.get("ended"), False),
                last_filament_mm=coalesce_float(
                    data.get("last_filament_mm"),
                    0.0
                ),
                last_print_duration=coalesce_int(
                    data.get("last_print_duration"),
                    0
                ),
                last_progress=data.get("last_progress"),
                start_time=data.get("start_time"),
                current_event_id=data.get("current_event_id"),
                last_notified_state=data.get("last_notified_state"),
                last_notified_filename=data.get("last_notified_filename"),
                connection_state=connection_state,
                offline_since=data.get("offline_since"),
                last_seen=data.get("last_seen")
            )
        self._last_snapshot = self._serialize_states(states)
        return states


    def save(self, states):
        snapshot = self._serialize_states(states)
        if snapshot == self._last_snapshot:
            return
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(
                snapshot,
                f,
                indent=2,
                ensure_ascii=False
            )
        self._last_snapshot = snapshot
