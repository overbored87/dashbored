"""
Personal Dashboard Telegram Bot
Parses natural language messages and stores structured data
"""

import os
import json
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import httpx

# Configuration
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # Get from @BotFather
DATABASE_URL = "YOUR_SUPABASE_URL"  # Or your database endpoint
DATABASE_KEY = "YOUR_SUPABASE_KEY"

# System prompt for Claude to parse messages
PARSING_PROMPT = """You are a personal dashboard assistant. Parse the user's message and extract structured data.

Identify which category this belongs to:
- finance: spending, income, bills
- fitness: workouts, exercise, health
- relationships: contact with friends/family, reminders
- dating: dates, dating app matches, follow-ups
- trips: travel plans, bookings, itineraries
- todos: tasks, reminders, goals

Return ONLY a JSON object with this structure:
{
  "category": "finance|fitness|relationships|dating|trips|todos",
  "data": {
    // Category-specific fields
  },
  "confidence": 0.0-1.0,
  "needs_clarification": false,
  "clarification_question": "optional question if unclear"
}

Examples:
- "Spent $47 on dinner" → {"category": "finance", "data": {"type": "expense", "amount": 47, "currency": "USD", "description": "dinner", "date": "2026-02-13"}}
- "Leg day - squats 225x5x3" → {"category": "fitness", "data": {"type": "workout", "exercise": "squats", "weight": 225, "sets": 3, "reps": 5, "notes": "leg day"}}
- "Coffee date with Sarah tomorrow at 2pm" → {"category": "dating", "data": {"type": "scheduled_date", "person": "Sarah", "activity": "coffee", "datetime": "2026-02-14T14:00:00"}}
- "Call mom this weekend" → {"category": "relationships", "data": {"type": "reminder", "person": "mom", "action": "call", "timeframe": "this weekend"}}
- "Tokyo trip April 15-22" → {"category": "trips", "data": {"destination": "Tokyo", "start_date": "2026-04-15", "end_date": "2026-04-22"}}

Be smart about parsing dates, amounts, and context. Current date is {current_date}.
"""


async def parse_with_claude(message_text: str) -> dict:
    """Use Claude API to parse the message into structured data"""
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": os.environ.get("ANTHROPIC_API_KEY", ""),
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1024,
                    "messages": [
                        {
                            "role": "user",
                            "content": PARSING_PROMPT.format(current_date=current_date) + f"\n\nMessage: {message_text}"
                        }
                    ]
                }
            )
            
            result = response.json()
            content = result["content"][0]["text"]
            
            # Extract JSON from response (Claude might wrap it in markdown)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            return json.loads(content)
            
    except Exception as e:
        return {
            "category": "unknown",
            "error": str(e),
            "needs_clarification": True,
            "clarification_question": "Sorry, I couldn't parse that. Could you rephrase?"
        }


async def save_to_database(category: str, data: dict, user_id: int):
    """Save parsed data to database (Supabase example)"""
    entry = {
        "user_id": user_id,
        "category": category,
        "data": data,
        "created_at": datetime.utcnow().isoformat(),
        "timestamp": datetime.now().isoformat()
    }
    
    # Example Supabase insert
    # In production, you'd use the actual Supabase client
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{DATABASE_URL}/rest/v1/dashboard_entries",
                headers={
                    "apikey": DATABASE_KEY,
                    "Authorization": f"Bearer {DATABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal"
                },
                json=entry
            )
            return response.status_code == 201
        except:
            # Fallback: save to local JSON file for demo
            os.makedirs("/home/claude/data", exist_ok=True)
            filename = f"/home/claude/data/{category}.jsonl"
            with open(filename, "a") as f:
                f.write(json.dumps(entry) + "\n")
            return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when /start is issued"""
    await update.message.reply_text(
        "👋 Welcome to your Personal Dashboard Bot!\n\n"
        "Just send me messages like:\n"
        "• 'Spent $50 on groceries'\n"
        "• 'Workout: bench press 185x5'\n"
        "• 'Coffee with Alex tomorrow at 3pm'\n"
        "• 'Tokyo trip April 15-22'\n\n"
        "I'll parse them and add to your dashboard!"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages"""
    user_message = update.message.text
    user_id = update.message.from_user.id
    
    # Show typing indicator
    await update.message.chat.send_action("typing")
    
    # Parse with Claude
    parsed = await parse_with_claude(user_message)
    
    # Check if clarification needed
    if parsed.get("needs_clarification"):
        question = parsed.get("clarification_question", "Could you provide more details?")
        await update.message.reply_text(f"🤔 {question}")
        return
    
    # Save to database
    category = parsed.get("category")
    data = parsed.get("data", {})
    
    success = await save_to_database(category, data, user_id)
    
    if success:
        # Format confirmation based on category
        emoji_map = {
            "finance": "💰",
            "fitness": "💪",
            "relationships": "👥",
            "dating": "💕",
            "trips": "✈️",
            "todos": "✅"
        }
        
        emoji = emoji_map.get(category, "📝")
        
        # Create human-readable confirmation
        confirmation = f"{emoji} Logged to {category}:\n"
        
        if category == "finance":
            amount = data.get("amount", "")
            desc = data.get("description", "")
            confirmation += f"${amount} - {desc}"
        elif category == "fitness":
            exercise = data.get("exercise", "workout")
            confirmation += f"{exercise.title()}"
            if "weight" in data:
                confirmation += f" - {data['weight']}lbs"
        elif category == "dating":
            person = data.get("person", "")
            activity = data.get("activity", "date")
            confirmation += f"{activity.title()} with {person}"
        elif category == "trips":
            dest = data.get("destination", "")
            confirmation += f"{dest}"
        else:
            confirmation += json.dumps(data, indent=2)
        
        await update.message.reply_text(confirmation)
    else:
        await update.message.reply_text("❌ Error saving data. Please try again.")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show quick stats from stored data"""
    # This is a placeholder - in production you'd query your database
    await update.message.reply_text(
        "📊 Your Stats:\n\n"
        "💰 Finance: 12 entries this month\n"
        "💪 Fitness: 8 workouts this week\n"
        "💕 Dating: 3 active conversations\n"
        "✈️ Trips: 1 upcoming\n\n"
        "View full dashboard at: https://your-dashboard.vercel.app"
    )


def main():
    """Start the bot"""
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start bot
    print("🤖 Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
