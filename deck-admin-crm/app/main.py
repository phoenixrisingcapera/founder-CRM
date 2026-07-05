from __future__ import annotations

import base64
import hashlib
import hmac
import html
import os
import time
from collections import Counter
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

APP_NAME = os.getenv("ADMIN_CONSOLE_NAME", "Deck Admin Console")
ADMIN_CONSOLE_PASSWORD = os.getenv("ADMIN_CONSOLE_PASSWORD", "")
ADMIN_CONSOLE_SECRET = os.getenv("ADMIN_CONSOLE_SECRET", "")
DECK_API_URL = os.getenv("DECK_API_URL", "https://api.deck.aistack.codes").rstrip("/")
ADMIN_APP_URL = os.getenv("ADMIN_APP_URL", "https://deck.aistack.codes").rstrip("/")
SUPERADMIN_AISTACK_URL = os.getenv("SUPERADMIN_AISTACK_URL", "").rstrip("/")
USER_ADMIN_BOOTSTRAP_TOKEN = os.getenv("USER_ADMIN_BOOTSTRAP_TOKEN", "")
COOKIE_NAME = "deck_admin_console"
BACKEND_TOKEN_COOKIE = "deck_admin_backend_token"
SESSION_TTL_SECONDS = 8 * 60 * 60
ROLES = ("general", "user", "admin", "super_admin")
_BOOTSTRAP_TOKEN_USED = False
ADMIN_FEATURE_TABS = (
    ("Overview", "/admin"),
    ("Users", "/admin/users"),
    ("Agents", "/admin/agents"),
    ("Agent Teams", "/admin/agent-teams"),
    ("Telemetry", "/admin/telemetry"),
    ("Learning", "/admin/learning"),
    ("Failure Tickets", "/admin/failure-tickets"),
    ("Safety Controls", "/admin/safety-controls"),
    ("Audit", "/admin/audit"),
    ("Provider Health", "/admin/provider-health"),
    ("Quotas", "/admin/quotas"),
)

app = FastAPI(title=APP_NAME)


def _secret() -> bytes:
    return (ADMIN_CONSOLE_SECRET or ADMIN_CONSOLE_PASSWORD or "local-admin-console").encode()


def _sign(value: str) -> str:
    return hmac.new(_secret(), value.encode(), hashlib.sha256).hexdigest()


def _issue_session() -> str:
    payload = f"{int(time.time())}:admin"
    encoded = base64.urlsafe_b64encode(payload.encode()).decode()
    return f"{encoded}.{_sign(encoded)}"


def _valid_session(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    encoded, signature = token.rsplit(".", 1)
    if not hmac.compare_digest(signature, _sign(encoded)):
        return False
    try:
        raw = base64.urlsafe_b64decode(encoded.encode()).decode()
        issued_at_text, subject = raw.split(":", 1)
        issued_at = int(issued_at_text)
    except (ValueError, TypeError):
        return False
    return subject == "admin" and time.time() - issued_at <= SESSION_TTL_SECONDS


def _is_unlocked(request: Request) -> bool:
    return _valid_session(request.cookies.get(COOKIE_NAME))


def _backend_token(request: Request, fallback: str = "") -> str:
    token = request.cookies.get(BACKEND_TOKEN_COOKIE) or fallback
    return token.strip()


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _page(title: str, body: str, *, status_code: int = 200) -> HTMLResponse:
    return HTMLResponse(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_esc(title)}</title>
  <style>
    :root {{
      color-scheme: dark;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #09111f;
      color: #edf5ff;
    }}
    body {{ margin: 0; background: #09111f; }}
    main {{ width: min(1280px, calc(100vw - 32px)); margin: 28px auto 44px; }}
    header {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 22px; }}
    h1 {{ margin: 0; font-size: 28px; letter-spacing: 0; }}
    h2 {{ margin: 0 0 14px; font-size: 18px; }}
    h3 {{ margin: 0 0 8px; font-size: 14px; color: #b8c8df; }}
    a {{ color: #22bdf8; }}
    code {{ color: #b8e8ff; }}
    .muted {{ color: #9fb1c8; }}
    .panel {{ border: 1px solid #26344f; background: #101a2c; border-radius: 8px; padding: 18px; margin-bottom: 18px; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }}
    .metric-grid {{ display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; margin-bottom: 18px; }}
    .metric {{ border: 1px solid #283956; background: #0d1628; border-radius: 8px; padding: 14px; min-height: 82px; }}
    .metric span {{ display: block; color: #9fb1c8; font-size: 12px; text-transform: uppercase; }}
    .metric strong {{ display: block; font-size: 28px; margin-top: 8px; }}
    .status {{ padding: 12px 14px; border-radius: 8px; margin-bottom: 18px; }}
    .ok {{ background: #07351e; color: #9df2c1; }}
    .error {{ background: #3b1118; color: #ffc0c9; }}
    .pill {{ display: inline-flex; align-items: center; min-height: 24px; padding: 0 9px; border-radius: 999px; background: #20304a; color: #c9d8ee; font-size: 12px; }}
    .pill.good {{ background: #083b27; color: #95f1c0; }}
    .pill.bad {{ background: #40141d; color: #ffbdc7; }}
    .tabs {{ display: flex; gap: 8px; align-items: center; overflow-x: auto; padding: 8px; margin: 0 0 18px; border: 1px solid #26344f; background: #0d1628; border-radius: 8px; }}
    .tab {{ display: inline-flex; align-items: center; min-height: 34px; padding: 0 12px; border-radius: 7px; background: #15243b; color: #dceaff; text-decoration: none; font-size: 13px; font-weight: 700; white-space: nowrap; }}
    .tab:hover, .tab:focus {{ background: #1e3557; outline: none; }}
    .tab.primary {{ background: #14b8ff; color: #fff; }}
    .tab.secondary {{ background: #20304a; color: #dceaff; }}
    .flag {{ display: inline-flex; align-items: center; gap: 6px; min-height: 22px; padding: 0 9px; border-radius: 999px; font-size: 11px; font-weight: 800; letter-spacing: .02em; text-transform: uppercase; }}
    .flag.good {{ background: #083b27; color: #95f1c0; }}
    .flag.warn {{ background: #4a3310; color: #ffd786; }}
    .flag.bad {{ background: #40141d; color: #ffbdc7; }}
    .flag.neutral {{ background: #20304a; color: #c9d8ee; }}
    .section-heading {{ display: flex; justify-content: space-between; gap: 12px; align-items: center; margin-bottom: 14px; }}
    .section-heading h2 {{ margin: 0; }}
    .section-copy {{ color: #9fb1c8; margin: 4px 0 0; font-size: 13px; line-height: 1.5; }}
    .stack {{ display: grid; gap: 14px; }}
    .dashboard-hero {{ border: 1px solid #26344f; background: linear-gradient(160deg, rgba(20,184,255,.16), rgba(58,87,166,.12) 35%, #0d1628 72%); border-radius: 14px; padding: 18px; margin-bottom: 18px; }}
    .hero-top {{ display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; flex-wrap: wrap; }}
    .hero-title {{ margin: 0; font-size: 30px; }}
    .hero-meta {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }}
    .hero-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 16px; }}
    .card-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
    .soft-card {{ border: 1px solid #283956; background: #0d1628; border-radius: 10px; padding: 14px; min-width: 0; }}
    .soft-card h3 {{ margin: 0 0 8px; font-size: 14px; }}
    .soft-card p {{ margin: 0; color: #9fb1c8; line-height: 1.5; }}
    .soft-card .value {{ font-size: 24px; font-weight: 800; margin-top: 8px; }}
    .soft-card .value small {{ font-size: 12px; color: #9fb1c8; font-weight: 600; }}
    label {{ display: block; color: #c6d3e8; font-size: 13px; margin-bottom: 8px; }}
    input, select {{ box-sizing: border-box; width: 100%; border: 1px solid #314263; border-radius: 8px; background: #0b1425; color: #eef5ff; padding: 11px 12px; font: inherit; }}
    input[type="hidden"] {{ display: none; }}
    button {{ border: 0; border-radius: 8px; background: #14b8ff; color: white; font-weight: 700; padding: 11px 15px; cursor: pointer; white-space: nowrap; }}
    button.secondary {{ background: #25344f; }}
    .actions {{ display: flex; gap: 10px; align-items: center; margin-top: 14px; flex-wrap: wrap; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border-bottom: 1px solid #263552; padding: 11px 9px; text-align: left; vertical-align: middle; }}
    th {{ color: #9fb1c8; font-size: 12px; text-transform: uppercase; letter-spacing: .05em; }}
    td form {{ display: flex; gap: 8px; align-items: center; }}
    td select {{ min-width: 140px; }}
    .table-wrap {{ overflow-x: auto; }}
    .bar-row {{ display: grid; grid-template-columns: minmax(150px, 1fr) 4fr 56px; gap: 10px; align-items: center; margin: 10px 0; }}
    .bar {{ height: 10px; border-radius: 999px; background: #23324d; overflow: hidden; }}
    .bar > span {{ display: block; height: 100%; background: #22bdf8; }}
    .activity {{ display: grid; gap: 10px; }}
    .event {{ border: 1px solid #283956; background: #0d1628; border-radius: 8px; padding: 12px; }}
    .event-top {{ display: flex; justify-content: space-between; gap: 12px; align-items: center; }}
    .endpoint-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
    .endpoint {{ border: 1px solid #283956; background: #0d1628; border-radius: 8px; padding: 10px; }}
    .endpoint code {{ display: block; overflow-wrap: anywhere; }}
    .kv-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
    .kv {{ border: 1px solid #283956; background: #0d1628; border-radius: 8px; padding: 12px; min-width: 0; }}
    .kv span {{ display: block; font-size: 12px; text-transform: uppercase; color: #9fb1c8; margin-bottom: 8px; }}
    .kv strong {{ display: block; font-size: 15px; line-height: 1.45; overflow-wrap: anywhere; }}
    .kv small {{ display: block; color: #9fb1c8; margin-top: 4px; line-height: 1.4; }}
    .json-box {{ border: 1px solid #283956; background: #0b1425; border-radius: 8px; padding: 12px; overflow-x: auto; white-space: pre-wrap; color: #dbe7ff; font-size: 12px; line-height: 1.55; }}
    .artifacts {{ display: grid; gap: 10px; }}
    .artifact {{ border: 1px solid #283956; background: #0d1628; border-radius: 8px; padding: 12px; display: grid; gap: 6px; }}
    .artifact-top {{ display: flex; justify-content: space-between; gap: 10px; align-items: center; flex-wrap: wrap; }}
    .artifact-meta {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    .artifacts-table {{ display: grid; gap: 8px; }}
    .artifacts-row {{ display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr) minmax(120px, 160px); gap: 10px; padding: 10px 12px; border: 1px solid #283956; border-radius: 8px; background: #0d1628; align-items: center; }}
    .artifacts-row code {{ overflow-wrap: anywhere; }}
    .detail-columns {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }}
    .select-row {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 10px; align-items: end; }}
    @media (max-width: 1080px) {{
      .metric-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
      .endpoint-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .hero-grid, .card-grid, .kv-grid, .detail-columns {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (max-width: 760px) {{
      main {{ width: min(100vw - 20px, 1280px); margin-top: 18px; }}
      header, .grid {{ grid-template-columns: 1fr; flex-direction: column; }}
      .metric-grid, .endpoint-grid {{ grid-template-columns: 1fr; }}
      .hero-grid, .card-grid, .kv-grid, .detail-columns, .select-row, .artifacts-row {{ grid-template-columns: 1fr; }}
      .bar-row {{ grid-template-columns: 1fr; }}
      .section-heading {{ align-items: flex-start; flex-direction: column; }}
    }}
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>{_esc(APP_NAME)}</h1>
      <div class="muted">{_esc(DECK_API_URL)}</div>
    </div>
    <form method="post" action="/logout"><button class="secondary" type="submit">Lock console</button></form>
  </header>
  {body}
</main>
</body>
</html>""",
        status_code=status_code,
    )


def _message(kind: str, text: str | None) -> str:
    if not text:
        return ""
    css = "ok" if kind == "ok" else "error"
    return f'<div class="status {css}">{_esc(text)}</div>'


def _pill(label: str, kind: str = "neutral") -> str:
    return f'<span class="flag {kind}">{_esc(label)}</span>'


def _is_truthy_status(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"ok", "healthy", "ready", "success", "completed", "loaded", "configured", "active"}:
        return True
    if text in {"warn", "warning", "degraded", "partial", "limited", "pending", "missing"}:
        return None
    if text in {"error", "failed", "disabled", "unavailable", "revoked"}:
        return False
    return None


def _kind_from_state(value: Any) -> str:
    truthy = _is_truthy_status(value)
    if truthy is True:
        return "good"
    if truthy is False:
        return "bad"
    return "warn"


def _value_from_payload(payload: Any, key: str, fallback: Any = "—") -> Any:
    if isinstance(payload, dict):
        value = payload.get(key)
        if value not in (None, "", [], {}):
            return value
    return fallback


def _kv_cards(items: list[tuple[str, Any, str | None]] | list[dict[str, Any]]) -> str:
    cards: list[str] = []
    for item in items:
        if isinstance(item, dict):
            label = item.get("label", "")
            value = item.get("value", "—")
            detail = item.get("detail")
            kind = item.get("kind", "neutral")
        else:
            label, value, detail = item
            kind = "neutral"
        cards.append(
            f'<div class="kv"><span>{_esc(label)}</span><strong>{_esc(value)}</strong>'
            f'{f"<small>{_esc(detail)}</small>" if detail else ""}</div>'
        )
    return f'<div class="kv-grid">{"".join(cards)}</div>'


def _render_steps(steps: list[dict[str, Any]]) -> str:
    if not steps:
        return '<p class="muted">No pipeline details available yet.</p>'
    rows = []
    for step in steps:
        state = str(step.get("state") or step.get("status") or "unknown")
        rows.append(
            f'<div class="artifact"><div class="artifact-top"><strong>{_esc(step.get("label") or step.get("name") or "Step")}</strong>'
            f'{_pill(state, _kind_from_state(state))}</div>'
            f'<div class="muted">{_esc(step.get("statusMessage") or step.get("description") or "")}</div></div>'
        )
    return f'<div class="artifacts">{"".join(rows)}</div>'


def _render_artifact_list(items: list[dict[str, Any]] | None, *, title_key: str = "artifactType") -> str:
    if not items:
        return '<p class="muted">No artifacts found.</p>'
    rows = []
    for item in items[:18]:
        if not isinstance(item, dict):
            item = {"label": item, "summary": str(item)}
        label = item.get(title_key) or item.get("label") or item.get("name") or "artifact"
        status = item.get("status") or item.get("state") or "unknown"
        rows.append(
            f'<div class="artifact"><div class="artifact-top"><strong>{_esc(label)}</strong>{_pill(status, _kind_from_state(status))}</div>'
            f'<div class="artifact-meta">'
            f'{_pill(item.get("artifactKey") or item.get("storagePath") or item.get("id") or "n/a", "neutral")}'
            f'{_pill(item.get("provider") or item.get("storageProvider") or "unknown", "neutral")}'
            f'{_pill(item.get("model") or item.get("schemaVersion") or "details", "neutral")}'
            f'</div>'
            f'<div class="muted">{_esc(item.get("summary") or item.get("errorMessage") or item.get("createdAt") or "")}</div>'
            f'</div>'
        )
    return f'<div class="artifacts">{"".join(rows)}</div>'


def _render_failure_feed(items: list[dict[str, Any]] | None, *, empty_message: str) -> str:
    if not items:
        return f'<p class="muted">{_esc(empty_message)}</p>'
    rows = []
    for item in items[:12]:
        if not isinstance(item, dict):
            item = {"errorName": str(item), "detail": str(item)}
        rows.append(
            f'<div class="event">'
            f'<div class="event-top"><strong>{_esc(item.get("errorName") or item.get("action") or "Event")}</strong>'
            f'{_pill(item.get("severity") or "medium", _kind_from_state(item.get("severity")))}'
            f'</div>'
            f'<div class="muted">{_esc(item.get("route") or item.get("apiPath") or item.get("resourceType") or "")}</div>'
            f'<div class="muted">{_esc(item.get("failureStage") or item.get("action") or item.get("result") or "")} · request {_esc(item.get("requestId"))}</div>'
            f'<div class="muted">{_esc(item.get("errorMessage") or item.get("detail") or "")}</div>'
            f'</div>'
        )
    return f'<div class="activity">{"".join(rows)}</div>'


def _render_failure_ticket_status(value: Any) -> str:
    text = str(value or "new")
    return _pill(text, _kind_from_state(text))


def _render_failure_tickets_summary(tickets: list[dict[str, Any]] | None) -> str:
    items = tickets or []
    summary = {
        "new": 0,
        "acknowledged": 0,
        "investigating": 0,
        "fixed": 0,
        "ignored": 0,
    }
    for ticket in items:
        status = str(ticket.get("status") or "new")
        if status in summary:
            summary[status] += 1
    return _kv_cards(
        [
            ("Total tickets", len(items), "Current filtered set"),
            ("New", summary["new"], "Awaiting triage"),
            ("Acknowledged", summary["acknowledged"], "Marked as seen"),
            ("Investigating", summary["investigating"], "Active debugging"),
            ("Fixed", summary["fixed"], "Resolved tickets"),
            ("Ignored", summary["ignored"], "Suppressed noise"),
        ]
    )


def _render_failure_tickets_table(tickets: list[dict[str, Any]]) -> str:
    if not tickets:
        return '<p class="muted">No failure tickets matched these filters.</p>'

    rows = []
    for ticket in tickets[:200]:
        ticket_id = str(ticket.get("id") or "")
        rows.append(
            f"""
<tr>
  <td>{_esc(ticket.get("createdAt") or ticket.get("created_at") or "n/a")}</td>
  <td>{_render_failure_ticket_status(ticket.get("status"))}</td>
  <td>{_render_failure_ticket_status(ticket.get("severity"))}</td>
  <td>{_esc(ticket.get("source") or "frontend")}</td>
  <td>{_esc(ticket.get("route") or ticket.get("apiPath") or "n/a")}<br><small>{_esc(ticket.get("statusCode") or "no status")}</small></td>
  <td>{_esc(ticket.get("errorName") or "Error")}<br><small>{_esc(ticket.get("errorMessage") or "No message captured")}</small></td>
  <td>{_esc(ticket.get("userEmail") or ticket.get("userId") or "anonymous")}<br><small>{_esc(ticket.get("deckId") or "no deck")}</small></td>
  <td><a class="tab secondary" href="/admin/failure-tickets/{_esc(ticket_id)}">Open</a></td>
</tr>"""
        )
    return f"""
<div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th>Time</th>
        <th>Status</th>
        <th>Severity</th>
        <th>Source</th>
        <th>Location</th>
        <th>Error</th>
        <th>User</th>
        <th>Action</th>
      </tr>
    </thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</div>
"""


def _matches_failure_ticket_filters(ticket: dict[str, Any], *, ticket_id: str = "", user_email: str = "") -> bool:
    if ticket_id:
        haystack = " ".join(
            str(ticket.get(field) or "")
            for field in ("id", "route", "pageUrl", "apiPath", "errorName", "errorMessage", "userEmail", "userId")
        ).lower()
        if ticket_id.lower() not in haystack:
            return False
    if user_email:
        haystack = " ".join(
            str(ticket.get(field) or "")
            for field in ("userEmail", "userId", "route", "pageUrl", "apiPath", "errorMessage")
        ).lower()
        if user_email.lower() not in haystack:
            return False
    return True


def _failure_tickets_filters_form(
    *,
    filters: dict[str, Any],
    limit: int,
) -> str:
    status = str(filters.get("status") or "")
    severity = str(filters.get("severity") or "")
    source = str(filters.get("source") or "")
    deck_id = str(filters.get("deckId") or "")
    ticket_id = str(filters.get("ticketId") or "")
    user_email = str(filters.get("userEmail") or "")
    return f"""
<form method="get" action="/admin/failure-tickets" class="select-row">
  <div class="card-grid">
    <label>
      Status
      <select name="status">
        <option value="" {"selected" if not status else ""}>All statuses</option>
        {"".join(f'<option value="{status_value}" {"selected" if status == status_value else ""}>{status_value}</option>' for status_value in ["new", "acknowledged", "investigating", "fixed", "ignored"])}
      </select>
    </label>
    <label>
      Severity
      <select name="severity">
        <option value="" {"selected" if not severity else ""}>All severities</option>
        {"".join(f'<option value="{severity_value}" {"selected" if severity == severity_value else ""}>{severity_value}</option>' for severity_value in ["critical", "high", "medium", "low"])}
      </select>
    </label>
    <label>
      Source
      <select name="source">
        <option value="" {"selected" if not source else ""}>All sources</option>
        {"".join(f'<option value="{source_value}" {"selected" if source == source_value else ""}>{source_value}</option>' for source_value in ["frontend", "api", "backend", "loader", "fallback"])}
      </select>
    </label>
    <label>
      Deck ID
      <input name="deckId" value="{_esc(deck_id)}" placeholder="deck id">
    </label>
    <label>
      Ticket ID
      <input name="ticketId" value="{_esc(ticket_id)}" placeholder="fail_...">
    </label>
    <label>
      User email
      <input name="userEmail" value="{_esc(user_email)}" placeholder="tester@example.com">
    </label>
  </div>
  <div class="actions" style="margin-top: 0;">
    <input type="hidden" name="limit" value="{_esc(limit)}">
    <button type="submit">Apply filters</button>
    <a class="tab secondary" href="/admin/failure-tickets">Reset</a>
    <a class="tab secondary" href="/admin/failure-tickets?limit=250">Load 250</a>
  </div>
</form>
"""


def _render_failure_tickets_index(
    *,
    tickets: list[dict[str, Any]] | None,
    payload: dict[str, Any] | None,
    ok: str | None = None,
    error: str | None = None,
) -> HTMLResponse:
    tickets_list = tickets or []
    filters = (payload or {}).get("filters") or {}
    limit = int((payload or {}).get("limit") or 100)
    body = f"""
{_message("ok", ok)}
{_message("error", error)}
{_console_tabs(logged_in=True)}
<section class="panel">
  <div class="section-heading">
    <div>
      <h2>Failure Tickets</h2>
      <p class="section-copy">Use this page to triage frontend, loader, API, and backend failures without leaving the admin console.</p>
    </div>
    <a class="tab primary" href="/">Back to overview</a>
  </div>
  {_failure_tickets_filters_form(filters=filters, limit=limit)}
  <div style="height: 14px;"></div>
  {_render_failure_tickets_summary(tickets_list)}
</section>
<section class="panel">
  <div class="section-heading">
    <div>
      <h2>Ticket list</h2>
      <p class="section-copy">{_esc((payload or {}).get("total") or len(tickets_list))} total matching tickets. Redaction stays in place for stack traces and context.</p>
    </div>
    <a class="tab secondary" href="/">Back to dashboard</a>
  </div>
  {_render_failure_tickets_table(tickets_list)}
</section>
<section class="panel">
  <div class="section-heading">
    <div>
      <h2>Notes</h2>
      <p class="section-copy">This console reads the live backend ticket API, so it can be used to verify the same ticket records that the production frontend sees.</p>
    </div>
  </div>
</section>
"""
    return _page("Failure Tickets", body)


def _render_failure_ticket_detail(
    *,
    ticket: dict[str, Any] | None,
    token: str = "",
    ok: str | None = None,
    error: str | None = None,
) -> HTMLResponse:
    ticket = ticket or {}
    body = f"""
{_message("ok", ok)}
{_message("error", error)}
{_console_tabs(logged_in=True)}
<section class="panel">
  <div class="section-heading">
    <div>
      <h2>{_esc(ticket.get("errorName") or "Failure ticket")}</h2>
      <p class="section-copy">{_esc(ticket.get("errorMessage") or "No message captured.")}</p>
    </div>
    <a class="tab primary" href="/admin/failure-tickets">Back to list</a>
  </div>
  <div class="kv-grid">
    {_kv_cards([
        ("Time", ticket.get("createdAt") or ticket.get("created_at") or "n/a", ticket.get("updatedAt") or ticket.get("updated_at")),
        ("Status", ticket.get("status") or "new", "Workflow state"),
        ("Severity", ticket.get("severity") or "medium", "Impact level"),
        ("Source", ticket.get("source") or "frontend", "Where the failure originated"),
        ("User", ticket.get("userEmail") or ticket.get("userId") or "anonymous", ticket.get("requestId") or "no request id"),
        ("Deck", ticket.get("deckId") or "n/a", ticket.get("pageUrl") or ticket.get("route") or "n/a"),
    ])}
  </div>
</section>
<div class="grid">
  <section class="panel">
    <h2>Failure context</h2>
    <dl>
      <div><dt>Route</dt><dd>{_esc(ticket.get("route") or "n/a")}</dd></div>
      <div><dt>Page URL</dt><dd>{_esc(ticket.get("pageUrl") or "n/a")}</dd></div>
      <div><dt>API path</dt><dd>{_esc(ticket.get("apiPath") or "n/a")}</dd></div>
      <div><dt>Status code</dt><dd>{_esc(ticket.get("statusCode") or "n/a")}</dd></div>
      <div><dt>Redirected</dt><dd>{_esc(ticket.get("isUserRedirected") or ticket.get("is_user_redirected") or "false")}</dd></div>
      <div><dt>Redirect target</dt><dd>{_esc(ticket.get("redirectedTo") or ticket.get("redirected_to") or "n/a")}</dd></div>
    </dl>
  </section>
  <section class="panel">
    <h2>Admin action</h2>
    <form method="post" action="/admin/failure-tickets/{_esc(ticket.get("id") or "")}">
      <input type="hidden" name="token" value="{_esc(token)}">
      <label>Status</label>
      <select name="status">
        {"".join(f'<option value="{status}" {"selected" if ticket.get("status") == status else ""}>{status}</option>' for status in ["new", "acknowledged", "investigating", "fixed", "ignored"])}
      </select>
      <label style="margin-top: 12px;">Admin notes</label>
      <input type="text" name="admin_notes" value="{_esc(ticket.get("adminNotes") or ticket.get("admin_notes") or "")}" placeholder="Internal note">
      <div class="actions">
        <button type="submit">Save changes</button>
      </div>
    </form>
  </section>
</div>
<details class="panel">
  <summary>Technical payload</summary>
  <div class="grid">
    <section>
      <h3>Context JSON</h3>
      <pre>{_esc(str(ticket.get("context") or ticket.get("contextJson") or ticket.get("frontendContextJson") or {}))}</pre>
    </section>
    <section>
      <h3>Stack trace</h3>
      <pre>{_esc(ticket.get("errorStack") or ticket.get("error_stack") or "No stack captured.")}</pre>
    </section>
  </div>
</details>
"""
    return _page("Failure Ticket", body)


def _render_section_title(title: str, copy: str | None = None) -> str:
    return f"""
<div class="section-heading">
  <div>
    <h2>{_esc(title)}</h2>
    {f'<p class="section-copy">{_esc(copy)}</p>' if copy else ""}
  </div>
</div>
"""


def _deck_selector(decks: list[dict[str, Any]], selected_deck_id: str | None, token: str) -> str:
    if not decks:
        return '<p class="muted">No decks are available to inspect yet.</p>'
    current_deck = decks[0]
    options = []
    for deck in decks:
        deck_id = str(deck.get("id") or "")
        if deck_id and deck_id == selected_deck_id:
            current_deck = deck
        title = f'{deck.get("title") or "Untitled deck"} · {deck.get("status") or "unknown"}'
        options.append(f'<option value="{_esc(deck_id)}" {"selected" if deck_id and deck_id == selected_deck_id else ""}>{_esc(title)}</option>')
    return f"""
<form method="post" action="/dashboard" class="select-row">
  <div>
    <label>Focus deck</label>
    <input type="hidden" name="token" value="{_esc(token)}">
    <select name="deck_id">
      {"".join(options)}
    </select>
  </div>
  <div class="actions" style="margin-top: 0;">
    <button type="submit">Load deck</button>
  </div>
</form>
<div class="hero-meta">
  {_pill(current_deck.get("title") or "Deck", "neutral")}
  {_pill(current_deck.get("status") or "unknown", _kind_from_state(current_deck.get("status") or "unknown"))}
  {_pill(current_deck.get("audience") or "no audience", "neutral")}
  {_pill(current_deck.get("workspaceName") or "workspace", "neutral")}
</div>
"""


def _render_load_deck_panel(
    *,
    token: str,
    selected_deck_id: str | None,
    decks: list[dict[str, Any]] | None,
    processing: dict[str, Any] | None,
    slides: dict[str, Any] | None,
    storage_health: dict[str, Any] | None,
    llm_health: dict[str, Any] | None,
    provider_health: dict[str, Any] | None,
    storage_inventory: dict[str, Any] | None,
    failure_tickets: list[dict[str, Any]] | None,
    smart_deck_failures: list[dict[str, Any]] | None,
) -> str:
    selector = _deck_selector(decks or [], selected_deck_id, token)
    deck_cards = _render_deck_artifact_summary(processing)
    slide_cards = ""
    if slides:
        rows: list[str] = []
        for slide in (slides.get("slides") or [])[:8]:
            rows.append(
                f'<div class="artifact"><div class="artifact-top"><strong>{_esc(slide.get("slideNumber") or slide.get("slideIndex") or "Slide")} · {_esc(slide.get("title") or "Untitled")}</strong>'
                f'{_pill(slide.get("status") or slide.get("state") or "ready", _kind_from_state(slide.get("status") or slide.get("state") or "ready"))}</div>'
                f'<div class="muted">{_esc(slide.get("summary") or slide.get("textPreview") or slide.get("narrativeNotesPreview") or "")}</div></div>'
            )
        if rows:
            slide_cards = f'<div class="artifacts">{"".join(rows)}</div>'
    inventory_items = []
    if isinstance(storage_inventory, dict):
        inventory_items = storage_inventory.get("orphanObjects") or storage_inventory.get("missingReferences") or []
    if not inventory_items and isinstance(storage_inventory, dict):
        inventory_items = storage_inventory.get("items") or []
    inventory_markup = _render_artifact_list(inventory_items, title_key="key") if inventory_items else '<p class="muted">No storage inventory artifacts are available yet for this deck.</p>'
    return f"""
<section class="dashboard-hero">
  <div class="hero-top">
    <div>
      <div class="muted" style="text-transform: uppercase; letter-spacing: .14em; font-size: 12px;">Load deck workspace</div>
      <h2 class="hero-title">Inspect one deck end to end.</h2>
      <p class="section-copy">Use this workspace to verify the upload chain, deck records, slide assets, storage health, and failure tickets that were created for the selected deck.</p>
      <div class="hero-meta">
        {_pill("deck record", "neutral")}
        {_pill("bucket write", "neutral")}
        {_pill("slide artifacts", "neutral")}
        {_pill("failure tickets", "neutral")}
      </div>
    </div>
  </div>
  <div style="margin-top: 14px;">{selector}</div>
</section>
<div class="stack">
  <div class="card-grid">
    <section class="soft-card">
      <h3>Storage health</h3>
      <div class="hero-meta">
        {_pill((storage_health or {}).get("status") or "unknown", _kind_from_state((storage_health or {}).get("status") or "unknown"))}
        {_pill((storage_health or {}).get("provider") or "storage", "neutral")}
      </div>
      <p>{_esc((storage_health or {}).get("detail") or (storage_health or {}).get("message") or "Storage health is reported by the backend.")}</p>
    </section>
    <section class="soft-card">
      <h3>LLM health</h3>
      <div class="hero-meta">
        {_pill((llm_health or {}).get("status") or "unknown", _kind_from_state((llm_health or {}).get("status") or "unknown"))}
        {_pill((llm_health or {}).get("provider") or "llm", "neutral")}
      </div>
      <p>{_esc((llm_health or {}).get("detail") or (llm_health or {}).get("summary") or "Model provider and knowledge checks are reported by the backend.")}</p>
    </section>
    <section class="soft-card">
      <h3>Provider health</h3>
      <div class="hero-meta">
        {_pill((provider_health or {}).get("status") or "unknown", _kind_from_state((provider_health or {}).get("status") or "unknown"))}
        {_pill((provider_health or {}).get("workspaceState") or "workspace", "neutral")}
      </div>
      <p>{_esc((provider_health or {}).get("summary") or "Backend provider counts and recent failures.")}</p>
    </section>
  </div>
  <div class="detail-columns">
    <section class="soft-card">
      <h3>Storage inventory</h3>
      <p>Referenced and orphaned bucket objects surfaced by the backend.</p>
      {inventory_markup}
    </section>
    <section class="soft-card">
      <h3>Deck artifacts</h3>
      <p>Source files, pipeline state, generated versions, and payload traces for this deck.</p>
      {deck_cards}
    </section>
  </div>
  <div class="detail-columns">
    <section class="soft-card">
      <h3>Slides and miniatures</h3>
      <p>Slide-level records and stored previews linked to the selected deck.</p>
      {slide_cards or '<p class="muted">No slide records are available for the selected deck.</p>'}
    </section>
    <section class="soft-card">
      <h3>Failure tickets</h3>
      <p>Backend failure tickets and Smart Deck failure events recorded for this deck.</p>
      {_render_failure_feed(failure_tickets, empty_message="No generic failure tickets are available for this deck.")}
      <div style="height: 10px;"></div>
      {_render_failure_feed(smart_deck_failures, empty_message="No Smart Deck failure events are available for this deck.")}
    </section>
  </div>
</div>
"""


def _login_page(error: str | None = None) -> HTMLResponse:
    return _page(
        "Unlock Deck Admin Console",
        f"""
<section class="panel">
  <h2>Unlock Console</h2>
  {_message("error", error)}
  <form method="post" action="/login">
    <label>Admin console password</label>
    <input name="password" type="password" required autocomplete="current-password">
    <div class="actions"><button type="submit">Unlock</button></div>
  </form>
</section>
""",
        status_code=401 if error else 200,
    )


async def _request_backend(method: str, path: str, *, token: str = "", payload: dict[str, Any] | None = None, bootstrap: bool = False) -> tuple[int, Any]:
    headers: dict[str, str] = {}
    if token:
        headers["authorization"] = f"Bearer {token}"
    headers["x-request-id"] = f"deck-admin-{uuid.uuid4().hex[:16]}"
    if payload is not None:
        headers["content-type"] = "application/json"
    if bootstrap and USER_ADMIN_BOOTSTRAP_TOKEN:
        headers["x-user-admin-bootstrap-token"] = USER_ADMIN_BOOTSTRAP_TOKEN
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.request(method, f"{DECK_API_URL}{path}", json=payload, headers=headers)
    try:
        data = response.json() if response.content else None
    except ValueError:
        data = response.text
    return response.status_code, data


def _can_use_bootstrap_token() -> bool:
    return bool(USER_ADMIN_BOOTSTRAP_TOKEN) and not _BOOTSTRAP_TOKEN_USED


def _mark_bootstrap_token_used() -> None:
    global _BOOTSTRAP_TOKEN_USED
    _BOOTSTRAP_TOKEN_USED = True


def _extract_error(payload: Any, fallback: str) -> str:
    if isinstance(payload, dict):
        detail = payload.get("detail") or payload.get("message")
        if isinstance(detail, str):
            return detail
    if isinstance(payload, str) and payload:
        return payload[:280]
    return fallback


def _metric(label: str, value: Any) -> str:
    return f'<div class="metric"><span>{_esc(label)}</span><strong>{_esc(value)}</strong></div>'


def _bar_rows(items: dict[str, Any] | list[dict[str, Any]], *, label_key: str = "action") -> str:
    if isinstance(items, dict):
        normalized = [{"label": key, "count": value} for key, value in items.items()]
    else:
        normalized = [{"label": item.get(label_key, ""), "count": item.get("count", 0)} for item in items]
    max_count = max([int(item["count"] or 0) for item in normalized] or [1])
    if not normalized:
        return '<p class="muted">No data yet.</p>'
    rows = []
    for item in normalized:
        count = int(item["count"] or 0)
        width = max(4, round((count / max_count) * 100)) if max_count else 4
        rows.append(
            f'<div class="bar-row"><span>{_esc(item["label"])}</span><div class="bar"><span style="width:{width}%"></span></div><strong>{count}</strong></div>'
        )
    return "".join(rows)


def _endpoint_inventory(openapi: dict[str, Any] | None) -> str:
    if not openapi:
        return '<p class="muted">OpenAPI inventory unavailable.</p>'
    paths = openapi.get("paths", {})
    method_counter: Counter[str] = Counter()
    cards = []
    for path, methods in sorted(paths.items()):
        if not isinstance(methods, dict):
            continue
        method_names = [method.upper() for method in methods.keys() if method.lower() in {"get", "post", "put", "patch", "delete"}]
        for method in method_names:
            method_counter[method] += 1
        if path.startswith("/api/") or path in {"/health", "/"}:
            cards.append(f'<div class="endpoint"><span class="pill">{", ".join(method_names)}</span><code>{_esc(path)}</code></div>')
    return f"""
<div class="metric-grid">
  {_metric("Total endpoints", len(paths))}
  {_metric("GET", method_counter["GET"])}
  {_metric("POST", method_counter["POST"])}
  {_metric("PATCH", method_counter["PATCH"])}
  {_metric("PUT", method_counter["PUT"])}
  {_metric("DELETE", method_counter["DELETE"])}
</div>
<div class="endpoint-grid">{"".join(cards[:60])}</div>
"""


def _render_artifact_list(items: list[dict[str, Any]] | None, *, title_key: str = "artifactType") -> str:
    if not items:
        return '<p class="muted">No artifacts found.</p>'
    rows = []
    for item in items[:18]:
        label = item.get(title_key) or item.get("label") or item.get("name") or "artifact"
        status = item.get("status") or item.get("state") or "unknown"
        rows.append(
            f'<div class="artifact"><div class="artifact-top"><strong>{_esc(label)}</strong>{_pill(status, _kind_from_state(status))}</div>'
            f'<div class="artifact-meta">'
            f'{_pill(item.get("artifactKey") or item.get("storagePath") or item.get("id") or "n/a", "neutral")}'
            f'{_pill(item.get("provider") or item.get("storageProvider") or "unknown", "neutral")}'
            f'{_pill(item.get("model") or item.get("schemaVersion") or "details", "neutral")}'
            f'</div>'
            f'<div class="muted">{_esc(item.get("summary") or item.get("errorMessage") or item.get("createdAt") or "")}</div>'
            f'</div>'
        )
    return f'<div class="artifacts">{"".join(rows)}</div>'


def _render_failure_feed(items: list[dict[str, Any]] | None, *, empty_message: str) -> str:
    if not items:
        return f'<p class="muted">{_esc(empty_message)}</p>'
    rows = []
    for item in items[:12]:
        rows.append(
            f'<div class="event">'
            f'<div class="event-top"><strong>{_esc(item.get("errorName") or item.get("action") or "Event")}</strong>'
            f'{_pill(item.get("severity") or "medium", _kind_from_state(item.get("severity")))}'
            f'</div>'
            f'<div class="muted">{_esc(item.get("route") or item.get("apiPath") or item.get("resourceType") or "")}</div>'
            f'<div class="muted">{_esc(item.get("failureStage") or item.get("action") or item.get("result") or "")} · request {_esc(item.get("requestId"))}</div>'
            f'<div class="muted">{_esc(item.get("errorMessage") or item.get("detail") or "")}</div>'
            f'</div>'
        )
    return f'<div class="activity">{"".join(rows)}</div>'


def _render_pipeline_cards(steps: list[dict[str, Any]] | dict[str, Any] | None) -> str:
    if not steps:
        return '<p class="muted">No pipeline details available yet.</p>'
    normalized = steps if isinstance(steps, list) else [steps]
    rows = []
    for step in normalized[:10]:
        state = str(step.get("state") or step.get("status") or "unknown")
        rows.append(
            f'<div class="artifact"><div class="artifact-top"><strong>{_esc(step.get("label") or step.get("name") or "Step")}</strong>'
            f'{_pill(state, _kind_from_state(state))}</div>'
            f'<div class="muted">{_esc(step.get("statusMessage") or step.get("description") or "")}</div></div>'
        )
    return f'<div class="artifacts">{"".join(rows)}</div>'


def _render_deck_artifact_summary(processing: dict[str, Any] | None) -> str:
    if not processing:
        return '<p class="muted">Select a deck to inspect its upload, slide, and artifact pipeline.</p>'
    counts = processing.get("counts") if isinstance(processing, dict) else {}
    source_file = processing.get("sourceFile") if isinstance(processing, dict) else None
    structure_preview = processing.get("structurePreview") if isinstance(processing, dict) else None
    cards = _kv_cards(
        [
            ("Source slides", counts.get("slides", 0), "Persisted source structure"),
            ("Blocks", counts.get("blocks", 0), "Extracted slide blocks"),
            ("Assets", counts.get("assets", 0), "Slide and artifact assets"),
            ("Extraction runs", counts.get("extractionRuns", 0), "Upload and parse attempts"),
            ("Generation jobs", counts.get("generationJobs", 0), "Smart Deck runs"),
            ("Design versions", counts.get("designVersions", 0), "Preview/apply history"),
        ]
    )
    source_summary = '<p class="muted">No source file metadata available.</p>'
    if isinstance(source_file, dict):
        source_summary = _kv_cards(
            [
                ("Filename", source_file.get("filename") or "—", source_file.get("originalFilename")),
                ("Storage path", source_file.get("storage_path") or source_file.get("storagePath") or "—", source_file.get("storageProvider")),
                ("Size", source_file.get("size") or "—", f'Pages: {source_file.get("pageCount") or "—"}'),
                ("Uploaded", source_file.get("uploaded_at") or source_file.get("uploadedAt") or "—", None),
            ]
        )
    step_markup = _render_pipeline_cards(processing.get("pipeline") if isinstance(processing, dict) else None)
    slides_markup = ""
    slide_rows: list[str] = []
    if isinstance(structure_preview, dict):
        for slide in (structure_preview.get("slides") or [])[:4]:
            slide_rows.append(
                f'<div class="artifact"><div class="artifact-top"><strong>{_esc(slide.get("slideNumber") or slide.get("slideIndex") or "Slide")} · {_esc(slide.get("title") or "Untitled")}</strong>'
                f'{_pill(f"{len(slide.get("blocks") or [])} blocks", "neutral")}</div>'
                f'<div class="muted">{_esc(slide.get("textPreview") or slide.get("narrativeNotesPreview") or slide.get("summary") or "")}</div></div>'
            )
    if slide_rows:
        slides_markup = '<div class="artifacts">' + "".join(slide_rows) + '</div>'
    return f"""
<div class="stack">
  <div class="card-grid">
    <section class="soft-card">
      <h3>Deck intake</h3>
      <p>Source file and extraction state for the current deck.</p>
      {source_summary}
    </section>
    <section class="soft-card">
      <h3>Pipeline status</h3>
      <p>Backend steps for upload, extraction, generation, and versions.</p>
      {step_markup}
    </section>
    <section class="soft-card">
      <h3>Pipeline counts</h3>
      <p>Live backend totals for the focused deck.</p>
      {cards}
    </section>
  </div>
  <div class="detail-columns">
    <section class="soft-card">
      <h3>Structure preview</h3>
      <p>Source slides and their latest extracted summaries.</p>
      {slides_markup or '<p class="muted">No slide preview cards available.</p>'}
    </section>
    <section class="soft-card">
      <h3>Artifact payloads</h3>
      <p>Design versions, generation jobs, and storage-backed artifact keys.</p>
      {_render_artifact_list((processing.get("artifacts") if isinstance(processing, dict) else None), title_key="artifactType")}
    </section>
  </div>
</div>
"""


def _console_tabs(*, logged_in: bool) -> str:
    sections = [
        ("Access", "#access"),
        ("Overview", "#overview"),
        ("Smart Deck", "#smart-deck"),
        ("Failure Tickets", "/admin/failure-tickets"),
        ("Load Deck", "#load-deck"),
        ("Users", "#users"),
        ("Decks", "#decks"),
        ("Activity", "#activity"),
        ("Endpoints", "#endpoints"),
    ]
    if not logged_in:
        sections = sections[:1]
    return f'<nav class="tabs" aria-label="Admin console sections">{"".join(f"<a class=\"tab\" href=\"{href}\">{_esc(label)}</a>" for label, href in sections)}</nav>'


def _feature_tabs() -> str:
    links: list[str] = []
    if SUPERADMIN_AISTACK_URL:
        links.append(
            f'<a class="tab primary" href="{_esc(SUPERADMIN_AISTACK_URL)}" '
            'target="_blank" rel="noreferrer">Super Admin Service</a>'
        )
    links.extend(
        f'<a class="tab primary" href="{_esc(ADMIN_APP_URL + path)}" target="_blank" rel="noreferrer">{_esc(label)}</a>'
        for label, path in ADMIN_FEATURE_TABS
    )
    rendered_links = "".join(links)
    return f"""
<section class="panel" id="features">
  <div class="section-heading">
    <h2>Admin Feature Tabs</h2>
    <span class="muted">Opens the full app admin pages.</span>
  </div>
  <nav class="tabs" aria-label="Full admin feature pages">{rendered_links}</nav>
</section>
"""


def _users_table(users: list[dict[str, Any]], token: str) -> str:
    rows = []
    for user in users:
        current_role = str(user.get("role", "general"))
        options = "".join(
            f'<option value="{role}" {"selected" if role == current_role else ""}>{role}</option>'
            for role in ROLES
        )
        rows.append(
            f"""
<tr>
  <td>{_esc(user.get("name"))}</td>
  <td>{_esc(user.get("email"))}</td>
  <td><span class="pill">{_esc(current_role)}</span></td>
  <td>{_esc(user.get("created_at", user.get("createdAt", "")))}</td>
  <td>
    <form method="post" action="/role">
      <input type="hidden" name="token" value="{_esc(token)}">
      <input type="hidden" name="user_id" value="{_esc(user.get("id"))}">
      <select name="role">{options}</select>
      <button type="submit">Save</button>
    </form>
  </td>
</tr>"""
        )
    body = "".join(rows) or '<tr><td colspan="5" class="muted">No users found.</td></tr>'
    return f"""
<div class="table-wrap">
  <table>
    <thead><tr><th>Name</th><th>Email</th><th>Role</th><th>Created</th><th>Assign role</th></tr></thead>
    <tbody>{body}</tbody>
  </table>
</div>
"""


def _decks_table(decks: list[dict[str, Any]]) -> str:
    rows = []
    for deck in decks:
        rows.append(
            f"""
<tr>
  <td>{_esc(deck.get("title"))}</td>
  <td><span class="pill">{_esc(deck.get("status"))}</span></td>
  <td>{_esc(deck.get("audience"))}</td>
  <td>{_esc(deck.get("slideCount", deck.get("slide_count", "")))}</td>
  <td>{_esc(deck.get("userId", deck.get("user_id", "")))}</td>
  <td>{_esc(deck.get("createdAt", deck.get("created_at", "")))}</td>
</tr>"""
        )
    body = "".join(rows) or '<tr><td colspan="6" class="muted">No decks found.</td></tr>'
    return f"""
<div class="table-wrap">
  <table>
    <thead><tr><th>Deck</th><th>Status</th><th>Audience</th><th>Slides</th><th>User</th><th>Created</th></tr></thead>
    <tbody>{body}</tbody>
  </table>
</div>
"""


def _activity_list(events: list[dict[str, Any]]) -> str:
    if not events:
        return '<p class="muted">No backend activity has been recorded yet.</p>'
    cards = []
    for event in events[:30]:
        result = str(event.get("result", ""))
        pill_class = "good" if result == "success" else "bad" if result in {"failure", "denied"} else ""
        cards.append(
            f"""
<div class="event">
  <div class="event-top">
    <strong>{_esc(event.get("action"))}</strong>
    <span class="pill {pill_class}">{_esc(result)}</span>
  </div>
  <div class="muted">{_esc(event.get("createdAt"))} · {_esc(event.get("actorEmail") or event.get("actorUserId") or "anonymous")}</div>
  <div class="muted">{_esc(event.get("resourceType"))} {_esc(event.get("resourceId"))} · request {_esc(event.get("requestId"))}</div>
</div>"""
        )
    return f'<div class="activity">{"".join(cards)}</div>'


def _dashboard(
    *,
    token: str = "",
    users: list[dict[str, Any]] | None = None,
    analytics: dict[str, Any] | None = None,
    decks: list[dict[str, Any]] | None = None,
    selected_deck_id: str | None = None,
    health: dict[str, Any] | None = None,
    storage_health: dict[str, Any] | None = None,
    llm_health: dict[str, Any] | None = None,
    provider_health: dict[str, Any] | None = None,
    storage_inventory: dict[str, Any] | None = None,
    processing: dict[str, Any] | None = None,
    slides: dict[str, Any] | None = None,
    failure_ticket_count: int | None = None,
    failure_tickets: list[dict[str, Any]] | None = None,
    smart_deck_failures: list[dict[str, Any]] | None = None,
    observability: dict[str, Any] | None = None,
    openapi: dict[str, Any] | None = None,
    ok: str | None = None,
    error: str | None = None,
) -> HTMLResponse:
    summary = (analytics or {}).get("summary", {})
    health_status = "ok" if isinstance(health, dict) and health.get("status") == "ok" else "unknown"
    if not USER_ADMIN_BOOTSTRAP_TOKEN:
        bootstrap_note = "Not configured"
    elif _BOOTSTRAP_TOKEN_USED:
        bootstrap_note = "Consumed in this service session"
    else:
        bootstrap_note = "Configured (will be disabled after successful use)"
    metric_section = ""
    if analytics:
        metric_section = f"""
<div class="metric-grid">
  {_metric("Backend health", health_status)}
  {_metric("Users", summary.get("users", 0))}
  {_metric("Workspaces", summary.get("workspaces", 0))}
  {_metric("Decks", summary.get("decks", 0))}
  {_metric("Auth sessions", summary.get("authSessions", 0))}
  {_metric("Audit events", summary.get("auditEvents", 0))}
  {_metric("Failure tickets", failure_ticket_count if failure_ticket_count is not None else "—")}
</div>
"""

    logged_in = users is not None or analytics is not None
    failure_ticket_label = failure_ticket_count if failure_ticket_count is not None else "—"
    quick_actions = f"""
<section class="panel">
  <div class="section-heading">
    <div>
      <h2>Quick access</h2>
      <p class="section-copy">Jump straight to failure triage without opening the full feature panel.</p>
    </div>
  </div>
  <div class="actions">
    <a class="tab primary" href="/admin/failure-tickets">Open failure tickets</a>
    <span class="pill neutral">Current tickets: {_esc(failure_ticket_label)}</span>
  </div>
</section>
"""
    user_section = f'<section class="panel" id="users"><h2>Users</h2>{_users_table(users or [], token)}</section>' if users is not None else ""
    deck_section = f'<section class="panel" id="decks"><h2>Decks</h2>{_decks_table(decks or [])}</section>' if decks is not None else ""
    endpoint_section = f'<section class="panel" id="endpoints"><h2>Backend Endpoints and Pages</h2>{_endpoint_inventory(openapi)}</section>' if openapi else ""
    activity_section = f"""
<section class="panel">
  <h2>User Roles</h2>
  {_bar_rows(analytics.get("roleCounts", {}))}
</section>
<section class="panel">
  <h2>Deck Status</h2>
  {_bar_rows(analytics.get("deckStatusCounts", {}))}
</section>
<section class="panel">
  <h2>Top Backend Actions</h2>
  {_bar_rows(analytics.get("topActions", []))}
</section>
<section class="panel">
  <h2>API Results</h2>
  {_bar_rows(analytics.get("auditResultCounts", {}))}
</section>
<section class="panel">
  <h2>Recent User Testing Activity</h2>
  {_activity_list(analytics.get("recentActivity", []))}
</section>
""" if analytics else '<section class="panel"><p class="muted">No analytics data loaded yet.</p></section>'

    smart_deck_section = f"""
<section class="panel" id="smart-deck">
  {_render_section_title(
      "Smart Deck",
      "Backend health, Smart Deck failures, and the latest ticket trail for preview generation, apply, and discard flows.",
  )}
  <div class="card-grid">
    <section class="soft-card">
      <h3>Failure tickets</h3>
      <p>Visible ticket trail from the backend failure system.</p>
      {_render_failure_feed(failure_tickets, empty_message="No failure tickets have been recorded for the current workspace yet.")}
    </section>
    <section class="soft-card">
      <h3>Smart Deck failures</h3>
      <p>Preview and generation failures surfaced as admin-visible events.</p>
      {_render_failure_feed(smart_deck_failures, empty_message="No Smart Deck failure events have been recorded yet.")}
    </section>
    <section class="soft-card">
      <h3>Health flags</h3>
      <p>Quick status markers for storage, model provider, and observed workspace readiness.</p>
      <div class="hero-meta">
        {_pill((storage_health or {}).get("status") or "unknown", _kind_from_state((storage_health or {}).get("status") or "unknown"))}
        {_pill((llm_health or {}).get("status") or "unknown", _kind_from_state((llm_health or {}).get("status") or "unknown"))}
        {_pill((provider_health or {}).get("status") or "unknown", _kind_from_state((provider_health or {}).get("status") or "unknown"))}
        {_pill((observability or {}).get("status") or "unknown", _kind_from_state((observability or {}).get("status") or "unknown"))}
      </div>
      <div class="stack" style="margin-top: 12px;">
        {_kv_cards([
            ("Storage", (storage_health or {}).get("status") or "unknown", (storage_health or {}).get("message") or (storage_health or {}).get("detail")),
            ("LLM", (llm_health or {}).get("status") or "unknown", (llm_health or {}).get("detail") or (llm_health or {}).get("summary")),
            ("Provider", (provider_health or {}).get("status") or "unknown", (provider_health or {}).get("summary")),
        ])}
      </div>
    </section>
  </div>
</section>
"""

    load_deck_panel = _render_load_deck_panel(
        token=token,
        selected_deck_id=selected_deck_id,
        decks=decks,
        processing=processing,
        slides=slides,
        storage_health=storage_health,
        llm_health=llm_health,
        provider_health=provider_health,
        storage_inventory=storage_inventory,
        failure_tickets=failure_tickets,
        smart_deck_failures=smart_deck_failures,
    )

    return _page(
        APP_NAME,
        f"""
{_message("ok", ok)}
{_message("error", error)}
{_console_tabs(logged_in=logged_in)}
{_feature_tabs()}
<section id="overview">
  {metric_section}
</section>
{smart_deck_section}
{quick_actions}
<div class="grid" id="access">
  <section class="panel">
    <h2>Backend Super Admin Login</h2>
    <p class="muted">Sign in with a backend <code>super_admin</code> account to load the full console.</p>
    <form method="post" action="/backend-login">
      <label>Email</label>
      <input name="email" type="email" required autocomplete="username">
      <label>Password</label>
      <input name="password" type="password" required autocomplete="current-password">
      <div class="actions"><button type="submit">Load dashboard</button></div>
    </form>
  </section>
  <section class="panel">
    <h2>First Admin Bootstrap</h2>
    <p class="muted">Bootstrap token: {_esc(bootstrap_note)}. Rotate it after first use or when rotated upstream.</p>
    <form method="post" action="/bootstrap">
      <label>Signed-up user email</label>
      <input name="email" type="email" required>
      <label>Role</label>
      <select name="role">{"".join(f'<option value="{role}" {"selected" if role == "super_admin" else ""}>{role}</option>' for role in ROLES)}</select>
      <div class="actions"><button type="submit">Promote with bootstrap token</button></div>
    </form>
  </section>
</div>
<section class="panel">
  <h2>Manual Backend Token</h2>
  <form method="post" action="/dashboard">
    <label>Bearer token</label>
    <input name="token" value="{_esc(token)}" required>
    <label>Focused deck</label>
    <input name="deck_id" value="{_esc(selected_deck_id or "")}" placeholder="Optional deck id">
    <div class="actions"><button type="submit">Refresh dashboard</button></div>
  </form>
</section>
<section id="activity">
  {_render_section_title("Operational activity", "Cross-check backend actions, deck state, and the latest service behavior across the console.")}
  {activity_section}
</section>
{user_section}
{deck_section}
<section class="panel" id="load-deck">
  {_render_section_title("Load Deck", "Open a single deck and inspect the linked artifacts, slide records, and backend state that support the Smart Deck flow.")}
  {load_deck_panel}
</section>
{endpoint_section}
""",
    )


async def _load_dashboard(token: str, *, deck_id: str | None = None, ok: str | None = None, error: str | None = None) -> HTMLResponse:
    health_status, health = await _request_backend("GET", "/api/health")
    openapi_status, openapi = await _request_backend("GET", "/openapi.json")
    users_status, users_payload = await _request_backend("GET", "/api/admin/users", token=token)
    analytics_status, analytics_payload = await _request_backend("GET", "/api/admin/users/analytics", token=token)
    decks_status, decks_payload = await _request_backend("GET", "/api/decks", token=token)
    storage_health_status, storage_health = await _request_backend("GET", "/api/admin/storage/health", token=token)
    llm_health_status, llm_health = await _request_backend("GET", "/api/admin/llm-knowledge/health", token=token)
    provider_health_status, provider_health = await _request_backend("GET", "/api/admin/provider-health", token=token)
    observability_status, observability = await _request_backend("GET", "/api/admin/telemetry/observability", token=token)
    failure_tickets_status, failure_tickets_payload = await _request_backend("GET", "/api/admin/failure-tickets?limit=1", token=token)

    load_error = error
    users = users_payload if users_status < 400 and isinstance(users_payload, list) else None
    analytics = analytics_payload if analytics_status < 400 and isinstance(analytics_payload, dict) else None
    decks = []
    if decks_status < 400 and isinstance(decks_payload, dict):
        decks = decks_payload.get("decks", [])
    first_deck_id = None
    if decks:
        first_deck_id = str(decks[0].get("id") or "") or None
    selected_deck_id = deck_id or first_deck_id
    processing = None
    slides = None
    storage_inventory = None
    failure_tickets = None
    failure_ticket_count = None
    smart_deck_failures = None
    if failure_tickets_status < 400 and isinstance(failure_tickets_payload, dict):
        try:
            failure_ticket_count = int(failure_tickets_payload.get("total") or len(failure_tickets_payload.get("tickets") or []))
        except (TypeError, ValueError):
            failure_ticket_count = None
    if selected_deck_id:
        processing_status, processing_payload = await _request_backend("GET", f"/api/admin/decks/{selected_deck_id}/processing", token=token)
        slides_status, slides_payload = await _request_backend("GET", f"/api/admin/decks/{selected_deck_id}/slides", token=token)
        inventory_status, inventory_payload = await _request_backend("GET", f"/api/admin/storage/inventory?prefix={selected_deck_id}", token=token)
        failure_status, failure_payload = await _request_backend("GET", f"/api/admin/failure-tickets?limit=12&deckId={selected_deck_id}", token=token)
        smart_failure_status, smart_failure_payload = await _request_backend("GET", f"/api/admin/smart-deck/failures?limit=12&deckId={selected_deck_id}", token=token)
        processing = processing_payload if processing_status < 400 and isinstance(processing_payload, dict) else None
        slides = slides_payload if slides_status < 400 and isinstance(slides_payload, dict) else None
        storage_inventory = inventory_payload if inventory_status < 400 and isinstance(inventory_payload, dict) else None
        if failure_status < 400 and isinstance(failure_payload, dict):
            failure_tickets = failure_payload.get("items") or failure_payload.get("tickets") or failure_payload.get("results") or []
        if smart_failure_status < 400 and isinstance(smart_failure_payload, dict):
            smart_deck_failures = smart_failure_payload.get("items") or smart_failure_payload.get("events") or smart_failure_payload.get("results") or []
    if users is None:
        load_error = load_error or _extract_error(users_payload, "Could not load users. Make sure this account is super_admin.")
    if analytics is None:
        load_error = load_error or _extract_error(analytics_payload, "Could not load backend analytics.")

    return _dashboard(
        token=token,
        users=users,
        analytics=analytics,
        decks=decks,
        selected_deck_id=selected_deck_id,
        health=health if health_status < 400 and isinstance(health, dict) else None,
        storage_health=storage_health if storage_health_status < 400 and isinstance(storage_health, dict) else None,
        llm_health=llm_health if llm_health_status < 400 and isinstance(llm_health, dict) else None,
        provider_health=provider_health if provider_health_status < 400 and isinstance(provider_health, dict) else None,
        storage_inventory=storage_inventory,
        processing=processing,
        slides=slides,
        failure_ticket_count=failure_ticket_count,
        failure_tickets=failure_tickets,
        smart_deck_failures=smart_deck_failures,
        observability=observability if observability_status < 400 and isinstance(observability, dict) else None,
        openapi=openapi if openapi_status < 400 and isinstance(openapi, dict) else None,
        ok=ok,
        error=load_error,
    )


async def _load_failure_tickets(
    token: str,
    *,
    limit: int = 100,
    status: str | None = None,
    severity: str | None = None,
    source: str | None = None,
    deck_id: str | None = None,
    ticket_id: str | None = None,
    user_email: str | None = None,
    ok: str | None = None,
    error: str | None = None,
) -> HTMLResponse:
    query = [f"limit={limit}"]
    if status:
        query.append(f"status={status}")
    if severity:
        query.append(f"severity={severity}")
    if source:
        query.append(f"source={source}")
    if deck_id:
        query.append(f"deckId={deck_id}")
    query_string = "&".join(query)
    status_code, payload = await _request_backend("GET", f"/api/admin/failure-tickets?{query_string}", token=token)
    if status_code >= 400 or not isinstance(payload, dict):
        return _render_failure_tickets_index(
            tickets=[],
            payload={
                "limit": limit,
                "filters": {
                    "status": status,
                    "severity": severity,
                    "source": source,
                    "deckId": deck_id,
                    "ticketId": ticket_id,
                    "userEmail": user_email,
                },
            },
            ok=ok,
            error=_extract_error(payload, "Could not load failure tickets."),
        )
    tickets = payload.get("tickets") or payload.get("items") or payload.get("results") or []
    if isinstance(tickets, list):
        tickets = [
            ticket
            for ticket in tickets
            if isinstance(ticket, dict)
            and _matches_failure_ticket_filters(ticket, ticket_id=ticket_id or "", user_email=user_email or "")
        ]
    payload = {
        **payload,
        "filters": {
            **(payload.get("filters") or {}),
            "status": status,
            "severity": severity,
            "source": source,
            "deckId": deck_id,
            "ticketId": ticket_id,
            "userEmail": user_email,
        },
    }
    return _render_failure_tickets_index(tickets=tickets, payload=payload, ok=ok, error=error)


async def _load_failure_ticket_detail(
    token: str,
    ticket_id: str,
    *,
    ok: str | None = None,
    error: str | None = None,
) -> HTMLResponse:
    status_code, payload = await _request_backend("GET", f"/api/admin/failure-tickets/{ticket_id}", token=token)
    if status_code >= 400 or not isinstance(payload, dict):
        return _render_failure_ticket_detail(ticket={"id": ticket_id}, token=token, ok=ok, error=_extract_error(payload, "Could not load the ticket."))
    ticket = payload.get("ticket") if isinstance(payload.get("ticket"), dict) else payload
    return _render_failure_ticket_detail(ticket=ticket, token=token, ok=ok, error=error)


@app.middleware("http")
async def no_store_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["cache-control"] = "no-store"
    response.headers["x-content-type-options"] = "nosniff"
    response.headers["x-frame-options"] = "DENY"
    return response


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "deck-admin-console"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    if not _is_unlocked(request):
        return _login_page()
    return _dashboard()


@app.post("/login")
async def login(password: str = Form(...)) -> Response:
    if not ADMIN_CONSOLE_PASSWORD:
        return _login_page("ADMIN_CONSOLE_PASSWORD is not configured.")
    if not hmac.compare_digest(password, ADMIN_CONSOLE_PASSWORD):
        return _login_page("Invalid admin console password.")
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(COOKIE_NAME, _issue_session(), httponly=True, secure=True, samesite="lax", max_age=SESSION_TTL_SECONDS)
    return response


@app.post("/logout")
async def logout() -> Response:
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response


@app.post("/backend-login", response_class=HTMLResponse)
async def backend_login(request: Request, email: str = Form(...), password: str = Form(...)) -> HTMLResponse:
    if not _is_unlocked(request):
        return _login_page()
    status_code, payload = await _request_backend("POST", "/api/auth/sign-in", payload={"email": email, "password": password})
    if status_code >= 400 or not isinstance(payload, dict) or not payload.get("access_token"):
        return _dashboard(error=_extract_error(payload, "Backend sign-in failed."))
    response = await _load_dashboard(str(payload["access_token"]), ok="Backend super_admin signed in.")
    response.set_cookie(BACKEND_TOKEN_COOKIE, str(payload["access_token"]), httponly=True, secure=True, samesite="lax", max_age=SESSION_TTL_SECONDS)
    return response


@app.post("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, token: str = Form(...), deck_id: str | None = Form(None)) -> HTMLResponse:
    if not _is_unlocked(request):
        return _login_page()
    response = await _load_dashboard(token, deck_id=deck_id or None, ok="Dashboard refreshed.")
    response.set_cookie(BACKEND_TOKEN_COOKIE, token, httponly=True, secure=True, samesite="lax", max_age=SESSION_TTL_SECONDS)
    return response


@app.get("/admin/failure-tickets", response_class=HTMLResponse)
async def failure_tickets(request: Request) -> HTMLResponse:
    if not _is_unlocked(request):
        return _login_page()
    token = _backend_token(request, request.query_params.get("token", ""))
    if not token:
        return _dashboard(error="Provide a backend bearer token in the dashboard first, then use the Failure Tickets tab.")
    return await _load_failure_tickets(
        token,
        limit=int(request.query_params.get("limit", "100") or "100"),
        status=request.query_params.get("status"),
        severity=request.query_params.get("severity"),
        source=request.query_params.get("source"),
        deck_id=request.query_params.get("deckId"),
        ticket_id=request.query_params.get("ticketId"),
        user_email=request.query_params.get("userEmail"),
    )


@app.get("/admin/failure-tickets/{ticket_id}", response_class=HTMLResponse)
async def failure_ticket_detail(request: Request, ticket_id: str) -> HTMLResponse:
    if not _is_unlocked(request):
        return _login_page()
    token = _backend_token(request, request.query_params.get("token", ""))
    if not token:
        return _dashboard(error="Provide a backend bearer token in the dashboard first, then open the ticket detail page.")
    return await _load_failure_ticket_detail(token, ticket_id)


@app.post("/admin/failure-tickets/{ticket_id}", response_class=HTMLResponse)
async def failure_ticket_update(
    request: Request,
    ticket_id: str,
    token: str = Form(...),
    status: str = Form(...),
    admin_notes: str | None = Form(None),
) -> HTMLResponse:
    if not _is_unlocked(request):
        return _login_page()
    status_code, payload = await _request_backend(
        "PATCH",
        f"/api/admin/failure-tickets/{ticket_id}",
        token=token,
        payload={"status": status, "adminNotes": admin_notes or ""},
    )
    if status_code >= 400:
        return await _load_failure_ticket_detail(token, ticket_id, error=_extract_error(payload, "Could not update ticket."))
    return await _load_failure_ticket_detail(token, ticket_id, ok="Ticket updated.")


@app.post("/role", response_class=HTMLResponse)
async def role(request: Request, token: str = Form(...), user_id: str = Form(...), role: str = Form(...)) -> HTMLResponse:
    if not _is_unlocked(request):
        return _login_page()
    status_code, payload = await _request_backend("PATCH", f"/api/admin/users/{user_id}/role", token=token, payload={"role": role})
    if status_code >= 400:
        return await _load_dashboard(token, error=_extract_error(payload, "Could not update user role."))
    return await _load_dashboard(token, ok="Role updated. Ask the user to sign out and sign in again.")


@app.post("/bootstrap", response_class=HTMLResponse)
async def bootstrap(request: Request, email: str = Form(...), role: str = Form(...)) -> HTMLResponse:
    if not _is_unlocked(request):
        return _login_page()
    if not USER_ADMIN_BOOTSTRAP_TOKEN:
        return _dashboard(error="USER_ADMIN_BOOTSTRAP_TOKEN is not configured on this admin service.")
    if not _can_use_bootstrap_token():
        return _dashboard(error="Bootstrap token is already consumed for this service session. Rotate and retry.")
    status_code, payload = await _request_backend(
        "POST",
        "/api/admin/users/bootstrap-role",
        payload={"email": email, "role": role},
        bootstrap=True,
    )
    if status_code >= 400:
        return _dashboard(error=_extract_error(payload, "Bootstrap role update failed. Check the backend token and email."))
    _mark_bootstrap_token_used()
    return _dashboard(ok=f"{email} is now {role}. Ask the user to sign out and sign in again.")
