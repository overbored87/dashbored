# Personal Dashboard Setup Guide

This guide will help you deploy your Telegram bot and web dashboard.

## Overview

**Architecture:**
- Telegram Bot (Python) → Parses messages with Claude API → Saves to database
- Web Dashboard (React) → Reads from database → Displays your life data

**Cost:** $0-5/month total

---

## Part 1: Telegram Bot Setup

### 1. Create Your Telegram Bot

1. Open Telegram and message [@BotFather](https://t.me/botfather)
2. Send `/newbot`
3. Choose a name (e.g., "My Life Dashboard")
4. Choose a username (e.g., "mylife_dashboard_bot")
5. **Save the bot token** - looks like `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`

### 2. Get Claude API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create an account or sign in
3. Go to "API Keys" section
4. Create a new key
5. **Save the API key** - starts with `sk-ant-`

### 3. Set Up Database (Supabase - Free)

1. Go to [supabase.com](https://supabase.com) and sign up
2. Create a new project
3. Go to Settings → API
4. **Save your:**
   - Project URL (looks like `https://xxxxx.supabase.co`)
   - `anon` public key (starts with `eyJ...`)

5. Create database table:
   - Go to SQL Editor
   - Run this query:

```sql
CREATE TABLE dashboard_entries (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    category TEXT NOT NULL,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_category ON dashboard_entries(category);
CREATE INDEX idx_user_id ON dashboard_entries(user_id);
CREATE INDEX idx_created_at ON dashboard_entries(created_at DESC);
```

### 4. Deploy Bot to Render (Free)

1. Create a GitHub repository
2. Upload these files:
   - `telegram_bot.py`
   - `requirements.txt`

3. Go to [render.com](https://render.com) and sign up
4. Click "New +" → "Web Service"
5. Connect your GitHub repository
6. Configure:
   - **Name:** personal-dashboard-bot
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python telegram_bot.py`
   - **Instance Type:** Free

7. Add Environment Variables:
   - `TELEGRAM_BOT_TOKEN`: Your bot token from BotFather
   - `ANTHROPIC_API_KEY`: Your Claude API key
   - `DATABASE_URL`: Your Supabase project URL
   - `DATABASE_KEY`: Your Supabase anon key

8. Click "Create Web Service"

Your bot is now live! Test it by messaging your bot on Telegram.

---

## Part 2: Web Dashboard Setup

### 1. Set Up React App

Create a new React app locally:

```bash
npx create-react-app my-dashboard
cd my-dashboard
npm install recharts
```

Replace `src/App.js` with the contents of `dashboard.jsx`

### 2. Connect to Database

Add Supabase client to fetch data:

```bash
npm install @supabase/supabase-js
```

Update the dashboard to fetch real data:

```javascript
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  'YOUR_SUPABASE_URL',
  'YOUR_SUPABASE_ANON_KEY'
);

// In your component:
useEffect(() => {
  async function fetchData() {
    const { data, error } = await supabase
      .from('dashboard_entries')
      .select('*')
      .order('created_at', { ascending: false });
    
    if (data) {
      // Group by category and set state
      const grouped = groupByCategory(data);
      setData(grouped);
    }
  }
  fetchData();
}, []);
```

### 3. Deploy to Vercel (Free)

1. Push your code to GitHub
2. Go to [vercel.com](https://vercel.com) and sign up
3. Click "New Project"
4. Import your GitHub repository
5. Vercel auto-detects React - just click "Deploy"
6. Your dashboard is live at `https://your-project.vercel.app`

---

## Part 3: Using Your Dashboard

### Send Messages to Your Bot

Just text your Telegram bot naturally:

**Finance:**
- "Spent $47 on dinner"
- "Earned $500 freelance income"

**Fitness:**
- "Workout: bench 185x5x3, squats 225x5"
- "Ran 5 miles in 42 minutes"

**Dating:**
- "Coffee date with Sarah tomorrow at 2pm"
- "Match with Emma on Hinge, chatting about travel"

**Relationships:**
- "Call mom this weekend"
- "Coffee with Mike on Friday"

**Trips:**
- "Tokyo trip April 15-22"
- "Booked flight to London"

**Todos:**
- "Finish Q1 report by Friday"
- "Schedule dentist appointment"

The bot will:
1. Parse your message with Claude
2. Confirm what it understood
3. Save to your database
4. Show up in your dashboard instantly (refresh page)

---

## Optional Enhancements

### Auto-Refresh Dashboard
Add this to make dashboard update automatically:

```javascript
// Refresh every 30 seconds
useEffect(() => {
  const interval = setInterval(fetchData, 30000);
  return () => clearInterval(interval);
}, []);
```

### Add Authentication
Protect your dashboard with Supabase Auth or simple password.

### Custom Domain
Both Vercel and Render support custom domains (free with your own domain).

### Mobile App View
The dashboard is already mobile-responsive. Add to home screen on iOS/Android.

---

## Costs

- **Telegram Bot:** Free
- **Supabase:** Free (500MB database, enough for years)
- **Render:** Free (with some sleep time) or $7/mo for always-on
- **Vercel:** Free (generous limits)
- **Claude API:** ~$0.10-1.00/month (messages are cheap)

**Total: $0-8/month**

---

## Troubleshooting

**Bot not responding:**
- Check Render logs for errors
- Verify environment variables are set
- Test API keys are valid

**Dashboard not showing data:**
- Check browser console for errors
- Verify Supabase connection
- Check if data exists in Supabase dashboard

**Need help?**
Check the logs in Render (for bot) and browser console (for dashboard).

---

You're all set! Text your bot and watch your dashboard come alive. 🚀
