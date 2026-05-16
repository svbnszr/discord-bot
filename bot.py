import os
import json
import asyncio
import logging
from datetime import datetime

import discord
from discord.ext import tasks
import requests
from bs4 import BeautifulSoup

# ── Config ────────────────────────────────────────────────────────────────────
DISCORD_TOKEN   = os.environ["DISCORD_TOKEN"]
CHANNEL_ID      = int(os.environ["CHANNEL_ID"])   # e.g. 1234567890123456789
SEEN_FILE       = "seen_ids.json"
POLL_MINUTES    = 15
TRT_URL         = "https://www.trtworld.com/"
HEADERS         = {"User-Agent": "Mozilla/5.0 (compatible; TRTBot/1.0)"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Seen-ID persistence ───────────────────────────────────────────────────────
def load_seen() -> set:
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen: set):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)

# ── Scraper ───────────────────────────────────────────────────────────────────
def scrape_latest() -> list[dict]:
    """Return a list of {title, url, summary} dicts for the Latest News section."""
    try:
        resp = requests.get(TRT_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.error("Fetch failed: %s", e)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    articles = []

    # TRT World article links follow /article/{id}
    seen_urls = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        if "/article/" not in href:
            continue

        # Normalise to absolute URL
        url = href if href.startswith("http") else "https://www.trtworld.com" + href
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # Grab the closest text as the title (skip empty / icon-only links)
        title = a_tag.get_text(separator=" ", strip=True)
        if len(title) < 20:          # too short → probably an image link
            continue

        # Try to find a nearby <p> for a summary; fall back to empty string
        parent = a_tag.find_parent()
        summary = ""
        if parent:
            p = parent.find("p")
            if p:
                summary = p.get_text(strip=True)[:300]

        articles.append({"title": title, "url": url, "summary": summary})
        if len(articles) >= 20:      # cap to avoid runaway on first start
            break

    return articles

# ── Discord bot ───────────────────────────────────────────────────────────────
intents = discord.Intents.default()
bot     = discord.Client(intents=intents)
seen_ids: set = set()

def article_id(url: str) -> str:
    """Use the short hash at the end of the TRT URL as a stable ID."""
    return url.rstrip("/").split("/")[-1]

def build_embed(article: dict) -> discord.Embed:
    embed = discord.Embed(
        title       = article["title"][:256],
        url         = article["url"],
        color       = discord.Color.from_str("#c8102e"),  # TRT red
        timestamp   = datetime.utcnow(),
    )
    if article["summary"]:
        embed.description = article["summary"]
    embed.set_footer(text="TRT World")
    return embed

@bot.event
async def on_ready():
    global seen_ids
    seen_ids = load_seen()
    log.info("Logged in as %s — watching TRT World every %d min", bot.user, POLL_MINUTES)
    check_news.start()

@tasks.loop(minutes=POLL_MINUTES)
async def check_news():
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        log.warning("Channel %s not found", CHANNEL_ID)
        return

    articles = scrape_latest()
    new_count = 0

    for article in reversed(articles):   # post oldest-first
        aid = article_id(article["url"])
        if aid in seen_ids:
            continue

        try:
            await channel.send(embed=build_embed(article))
            seen_ids.add(aid)
            save_seen(seen_ids)
            new_count += 1
            await asyncio.sleep(1)       # avoid Discord rate limits
        except discord.HTTPException as e:
            log.error("Discord send error: %s", e)

    if new_count:
        log.info("Posted %d new article(s)", new_count)
    else:
        log.info("No new articles found")

@check_news.before_loop
async def before_check():
    await bot.wait_until_ready()

bot.run(DISCORD_TOKEN)
