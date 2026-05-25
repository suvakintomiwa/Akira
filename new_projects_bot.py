import requests
import time
import sqlite3
import logging
from datetime import datetime
import schedule
import threading

from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

# ========================= CONFIG =========================
BOT_TOKEN = "8973126506:AAEup-O1Ba1ZDKw7VaQ5AvO3XpFVbuorE_o"      # ← PUT YOUR TOKEN HERE
YOUR_CHAT_ID = 7495097942             # ← PUT YOUR CHAT ID HERE

MIN_LIQUIDITY = 3000
MIN_FDV = 5000
ENABLED_CHAINS = ["solana", "base", "ethereum"]
PAUSED = False

DB_FILE = "seen_projects.db"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# DB
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
conn.execute("CREATE TABLE IF NOT EXISTS seen (pair_id TEXT PRIMARY KEY, source TEXT, timestamp TEXT)")
conn.commit()

bot = Bot(token=BOT_TOKEN)

def is_seen(pair_id):
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM seen WHERE pair_id=?", (pair_id,))
    return cursor.fetchone() is not None

def mark_seen(pair_id, source):
    conn.execute("INSERT OR IGNORE INTO seen (pair_id, source, timestamp) VALUES (?, ?, ?)",
                 (pair_id, source, datetime.now().isoformat()))
    conn.commit()

# Socials
def get_social_links(mint: str):
    socials = {"twitter": None, "telegram": None, "website": None}
    try:
        url = f"https://public-api.birdeye.so/defi/token_overview?address={mint}"
        headers = {"x-chain": "solana"}
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code == 200:
            data = r.json().get("data", {})
            socials["twitter"] = data.get("twitter")
            socials["telegram"] = data.get("telegram")
            socials["website"] = data.get("website")
    except:
        pass
    return socials

def send_alert(project, source="General"):
    if PAUSED: return
    msg = f"🚀 <b>New Project Detected!</b> [{source}]\n\n"
    msg += f"💎 <b>{project.get('name')} ({project.get('symbol')})</b>\n"
    msg += f"🔗 Chain: {project.get('chain', 'Solana').upper()}\n"
    
    if project.get('mcap'): msg += f"📊 MCAP: ${project.get('mcap'):,.0f}\n"
    if project.get('liquidity'): msg += f"💰 Liquidity: ${project.get('liquidity'):,.0f}\n"

    socials = project.get("socials", {})
    if socials.get("twitter"): msg += f"🐦 <a href='{socials['twitter']}'>Twitter</a>\n"
    if socials.get("telegram"): msg += f"📱 <a href='{socials['telegram']}'>Telegram</a>\n"
    if socials.get("website"): msg += f"🌐 <a href='{socials['website']}'>Website</a>\n"
    
    if project.get("url"):
        msg += f"\n🔍 <a href='{project['url']}'>View Project</a>"

    bot.send_message(chat_id=YOUR_CHAT_ID, text=msg, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

# Scanners (simplified)
def scan_pumpfun():
    if PAUSED: return
    try:
        r = requests.get("https://frontend-api.pump.fun/coins?offset=0&limit=30&sort=created_timestamp&order=DESC", timeout=10)
        coins = r.json() if r.status_code == 200 else []
        
        for coin in coins:
            mint = coin.get("mint")
            if not mint or is_seen(mint): continue
                
            project = {
                "name": coin.get("name"),
                "symbol": coin.get("symbol"),
                "mcap": coin.get("market_cap"),
                "liquidity": coin.get("liquidity"),
                "chain": "solana",
                "socials": get_social_links(mint),
                "url": f"https://pump.fun/{mint}"
            }
            send_alert(project, "Pump.fun")
            mark_seen(mint, "Pump.fun")
            time.sleep(0.4)
    except: pass

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ <b>Akira Bot is Online!</b>", parse_mode=ParseMode.HTML)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Use /status to check settings", parse_mode=ParseMode.HTML)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    st = "🟢 Running" if not PAUSED else "⏸️ Paused"
    text = f"<b>Akira Status</b>\nStatus: {st}\nMin Liquidity: ${MIN_LIQUIDITY}\nMin FDV: ${MIN_FDV}"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# Main
def run_scanners():
    schedule.every(20).seconds.do(scan_pumpfun)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    print("🚀 Akira Bot Starting...")

    threading.Thread(target=run_scanners, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("status", status))

    print("🤖 Akira is now running! Test it on Telegram.")
    app.run_polling()