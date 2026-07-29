from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class SessionLogger:
    def __init__(self, data_dir: str | Path, enabled: bool = True):
        self.enabled = enabled
        self.path: Path | None = None
        if enabled:
            log_dir = Path(data_dir) / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            self.path = log_dir / f"session-{stamp}.jsonl"

    def event(self, name: str, **payload) -> None:
        if not self.enabled or self.path is None:
            return
        row = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": name,
            **payload,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
