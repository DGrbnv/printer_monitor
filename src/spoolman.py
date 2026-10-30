import time
import requests

_CACHE_MISS = object()


class SpoolmanAPI:
    def __init__(
        self,
        url: str,
        cache_ttl_seconds: int = 0,
        error_ttl_seconds: int = 0,
    ):
        self.url = url.rstrip("/") if url else None
        self.cache_ttl_seconds = max(0, int(cache_ttl_seconds))
        self.error_ttl_seconds = max(0, int(error_ttl_seconds))
        self._cache = {}
        self.last_error = False

    def _get_cached(self, printer_name: str):
        entry = self._cache.get(printer_name)
        if not entry:
            return _CACHE_MISS
        expires_at, spool = entry
        if time.monotonic() >= expires_at:
            self._cache.pop(printer_name, None)
            return _CACHE_MISS
        return spool

    def _store_cached(self, printer_name: str, spool, ttl_seconds: int):
        if ttl_seconds <= 0:
            return
        expires_at = time.monotonic() + ttl_seconds
        self._cache[printer_name] = (expires_at, spool)

    def get_spool_for_printer(self, printer_name: str):
        if not self.url:
            self.last_error = False
            return None
        cached = self._get_cached(printer_name)
        if cached is not _CACHE_MISS:
            self.last_error = False
            return cached
        try:
            r = requests.get(
                f"{self.url}/api/v1/spool",
                params={"location": printer_name, "limit": 1},
                timeout=5
            )
            if r.status_code != 200:
                self.last_error = True
                self._store_cached(printer_name, None, self.error_ttl_seconds)
                return None
            data = r.json()
            spool = data[0] if data else None
            self._store_cached(printer_name, spool, self.cache_ttl_seconds)
            self.last_error = False
            return spool
        except requests.exceptions.RequestException:
            self.last_error = True
            self._store_cached(printer_name, None, self.error_ttl_seconds)
            return None

    @staticmethod
    def filament_name(spool):
        filament = spool.get("filament", {})
        vendor = filament.get("vendor", {})
        brand = vendor.get("name") if isinstance(vendor, dict) else ""
        name = filament.get("name", "")
        material = filament.get("material", "PLA")
        return f"{brand} {name} ({material})".strip()
