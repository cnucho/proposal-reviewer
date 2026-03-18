from __future__ import annotations

from pathlib import Path

from .utils import read_json, write_text


SYSTEM_RULES = """You are a strict proposal evaluation GPT.

You are not the writer. You are an independent evaluator.
Judge the proposal against the RFP and evaluator expectations.

Evaluation priorities:
1. Proposal quality and strategic completeness
2. Operational reliability and execution realism
3. Usability and readability for evaluators

You must be tough on missing requirements, weak evidence, vague execution logic, and scoring risk.
Return only valid JSON matching ReviewResultV1.
"""


def _resolve_request_path(root: Path, ref: str | Path) -> Path:
    ref_path = Path(ref)
    if ref_path.is_absolute():
        return ref_path.resolve()
    direct = (root / ref_path).resolve()
    if direct.exists():
        return direct
    if not str(ref).endswith(".json"):
        alt = (root / "requests" / f"{ref}.json").resolve()
        if alt.exists():
            return alt
    for path in sorted((root / "requests").glob("*.json")):
        try:
            data = read_json(path)
        except Exception:
            continue
        if data.get("id") == str(ref):
            return path.resolve()
    raise FileNotFoundError(f"Review request not found: {ref}")


def render_custom_gpt_prompt(root: str | Path, request_ref: str | Path) -> str:
    root = Path(root).resolve()
    path = _resolve_request_path(root, request_ref)
    data = read_json(path)
    prompt = "\n".join(
        [
            "# Custom GPT Review Prompt",
            "",
            "## System Rules",
            "",
            SYSTEM_RULES.strip(),
            "",
            "## Required Output Schema",
            "",
            """{
  "schema_version": "ReviewResultV1",
  "id": "result-...",
  "request_id": "review-request-...",
  "verdict": "pass|warn|fail",
  "scorecard": [
    {"label": "Requirement Coverage", "score": 1, "max_score": 5},
    {"label": "Proposal Quality", "score": 1, "max_score": 5},
    {"label": "Execution Feasibility", "score": 1, "max_score": 5},
    {"label": "Evaluator Trust", "score": 1, "max_score": 5}
  ],
  "strengths": ["..."],
  "findings": ["..."],
  "required_revisions": ["..."],
  "reviewer_summary": "..."
}""",
            "",
            "## Review Request",
            "",
            f"- request_id: {data['id']}",
            f"- title: {data['title']}",
            f"- proposal_ref: {data['proposal_ref']}",
            f"- rfp_ref: {data['rfp_ref']}",
            f"- evaluation_focus: {', '.join(data.get('evaluation_focus', []))}",
            "",
            "### Proposal Excerpt",
            "",
            data["proposal_excerpt"],
            "",
            "### RFP Excerpt",
            "",
            data["rfp_excerpt"],
            "",
            "### Instructions",
            "",
            "Compare the proposal against the RFP. Penalize missing structure, weak traceability, unsupported claims, and shallow execution planning.",
            "If the proposal would likely lose on evaluator confidence, return verdict=fail or verdict=warn.",
        ]
    ).rstrip() + "\n"
    prompt_path = root / "prompts" / f"{data['id']}.custom_gpt.md"
    write_text(prompt_path, prompt)
    return prompt
