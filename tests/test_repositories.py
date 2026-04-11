from pathlib import Path

from app.repositories.settings_repository import SettingsRepository


def test_settings_repository_creates_default_file(tmp_path: Path) -> None:
    repo = SettingsRepository(tmp_path / "settings.json")
    settings = repo.load()
    assert settings.interval_days == 14
