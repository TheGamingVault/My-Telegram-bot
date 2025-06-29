from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update
import os

# ✅ START Command Function
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is alive baby!")

# ✅ MAIN Function - NO asyncio.run()
async def main():
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    if not BOT_TOKEN:
        raise Exception("❌ BOT_TOKEN missing! Set it in environment variables.")
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    print("🤖 Bot started")
    await app.run_polling()

# ✅ Render-Compatible Event Loop Fix
import asyncio
try:
    asyncio.get_event_loop().run_until_complete(main())
except RuntimeError as e:
    if "already running" in str(e):
        asyncio.create_task(main())