import logging
import signal
import threading

from src.config import Config
from src.event_logger import EventLogger
from src.monitor import Monitor
from src.printer import PrinterAPI
from src.spoolman import SpoolmanAPI
from src.state_manager import StateManager
from src.telegram import TelegramBot
from src.utils import cleanup_logs, setup_logging

logger = logging.getLogger(__name__)


def main():
    cfg = Config("config.yaml")
    setup_logging(str(cfg.log_file), "INFO")
    cleanup_logs(cfg.log_file)

    printers = [
        PrinterAPI(name, data["url"])
        for name, data in cfg.printers.items()
    ]

    spoolman = SpoolmanAPI(
        cfg.spoolman_url,
        cache_ttl_seconds=cfg.spoolman_cache_ttl_seconds,
        error_ttl_seconds=cfg.spoolman_error_ttl_seconds
    )
    telegram = TelegramBot(
        cfg.telegram["bot_token"],
        cfg.telegram["chat_id"],
        cfg.telegram_retries
    )
    state_mgr = StateManager(cfg.state_file)
    event_logger = EventLogger(cfg.db_file)

    states = state_mgr.load(cfg.printers.keys())
    monitor = Monitor(
        printers,
        spoolman,
        telegram,
        states,
        event_logger
    )

    if cfg.monitoring.get("startup_message", True):
        telegram.send("🟢 <b>Мониторинг принтеров запущен</b>")

    shutdown_event = threading.Event()

    def _handle_shutdown(signum, frame):
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _handle_shutdown)

    try:
        while not shutdown_event.is_set():
            for printer in printers:
                monitor.process(printer)
            # Сохраняем снимок только при изменении состояния/прогресса/файла
            # или старта/окончания печати.
            state_mgr.save(states)
            shutdown_event.wait(cfg.interval)
    except KeyboardInterrupt:
        shutdown_event.set()
    finally:
        state_mgr.save(states)
        if shutdown_event.is_set() and cfg.monitoring.get("shutdown_message", False):
            try:
                telegram.send("🔴 <b>Мониторинг принтеров остановлен</b>")
            except Exception:
                logger.exception("Failed to send shutdown message to Telegram")


if __name__ == "__main__":
    main()
