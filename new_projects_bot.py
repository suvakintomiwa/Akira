import os
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
BOT_TOKEN = os.getenv("8973126506:AAEup-O1Ba1ZDKw7VaQ5AvO3XpFVbuorE_o")
YOUR_CHAT_ID = int(os.getenv("7495097942"))

MIN_LIQUIDITY = int(os.getenv("MIN_LIQUIDITY", 1500))
MIN_FDV = int(os.getenv("MIN_FDV", 4000))
ENABLED_CHAINS = [x.strip() for x in os.getenv("ENABLED_CHAINS", "solana,base,ethereum").split(",")]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("🚀 Akira Bot Starting on Railway...")

# DB Setup
conn = sqlite3.connect("seen_projects.db", check_same_thread=False)
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

def send_alert(project, source):
    try:
        msg = f"🚀 <b>New {source} Project</b>\n\n"
        msg += f"💎 {project.get('name')} ({project.get('symbol')})\n"
        msg += f"💰 Liq: ${project.get('liquidity',0):,.0f} | MCAP: ${project.get('mcap',0):,.0f}\n"
        
        if project.get("url"):
            msg += f"\n🔗 {project['url']}"
        
        bot.send_message(
            chat_id=YOUR_CHAT_ID, 
            text=msg, 
            parse_mode=ParseMode.HTML, 
            disable_web_page_preview=True
        )
        logger.info(f"✅ Alert sent → {project.get('name')}")
    except Exception as e:
        logger.error(f"Send failed: {e}")

# Pump.fun Scanner
def scan_pumpfun():
    logger.info("Scanning Pump.fun...")
    try:
        r = requests.get(
            "https://frontend-api.pump.fun/coins?offset=0&limit=30&sort=created_timestamp&order=DESC", 
            timeout=15
        )
        coins = r.json() if r.status_code == 200 else []
        
        for coin in coins[:20]:
            mint = coin.get("mint")
            if not mint or is_seen(mint):
                continue

            project = {
                "name": coin.get("name"),
                "symbol": coin.get("symbol"),
                "mcap": coin.get("market_cap", 0),
                "liquidity": coin.get("liquidity", 0),
                "url": f"https://pump.fun/{mint}"
            }
            send_alert(project, "Pump.fun")
            mark_seen(mint, "Pump.fun")
            time.sleep(0.6)
    except Exception as e:
        logger.error(f"Pump.fun error: {e}")

# Main
def run_scanners():
    schedule.every(22).seconds.do(scan_pumpfun)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_scanners, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", lambda u,c: u.message.reply_text("✅ Akira is running on Railway!")))
    
    logger.info("Bot Started Successfully - Polling...")
    app.run_polling(drop_pending_updates=True)   # This helps with conflicts