import time

import requests


class TelegramBot:
    def __init__(self, token: str, chat_id: str, retries: int = 3):
        self.token = token
        self.chat_id = chat_id
        self.retries = max(1, retries)

    def send(self, text: str):
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        self._post(url, json=payload)


    def _post(self, url: str, json=None):
        last_error = None
        for attempt in range(self.retries):
            try:
                r = requests.post(
                    url,
                    json=json,
                    timeout=10
                )
                r.raise_for_status()
                return
            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < self.retries - 1:
                    time.sleep(1 + attempt)
        raise RuntimeError(
            f"Telegram request failed after {self.retries} attempts "
            f"({type(last_error).__name__})"
        ) from None
