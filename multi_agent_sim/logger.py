"""
logger.py
Conversation logger that writes transcript to file and keeps in-memory record.
"""
from typing import List, Tuple
import datetime


class ConversationLogger:
    def __init__(self, path: str | None = None):
        self.path = path
        self.records: List[Tuple[str, str, str]] = []  # (timestamp, role, message)

    def append(self, role: str, message: str) -> None:
        ts = datetime.datetime.utcnow().isoformat()
        self.records.append((ts, role, message))
        if self.path:
            try:
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(f"{ts}\t{role}: {message}\n\n")
            except Exception:
                pass

    def get_transcript(self) -> str:
        return "\n".join([f"{ts}\t{r}: {m}" for ts, r, m in self.records])

    def clear(self) -> None:
        self.records.clear()
        if self.path:
            try:
                open(self.path, "w", encoding="utf-8").close()
            except Exception:
                pass
