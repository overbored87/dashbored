"""
Personal Dashboard Telegram Bot
Parses natural language messages via Claude and stores structured data in Supabase.
Supports 3 widgets: Finance, Dating, Todos.
"""

import os
import re
import json
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
DATABASE_URL = os.environ["DATABASE_URL"]            # e.g. https://xyz.supabase.co
DATABASE_KEY = os.environ["DATABASE_KEY"]             # service-role or anon key
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

TABLE_NAME = os.environ.get("DATABASE_TABLE", "dashboard_entries")
LOCAL_TZ = ZoneInfo("Asia/Singapore")                # SGT UTC+8

# ---------------------------------------------------------------------------
# Parsing prompt — tightly scoped to 3 categories
# ---------------------------------------------------------------------------
PARSING_PROMPT = """You are a structured-data extraction engine for a personal dashboard.
Your ONLY job is to return valid JSON — no commentary, no markdown fences.

Today's date: {current_date}

ACTIONS:
- "add" (default): log a new entry
- "remove": delete an existing entry. User might say "remove", "delete", "undo", "cancel", etc.

CATEGORIES (pick exactly one):

1. **finance** — any mention of spending, bills, subscriptions, purchases.
   For action "add":
     Required: amount (positive number), description (short label), subcategory, date (YYYY-MM-DD, default today)
     subcategory: lowercase snake_case label. Reuse when possible. Examples: "food", "transport", "rent", "entertainment", "shopping", "health", "utilities", "subscription", "groceries", "coffee", "dining_out". Invent new ones naturally as needed.
   For action "remove":
     Provide as many identifying fields as possible: amount, description, subcategory, date — whatever the user mentions.

2. **net_worth** — account balance updates for savings or trading accounts. User might say "savings 15000", "trading acc 8500", or update both at once like "savings 15k, trading 8k".
   Action is always "add" (each message is a new snapshot).
   Required: at least one of savings (number) or trading (number). Include both if the user provides both.
   Optional: date (YYYY-MM-DD, default today)

3. **dating** — matches, dates, follow-ups, rejections, relationship status updates.
   For action "add":
     Required: person (title case), status ("active" | "texting" | "backburner")
     Optional: platform, activity, location, notes, date (YYYY-MM-DD), rating (1-5)
   For action "remove":
     Required: person (the name to remove)

4. **todos** — tasks, reminders, goals, deadlines.
   For action "add":
     Required: task (concise description), priority ("high" | "medium" | "low"), status ("pending" | "in_progress" | "done")
     Optional: due (YYYY-MM-DD), tags (list of strings), reminder_time (ISO 8601 with timezone, e.g. "2026-02-15T15:00:00+08:00")
   If the user says "remind me" or mentions a specific time (e.g. "at 3pm", "tomorrow morning", "tonight at 8"), ALWAYS set reminder_time.
   Interpret relative times based on current datetime. "morning" = 09:00, "afternoon" = 14:00, "evening" = 19:00, "tonight" = 20:00.
   Always use timezone offset +08:00 (Singapore Time).

RULES:
- Return ONLY a single JSON object. No markdown, no explanation.
- Current datetime: {current_datetime} (timezone: Asia/Singapore, UTC+8)
- All dates must be YYYY-MM-DD. Resolve relative dates (e.g. "Friday" → next Friday).
- If "yesterday" is mentioned, subtract 1 day from today.
- Currency is always SGD — do not include a currency field.
- confidence: float 0-1 reflecting how certain you are of the parse.
- If the message is ambiguous or doesn't fit any category, set:
  "category": "unknown", "needs_clarification": true, "clarification_question": "<your question>"

OUTPUT SCHEMA:
{{
  "action": "add" | "remove",
  "category": "finance" | "net_worth" | "dating" | "todos" | "unknown",
  "data": {{ ... }},
  "confidence": 0.0-1.0,
  "needs_clarification": false,
  "clarification_question": null
}}

Now parse this message:
\"\"\"{message}\"\"\"
"""


# ---------------------------------------------------------------------------
# Validation schemas — enforce required fields per category
# ---------------------------------------------------------------------------
REQUIRED_FIELDS = {
    "finance": {"amount", "description", "subcategory"},
    "net_worth": set(),     # at least one of savings/trading, validated below
    "dating": {"person", "status"},
    "todos": {"task", "priority", "status"},
}

# For remove actions, we only need enough to identify the entry
REQUIRED_FIELDS_REMOVE = {
    "finance": set(),       # any combination of amount/description/date is fine
    "net_worth": set(),
    "dating": {"person"},   # must know who to remove
    "todos": set(),
}

VALID_ENUMS = {
    "dating": {
        "status": {"active", "texting", "backburner"},
    },
    "todos": {
        "priority": {"high", "medium", "low"},
        "status": {"pending", "in_progress", "done"},
    },
}


def validate_parsed(parsed: dict) -> tuple[bool, str]:
    """Validate parsed data against the schema. Returns (is_valid, error_message)."""
    category = parsed.get("category")
    action = parsed.get("action", "add")

    required_map = REQUIRED_FIELDS_REMOVE if action == "remove" else REQUIRED_FIELDS
    if category not in required_map:
        return False, f"Unknown category: {category}"

    data = parsed.get("data", {})
    missing = required_map[category] - set(data.keys())
    if missing:
        return False, f"Missing fields for {category}: {missing}"

    # Only validate enums for add actions
    if action == "add":
        for field, allowed in VALID_ENUMS.get(category, {}).items():
            value = data.get(field)
            if value and value not in allowed:
                return False, f"Invalid {field}='{value}' for {category}. Allowed: {allowed}"

        # Finance-specific: amount must be a positive number
        if category == "finance":
            amount = data.get("amount")
            if not isinstance(amount, (int, float)) or amount <= 0:
                return False, f"Invalid amount: {amount}"

        # Net worth: must have at least one of savings or trading
        if category == "net_worth":
            has_savings = isinstance(data.get("savings"), (int, float))
            has_trading = isinstance(data.get("trading"), (int, float))
            if not has_savings and not has_trading:
                return False, "net_worth requires at least one of: savings, trading"

    return True, ""


# ---------------------------------------------------------------------------
# Claude API — parse message
# ---------------------------------------------------------------------------
async def parse_with_claude(message_text: str) -> dict:
    """Send the message to Claude for structured extraction."""
    now = datetime.now(LOCAL_TZ)
    current_date = now.strftime("%Y-%m-%d")
    current_datetime = now.isoformat()
    prompt = PARSING_PROMPT.format(
        current_date=current_date,
        current_datetime=current_datetime,
        message=message_text,
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 512,
                    "temperature": 0,          # deterministic parsing
                    "messages": [{"role": "user", "content": prompt}],
                },
            )

        if resp.status_code != 200:
            print(f"❌ Claude API {resp.status_code}: {resp.text}")
            return _error_response("Sorry, I had trouble processing that. Could you try again?")

        content = resp.json()["content"][0]["text"].strip()

        # Strip markdown fences if Claude accidentally adds them
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)

        parsed = json.loads(content)

        # Validate
        if parsed.get("needs_clarification"):
            return parsed

        is_valid, err = validate_parsed(parsed)
        if not is_valid:
            print(f"⚠️  Validation failed: {err}")
            return _error_response("I wasn't sure how to categorise that. Could you rephrase?")

        # Inject defaults
        _apply_defaults(parsed)
        return parsed

    except json.JSONDecodeError as e:
        print(f"❌ JSON parse error: {e}\nRaw content: {content!r}")
        return _error_response("I couldn't understand that. Could you rephrase?")
    except Exception as e:
        print(f"❌ Unexpected error in parse_with_claude: {e}")
        return _error_response("Something went wrong. Please try again.")


def _error_response(question: str) -> dict:
    return {
        "category": "unknown",
        "needs_clarification": True,
        "clarification_question": question,
    }


def _apply_defaults(parsed: dict):
    """Fill in sensible defaults for optional fields."""
    data = parsed.get("data", {})
    today = datetime.now().strftime("%Y-%m-%d")

    if parsed["category"] == "finance":
        data.setdefault("date", today)

    elif parsed["category"] == "net_worth":
        data.setdefault("date", today)

    elif parsed["category"] == "dating":
        data.setdefault("date", today)

    elif parsed["category"] == "todos":
        data.setdefault("status", "pending")
        data.setdefault("tags", [])


# ---------------------------------------------------------------------------
# Supabase persistence
# ---------------------------------------------------------------------------
async def save_to_supabase(category: str, data: dict, user_id: int) -> bool:
    """Insert a row into the single dashboard_entries table."""
    row = {
        "user_id": str(user_id),
        "category": category,
        "data": json.dumps(data),       # JSONB column — store as string for the REST API
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{DATABASE_URL}/rest/v1/{TABLE_NAME}",
                headers={
                    "apikey": DATABASE_KEY,
                    "Authorization": f"Bearer {DATABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation",
                },
                json=row,
            )

        if resp.status_code in (200, 201):
            print(f"✅ Saved to Supabase: {category}")
            return True
        else:
            print(f"❌ Supabase error {resp.status_code}: {resp.text}")
            return False

    except Exception as e:
        print(f"❌ Supabase request failed: {e}")
        return False


async def remove_from_supabase(category: str, data: dict, user_id: int) -> dict | None:
    """Find and delete a matching entry. Returns the deleted entry or None."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Fetch recent entries in this category to find a match
            resp = await client.get(
                f"{DATABASE_URL}/rest/v1/{TABLE_NAME}",
                headers={
                    "apikey": DATABASE_KEY,
                    "Authorization": f"Bearer {DATABASE_KEY}",
                },
                params={
                    "user_id": f"eq.{str(user_id)}",
                    "category": f"eq.{category}",
                    "order": "created_at.desc",
                    "limit": "50",
                    "select": "id,category,data,created_at",
                },
            )

            if resp.status_code != 200 or not resp.json():
                return None

            rows = resp.json()

            # Find best matching entry
            match = _find_best_match(category, data, rows)
            if not match:
                return None

            # Delete it
            del_resp = await client.delete(
                f"{DATABASE_URL}/rest/v1/{TABLE_NAME}",
                headers={
                    "apikey": DATABASE_KEY,
                    "Authorization": f"Bearer {DATABASE_KEY}",
                },
                params={"id": f"eq.{match['id']}"},
            )

            if del_resp.status_code in (200, 204):
                return match
            return None

    except Exception as e:
        print(f"❌ Supabase remove failed: {e}")
        return None


def _find_best_match(category: str, search: dict, rows: list[dict]) -> dict | None:
    """Score rows against search criteria and return the best match."""
    best_row = None
    best_score = 0

    for row in rows:
        row_data = row["data"] if isinstance(row["data"], dict) else json.loads(row["data"])
        score = 0

        if category == "finance":
            if search.get("amount") and row_data.get("amount") == search["amount"]:
                score += 3
            if search.get("description") and search["description"].lower() in row_data.get("description", "").lower():
                score += 2
            if search.get("subcategory") and row_data.get("subcategory") == search["subcategory"]:
                score += 1
            if search.get("date") and row_data.get("date") == search["date"]:
                score += 1

        elif category == "dating":
            if search.get("person") and search["person"].lower() == row_data.get("person", "").lower():
                score += 5  # Name is the primary key for dating

        if score > best_score:
            best_score = score
            best_row = row

    return best_row if best_score > 0 else None


# ---------------------------------------------------------------------------
# Telegram handlers
# ---------------------------------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Welcome to your Personal Dashboard Bot!*\n\n"
        "Just send me messages naturally and I'll log them:\n\n"
        "💰 *Finance*\n"
        "  • _Spent $50 on groceries_\n"
        "  • _Earned $3000 freelance payment_\n"
        "  • _Netflix subscription $15.90_\n\n"
        "💕 *Dating*\n"
        "  • _Matched with Emma on Hinge_\n"
        "  • _Had coffee with Jessica, went great_\n"
        "  • _Alex hasn't replied in 3 days_\n\n"
        "✅ *To-dos*\n"
        "  • _Finish Q1 report by Friday_\n"
        "  • _Buy birthday gift for mom_\n\n"
        "Commands: /stats · /recent · /help",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *How to use this bot*\n\n"
        "Just type naturally — I'll figure out the category.\n\n"
        "Tips:\n"
        "• Include dollar amounts for finance entries\n"
        "• Mention people's names for dating entries\n"
        "• Use words like 'need to', 'should', 'by Friday' for todos\n\n"
        "Commands:\n"
        "/stats — quick summary of your data\n"
        "/recent — last 5 entries\n"
        "/delete — remove the last entry",
        parse_mode="Markdown",
    )


async def cmd_recent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch last 5 entries from Supabase."""
    user_id = str(update.message.from_user.id)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{DATABASE_URL}/rest/v1/{TABLE_NAME}",
                headers={
                    "apikey": DATABASE_KEY,
                    "Authorization": f"Bearer {DATABASE_KEY}",
                },
                params={
                    "user_id": f"eq.{user_id}",
                    "order": "created_at.desc",
                    "limit": "5",
                    "select": "category,data,created_at",
                },
            )

        if resp.status_code != 200:
            await update.message.reply_text("❌ Couldn't fetch recent entries.")
            return

        rows = resp.json()
        if not rows:
            await update.message.reply_text("No entries yet! Send me a message to get started.")
            return

        lines = ["📋 *Recent entries:*\n"]
        emoji_map = {"finance": "💰", "net_worth": "🏦", "dating": "💕", "todos": "✅"}
        for row in rows:
            data = row["data"] if isinstance(row["data"], dict) else json.loads(row["data"])
            cat = row["category"]
            emoji = emoji_map.get(cat, "📝")
            summary = _summarise_entry(cat, data)
            lines.append(f"{emoji} {summary}")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    except Exception as e:
        print(f"❌ /recent error: {e}")
        await update.message.reply_text("❌ Something went wrong fetching your entries.")


async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show aggregated stats from Supabase."""
    user_id = str(update.message.from_user.id)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{DATABASE_URL}/rest/v1/{TABLE_NAME}",
                headers={
                    "apikey": DATABASE_KEY,
                    "Authorization": f"Bearer {DATABASE_KEY}",
                },
                params={
                    "user_id": f"eq.{user_id}",
                    "select": "category,data",
                },
            )

        if resp.status_code != 200:
            await update.message.reply_text("❌ Couldn't fetch stats.")
            return

        rows = resp.json()
        finance_count = 0
        total_spent = 0.0
        dating_count = 0
        todos_pending = 0

        for row in rows:
            data = row["data"] if isinstance(row["data"], dict) else json.loads(row["data"])
            cat = row["category"]
            if cat == "finance":
                finance_count += 1
                total_spent += data.get("amount", 0)
            elif cat == "dating":
                dating_count += 1
            elif cat == "todos":
                if data.get("status") in ("pending", "in_progress"):
                    todos_pending += 1

        await update.message.reply_text(
            f"📊 *Your Stats*\n\n"
            f"💰 Finance: {finance_count} entries · ${total_spent:,.2f} spent\n"
            f"💕 Dating: {dating_count} entries\n"
            f"✅ Todos: {todos_pending} pending tasks",
            parse_mode="Markdown",
        )

    except Exception as e:
        print(f"❌ /stats error: {e}")
        await update.message.reply_text("❌ Something went wrong fetching stats.")


async def cmd_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete the most recent entry."""
    user_id = str(update.message.from_user.id)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Fetch the latest entry's id
            resp = await client.get(
                f"{DATABASE_URL}/rest/v1/{TABLE_NAME}",
                headers={
                    "apikey": DATABASE_KEY,
                    "Authorization": f"Bearer {DATABASE_KEY}",
                },
                params={
                    "user_id": f"eq.{user_id}",
                    "order": "created_at.desc",
                    "limit": "1",
                    "select": "id,category,data",
                },
            )

            if resp.status_code != 200 or not resp.json():
                await update.message.reply_text("Nothing to delete.")
                return

            entry = resp.json()[0]
            entry_id = entry["id"]

            # Delete it
            del_resp = await client.delete(
                f"{DATABASE_URL}/rest/v1/{TABLE_NAME}",
                headers={
                    "apikey": DATABASE_KEY,
                    "Authorization": f"Bearer {DATABASE_KEY}",
                },
                params={"id": f"eq.{entry_id}"},
            )

        if del_resp.status_code in (200, 204):
            data = entry["data"] if isinstance(entry["data"], dict) else json.loads(entry["data"])
            summary = _summarise_entry(entry["category"], data)
            await update.message.reply_text(f"🗑️ Deleted: {summary}")
        else:
            await update.message.reply_text("❌ Couldn't delete the entry.")

    except Exception as e:
        print(f"❌ /delete error: {e}")
        await update.message.reply_text("❌ Something went wrong.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle any text message — parse and store or remove."""
    user_message = update.message.text
    user_id = update.message.from_user.id

    await update.message.chat.send_action("typing")

    parsed = await parse_with_claude(user_message)

    # Clarification needed?
    if parsed.get("needs_clarification"):
        question = parsed.get("clarification_question", "Could you provide more details?")
        await update.message.reply_text(f"🤔 {question}")
        return

    action = parsed.get("action", "add")
    category = parsed["category"]
    data = parsed["data"]
    confidence = parsed.get("confidence", 0)
    low_conf = confidence < 0.7

    emoji_map = {"finance": "💰", "net_worth": "🏦", "dating": "💕", "todos": "✅"}
    emoji = emoji_map.get(category, "📝")

    if action == "remove":
        deleted = await remove_from_supabase(category, data, user_id)
        if deleted:
            del_data = deleted["data"] if isinstance(deleted["data"], dict) else json.loads(deleted["data"])
            summary = _summarise_entry(category, del_data)
            await update.message.reply_text(f"🗑️ Removed: {summary}", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Couldn't find a matching entry to remove.")
    else:
        success = await save_to_supabase(category, data, user_id)
        if success:
            summary = _summarise_entry(category, data)
            reply = f"{emoji} {summary}"
            if low_conf:
                reply += "\n\n⚠️ _I'm not fully sure about this — use /delete if it's wrong._"
            await update.message.reply_text(reply, parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Failed to save. Please try again.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _summarise_entry(category: str, data: dict) -> str:
    """Human-readable one-liner for a dashboard entry."""
    if category == "finance":
        amt = data.get("amount", 0)
        desc = data.get("description", "")
        subcat = data.get("subcategory", "")
        line = f"*${amt}* — {desc}"
        if subcat:
            line += f" `#{subcat}`"
        return line

    elif category == "net_worth":
        parts = []
        if "savings" in data:
            parts.append(f"Savings: *${data['savings']:,.0f}*")
        if "trading" in data:
            parts.append(f"Trading: *${data['trading']:,.0f}*")
        total = data.get("savings", 0) + data.get("trading", 0)
        parts.append(f"Total: *${total:,.0f}*")
        return " · ".join(parts)

    elif category == "dating":
        person = data.get("person", "someone")
        status = data.get("status", "")
        notes = data.get("notes", "")
        status_icons = {"active": "🟢", "texting": "💬", "backburner": "⏸️"}
        icon = status_icons.get(status, "💕")
        line = f"{icon} *{person}* — {status}"
        if notes:
            line += f" ({notes})"
        return line

    elif category == "todos":
        task = data.get("task", "untitled task")
        priority = data.get("priority", "medium")
        due = data.get("due", "")
        reminder = data.get("reminder_time", "")
        priority_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        icon = priority_icons.get(priority, "⚪")
        line = f"{icon} {task}"
        if due:
            line += f" (due {due})"
        if reminder:
            try:
                rt = datetime.fromisoformat(reminder).astimezone(LOCAL_TZ)
                line += f"\n🔔 Reminder: {rt.strftime('%d/%m/%y %I:%M %p')}"
            except (ValueError, TypeError):
                pass
        return line

    return json.dumps(data)


# ---------------------------------------------------------------------------
# Reminder scheduler
# ---------------------------------------------------------------------------
async def check_reminders(context: ContextTypes.DEFAULT_TYPE):
    """Called every 60 seconds by the job queue. Sends due reminders."""
    now_utc = datetime.now(timezone.utc)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Fetch all pending todos that have a reminder_time
            resp = await client.get(
                f"{DATABASE_URL}/rest/v1/{TABLE_NAME}",
                headers={
                    "apikey": DATABASE_KEY,
                    "Authorization": f"Bearer {DATABASE_KEY}",
                },
                params={
                    "category": "eq.todos",
                    "select": "id,user_id,data",
                },
            )

        if resp.status_code != 200:
            print(f"⚠️ Reminder check failed: {resp.status_code}")
            return

        rows = resp.json()
        for row in rows:
            data = row["data"] if isinstance(row["data"], dict) else json.loads(row["data"])

            # Skip if no reminder, already reminded, or already done
            reminder_str = data.get("reminder_time")
            if not reminder_str:
                continue
            if data.get("reminded"):
                continue
            if data.get("status") == "done":
                continue

            # Parse reminder time and check if it's due
            try:
                reminder_time = datetime.fromisoformat(reminder_str).astimezone(timezone.utc)
            except (ValueError, TypeError):
                continue

            if reminder_time > now_utc:
                continue

            # It's due — send the reminder
            user_id = row["user_id"]
            task = data.get("task", "Something")
            due = data.get("due", "")

            reminder_text = (
                f"🔔 *Reminder!*\n\n"
                f"{task}"
            )
            if due:
                reminder_text += f"\n📅 Due: {due}"

            try:
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=reminder_text,
                    parse_mode="Markdown",
                )
                print(f"✅ Sent reminder to {user_id}: {task}")
            except Exception as e:
                print(f"❌ Failed to send reminder to {user_id}: {e}")
                continue

            # Mark as reminded so we don't send again
            data["reminded"] = True
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.patch(
                        f"{DATABASE_URL}/rest/v1/{TABLE_NAME}",
                        headers={
                            "apikey": DATABASE_KEY,
                            "Authorization": f"Bearer {DATABASE_KEY}",
                            "Content-Type": "application/json",
                            "Prefer": "return=minimal",
                        },
                        params={"id": f"eq.{row['id']}"},
                        json={"data": json.dumps(data)},
                    )
            except Exception as e:
                print(f"⚠️ Failed to mark reminded: {e}")

    except Exception as e:
        print(f"❌ Reminder check error: {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("stats", cmd_stats))
    app.add_handler(CommandHandler("recent", cmd_recent))
    app.add_handler(CommandHandler("delete", cmd_delete))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Schedule reminder checker every 60 seconds
    app.job_queue.run_repeating(check_reminders, interval=60, first=10)

    print("🤖 Dashboard bot is running...")
    print("⏰ Reminder checker active (every 60s)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
