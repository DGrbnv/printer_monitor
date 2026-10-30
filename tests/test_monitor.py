from src.models import PrinterState
from src.monitor import Monitor


class FakePrinter:
    def __init__(self, name, status_sequence, error=None):
        self.name = name
        self._status_sequence = list(status_sequence)
        self._error = error

    def get_status(self):
        if self._error:
            raise RuntimeError(self._error)
        return self._status_sequence.pop(0)


class FakeSpoolman:
    def __init__(self, spool=None):
        self._spool = spool

    def get_spool_for_printer(self, printer_name):
        return self._spool

    @staticmethod
    def filament_name(spool):
        return "Test PLA"


class FakeTelegram:
    def __init__(self):
        self.messages = []

    def send(self, text):
        self.messages.append(text)


class FakeEventLogger:
    def __init__(self):
        self.events = []
        self.next_id = 1

    def log_start(self, printer, filename, started_at):
        event_id = self.next_id
        self.next_id += 1
        self.events.append(("start", printer, filename))
        return event_id

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
        self.events.append(
            (
                "end",
                event_id,
                printer,
                filename,
                status,
                filament_grams,
                error_reason,
            )
        )


def make_status(state, filename="test.gcode", filament=100.0, duration=120, progress=0.5):
    return {
        "print_stats": {
            "state": state,
            "filename": filename,
            "filament_used": filament,
            "print_duration": duration,
            "total_duration": duration + 60,
        },
        "display_status": {
            "progress": progress
        }
    }


def test_end_message_sent_once():
    printer = FakePrinter(
        "P1",
        [
            make_status("printing", filament=50.0, duration=10),
            make_status("complete", filament=120.0, duration=100),
        ],
    )
    spoolman = FakeSpoolman({"remaining_weight": 800, "remaining_length": 20000})
    telegram = FakeTelegram()
    logger = FakeEventLogger()
    states = {"P1": PrinterState()}
    monitor = Monitor([printer], spoolman, telegram, states, logger)

    monitor.process(printer)
    monitor.process(printer)

    assert len(telegram.messages) == 2
    assert logger.events[0][0] == "start"
    assert logger.events[1][0] == "end"


def test_disconnect_sends_offline():
    printer = FakePrinter("P1", [], error="Moonraker down")
    spoolman = FakeSpoolman()
    telegram = FakeTelegram()
    logger = FakeEventLogger()
    state = PrinterState(
        last_state="printing",
        last_filename="file.gcode",
        start_filament_mm=10.0,
        last_filament_mm=100.0,
        last_print_duration=60,
    )
    states = {"P1": state}
    monitor = Monitor([printer], spoolman, telegram, states, logger)

    monitor.process(printer)

    assert len(telegram.messages) == 1
    assert "Потеряна связь" in telegram.messages[0]


def test_eta_parsing_requires_seconds():
    eta = Monitor.eta_from_filename("part_1h20m.gcode")
    assert eta is not None

    eta = Monitor.eta_from_filename("part_1h20m30s.gcode")
    assert eta is not None


def test_start_message_sent_once_across_transient_states():
    printer = FakePrinter(
        "P1",
        [
            make_status("printing", filament=50.0, duration=10),
            make_status("standby", filament=55.0, duration=15),
            make_status("printing", filament=60.0, duration=20),
        ],
    )
    spoolman = FakeSpoolman({"remaining_weight": 800, "remaining_length": 20000})
    telegram = FakeTelegram()
    logger = FakeEventLogger()
    states = {"P1": PrinterState()}
    monitor = Monitor([printer], spoolman, telegram, states, logger)

    monitor.process(printer)
    monitor.process(printer)
    monitor.process(printer)

    assert len(telegram.messages) == 1
    assert logger.events[0][0] == "start"


def test_filament_consumption_omitted_when_spool_changes():
    spool = {"id": 1, "remaining_weight": 33.0, "remaining_length": 10000}
    printer = FakePrinter(
        "P1",
        [
            make_status("printing", filament=10.0, duration=10),
            make_status("complete", filament=20.0, duration=50),
        ],
    )
    spoolman = FakeSpoolman(spool)
    telegram = FakeTelegram()
    logger = FakeEventLogger()
    states = {"P1": PrinterState()}
    monitor = Monitor([printer], spoolman, telegram, states, logger)

    monitor.process(printer)
    spool["id"] = 2
    spool["remaining_weight"] = 32.5
    monitor.process(printer)

    assert logger.events[1][0] == "end"
    assert logger.events[1][5] is None


def test_offline_sent_once_until_recovery():
    printer = FakePrinter("P1", [], error="Moonraker down")
    spoolman = FakeSpoolman()
    telegram = FakeTelegram()
    logger = FakeEventLogger()
    state = PrinterState(last_state="idle", last_filename="file.gcode")
    states = {"P1": state}
    monitor = Monitor([printer], spoolman, telegram, states, logger)
    monitor._backoff_initial_seconds = 0
    monitor._backoff_max_seconds = 0

    monitor.process(printer)
    first_offline_since = state.offline_since
    monitor.process(printer)

    assert len(telegram.messages) == 1
    assert "Принтер недоступен" in telegram.messages[0]
    assert state.connection_state == "offline"
    assert state.offline_since == first_offline_since


def test_recovery_message_after_offline():
    printer = FakePrinter(
        "P1",
        [make_status("idle")],
        error="Moonraker down",
    )
    spoolman = FakeSpoolman()
    telegram = FakeTelegram()
    logger = FakeEventLogger()
    state = PrinterState(last_state="idle")
    states = {"P1": state}
    monitor = Monitor([printer], spoolman, telegram, states, logger)
    monitor._backoff_initial_seconds = 0
    monitor._backoff_max_seconds = 0

    monitor.process(printer)
    printer._error = None
    monitor.process(printer)

    assert len(telegram.messages) == 2
    assert "Принтер недоступен" in telegram.messages[0]
    assert "Соединение восстановлено" in telegram.messages[1]
    assert state.connection_state == "online"
    assert state.offline_since is None
    assert state.last_seen is not None


def test_spoolman_error_on_end_does_not_break_monitoring():
    class EndFailSpoolman:
        def get_spool_for_printer(self, printer_name):
            raise RuntimeError("spoolman unavailable")

        @staticmethod
        def filament_name(spool):
            return "Test PLA"

    printer = FakePrinter(
        "P1",
        [
            make_status("printing", filament=50.0, duration=10),
            make_status("complete", filament=120.0, duration=100),
        ],
    )
    spoolman = EndFailSpoolman()
    telegram = FakeTelegram()
    logger = FakeEventLogger()
    states = {"P1": PrinterState()}
    monitor = Monitor([printer], spoolman, telegram, states, logger)

    monitor.process(printer)
    monitor.process(printer)

    assert len(telegram.messages) == 2
    assert "Филамент:</b> неизвестно" in telegram.messages[1]
    assert logger.events[1][0] == "end"
