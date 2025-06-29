import logging
from telegram import Update, ChatPermissions, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from collections import defaultdict
import time
import asyncio
import json
import os
from datetime import datetime

# 🔐 Bot Token (Secure via Environment Variable)
BOT_TOKEN = os.getenv("BOT_TOKEN")  # OR replace with your bot token string

# ⚙️ Settings
FLOOD_LIMIT = 5
FLOOD_TIME = 6
MUTE_DURATION = 600  # 10 minutes
WARN_LIMIT = 3
CHANNEL_ID = -1002081570293  # Your backup channel ID

# 📁 Data Files
DATA_FILE = "data.json"
GAMES_FILE = "games.json"
CATEGORIES_FILE = "categories.json"
REQUESTS_FILE = "requests.json"

# 📋 Messages
WELCOME_MESSAGE = "👋 Welcome to *The Gaming Vault*! Type /rules to know the rules baby!"
RULES_MESSAGE = "📜 *Group Rules*\n1. No spamming\n2. No bad words\n3. Respect all\n4. Use /find to search\n5. /requestgame to request"

# 🧹 Bad Words
BAD_WORDS = ["fuck", "bitch", "chutiya", "madarchod", "randi"]

# 🤖 Custom Replies
CUSTOM_REPLIES = {
    "link": "🔗 Game links are only for channel followers. Check pinned post!",
    "offline": "📴 Server down ho sakta hai. Thoda ruk jao baby...",
    "error": "⚠️ Oops! Kuch galat ho gaya. Contact admin please!"
}

# 📦 In-Memory Stores
user_xp = defaultdict(int)
user_warnings = defaultdict(int)
game_posts = {}
categories = {}
game_requests = {}
user_messages = defaultdict(list)

# 🛠️ Load Saved Data
def load_data():
    global user_xp, user_warnings, game_posts, categories, game_requests
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            user_xp.update({int(k): v for k, v in data.get("xp", {}).items()})
            user_warnings.update({int(k): v for k, v in data.get("warns", {}).items()})
    if os.path.exists(GAMES_FILE):
        with open(GAMES_FILE, 'r') as f:
            game_posts.update(json.load(f))
    if os.path.exists(CATEGORIES_FILE):
        with open(CATEGORIES_FILE, 'r') as f:
            categories.update(json.load(f))
    if os.path.exists(REQUESTS_FILE):
        with open(REQUESTS_FILE, 'r') as f:
            game_requests.update(json.load(f))

# 💾 Save Functions
def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump({"xp": dict(user_xp), "warns": dict(user_warnings)}, f)

def save_games():
    with open(GAMES_FILE, 'w') as f:
        json.dump(game_posts, f)

def save_categories():
    with open(CATEGORIES_FILE, 'w') as f:
        json.dump(categories, f)

def save_requests():
    with open(REQUESTS_FILE, 'w') as f:
        json.dump(game_requests, f)

# ✅ Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot is online & sexy as ever!\nUse /rules, /rank, /daily XP & more!")

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text(RULES_MESSAGE, parse_mode="Markdown")
    try:
        await context.bot.pin_chat_message(update.effective_chat.id, msg.message_id)
    except Exception as e:
        logging.warning(f"Pin failed: {e}")

async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        await update.message.reply_text(WELCOME_MESSAGE, parse_mode="Markdown")

# 🧠 XP
async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    xp = user_xp[user_id]
    level = xp // 10
    await update.message.reply_text(f"🏅 XP: {xp} | Level: {level}")

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sorted_users = sorted(user_xp.items(), key=lambda x: x[1], reverse=True)[:5]
    leaderboard = "🏆 *Top 5 Members:*\n"
    for i, (uid, xp) in enumerate(sorted_users, 1):
        leaderboard += f"{i}. User {uid} – {xp} XP\n"
    await update.message.reply_text(leaderboard, parse_mode="Markdown")

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_xp[user_id] += 10
    save_data()
    await update.message.reply_text("🎁 Daily XP collected! +10 XP 🥳")

# 🎮 Game Management
async def find(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(context.args).lower()
    if not query:
        await update.message.reply_text("❓ Use: /find <game name>")
        return
    matches = [g for g in game_posts if query in g.lower()]
    if matches:
        await update.message.reply_text("🎮 Found:\n" + '\n'.join(f"• {m}" for m in matches))
    else:
        await update.message.reply_text("❌ No games found baby 😢")

async def game_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "🎮" in update.message.text and "Download Links" in update.message.text:
        title_line = update.message.text.splitlines()[0]
        title = title_line.replace("🎮", "").replace("– Full PC Game", "").strip()
        game_posts[title] = update.message.message_id
        save_games()

async def anti_fake_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if "pubg 5gb" in text or "hack game" in text:
        await update.message.reply_text("⚠️ Fake Game Alert! Yeh post suspicious lagta hai.")
        await update.message.delete()

async def suggest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    genre = ' '.join(context.args).lower()
    genre_map = {
        "action": ["GTA V", "Sleeping Dogs", "Max Payne 3"],
        "openworld": ["RDR2", "Watch Dogs", "Cyberpunk"],
        "adventure": ["Uncharted 4", "Tomb Raider", "Life is Strange"]
    }
    suggestions = genre_map.get(genre, [])
    if suggestions:
        await update.message.reply_text("🎯 Try These:\n• " + '\n• '.join(suggestions))
    else:
        await update.message.reply_text("🤔 Genre not found baby. Try: action, openworld, adventure")

# 📝 Requests
async def requestgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    game = ' '.join(context.args)
    if not game:
        await update.message.reply_text("📝 Use: /requestgame <game name>")
        return
    user = update.message.from_user.username or update.message.from_user.first_name
    game_requests[game] = user
    save_requests()
    await update.message.reply_text(f"✅ Request added for: {game} by {user}")

async def requestlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not game_requests:
        await update.message.reply_text("📭 No requests yet.")
        return
    msg = "📋 Game Requests:\n"
    for g, u in game_requests.items():
        msg += f"• {g} – {u}\n"
    await update.message.reply_text(msg)

# 🗂️ Categories
async def addcategory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❗Use: /addcategory <game> <category>")
        return
    game, category = context.args[0], context.args[1]
    if category not in categories:
        categories[category] = []
    if game not in categories[category]:
        categories[category].append(game)
        save_categories()
        await update.message.reply_text(f"✅ {game} added to {category}")

async def listcategory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❗Use: /listcategory <category>")
        return
    category = context.args[0]
    if category in categories:
        msg = f"🎮 *{category.upper()} Games:*\n" + '\n'.join(f"• {g}" for g in categories[category])
        await update.message.reply_text(msg, parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Category not found.")

# 🚨 Flood Protection
async def check_flood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    chat_id = update.effective_chat.id
    now = time.time()
    user_messages[user_id] = [t for t in user_messages[user_id] if now - t < FLOOD_TIME]
    user_messages[user_id].append(now)

    if len(user_messages[user_id]) > FLOOD_LIMIT:
        user_warnings[user_id] += 1
        warns = user_warnings[user_id]
        save_data()

        if warns >= WARN_LIMIT:
            await update.message.reply_text("⛔ Auto-muted for spamming. You'll be unmuted in 10 mins.")
            await context.bot.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=False), until_date=int(now + MUTE_DURATION))
            await asyncio.sleep(MUTE_DURATION)
            await context.bot.restrict_chat_member(chat_id, user_id, ChatPermissions(can_send_messages=True))
            await update.message.reply_text("✅ User auto-unmuted after 10 mins.")
        else:
            await update.message.reply_text(f"⚠️ Warning {warns}/{WARN_LIMIT}: Don’t spam baby!")

# ⏰ Weekly Backup
async def weekly_backup(app):
    while True:
        now = datetime.now()
        if now.weekday() == 6 and now.hour == 12:
            with open(GAMES_FILE, 'rb') as f:
                await app.bot.send_document(CHANNEL_ID, InputFile(f), caption="📦 Weekly Game Backup\n🤖 Powered with love by *Your AI Baby* 💖", parse_mode="Markdown")
            with open(CATEGORIES_FILE, 'rb') as f:
                await app.bot.send_document(CHANNEL_ID, InputFile(f), caption="📂 Category Backup\n🤖 Powered with love by *Your AI Baby* 💖", parse_mode="Markdown")
            await asyncio.sleep(86400)
        await asyncio.sleep(3600)

# 🚀 Run the Bot
async def main():
    load_data()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("rank", rank))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("find", find))
    app.add_handler(CommandHandler("suggest", suggest))
    app.add_handler(CommandHandler("requestgame", requestgame))
    app.add_handler(CommandHandler("requestlist", requestlist))
    app.add_handler(CommandHandler("addcategory", addcategory))
    app.add_handler(CommandHandler("listcategory", listcategory))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, game_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, anti_fake_check))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_flood))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))

    # Start backup loop
    asyncio.create_task(weekly_backup(app))

    print("🤖 Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
