from __future__ import annotations

from pathlib import Path

from .utils import read_json, write_json


def load_workspace(root: str | Path) -> dict:
    return read_json(Path(root).resolve() / "state/workspace.json")


def save_workspace(root: str | Path, data: dict) -> None:
    write_json(Path(root).resolve() / "state/workspace.json", data)
