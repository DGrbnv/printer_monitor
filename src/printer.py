import requests


class PrinterAPI:
    def __init__(self, name: str, url: str, timeout: int = 5):
        self.name = name
        self.url = url.rstrip("/")
        self.timeout = timeout

    def get_status(self):
        try:
            r = requests.get(
                f"{self.url}/printer/objects/query?print_stats&display_status",
                timeout=self.timeout
            )
            r.raise_for_status()
            data = r.json()
            return data.get("result", {}).get("status", {})

        except requests.exceptions.RequestException as e:
            # Скрываем вложенный traceback requests/urllib3 в рабочем логе:
            # для мониторинга достаточно краткой причины недоступности.
            raise RuntimeError(
                f"{self.name}: Moonraker недоступен ({e})"
            ) from None
