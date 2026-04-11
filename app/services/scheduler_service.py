from __future__ import annotations

from datetime import datetime
from typing import Set

from PySide6.QtCore import QTimer

from app.repositories.settings_repository import SettingsRepository
from app.services.sync_service import SyncService


class SchedulerService:
    def __init__(self, sync_service: SyncService, settings_repository: SettingsRepository) -> None:
        self.sync_service = sync_service
        self.settings_repository = settings_repository

        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)

        self._executed_keys_today: Set[str] = set()
        self._last_day: str = self._today_key()

    def start(self) -> None:
        self.timer.start(60_000)
        self._tick()

    def stop(self) -> None:
        self.timer.stop()

    def refresh(self) -> None:
        self._tick()

    def _tick(self) -> None:
        settings = self.settings_repository.load()

        if not settings.auto_sync_enabled:
            self._reset_day_if_needed()
            return

        now = datetime.now()
        self._reset_day_if_needed(now)

        current_time = now.strftime("%H:%M")
        today = now.strftime("%Y-%m-%d")

        valid_times = self._normalize_times(settings.sync_times)

        if current_time not in valid_times:
            return

        execution_key = f"{today} {current_time}"
        if execution_key in self._executed_keys_today:
            return

        try:
            self.sync_service.run_sync()
            self._executed_keys_today.add(execution_key)
        except Exception as exc:
            print(f"[Scheduler] Sync failed at {execution_key}: {exc}")

    def _normalize_times(self, times: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()

        for value in times:
            if not isinstance(value, str):
                continue

            candidate = value.strip()
            if not self._is_valid_time(candidate):
                continue

            if candidate in seen:
                continue

            seen.add(candidate)
            normalized.append(candidate)

        normalized.sort()
        return normalized

    def _is_valid_time(self, value: str) -> bool:
        try:
            datetime.strptime(value, "%H:%M")
            return True
        except ValueError:
            return False

    def _reset_day_if_needed(self, now: datetime | None = None) -> None:
        if now is None:
            now = datetime.now()

        current_day = now.strftime("%Y-%m-%d")
        if current_day != self._last_day:
            self._executed_keys_today.clear()
            self._last_day = current_day

    def _today_key(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")