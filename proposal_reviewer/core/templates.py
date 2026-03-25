from __future__ import annotations

from pathlib import Path

from .utils import read_json, write_text


SUBMISSION_REVIEWER_URL = "https://chatgpt.com/g/g-69be092bffa88191925429d761e2d1c8-proposal-submission-reviewer"


SYSTEM_RULES = """You are a strict proposal evaluation GPT.

You are not the writer. You are an independent evaluator.
Judge the proposal against the RFP and evaluator expectations.

Evaluation priorities:
1. Proposal quality and strategic completeness
2. Operational reliability and execution realism
3. Usability and readability for evaluators

You must be tough on missing requirements, weak evidence, vague execution logic, and scoring risk.
Do not reward fluent writing when requirement coverage is weak.
Do not infer missing sections as present.
Do not be generous because the draft looks promising.
Return only valid JSON matching ReviewResultV1.
"""


RUBRIC_TEXT = """### Scoring Rubric

- Requirement Coverage
  Score 5: major RFP requirements are explicitly covered and easy to trace.
  Score 3: some coverage exists, but mapping is incomplete or weak.
  Score 1: key RFP requirements are absent, vague, or untraceable.
- Proposal Quality
  Score 5: the proposal is strategically complete, persuasive, and section logic is strong.
  Score 3: the proposal has useful content but still feels partial or uneven.
  Score 1: the proposal reads like an early draft, outline, or fragmented note set.
- Execution Feasibility
  Score 5: roadmap, roles, milestones, budget logic, and delivery mechanics are concrete.
  Score 3: execution is described but lacks operational detail.
  Score 1: execution claims are generic and would not reassure evaluators.
- Evaluator Trust
  Score 5: claims are supported, risks are addressed, and the document feels submission-ready.
  Score 3: some confidence exists but important proof or clarity is missing.
  Score 1: unsupported claims, missing evidence, or structural gaps make the proposal risky.
"""


JUDGMENT_RULES = """### Judgment Rules

- If the draft misses core RFP deliverables, roadmap elements, budget logic, governance, or traceability, the verdict should usually be `fail`.
- If the draft has strong intent but still has serious evaluator risk, the verdict should usually be `warn`.
- Only use `pass` when the proposal would likely survive a demanding human evaluation panel.
- Prefer specific criticism over generic writing advice.
- Findings should describe likely evaluator objections, not just stylistic concerns.
- Required revisions should be concrete enough that a writer can act on them immediately.
- If the RFP excerpt is weak or partially corrupted, mention that limitation in the findings, but still judge the proposal using the visible evidence.
"""


OUTPUT_RULES = """### Output Rules

- Return JSON only. Do not wrap it in markdown fences.
- Keep `strengths` concise and evidence-based.
- Provide at least 3 `findings` when verdict is `warn`.
- Provide at least 5 `findings` and 5 `required_revisions` when verdict is `fail`.
- `reviewer_summary` should read like an executive decision memo for a proposal manager.
"""


DECISION_LENS = """### Evaluator Decision Lens

Before scoring, ask yourself:

1. Would a serious evaluator believe this team fully understood the RFP?
2. Would a serious evaluator trust this team to execute the work without major ambiguity?
3. Would this draft survive side-by-side comparison with a stronger competing proposal?
4. Would this draft look submission-ready, or like an internal working draft?

If the honest answer to two or more of these is "no", the verdict should rarely be `pass`.
"""


SCORE_CONSISTENCY_RULES = """### Score Consistency Rules

- A proposal with missing core sections should not receive a high Proposal Quality score.
- A proposal with weak traceability should not receive a high Requirement Coverage score.
- A proposal with vague roadmap, budget, ownership, or milestones should not receive a high Execution Feasibility score.
- A proposal with unsupported claims or visible structural gaps should not receive a high Evaluator Trust score.
- If two or more scorecard items are 2 or below, the verdict should normally be `fail` or `warn`, not `pass`.
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
            f"Recommended GPT: {SUBMISSION_REVIEWER_URL}",
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
            RUBRIC_TEXT,
            "",
            JUDGMENT_RULES,
            "",
            DECISION_LENS,
            "",
            SCORE_CONSISTENCY_RULES,
            "",
            OUTPUT_RULES,
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
            "Compare the proposal against the RFP as if you are trying to decide whether this draft is safe to submit.",
            "Penalize missing structure, weak traceability, unsupported claims, shallow execution planning, and soft strategic logic.",
            "Focus on evaluator risk, score loss, and likely rejection reasons before commenting on style.",
            "Treat this as a red-team review for a proposal manager, not as friendly writing feedback.",
            "When in doubt, choose the harsher but defensible judgment rather than an optimistic interpretation.",
            "Required revisions should be ordered by what most improves submission readiness and score protection.",
        ]
    ).rstrip() + "\n"
    prompt_path = root / "prompts" / f"{data['id']}.custom_gpt.md"
    write_text(prompt_path, prompt)
    return prompt
