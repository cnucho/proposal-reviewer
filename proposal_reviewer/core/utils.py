from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_text(path: Path, text: str) -> None:
    ensure_parent(path)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: dict) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict:
    return json.loads(read_text(path))


def relative_ref(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def make_id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{stamp}-{uuid.uuid4().hex[:8]}"


def safe_excerpt(text: str, *, max_chars: int = 5000) -> str:
    compact = text.strip()
    if len(compact) <= max_chars:
        return compact
    return compact[:max_chars] + "\n...[truncated]"
