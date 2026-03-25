from proposal_reviewer.cli import main
from proposal_reviewer.core.project_init import init_project
from proposal_reviewer.core.review_request import create_review_request
from proposal_reviewer.core.utils import read_json, write_json


def test_make_review_request_and_render_prompt(tmp_path, capsys):
    root = init_project(tmp_path / "reviewer")
    (root / "raw/proposals/proposal.md").write_text("# Proposal\n\nExecution plan", encoding="utf-8")
    (root / "raw/rfp/rfp.txt").write_text("RFP requires roadmap, budget, and governance.", encoding="utf-8")

    report = create_review_request(
        root,
        title="Test Request",
        proposal_ref="raw/proposals/proposal.md",
        rfp_ref="raw/rfp/rfp.txt",
        request_id="review-request-001",
    )
    assert report.ok is True

    assert main(["render-custom-gpt", str(root), "review-request-001"]) == 0
    out = capsys.readouterr().out
    assert "Custom GPT Review Prompt" in out
    assert "Recommended GPT: https://chatgpt.com/g/g-69be092bffa88191925429d761e2d1c8-proposal-submission-reviewer" in out
    assert "Return only valid JSON matching ReviewResultV1." in out
    assert "Scoring Rubric" in out
    assert "Judgment Rules" in out
    assert "Evaluator Decision Lens" in out
    assert "Score Consistency Rules" in out
    assert "trying to decide whether this draft is safe to submit" in out
    assert "choose the harsher but defensible judgment" in out


def test_import_request_bundle_and_validate(tmp_path, capsys):
    writer_bundle = tmp_path / "bundle.json"
    write_json(
        writer_bundle,
        {
            "schema_version": "ReviewRequestV1",
            "id": "review-request-imported",
            "title": "Imported Request",
            "proposal_ref": "exports/doc/proposal_export.md",
            "rfp_ref": "raw/rfp/rfp_excerpt.txt",
            "proposal_excerpt": "Proposal excerpt",
            "rfp_excerpt": "RFP excerpt",
            "evaluation_focus": ["proposal quality", "evaluator trust"],
            "created_at": "2026-03-18T00:00:00Z",
        },
    )

    root = init_project(tmp_path / "reviewer")
    assert main(["import-request", str(root), str(writer_bundle)]) == 0
    imported = read_json(root / "requests/review-request-imported.json")
    assert imported["title"] == "Imported Request"

    assert main(["validate", str(root)]) == 0
    out = capsys.readouterr().out
    assert "ok=True" in out
