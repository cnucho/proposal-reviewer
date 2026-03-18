from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .store import load_workspace, save_workspace
from .utils import make_id, read_text, relative_ref, safe_excerpt, utc_now_iso, write_json


@dataclass
class ReviewRequestReport:
    ok: bool
    request_ref: str
    prompt_ref: str
    title: str

    def to_text(self) -> str:
        return "\n".join(
            [
                f"ok={self.ok}",
                f"title={self.title}",
                f"request_ref={self.request_ref}",
                f"prompt_ref={self.prompt_ref}",
            ]
        )


def create_review_request(
    root: str | Path,
    *,
    title: str,
    proposal_ref: str,
    rfp_ref: str,
    focus: list[str] | None = None,
    request_id: str | None = None,
) -> ReviewRequestReport:
    root = Path(root).resolve()
    proposal_path = (root / proposal_ref).resolve()
    rfp_path = (root / rfp_ref).resolve()
    if not proposal_path.exists():
        raise FileNotFoundError(f"Proposal file not found: {proposal_path}")
    if not rfp_path.exists():
        raise FileNotFoundError(f"RFP file not found: {rfp_path}")

    request_id = request_id or make_id("review-request")
    payload = {
        "schema_version": "ReviewRequestV1",
        "id": request_id,
        "title": title,
        "proposal_ref": relative_ref(root, proposal_path),
        "rfp_ref": relative_ref(root, rfp_path),
        "proposal_excerpt": safe_excerpt(read_text(proposal_path), max_chars=5000),
        "rfp_excerpt": safe_excerpt(read_text(rfp_path), max_chars=5000),
        "evaluation_focus": focus or [
            "proposal quality",
            "requirement traceability",
            "execution feasibility",
            "evaluator trust",
        ],
        "created_at": utc_now_iso(),
    }
    request_path = root / "requests" / f"{request_id}.json"
    prompt_path = root / "prompts" / f"{request_id}.custom_gpt.md"
    write_json(request_path, payload)
    workspace = load_workspace(root)
    workspace.setdefault("latest_refs", {}).update(
        {
            "latest_request": relative_ref(root, request_path),
            "latest_prompt": relative_ref(root, prompt_path),
        }
    )
    workspace["updated_at"] = utc_now_iso()
    save_workspace(root, workspace)
    return ReviewRequestReport(
        ok=True,
        request_ref=relative_ref(root, request_path),
        prompt_ref=relative_ref(root, prompt_path),
        title=title,
    )
