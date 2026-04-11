from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class StateRepository:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        if self.file_path.exists():
            return
        self.save({
            "processed_episode_ids": [],
            "last_sync_at": None,
        })

    def load(self) -> Dict[str, Any]:
        try:
            return json.loads(self.file_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"processed_episode_ids": [], "last_sync_at": None}

    def save(self, state: Dict[str, Any]) -> None:
        self.file_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
