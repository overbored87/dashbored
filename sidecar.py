"""Dashbored's sidecar — exposes dashboard writes (todos/reminders, spending,
net worth) to Siren.

Implements Siren's sidecar contract v0:
    GET  /health
    POST /invoke  {"tool": ..., "args": {...}}  header X-Siren-Key
          -> {"result": ...}   (writes are fast — synchronous, no job_id)

Federation: Siren READS dashboard_entries directly, but every write is
delegated here so Dashbored stays the single owner of its tables. Rows are
written straight to the Dashbored Supabase project via its REST API, matching
the Telegram bot's row shape exactly (jsonb `data` object, string user_id, UTC
created_at, todos default status/tags) so the dashboard renders them and the
bot's own reminder checker fires todo reminders — a todo carrying a
`reminder_time` (and not yet `reminded`/`done`) is picked up automatically.

Runs as its own lightweight Railway service alongside the bot: same repo,
different start command (`uvicorn sidecar:app --host 0.0.0.0 --port $PORT`). It
does NOT import telegram_bot (that would pull in python-telegram-bot and every
var it reads at import); it just re-uses the same DATABASE_* env.

Env: SIREN_API_KEY (shared secret Siren sends as X-Siren-Key),
     DATABASE_URL, DATABASE_KEY (Dashbored Supabase, service role),
     DATABASE_TABLE (optional, default dashboard_entries),
     DASHBORED_USER_ID (your Telegram id — stamped on rows so reminders reach
     you; the bot's reminder checker sends to this id).
"""

import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, Header, HTTPException

app = FastAPI(title="Dashbored sidecar")

SIREN_API_KEY = os.environ.get("SIREN_API_KEY", "")
DATABASE_URL = os.environ["DATABASE_URL"].rstrip("/")
DATABASE_KEY = os.environ["DATABASE_KEY"]
DATABASE_TABLE = os.environ.get("DATABASE_TABLE", "dashboard_entries")
USER_ID = os.environ.get("DASHBORED_USER_ID", "")
_TZ = ZoneInfo("Asia/Singapore")

VALID_PRIORITY = {"high", "medium", "low"}
VALID_STATUS = {"pending", "in_progress", "done"}

# One keep-alive pool for all Supabase REST calls.
_http = httpx.Client(
    base_url=f"{DATABASE_URL}/rest/v1",
    headers={
        "apikey": DATABASE_KEY,
        "Authorization": f"Bearer {DATABASE_KEY}",
        "Content-Type": "application/json",
    },
    timeout=15.0,
)


def _auth(x_siren_key: str) -> None:
    if not SIREN_API_KEY or x_siren_key != SIREN_API_KEY:
        raise HTTPException(status_code=401, detail="invalid or missing X-Siren-Key")


def _today() -> str:
    return datetime.now(_TZ).strftime("%Y-%m-%d")


def _insert(category: str, data: dict) -> dict:
    """Insert a dashboard_entries row in the bot's exact shape and return it."""
    row = {
        "user_id": str(USER_ID),
        "category": category,
        "data": data,  # jsonb — PostgREST encodes the native object
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    resp = _http.post(f"/{DATABASE_TABLE}", json=row, headers={"Prefer": "return=representation"})
    resp.raise_for_status()
    created = resp.json()
    return created[0] if isinstance(created, list) and created else created


def _get_todo(row_id: str) -> dict | None:
    resp = _http.get(
        f"/{DATABASE_TABLE}",
        params={"id": f"eq.{row_id}", "select": "id,category,data,user_id"},
    )
    resp.raise_for_status()
    rows = resp.json()
    return rows[0] if rows else None


def _patch_data(row_id: str, data: dict) -> None:
    resp = _http.patch(f"/{DATABASE_TABLE}", params={"id": f"eq.{row_id}"}, json={"data": data})
    resp.raise_for_status()


def _norm_priority(value: str) -> str:
    p = (value or "medium").lower()
    if p not in VALID_PRIORITY:
        raise HTTPException(status_code=400, detail=f"priority must be one of {sorted(VALID_PRIORITY)}")
    return p


def _norm_status(value: str) -> str:
    s = (value or "pending").lower()
    if s not in VALID_STATUS:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(VALID_STATUS)}")
    return s


@app.get("/health")
def health():
    return {"status": "ok", "agent": "dashbored"}


@app.post("/invoke")
def invoke(body: dict, x_siren_key: str = Header(default="")):
    _auth(x_siren_key)
    if not USER_ID:
        raise HTTPException(status_code=500, detail="DASHBORED_USER_ID not set on the sidecar")
    tool = body.get("tool")
    args = body.get("args") or {}

    try:
        # --- todos / reminders ------------------------------------------------
        if tool == "add_todo":
            task = args.get("task")
            if not task:
                raise HTTPException(status_code=400, detail="add_todo needs 'task'")
            data = {
                "task": task,
                "priority": _norm_priority(args.get("priority")),
                "status": _norm_status(args.get("status")),
                "tags": args.get("tags") or [],
            }
            if args.get("due"):
                data["due"] = args["due"]
            if args.get("reminder_time"):
                # ISO 8601 with +08:00 offset; the bot's checker fires on this.
                data["reminder_time"] = args["reminder_time"]
            row = _insert("todos", data)
            return {"result": {"ok": True, "id": row.get("id"), "data": row.get("data")}}

        if tool in ("update_todo", "complete_todo"):
            row_id = args.get("id")
            if not row_id:
                raise HTTPException(status_code=400, detail=f"{tool} needs 'id' (from query_dashboard todos)")
            row = _get_todo(row_id)
            if not row or row.get("category") != "todos":
                return {"result": {"ok": False, "error": f"no todo with id {row_id}"}}
            if str(row.get("user_id")) != str(USER_ID):
                raise HTTPException(status_code=403, detail="todo belongs to another user")
            data = dict(row.get("data") or {})
            if tool == "complete_todo":
                data["status"] = "done"
            else:
                if args.get("task"):
                    data["task"] = args["task"]
                if args.get("priority"):
                    data["priority"] = _norm_priority(args["priority"])
                if args.get("status"):
                    data["status"] = _norm_status(args["status"])
                if "due" in args:
                    data["due"] = args["due"]
                if "reminder_time" in args:
                    data["reminder_time"] = args["reminder_time"]
                    # A rescheduled reminder should fire again, so clear the
                    # bot's "already sent" flag.
                    data.pop("reminded", None)
            _patch_data(row_id, data)
            return {"result": {"ok": True, "id": row_id, "data": data}}

        # --- spending ---------------------------------------------------------
        if tool == "log_spending":
            amount, description = args.get("amount"), args.get("description")
            if amount is None or not description:
                raise HTTPException(
                    status_code=400,
                    detail="log_spending needs 'amount' and 'description'",
                )
            # subcategory is optional: a spend logged conversationally ("a $12
            # coffee") often has no explicit bucket, and rejecting it would drop
            # the spend entirely. Default to "other" — the dashboard already
            # falls back to the description for the label.
            data = {
                "amount": amount,
                "description": description,
                "subcategory": args.get("subcategory") or "other",
                "date": args.get("date") or _today(),
            }
            row = _insert("spending", data)
            return {"result": {"ok": True, "id": row.get("id")}}

        # --- net worth --------------------------------------------------------
        if tool == "set_net_worth":
            savings, trading = args.get("savings"), args.get("trading")
            if savings is None and trading is None:
                raise HTTPException(
                    status_code=400,
                    detail="set_net_worth needs at least one of 'savings' or 'trading'",
                )
            data = {"date": args.get("date") or _today()}
            if savings is not None:
                data["savings"] = savings
            if trading is not None:
                data["trading"] = trading
            row = _insert("net_worth", data)
            return {"result": {"ok": True, "id": row.get("id")}}

        # --- remove any entry --------------------------------------------------
        if tool == "remove_entry":
            row_id = args.get("id")
            if not row_id:
                raise HTTPException(
                    status_code=400, detail="remove_entry needs 'id' (from query_dashboard)"
                )
            # Delete scoped to this user, and return what was removed so Siren
            # can confirm it by name. The user_id filter doubles as the
            # ownership guard — a foreign row simply matches nothing.
            resp = _http.delete(
                f"/{DATABASE_TABLE}",
                params={"id": f"eq.{row_id}", "user_id": f"eq.{USER_ID}"},
                headers={"Prefer": "return=representation"},
            )
            resp.raise_for_status()
            removed = resp.json()
            if not removed:
                return {"result": {"ok": False, "error": f"no entry with id {row_id}"}}
            return {
                "result": {
                    "ok": True,
                    "id": row_id,
                    "category": removed[0].get("category"),
                    "data": removed[0].get("data"),
                }
            }

        raise HTTPException(status_code=400, detail=f"unknown tool: {tool}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"supabase error {e.response.status_code}: {e.response.text[:300]}",
        )
