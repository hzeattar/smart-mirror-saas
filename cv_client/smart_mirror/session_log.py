from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


class SessionLogger:
    def __init__(self, data_dir: str | Path, enabled: bool = True):
        self.enabled = enabled
        self.path: Path | None = None
        self._pending_remote: list[dict] = []
        self.session_id = uuid.uuid4().hex
        self.sequence = 0
        if enabled:
            log_dir = Path(data_dir) / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            self.path = log_dir / f"session-{stamp}.jsonl"

    def event(self, name: str, severity: str = "info", **payload) -> dict | None:
        if not self.enabled or self.path is None:
            return None
        self.sequence += 1
        row = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "session_id": self.session_id,
            "sequence": self.sequence,
            "severity": severity,
            "event": name,
            **payload,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        self._pending_remote.append(row)
        return row

    def drain_remote(self, limit: int = 25) -> list[dict]:
        rows = self._pending_remote[:limit]
        del self._pending_remote[:limit]
        return rows

    def restore_remote(self, rows: list[dict]) -> None:
        self._pending_remote = rows + self._pending_remote
