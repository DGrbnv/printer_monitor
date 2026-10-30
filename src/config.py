import os
from pathlib import Path

import yaml
from dotenv import load_dotenv


class ConfigError(Exception):
    pass


class Config:
    def __init__(self, path: str):
        self.path = Path(path).resolve()
        self.base_dir = self.path.parent
        self._load_env()
        self.data = self._load()
        self._validate()
        self._resolve_paths()

    def _load_env(self):
        env_path = self.base_dir / ".env"
        load_dotenv(env_path, override=False)

    def _load(self):
        if not self.path.exists():
            raise ConfigError(f"Config file not found: {self.path}")

        with open(self.path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _validate(self):
        required = ("printers", "monitoring")
        for key in required:
            if key not in self.data:
                raise ConfigError(f"Missing '{key}' section in config")

        telegram = self.data.get("telegram", {})
        token = telegram.get("bot_token") or os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = telegram.get("chat_id") or os.getenv("TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            raise ConfigError("Missing Telegram credentials in config or env")

    def _resolve_paths(self):
        paths = self.data.setdefault("paths", {})

        data_dir = paths.get("data_dir", "data")
        logs_dir = paths.get("logs_dir", "logs")

        self.data_dir = (self.base_dir / data_dir).resolve()
        self.logs_dir = (self.base_dir / logs_dir).resolve()

        self.data_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)

        self.state_file = self.data_dir / paths.get("state_file", "printer_states.json")
        self.log_file = self.logs_dir / paths.get("log_file", "printer_monitor.log")
        self.db_file = self.data_dir / paths.get("db_file", "print_events.db")

    @property
    def printers(self):
        return self.data["printers"]

    @property
    def telegram(self) -> dict[str, str]:
        telegram = self.data.get("telegram", {})

        token = telegram.get("bot_token") or os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = telegram.get("chat_id") or os.getenv("TELEGRAM_CHAT_ID")

        if not isinstance(token, str) or not token:
            raise ConfigError("Invalid Telegram bot token")

        if not isinstance(chat_id, str) or not chat_id:
            raise ConfigError("Invalid Telegram chat ID")

        return {
            "bot_token": token,
            "chat_id": chat_id,
        }

    @property
    def monitoring(self):
        return self.data["monitoring"]

    @property
    def spoolman_url(self):
        spoolman = self.data.get("spoolman", {})
        return spoolman.get("url")

    @property
    def spoolman_cache_ttl_seconds(self) -> int:
        spoolman = self.data.get("spoolman", {})
        return int(spoolman.get("cache_ttl_seconds", 30))

    @property
    def spoolman_error_ttl_seconds(self) -> int:
        spoolman = self.data.get("spoolman", {})
        return int(spoolman.get("error_ttl_seconds", 5))

    @property
    def interval(self) -> int:
        env_interval = os.getenv("MONITOR_CHECK_INTERVAL")
        if env_interval:
            return int(env_interval)
        return int(self.data["monitoring"]["check_interval"])


    @property
    def telegram_retries(self) -> int:
        return int(self.data["monitoring"].get("telegram_retries", 3))
