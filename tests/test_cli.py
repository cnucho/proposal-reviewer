from proposal_reviewer.cli import main
from proposal_reviewer.core.project_init import init_project
from proposal_reviewer.core.review_request import create_review_request


def test_make_review_request_and_render_prompt(tmp_path, capsys):
    root = init_project(tmp_path / "reviewer")
    (root / "raw/proposals/proposal.md").write_text("# Proposal\n\nExecution plan", encoding="utf-8")
    (root / "raw/rfp/rfp.txt").write_text("RFP requires roadmap, budget, and governance.", encoding="utf-8")

    report = create_review_request(
        root,
        title="Test Request",
        proposal_ref="raw/proposals/proposal.md",
        rfp_ref="raw/rfp/rfp.txt",
    )
    assert report.ok is True

    assert main(["render-custom-gpt", str(root), "requests/" + report.request_ref.split("/")[-1]]) == 0
    out = capsys.readouterr().out
    assert "Custom GPT Review Prompt" in out
    assert "Return only valid JSON matching ReviewResultV1." in out


def test_validate_project_accepts_request_schema(tmp_path, capsys):
    root = init_project(tmp_path / "reviewer")
    (root / "raw/proposals/proposal.md").write_text("A proposal", encoding="utf-8")
    (root / "raw/rfp/rfp.txt").write_text("An RFP", encoding="utf-8")
    create_review_request(
        root,
        title="Validation Request",
        proposal_ref="raw/proposals/proposal.md",
        rfp_ref="raw/rfp/rfp.txt",
    )

    assert main(["validate", str(root)]) == 0
    out = capsys.readouterr().out
    assert "ok=True" in out
