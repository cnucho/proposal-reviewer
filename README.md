# Proposal Reviewer

`proposal-reviewer` is a standalone proposal review app designed to work with a Custom GPT evaluator.

It keeps the review process independent from the proposal authoring tool:

- the app manages review requests, result files, and validation
- the Custom GPT performs the actual evaluation
- the writer app can later export into this app and import the result back

## What It Does

- creates structured review requests from proposal and RFP text
- imports review request bundles from the writer app
- renders a strict Custom GPT prompt for proposal evaluation
- validates review requests and results against JSON schemas
- summarizes evaluator output into a quick review report

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install .[dev]
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install .[dev]
```

## Quick Start

Initialize a project:

```bash
python -m proposal_reviewer.cli init ./my_review_project --title "Proposal Review Workspace"
```

Import a review request bundle exported from the writer app:

```bash
python -m proposal_reviewer.cli import-request ./my_review_project ../writer_project/exports/handoff/review-request-001.json
```

Render the Custom GPT prompt:

```bash
python -m proposal_reviewer.cli render-custom-gpt ./my_review_project review-request-001
```

Validate the workspace:

```bash
python -m proposal_reviewer.cli validate ./my_review_project
```

## Default Layout

```text
raw/
  proposals/
  rfp/
requests/
results/
prompts/
state/
schemas/
```

## Review Philosophy

The reviewer is intentionally stricter than the writer.

- proposal quality is judged against the RFP, not against writing fluency alone
- requirement traceability matters more than surface polish
- missing evidence, weak execution logic, and scoring risk are treated as first-class defects

## Tests

```bash
python -m pytest -q
```
