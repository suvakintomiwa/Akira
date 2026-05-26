import os
import requests
import time
import logging
import schedule
import threading
from datetime import datetime

from telegram import Bot
from telegram.ext import Application, CommandHandler
from telegram.constants import ParseMode

# ====================== YOUR INFO ======================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8973126506:AAEup-O1Ba1ZDKw7VaQ5AvO3XpFVbuorE_o")
YOUR_CHAT_ID = int(os.getenv("YOUR_CHAT_ID", "7495097942"))

MIN_LIQUIDITY = int(os.getenv("MIN_LIQUIDITY", 1200))
MIN_FDV = int(os.getenv("MIN_FDV", 3000))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

seen = set()
bot = Bot(token=BOT_TOKEN)

print("🚀 Akira Private Scanner v3 Started")

# ====================== ALERT ======================
def send_alert(coin):
    try:
        name = coin.get("name", "Unknown")
        symbol = coin.get("symbol", "???")
        mcap = coin.get("market_cap") or 0
        liquidity = coin.get("liquidity") or 0
        mint = coin.get("mint")

        msg = f"""🚀 <b>NEW PUMP.FUN LAUNCH</b>

💎 <b>{name} ({symbol})</b>
📊 MCAP: ${mcap:,.0f}
💰 Liquidity: ${liquidity:,.0f}

🔗 <a href="https://pump.fun/{mint}">Pump.fun</a> • <a href="https://dexscreener.com/solana/{mint}">DexScreener</a>
"""

        bot.send_message(chat_id=YOUR_CHAT_ID, text=msg, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        logger.info(f"✅ Sent alert: {name}")
    except Exception as e:
        logger.error(f"Send error: {e}")

# ====================== SCANNER ======================
def scan_pumpfun():
    try:
        logger.info("Scanning new coins...")
        r = requests.get(
            "https://frontend-api.pump.fun/coins?offset=0&limit=30&sort=created_timestamp&order=DESC",
            timeout=12
        )
        coins = r.json() if r.status_code == 200 else []

        for coin in coins[:15]:
            mint = coin.get("mint")
            if not mint or mint in seen:
                continue

            liquidity = coin.get("liquidity") or 0
            mcap = coin.get("market_cap") or 0

            if liquidity < MIN_LIQUIDITY and mcap < MIN_FDV:
                continue

            seen.add(mint)
            send_alert(coin)
            time.sleep(0.8)
    except Exception as e:
        logger.error(f"Scan error: {e}")

# ====================== COMMANDS ======================
async def start(update, context):
    await update.message.reply_text("✅ <b>Akira is Running Successfully</b>", parse_mode=ParseMode.HTML)

# ====================== MAIN ======================
def run_scanners():
    schedule.every(20).seconds.do(scan_pumpfun)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    threading.Thread(target=run_scanners, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    logger.info("Starting polling...")
    app.run_polling(drop_pending_updates=True)
