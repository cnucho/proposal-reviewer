from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core.importer import import_review_request
from .core.project_init import init_project
from .core.review_request import create_review_request
from .core.review_result import summarize_review_result
from .core.templates import render_custom_gpt_prompt
from .core.validator import validate_project


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="proposal-reviewer",
        description="Standalone proposal reviewer for Custom GPT based evaluation.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init_parser = sub.add_parser("init", help="Initialize an empty reviewer project.")
    init_parser.add_argument("path", help="Target project directory.")
    init_parser.add_argument("--title", default="Proposal Review Workspace", help="Workspace title.")

    request_parser = sub.add_parser("make-review-request", help="Create a review request from proposal and RFP files.")
    request_parser.add_argument("path", help="Project directory.")
    request_parser.add_argument("--title", required=True, help="Review request title.")
    request_parser.add_argument("--proposal-ref", required=True, help="Project-relative proposal file path.")
    request_parser.add_argument("--rfp-ref", required=True, help="Project-relative RFP file path.")
    request_parser.add_argument("--focus", action="append", default=[], help="Evaluation focus area.")
    request_parser.add_argument("--request-id", default=None, help="Optional fixed request id.")

    import_parser = sub.add_parser("import-request", help="Import a review request bundle exported from the writer app.")
    import_parser.add_argument("path", help="Project directory.")
    import_parser.add_argument("bundle_ref", help="Absolute or relative path to a ReviewRequestV1 JSON file.")

    prompt_parser = sub.add_parser("render-custom-gpt", help="Render a strict Custom GPT evaluation prompt.")
    prompt_parser.add_argument("path", help="Project directory.")
    prompt_parser.add_argument("request_ref", help="Request id or request path.")

    summarize_parser = sub.add_parser("summarize-result", help="Summarize a review result file.")
    summarize_parser.add_argument("path", help="Project directory.")
    summarize_parser.add_argument("result_ref", help="Result id or result path.")

    validate_parser = sub.add_parser("validate", help="Validate requests and results against schemas.")
    validate_parser.add_argument("path", help="Project directory.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        path = init_project(args.path, title=args.title)
        print(f"Initialized reviewer project at: {path}")
        return 0
    if args.command == "make-review-request":
        report = create_review_request(
            args.path,
            title=args.title,
            proposal_ref=args.proposal_ref,
            rfp_ref=args.rfp_ref,
            focus=args.focus or None,
            request_id=args.request_id,
        )
        print(report.to_text())
        return 0 if report.ok else 1
    if args.command == "import-request":
        report = import_review_request(args.path, args.bundle_ref)
        print(report.to_text())
        return 0 if report.ok else 1
    if args.command == "render-custom-gpt":
        print(render_custom_gpt_prompt(args.path, args.request_ref))
        return 0
    if args.command == "summarize-result":
        print(json.dumps(summarize_review_result(args.path, args.result_ref), ensure_ascii=False, indent=2))
        return 0
    if args.command == "validate":
        report = validate_project(args.path)
        print(report.to_text())
        return 0 if report.ok else 1
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
