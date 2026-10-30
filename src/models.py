from dataclasses import dataclass


@dataclass
class PrinterState:
    """Persisted printer state.

    Contract for restore:
    - Optional fields may be None when not known.
    - Numeric/bool fields are defaulted when missing or null.
    """
    last_state: str | None = None
    last_filename: str | None = None
    start_filament_mm: float = 0.0
    start_remaining_weight: float | None = None
    start_spool_id: int | None = None
    seen_idle: bool = False
    ended: bool = False
    last_filament_mm: float = 0.0
    last_print_duration: int = 0
    last_progress: float | None = None
    start_time: str | None = None
    current_event_id: int | None = None
    last_notified_state: str | None = None
    last_notified_filename: str | None = None
    connection_state: str = "online"
    offline_since: str | None = None
    last_seen: str | None = None
