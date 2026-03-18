from __future__ import annotations

from pathlib import Path

from .utils import read_json


def _resolve_result_path(root: Path, ref: str | Path) -> Path:
    ref_path = Path(ref)
    if ref_path.is_absolute():
        return ref_path.resolve()
    direct = (root / ref_path).resolve()
    if direct.exists():
        return direct
    if not str(ref).endswith(".json"):
        alt = (root / "results" / f"{ref}.json").resolve()
        if alt.exists():
            return alt
    raise FileNotFoundError(f"Review result not found: {ref}")


def summarize_review_result(root: str | Path, result_ref: str | Path) -> dict:
    root = Path(root).resolve()
    path = _resolve_result_path(root, result_ref)
    data = read_json(path)
    total = sum(item["score"] for item in data.get("scorecard", []))
    maximum = sum(item["max_score"] for item in data.get("scorecard", []))
    return {
        "result_ref": path.relative_to(root).as_posix(),
        "verdict": data.get("verdict"),
        "score_total": total,
        "score_max": maximum,
        "strength_count": len(data.get("strengths", [])),
        "finding_count": len(data.get("findings", [])),
        "required_revision_count": len(data.get("required_revisions", [])),
        "reviewer_summary": data.get("reviewer_summary", ""),
    }
