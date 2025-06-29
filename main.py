import sys
print(f"✅ Running with Python version: {sys.version}")

import logging
import os
import time
import json
import asyncio
from datetime import datetime
from collections import defaultdict
from telegram import Update, ChatPermissions
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
)

# 🌐 Bot token from environment
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Config
FLOOD_LIMIT = 5
FLOOD_TIME = 6
MUTE_DURATION = 600
WARN_LIMIT = 3
CHANNEL_ID = -1002081570293  # Your backup channel ID

# Files
DATA_FILE = "data.json"
GAMES_FILE = "games.json"
CATEGORIES_FILE = "categories.json"
REQUESTS_FILE = "requests.json"

# Setup logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load data
def load_json(path, default): return json.load(open(path)) if os.path.exists(path) else default
data = load_json(DATA_FILE, {"xp": {}, "warns": {}})
game_posts = load_json(GAMES_FILE, {})
categories = load_json(CATEGORIES_FILE, {})
game_requests = load_json(REQUESTS_FILE, {})

user_xp = defaultdict(int, {int(k): v for k, v in data["xp"].items()})
user_warnings = defaultdict(int, {int(k): v for k, v in data["warns"].items()})
user_messages = defaultdict(list)

# Constants
BAD_WORDS = ["fuck", "bitch", "chutiya", "madarchod", "randi"]

# Save helpers
def save_data(): json.dump({"xp": dict(user_xp), "warns": dict(user_warnings)}, open(DATA_FILE, 'w'))
def save_games(): json.dump(game_posts, open(GAMES_FILE, 'w'))
def save_categories(): json.dump(categories, open(CATEGORIES_FILE, 'w'))
def save_requests(): json.dump(game_requests, open(REQUESTS_FILE, 'w'))

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot is online & sexy as ever!")

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "📜 *Group Rules*\n"
        "1. No spamming\n2. No bad words\n3. Respect everyone\n"
        "4. Use /find <game>\n5. Use /requestgame <name>"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_xp[uid] += 10
    save_data()
    await update.message.reply_text("🎁 Daily XP collected! +10 XP")

async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    xp = user_xp[uid]
    await update.message.reply_text(f"🏅 Your XP: {xp} | Level: {xp//10}")

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_users = sorted(user_xp.items(), key=lambda x: x[1], reverse=True)[:5]
    msg = "🏆 *Top 5 Users:*\n" + '\n'.join(f"{i+1}. User {uid} – {xp} XP" for i, (uid, xp) in enumerate(top_users))
    await update.message.reply_text(msg, parse_mode="Markdown")

async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(context.args).lower()
    if not query:
        await update.message.reply_text("❓ Use: /find <game name>")
        return
    matches = [g for g in game_posts if query in g.lower()]
    if matches:
        msg = "🎮 Found:\n" + '\n'.join(f"• {m}" for m in matches)
    else:
        msg = "❌ No matching game found."
    await update.message.reply_text(msg)

async def requestgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = ' '.join(context.args)
    if not name:
        await update.message.reply_text("❗ Use: /requestgame <game name>")
        return
    username = update.effective_user.username or update.effective_user.first_name
    game_requests[name] = username
    save_requests()
    await update.message.reply_text(f"✅ Request added for: {name} by {username}")

async def listcategory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗ Use: /listcategory <category>")
        return
    category = context.args[0]
    if category in categories:
        msg = f"🎮 *{category.upper()} Games:*\n" + '\n'.join(f"• {g}" for g in categories[category])
    else:
        msg = "❌ Category not found."
    await update.message.reply_text(msg, parse_mode="Markdown")

# Spam Mute System
async def check_flood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    now = time.time()
    user_messages[uid] = [t for t in user_messages[uid] if now - t < FLOOD_TIME]
    user_messages[uid].append(now)
    if len(user_messages[uid]) > FLOOD_LIMIT:
        user_warnings[uid] += 1
        save_data()
        if user_warnings[uid] >= WARN_LIMIT:
            await update.message.reply_text("⛔ Spamming detected. Auto-muted for 10 mins.")
            await context.bot.restrict_chat_member(update.effective_chat.id, uid, ChatPermissions(can_send_messages=False))
            await asyncio.sleep(MUTE_DURATION)
            await context.bot.restrict_chat_member(update.effective_chat.id, uid, ChatPermissions(can_send_messages=True))
            user_warnings[uid] = 0
            save_data()

# Game post detection
async def game_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text and "🎮" in update.message.text and "Download Links" in update.message.text:
        title = update.message.text.splitlines()[0].replace("🎮", "").split("–")[0].strip()
        game_posts[title] = update.message.message_id
        save_games()
        await update.message.reply_text(f"🗂️ Game indexed: {title}")

# Bad word filter
async def bad_word_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if any(bad in text for bad in BAD_WORDS):
        await update.message.reply_text("⚠️ Language alert! Respect the vault.")
        try: await update.message.delete()
        except: pass

# Main app
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("rank", rank))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("find", find))
    app.add_handler(CommandHandler("requestgame", requestgame))
    app.add_handler(CommandHandler("listcategory", listcategory))

    # Message watchers
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), game_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), bad_word_filter))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), check_flood))

    print("🤖 Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())