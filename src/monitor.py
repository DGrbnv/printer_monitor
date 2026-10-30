import logging
import re
import time
from datetime import datetime, timedelta

from .formatter import end_message, offline_message, recovery_message, start_message

_UNSET = object()
_DEFAULT_BACKOFF_INITIAL_SECONDS = 1.0
_DEFAULT_BACKOFF_MAX_SECONDS = 60.0
_UNKNOWN_FILAMENT = "неизвестно"
logger = logging.getLogger(__name__)


class Monitor:
    def __init__(self, printers, spoolman, telegram, states, event_logger):
        self.printers = printers
        self.spoolman = spoolman
        self.telegram = telegram
        self.states = states
        self.event_logger = event_logger
        self._status_backoff = {}
        self._spoolman_backoff = {}
        self._backoff_initial_seconds = _DEFAULT_BACKOFF_INITIAL_SECONDS
        self._backoff_max_seconds = _DEFAULT_BACKOFF_MAX_SECONDS

    @staticmethod
    def filament_grams(used_mm, spool):
        if not spool:
            return None
        w = spool.get("remaining_weight")
        l = spool.get("remaining_length")
        if not w or not l:
            return None
        return (used_mm / 1000) * (w / l)

    @staticmethod
    def eta_from_moonraker(stats):
        total = stats.get("total_duration")
        current = stats.get("print_duration")
        if total and current and total > current:
            return datetime.now() + timedelta(seconds=(total - current))
        return None

    @staticmethod
    def eta_from_filename(filename: str):
        parts = re.findall(r'(\d+)([hms])', filename)
        if not parts:
            return None
        seconds = 0
        for value, unit in parts:
            value = int(value)
            if unit == "h":
                seconds += value * 3600
            elif unit == "m":
                seconds += value * 60
            elif unit == "s":
                seconds += value
        if seconds <= 0:
            return None

        return datetime.now() + timedelta(seconds=seconds)

    def _is_backing_off(self, backoff, printer_name, now):
        entry = backoff.get(printer_name)
        if not entry:
            return False
        return now < entry["next_attempt"]

    def _note_success(self, backoff, printer_name):
        backoff.pop(printer_name, None)

    def _note_failure(self, backoff, printer_name, now):
        entry = backoff.get(printer_name)
        if entry:
            delay = min(entry["delay"] * 2, self._backoff_max_seconds)
        else:
            delay = self._backoff_initial_seconds
        backoff[printer_name] = {"delay": delay, "next_attempt": now + delay}

    def process(self, printer):
        now = time.monotonic()
        if self._is_backing_off(self._status_backoff, printer.name, now):
            return
        state = self.states[printer.name]
        # Обновляем состояние только при реальных изменениях (смена состояния,
        # прогресса, файла или события старта/окончания), чтобы не писать
        # идентичный снимок.
        try:
            status = printer.get_status()
        except RuntimeError as err:
            if state.connection_state != "offline":
                logger.error(
                    "Failed to get printer status for '%s': %s",
                    printer.name,
                    err
                )
            else:
                logger.warning(
                    "Printer '%s' is still unreachable: %s",
                    printer.name,
                    err
                )
            self._note_failure(self._status_backoff, printer.name, now)
            if state.connection_state != "offline":
                state.connection_state = "offline"
                if state.offline_since is None:
                    state.offline_since = datetime.now().isoformat()
                if not (state.last_state == "printing" and not state.ended):
                    self._safe_send(
                        offline_message(
                            printer.name,
                            state.last_state,
                            state.last_filename
                        )
                    )
            if state.last_state == "printing" and not state.ended:
                self._send_end_message(
                    printer=printer,
                    state=state,
                    current_state="offline",
                    error_reason="moonraker_unreachable"
                )
            return  # просто пропускаем этот принтер
        else:
            self._note_success(self._status_backoff, printer.name)

        recovered_at = datetime.now()
        if state.connection_state == "offline" and state.offline_since:
            offline_since = datetime.fromisoformat(state.offline_since)
            self._safe_send(
                recovery_message(
                    printer.name,
                    offline_since,
                    recovered_at
                )
            )
            state.offline_since = None
        state.connection_state = "online"
        state.last_seen = recovered_at.isoformat()

        stats = status.get("print_stats", {})
        display = status.get("display_status", {})

        current = stats.get("state")
        if not current:
            return
        if current == "printing":
            state.ended = False

        filename = stats.get("filename", "")
        filament_mm = float(stats.get("filament_used", 0))
        duration = int(stats.get("print_duration", 0))
        state.last_filament_mm = filament_mm
        state.last_print_duration = duration

        spool = None
        if not self._is_backing_off(self._spoolman_backoff, printer.name, now):
            try:
                spool = self.spoolman.get_spool_for_printer(printer.name)
            except Exception:
                logger.exception(
                    "Spoolman request failed for printer '%s'",
                    printer.name
                )
                self._note_failure(self._spoolman_backoff, printer.name, now)
                spool = None
            else:
                if getattr(self.spoolman, "last_error", False):
                    self._note_failure(self._spoolman_backoff, printer.name, now)
                else:
                    self._note_success(self._spoolman_backoff, printer.name)
        filament_name = self.spoolman.filament_name(spool) if spool else _UNKNOWN_FILAMENT
        progress = display.get("progress")
        if isinstance(progress, (int, float)):
            progress = max(0.0, min(progress * 100, 100.0))
        else:
            progress = None
        state.last_progress = progress

        if current in ("idle", "standby", "ready", "complete"):
            state.seen_idle = True

        if (
            current == "printing"
            and state.last_state != "printing"
            and state.current_event_id is None
            and not self._already_notified(state, "printing", filename)
        ):
            state.start_filament_mm = filament_mm
            state.start_remaining_weight = (
                float(spool.get("remaining_weight"))
                if spool and spool.get("remaining_weight") is not None
                else None
            )
            state.start_spool_id = spool.get("id") if spool else None
            now = datetime.now()
            state.start_time = now.isoformat()
            state.current_event_id = self.event_logger.log_start(
                printer.name,
                filename,
                now
            )

            eta = self.eta_from_moonraker(stats)
            if not eta:
                eta = self.eta_from_filename(filename)

            message = start_message(
                printer.name,
                filename,
                spool,
                filament_name,
                eta,
                progress
            )

            self._safe_send(message)

            state.last_notified_state = "printing"
            state.last_notified_filename = filename

        if (
            current in ("complete", "cancelled", "error")
            and state.last_state == "printing"
            and not state.ended
            ):
            self._send_end_message(
                printer=printer,
                state=state,
                current_state=current,
                filename=filename,
                filament_mm=filament_mm,
                duration=duration,
                spool=spool,
                filament_name=filament_name
            )

        state.last_state = current
        state.last_filename = filename

    def _already_notified(self, state, target_state, filename):
        return (
            state.last_notified_state == target_state
            and state.last_notified_filename == filename
        )

    def _send_end_message(
        self,
        printer,
        state,
        current_state,
        error_reason=None,
        filename=None,
        filament_mm=None,
        duration=None,
        spool=_UNSET,
        filament_name=_UNSET
    ):
        state.ended = True
        filename = filename or state.last_filename or ""
        filament_mm = filament_mm if filament_mm is not None else state.last_filament_mm
        duration = duration if duration is not None else state.last_print_duration
        if spool is _UNSET:
            try:
                spool = self.spoolman.get_spool_for_printer(printer.name)
            except Exception:
                logger.exception(
                    "Spoolman request failed for printer '%s'",
                    printer.name
                )
                spool = None
        if filament_name is _UNSET:
            filament_name = (
                self.spoolman.filament_name(spool)
                if spool else _UNKNOWN_FILAMENT
            )

        if self._already_notified(state, current_state, filename):
            state.ended = True
            return

        used_mm = filament_mm - state.start_filament_mm
        if used_mm <= 0:
            used_mm = filament_mm

        grams = None
        if isinstance(spool, dict):
            end_spool_id = spool.get("id")
            if state.start_spool_id is not None and end_spool_id != state.start_spool_id:
                grams = None
            else:
                end_remaining_weight = spool.get("remaining_weight")
                if (
                    state.start_remaining_weight is not None
                    and end_remaining_weight is not None
                ):
                    grams = state.start_remaining_weight - float(end_remaining_weight)
                    if grams <= 0:
                        grams = None
                if grams is None:
                    grams = self.filament_grams(used_mm, spool)

        self.event_logger.log_end(
            state.current_event_id,
            printer.name,
            filename,
            current_state,
            filament_name,
            grams,
            duration,
            datetime.now(),
            error_reason
        )
        state.current_event_id = None

        self._safe_send(
            end_message(
                printer.name,
                filename,
                duration,
                grams,
                spool,
                filament_name,
                current_state,
                error_reason
            )
        )
        state.last_notified_state = current_state
        state.last_notified_filename = filename

    def _safe_send(self, text: str):
        try:
            self.telegram.send(text)
        except Exception:
            logger.exception("Telegram send failed")
