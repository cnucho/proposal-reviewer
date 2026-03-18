from __future__ import annotations

from pathlib import Path

from .project_layout import PLACEHOLDER_FILES, REQUIRED_DIRECTORIES, REQUIRED_FILES
from .utils import ensure_parent, utc_now_iso, write_json, write_text


def init_project(path: str | Path, *, title: str = "Proposal Review Workspace") -> Path:
    root = Path(path).resolve()
    root.mkdir(parents=True, exist_ok=True)
    for rel in REQUIRED_DIRECTORIES:
        (root / rel).mkdir(parents=True, exist_ok=True)
    for rel in REQUIRED_FILES:
        target = root / rel
        ensure_parent(target)
        if not target.exists():
            target.write_text("", encoding="utf-8")
    for rel, content in PLACEHOLDER_FILES.items():
        target = root / rel
        if target.exists() and target.stat().st_size > 0:
            continue
        if rel.endswith(".json"):
            if isinstance(content, str):
                write_text(target, content)
            else:
                write_json(target, content)
        else:
            write_text(target, content)

    write_json(
        root / "state/workspace.json",
        {
            "schema_version": "ReviewerWorkspaceV1",
            "title": title,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "latest_refs": {},
        },
    )
    return root
