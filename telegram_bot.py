"""
Personal Dashboard Telegram Bot
Parses natural language messages via Claude and stores structured data in Supabase.
Supports 3 widgets: Finance, Dating, Todos.
"""

import os
import re
import json
from datetime import datetime, timezone
from telegram import Update
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
DATABASE_URL = os.environ["SUPABASE_URL"]            # e.g. https://xyz.supabase.co
DATABASE_KEY = os.environ["SUPABASE_KEY"]             # service-role or anon key
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

TABLE_NAME = os.environ.get("SUPABASE_TABLE", "dashboard_entries")

# ---------------------------------------------------------------------------
# Parsing prompt — tightly scoped to 3 categories
# ---------------------------------------------------------------------------
PARSING_PROMPT = """You are a structured-data extraction engine for a personal dashboard.
Your ONLY job is to return valid JSON — no commentary, no markdown fences.

Today's date: {current_date}

CATEGORIES (pick exactly one):

1. **finance** — any mention of spending, earning, bills, subscriptions, transfers, savings.
   Required fields:
   - amount: number (positive for income, negative for expenses)
   - currency: ISO code, default "SGD"
   - description: short label
   - subcategory: a lowercase snake_case label for what it's about. Reuse existing labels when possible for consistency. Examples: "food", "transport", "rent", "entertainment", "shopping", "health", "utilities", "salary", "freelance", "subscription", "groceries", "coffee", "dining_out". Invent new ones naturally as needed.
   - date: YYYY-MM-DD (infer from context; default today)

2. **dating** — matches, dates, follow-ups, rejections, relationship status updates.
   Required fields:
   - person: name (title case)
   - status: "active" | "texting" | "backburner"
     - active: currently going on dates / seeing each other
     - texting: matched or chatting but haven't met yet
     - backburner: low priority, not actively pursuing
   Optional: platform (app name or "in_person"), activity, location, notes, date (YYYY-MM-DD), rating (1-5)

3. **todos** — tasks, reminders, goals, deadlines.
   Required fields:
   - task: concise description
   - priority: "high" | "medium" | "low" (infer from urgency cues)
   - status: "pending" | "in_progress" | "done"
   Optional: due (YYYY-MM-DD), tags (list of strings)

RULES:
- Return ONLY a single JSON object. No markdown, no explanation.
- All dates must be YYYY-MM-DD. Resolve relative dates (e.g. "Friday" → next Friday).
- If "yesterday" is mentioned, subtract 1 day from today.
- Currency: default SGD unless another currency symbol/code is explicit.
- confidence: float 0-1 reflecting how certain you are of the parse.
- If the message is ambiguous or doesn't fit any category, set:
  "category": "unknown", "needs_clarification": true, "clarification_question": "<your question>"

OUTPUT SCHEMA:
{{
  "category": "finance" | "dating" | "todos" | "unknown",
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
    "dating": {"person", "status"},
    "todos": {"task", "priority", "status"},
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
    if category not in REQUIRED_FIELDS:
        return False, f"Unknown category: {category}"

    data = parsed.get("data", {})
    missing = REQUIRED_FIELDS[category] - set(data.keys())
    if missing:
        return False, f"Missing fields for {category}: {missing}"

    # Check enum values
    for field, allowed in VALID_ENUMS.get(category, {}).items():
        value = data.get(field)
        if value and value not in allowed:
            return False, f"Invalid {field}='{value}' for {category}. Allowed: {allowed}"

    # Finance-specific: amount must be a positive number
    if category == "finance":
        amount = data.get("amount")
        if not isinstance(amount, (int, float)) or amount <= 0:
            return False, f"Invalid amount: {amount}"

    return True, ""


# ---------------------------------------------------------------------------
# Claude API — parse message
# ---------------------------------------------------------------------------
async def parse_with_claude(message_text: str) -> dict:
    """Send the message to Claude for structured extraction."""
    current_date = datetime.now().strftime("%Y-%m-%d")
    prompt = PARSING_PROMPT.format(current_date=current_date, message=message_text)

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
        data.setdefault("currency", "SGD")
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
                f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
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
                f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
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
        emoji_map = {"finance": "💰", "dating": "💕", "todos": "✅"}
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
                f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
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
                amt = data.get("amount", 0)
                if amt < 0:
                    total_spent += abs(amt)
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
                f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
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
                f"{SUPABASE_URL}/rest/v1/{TABLE_NAME}",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
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
    """Handle any text message — parse and store."""
    user_message = update.message.text
    user_id = update.message.from_user.id

    await update.message.chat.send_action("typing")

    parsed = await parse_with_claude(user_message)

    # Clarification needed?
    if parsed.get("needs_clarification"):
        question = parsed.get("clarification_question", "Could you provide more details?")
        await update.message.reply_text(f"🤔 {question}")
        return

    category = parsed["category"]
    data = parsed["data"]
    confidence = parsed.get("confidence", 0)

    # Low confidence warning
    low_conf = confidence < 0.7
    
    success = await save_to_supabase(category, data, user_id)

    if success:
        emoji_map = {"finance": "💰", "dating": "💕", "todos": "✅"}
        emoji = emoji_map.get(category, "📝")
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
        cur = data.get("currency", "SGD")
        desc = data.get("description", "")
        subcat = data.get("subcategory", "")
        sign = "+" if amt > 0 else ""
        line = f"*{sign}{cur} {amt}* — {desc}"
        if subcat:
            line += f" `#{subcat}`"
        return line

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
        priority_icons = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        icon = priority_icons.get(priority, "⚪")
        line = f"{icon} {task}"
        if due:
            line += f" (due {due})"
        return line

    return json.dumps(data)


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

    print("🤖 Dashboard bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()