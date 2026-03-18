from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .store import load_workspace, save_workspace
from .utils import read_json, relative_ref, utc_now_iso, write_json


@dataclass
class ImportRequestReport:
    ok: bool
    request_ref: str
    request_id: str

    def to_text(self) -> str:
        return "\n".join(
            [
                f"ok={self.ok}",
                f"request_id={self.request_id}",
                f"request_ref={self.request_ref}",
            ]
        )


def import_review_request(root: str | Path, bundle_ref: str | Path) -> ImportRequestReport:
    root = Path(root).resolve()
    bundle_path = Path(bundle_ref)
    full_path = bundle_path if bundle_path.is_absolute() else bundle_path.resolve()
    if not full_path.exists():
        raise FileNotFoundError(f"Review request bundle not found: {full_path}")

    data = read_json(full_path)
    request_id = data["id"]
    target_path = root / "requests" / f"{request_id}.json"
    write_json(target_path, data)

    workspace = load_workspace(root)
    workspace.setdefault("latest_refs", {}).update({"latest_request": relative_ref(root, target_path)})
    workspace["updated_at"] = utc_now_iso()
    save_workspace(root, workspace)

    return ImportRequestReport(ok=True, request_ref=relative_ref(root, target_path), request_id=request_id)
