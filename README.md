# TRT World Discord Bot

Posts the latest news from trtworld.com to a Discord channel every 15 minutes.

## Files

| File | Purpose |
|------|---------|
| `bot.py` | Main bot |
| `requirements.txt` | Python dependencies |
| `seen_ids.json` | Auto-created — tracks posted articles |

---

## Setup

### 1. Create a Discord bot

1. Go to https://discord.com/developers/applications → **New Application**
2. Under **Bot** → click **Add Bot** → copy the **Token**
3. Under **OAuth2 → URL Generator** select scopes: `bot`  
   Bot permissions: `Send Messages`, `Embed Links`
4. Open the generated URL and invite the bot to your server

### 2. Get your channel ID

In Discord: **Settings → Advanced → Developer Mode ON**  
Right-click your target channel → **Copy Channel ID**

### 3. Deploy to a free service

#### Option A — Railway (recommended, easiest)
1. Push these files to a GitHub repo
2. Go to https://railway.app → **New Project → Deploy from GitHub**
3. Add environment variables:
   - `DISCORD_TOKEN` = your bot token
   - `CHANNEL_ID` = your channel ID (numbers only)
4. Railway auto-detects Python and installs requirements. Done.

#### Option B — Render
1. Push to GitHub
2. https://render.com → **New → Web Service** (or Background Worker)
3. Set **Build Command**: `pip install -r requirements.txt`  
   **Start Command**: `python bot.py`
4. Add the same env vars under **Environment**

#### Option C — Run locally
```bash
pip install -r requirements.txt
export DISCORD_TOKEN="your-token-here"
export CHANNEL_ID="123456789012345678"
python bot.py
```

---

## How it works

- Every 15 minutes the bot fetches the TRT World homepage
- It finds all `/article/` links and extracts title + summary
- Any article whose ID hasn't been seen before gets posted as a Discord embed
- Seen IDs are saved to `seen_ids.json` so nothing gets double-posted
- On first run it will post up to 20 of the currently visible articles
