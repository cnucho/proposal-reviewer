from __future__ import annotations

import html
import json
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from jsonschema import Draft202012Validator

from .importer import import_review_request
from .review_request import create_review_request
from .review_result import summarize_review_result
from .store import load_workspace, save_workspace
from .templates import SUBMISSION_REVIEWER_URL, render_custom_gpt_prompt
from .utils import read_json, read_text, relative_ref, utc_now_iso, write_json
from .validator import validate_project

CATALOG_PATH = Path(r"D:/applications/proposal-gpt/catalog/proposal_gpt_catalog.html")
OVERVIEW_PATH = Path(r"D:/applications/proposal-gpt/catalog/proposal_ecosystem_overview.html")


def _esc(value: object) -> str:
    return html.escape(str(value))


def _workspace(root: Path) -> dict:
    data = load_workspace(root)
    data.setdefault("latest_refs", {})
    return data


def _request_items(root: Path) -> list[dict]:
    items = []
    for path in sorted((root / "requests").glob("*.json")):
        try:
            data = read_json(path)
        except Exception:
            continue
        items.append(
            {
                "id": data.get("id", path.stem),
                "title": data.get("title", path.stem),
                "focus": data.get("evaluation_focus", []),
                "created_at": data.get("created_at", ""),
                "path": path,
                "ref": relative_ref(root, path),
            }
        )
    return list(reversed(items))


def _result_items(root: Path) -> list[dict]:
    items = []
    for path in sorted((root / "results").glob("*.json")):
        try:
            summary = summarize_review_result(root, path)
        except Exception:
            continue
        summary["path"] = path
        summary["id"] = path.stem
        items.append(summary)
    return list(reversed(items))


def _save_result_json(root: Path, request_ref: str, raw_json: str) -> tuple[str, str]:
    request_path = _resolve_request_path(root, request_ref)
    request_data = read_json(request_path)
    data = json.loads(raw_json)
    validator = Draft202012Validator(read_json(root / "schemas" / "review_result_v1.schema.json"))
    errors = sorted(validator.iter_errors(data), key=lambda item: list(item.absolute_path))
    if errors:
        error = errors[0]
        where = ".".join(str(part) for part in error.absolute_path) or "$"
        raise ValueError(f"{where}: {error.message}")
    target = root / "results" / f"{data['id']}.json"
    write_json(target, data)
    workspace = _workspace(root)
    workspace["latest_refs"].update(
        {
            "latest_request": relative_ref(root, request_path),
            "latest_result": relative_ref(root, target),
        }
    )
    workspace["updated_at"] = utc_now_iso()
    save_workspace(root, workspace)
    return relative_ref(root, target), request_data.get("title", "")


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
    raise FileNotFoundError(f"Review request not found: {ref}")


def _layout(root: Path, *, title: str, body_html: str, message: str = "", active: str = "dashboard") -> str:
    workspace = _workspace(root)
    latest = workspace.get("latest_refs", {})
    tabs = [
        ("dashboard", "/", "????"),
        ("help", "/help", "???"),
    ]
    nav = []
    for key, href, label in tabs:
        cls = "active" if key == active else ""
        nav.append(f"<a class='{cls}' href='{href}'>{_esc(label)}</a>")
    return f"""
<!doctype html>
<html lang='ko'>
<head>
<meta charset='utf-8'/>
<meta name='viewport' content='width=device-width, initial-scale=1'/>
<title>{_esc(title)}</title>
<style>
:root {{
  --bg: #f5f1e8;
  --ink: #1f1b16;
  --card: rgba(255,255,255,0.88);
  --line: rgba(84,62,41,0.18);
  --accent: #9c4f2f;
  --accent-2: #2f5c63;
  --soft: #eadfce;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font-family: "Segoe UI", sans-serif; color: var(--ink); background: radial-gradient(circle at top left, #fff6e8, var(--bg) 45%), linear-gradient(135deg, #f0ece6, #f7f3ec); }}
a {{ color: var(--accent-2); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
header {{ padding: 28px 32px 12px; }}
header h1 {{ margin: 0 0 8px; font-size: 32px; }}
header p {{ margin: 0; max-width: 760px; line-height: 1.5; }}
.wrap {{ padding: 0 32px 32px; }}
nav {{ display: flex; gap: 10px; margin: 16px 0 20px; }}
nav a {{ padding: 10px 14px; border: 1px solid var(--line); border-radius: 999px; background: rgba(255,255,255,0.55); }}
nav a.active {{ background: var(--ink); color: #fff; border-color: var(--ink); }}
.grid {{ display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 18px; align-items: start; }}
.grid-2 {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }}
.card {{ background: var(--card); border: 1px solid var(--line); border-radius: 20px; padding: 20px; box-shadow: 0 10px 40px rgba(80,60,30,0.08); backdrop-filter: blur(10px); }}
.notice {{ margin-bottom: 16px; background: #fff3cc; border: 1px solid #e8d08d; border-radius: 14px; padding: 14px 16px; white-space: pre-wrap; }}
textarea, input[type=text] {{ width: 100%; padding: 10px 12px; border-radius: 12px; border: 1px solid var(--line); background: rgba(255,255,255,0.92); }}
textarea {{ min-height: 100px; resize: vertical; }}
button {{ cursor: pointer; border: 0; border-radius: 999px; padding: 10px 14px; background: var(--accent); color: white; }}
button.secondary {{ background: #6d786d; }}
button.ghost {{ background: transparent; color: var(--accent); border: 1px solid var(--line); }}
.small {{ color: #5e5347; font-size: 13px; line-height: 1.5; }}
.list {{ display: grid; gap: 12px; }}
.item {{ border: 1px solid var(--line); border-radius: 16px; padding: 14px; background: rgba(255,255,255,0.72); }}
.badge {{ display: inline-block; padding: 4px 9px; border-radius: 999px; background: var(--soft); margin-right: 6px; margin-bottom: 6px; font-size: 12px; }}
pre {{ white-space: pre-wrap; word-break: break-word; background: rgba(39,29,22,0.92); color: #f6f1e7; padding: 14px; border-radius: 14px; min-height: 160px; }}
.codebox {{ white-space: pre-wrap; word-break: break-word; min-height: 240px; background: rgba(39,29,22,0.94); color: #f5ecdf; border-radius: 16px; padding: 16px; }}
.hero {{ display: grid; grid-template-columns: 1.1fr 0.9fr; gap: 18px; }}
.stat {{ padding: 14px; border-radius: 16px; background: linear-gradient(135deg, rgba(156,79,47,0.12), rgba(47,92,99,0.10)); border: 1px solid var(--line); }}
footer {{ margin-top: 24px; font-size: 12px; color: #655a4f; }}
@media (max-width: 980px) {{ .grid, .grid-2, .hero {{ grid-template-columns: 1fr; }} .wrap, header {{ padding-left: 18px; padding-right: 18px; }} }}
</style>
</head>
<body>
<header>
  <h1>??? ?? ??????</h1>
  <p>Use this workspace to keep proposal review independent from the writer. The app manages requests and results, while the Custom GPT performs the actual evaluation.</p>
  <nav>{''.join(nav)}</nav>
</header>
<div class='wrap'>
  {f"<div class='notice'>{_esc(message)}</div>" if message else ''}
  <div class='small' style='margin-bottom:16px'>
    workspace: {_esc(root.name)} | latest_request: {_esc(latest.get('latest_request', '-'))} | latest_result: {_esc(latest.get('latest_result', '-'))}
  </div>
  {body_html}
  <footer>?? GPT: <a href='{_esc(SUBMISSION_REVIEWER_URL)}' target='_blank' rel='noreferrer'>Proposal Submission Reviewer</a> | ??? ??: {_esc(OVERVIEW_PATH)} | GPT ????: {_esc(CATALOG_PATH)}</footer>
</div>
</body>
</html>
"""


def render_dashboard_html(root: Path, *, message: str = "") -> str:
    requests = _request_items(root)
    results = _result_items(root)
    workspace = _workspace(root)
    body = f"""
<div class='hero'>
  <div class='card'>
    <h2>?? ??</h2>
    <div class='small'>
      1. Export a review request JSON from the writer app, or create a request here from proposal and RFP files.<br/>
      2. Open the saved request and render the Custom GPT prompt.<br/>
      3. Run the Proposal Submission Reviewer GPT and paste the returned JSON result here.<br/>
      4. Save the structured result so verdict, findings, and revision actions remain traceable.
    </div>
    <div style='margin-top:14px'>
      <a href='{_esc(SUBMISSION_REVIEWER_URL)}' target='_blank' rel='noreferrer'><button>Submission Reviewer ??</button></a>
      <a href='/help'><button class='ghost'>??? ??</button></a>
    </div>
  </div>
  <div class='card'>
    <h2>???? ??</h2>
    <div class='stat'><strong>requests</strong><div>{len(requests)}</div></div>
    <div class='stat' style='margin-top:10px'><strong>results</strong><div>{len(results)}</div></div>
    <div class='stat' style='margin-top:10px'><strong>latest prompt</strong><div class='small'>{_esc(workspace.get('latest_refs', {}).get('latest_prompt', '-'))}</div></div>
  </div>
</div>
<div class='grid' style='margin-top:18px'>
  <div class='card'>
    <h2>?? ?? ???</h2>
    <form method='post' action='/create-request'>
      <label>??</label><br/>
      <input type='text' name='title' required placeholder='?: STSI ??? 1? ??'/><br/><br/>
      <label>??? ??? ??</label><br/>
      <input type='text' name='proposal_ref' required placeholder='raw/proposals/proposal.md'/><br/><br/>
      <label>RFP ??? ??</label><br/>
      <input type='text' name='rfp_ref' required placeholder='raw/rfp/rfp.txt'/><br/><br/>
      <label>?? ?? (? ?? ??)</label><br/>
      <textarea name='focus' placeholder='requirement traceability
execution feasibility
evaluator trust'></textarea><br/><br/>
      <button type='submit'>?? ?? ??</button>
    </form>
    <hr style='margin:20px 0; border:none; border-top:1px solid var(--line)'/>
    <h3>Writer JSON ?? ????</h3>
    <form method='post' action='/import-request'>
      <label>?? ?? JSON ??</label><br/>
      <input type='text' name='bundle_ref' required placeholder='D:/applications/.../review-request-001.json'/><br/><br/>
      <button class='secondary' type='submit'>JSON ????</button>
    </form>
  </div>
  <div class='card'>
    <h2>?? ??? ??? ??</h2>
    <div class='small'>
      The reviewer is intentionally stricter than the writer. It should judge submission safety, not just writing fluency.<br/><br/>
      Recommended sequence:<br/>
      1. Draft in Phase G or STSI writer<br/>
      2. Use Proposal Red Team for internal attack review<br/>
      3. Revise the draft<br/>
      4. Use Proposal Submission Reviewer for final go/no-go judgment
    </div>
    <div style='margin-top:14px'>
      <span class='badge'>Writer? ???</span>
      <span class='badge'>Red Team? ?? ??</span>
      <span class='badge'>Submission Reviewer? ?? ??</span>
    </div>
  </div>
</div>
<div class='grid-2' style='margin-top:18px'>
  <div class='card'>
    <h2>?? ?? ??</h2>
    <div class='list'>
      {''.join(_request_card(root, item) for item in requests) or "<div class='small'>?? ?? ??? ????.</div>"}
    </div>
  </div>
  <div class='card'>
    <h2>??? ??</h2>
    <div class='list'>
      {''.join(_result_card(root, item) for item in results) or "<div class='small'>?? ??? ?? ??? ????.</div>"}
    </div>
  </div>
</div>
"""
    return _layout(root, title="Proposal Reviewer", body_html=body, message=message, active="dashboard")


def _request_card(root: Path, item: dict) -> str:
    return f"""
<div class='item'>
  <strong>{_esc(item['title'])}</strong><br/>
  <div class='small'>{_esc(item['id'])}</div>
  <div style='margin:8px 0'>{''.join(f"<span class='badge'>{_esc(x)}</span>" for x in item.get('focus', [])[:4])}</div>
  <div class='small'>created_at: {_esc(item.get('created_at', ''))}</div>
  <div style='margin-top:10px'>
    <a href='/request?ref={quote(item['ref'])}'><button class='ghost'>??</button></a>
    <a href='/file?ref={quote(item['ref'])}'><button class='ghost'>JSON ??</button></a>
  </div>
</div>
"""


def _result_card(root: Path, item: dict) -> str:
    return f"""
<div class='item'>
  <strong>{_esc(item['id'])}</strong><br/>
  <div style='margin:8px 0'>
    <span class='badge'>verdict: {_esc(item.get('verdict', '-'))}</span>
    <span class='badge'>score: {_esc(item.get('score_total', 0))}/{_esc(item.get('score_max', 0))}</span>
  </div>
  <div class='small'>{_esc(item.get('reviewer_summary', ''))}</div>
  <div style='margin-top:10px'>
    <a href='/file?ref={quote(item['result_ref'])}'><button class='ghost'>?? JSON ??</button></a>
  </div>
</div>
"""


def render_request_html(root: Path, request_ref: str, *, message: str = "") -> str:
    path = _resolve_request_path(root, request_ref)
    data = read_json(path)
    prompt = render_custom_gpt_prompt(root, path)
    body = f"""
<div class='grid'>
  <div class='card'>
    <h2>{_esc(data.get('title', data.get('id', 'Review Request')))}</h2>
    <div class='small'>request_id: {_esc(data.get('id', ''))}</div>
    <div style='margin-top:10px'>{''.join(f"<span class='badge'>{_esc(x)}</span>" for x in data.get('evaluation_focus', []))}</div>
    <p class='small'>proposal_ref: {_esc(data.get('proposal_ref', ''))}<br/>rfp_ref: {_esc(data.get('rfp_ref', ''))}</p>
    <p><a href='{_esc(SUBMISSION_REVIEWER_URL)}' target='_blank' rel='noreferrer'>Proposal Submission Reviewer ??</a></p>
    <p><a href='/'>????? ????</a></p>
  </div>
  <div class='card'>
    <h2>?? ??</h2>
    <div class='small'>
      1. Create or import a review request.<br/>
      2. Open the Proposal Submission Reviewer GPT.<br/>
      3. Paste the returned JSON into the result form and save it.<br/>
      4. Review the verdict, findings, and revision actions before submission.
    </div>
  </div>
</div>
<div class='grid-2' style='margin-top:18px'>
  <div class='card'>
    <h2>Proposal Excerpt</h2>
    <div class='codebox'>{_esc(data.get('proposal_excerpt', ''))}</div>
  </div>
  <div class='card'>
    <h2>RFP Excerpt</h2>
    <div class='codebox'>{_esc(data.get('rfp_excerpt', ''))}</div>
  </div>
</div>
<div class='card' style='margin-top:18px'>
  <h2>Custom GPT Prompt</h2>
  <textarea readonly style='min-height:320px'>{_esc(prompt)}</textarea>
</div>
<div class='card' style='margin-top:18px'>
  <h2>?? JSON ??</h2>
  <form method='post' action='/save-result'>
    <input type='hidden' name='request_ref' value='{_esc(relative_ref(root, path))}'/>
    <label>Custom GPT ?? JSON</label><br/>
    <textarea name='result_json' style='min-height:280px' placeholder='GPT? ??? ?? JSON? ??? ?? ????.'></textarea><br/><br/>
    <button type='submit'>?? ??</button>
  </form>
</div>
"""
    return _layout(root, title=f"Review Request {data.get('id', '')}", body_html=body, message=message, active="dashboard")


def render_help_html(root: Path, *, message: str = "") -> str:
    body = f"""
<div class='grid'>
  <div class='card'>
    <h2>? ?? ??</h2>
    <div class='small'>
      Proposal Reviewer exists to keep evaluation independent from drafting. It focuses on evaluator risk, evidence gaps, execution logic, and submission safety.
    </div>
    <div style='margin-top:14px'>
      <span class='badge'>?? ??</span>
      <span class='badge'>?? ??? ??</span>
      <span class='badge'>???? JSON ??</span>
    </div>
  </div>
  <div class='card'>
    <h2>?? GPT</h2>
    <div class='small'>
      Use multiple GPTs together instead of relying on one all-purpose GPT.<br/><br/>
      Proposal Researcher: evidence gathering<br/>
      Proposal Writer: drafting and revision<br/>
      Proposal Red Team: weakness attack review<br/>
      Proposal Submission Reviewer: final submission judgment
    </div>
    <p style='margin-top:12px'><a href='{_esc(SUBMISSION_REVIEWER_URL)}' target='_blank' rel='noreferrer'>Submission Reviewer ??</a></p>
  </div>
</div>
<div class='card' style='margin-top:18px'>
  <h2>?? ??</h2>
  <div class='small'>
    PowerShell:<br/><br/>
    cd D:/applications/proposal-reviewer<br/>
    python -m venv .venv<br/>
    ./.venv/Scripts/Activate.ps1<br/>
    python -m pip install --upgrade pip<br/>
    python -m pip install .[dev]<br/>
    python -m proposal_reviewer.cli launch ./demo_review --title "Proposal Review Workspace"<br/><br/>
    ?? ??: http://127.0.0.1:8877
  </div>
</div>
<div class='card' style='margin-top:18px'>
  <h2>GPT ????</h2>
  <div class='small'>
    Ecosystem overview HTML: {_esc(OVERVIEW_PATH)}<br/>
    GPT catalog HTML: {_esc(CATALOG_PATH)}<br/>
    ? ????? ? ? GPT? ??? ?? GPT? ??? ???? ??? ??? ??? ??? ?? ??? ?????.
  </div>
</div>
"""
    return _layout(root, title="Reviewer Help", body_html=body, message=message, active="help")


def serve_reviewer_ui(root: str | Path, *, host: str = "127.0.0.1", port: int = 8877, open_browser: bool = True) -> None:
    project_root = Path(root).resolve()

    class Handler(BaseHTTPRequestHandler):
        def _send_html(self, html_text: str, status: int = 200) -> None:
            payload = html_text.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _redirect(self, location: str) -> None:
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", location)
            self.end_headers()

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            message = params.get("msg", [""])[0]
            if parsed.path == "/":
                self._send_html(render_dashboard_html(project_root, message=message))
                return
            if parsed.path == "/help":
                self._send_html(render_help_html(project_root, message=message))
                return
            if parsed.path == "/request":
                ref = params.get("ref", [""])[0]
                self._send_html(render_request_html(project_root, unquote(ref), message=message))
                return
            if parsed.path == "/file":
                ref = params.get("ref", [""])[0]
                path = (project_root / unquote(ref)).resolve()
                if not path.exists():
                    self._send_html(_layout(project_root, title="Not Found", body_html="<div class='card'><h2>File not found.</h2></div>", message="file not found"), status=404)
                    return
                body = f"<div class='card'><h2>{_esc(path.name)}</h2><pre>{_esc(read_text(path))}</pre></div>"
                self._send_html(_layout(project_root, title=path.name, body_html=body, active="dashboard"))
                return
            self._send_html(_layout(project_root, title="Not Found", body_html="<div class='card'><h2>Page not found.</h2></div>"), status=404)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            form = {key: values[0] for key, values in parse_qs(raw).items()}
            try:
                if parsed.path == "/create-request":
                    focus = [line.strip() for line in form.get("focus", "").splitlines() if line.strip()]
                    report = create_review_request(
                        project_root,
                        title=form["title"],
                        proposal_ref=form["proposal_ref"],
                        rfp_ref=form["rfp_ref"],
                        focus=focus or None,
                    )
                    self._redirect(f"/request?ref={quote(report.request_ref)}&msg={quote('review request created')}")
                    return
                if parsed.path == "/import-request":
                    report = import_review_request(project_root, form["bundle_ref"])
                    self._redirect(f"/request?ref={quote(report.request_ref)}&msg={quote('review request imported')}")
                    return
                if parsed.path == "/save-result":
                    result_ref, title = _save_result_json(project_root, form["request_ref"], form["result_json"])
                    self._redirect(f"/?msg={quote(f'result saved for {title}: {result_ref}')}")
                    return
            except Exception as exc:
                target = "/help" if parsed.path == "/save-result" else "/"
                self._redirect(f"{target}?msg={quote(str(exc))}")
                return
            self._redirect("/?msg=unsupported action")

        def log_message(self, format: str, *args) -> None:
            return

    server = ThreadingHTTPServer((host, port), Handler)
    if open_browser:
        try:
            webbrowser.open(f"http://{host}:{port}")
        except Exception:
            pass
    print(f"Proposal Reviewer UI running on http://{host}:{port}")
    server.serve_forever()
