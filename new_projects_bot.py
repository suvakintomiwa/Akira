import os
import requests
import time
import logging
import schedule
import threading
import sys
from datetime import datetime

from telegram import Bot
from telegram.ext import Application, CommandHandler
from telegram.constants import ParseMode

# ====================== YOUR CREDENTIALS ======================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8973126506:AAEup-O1Ba1ZDKw7VaQ5AvO3XpFVbuorE_o")
YOUR_CHAT_ID = int(os.getenv("YOUR_CHAT_ID", "7495097942"))

# ====================== SETTINGS ======================
MIN_LIQUIDITY = int(os.getenv("MIN_LIQUIDITY", 1500))
MIN_FDV = int(os.getenv("MIN_FDV", 3500))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

seen = set()
bot = Bot(token=BOT_TOKEN)

print("🚀 Akira Max Private Scanner Started...")

# ====================== ALERT FUNCTION ======================
def send_alert(coin, source):
    try:
        name = coin.get("name", "Unknown")
        symbol = coin.get("symbol", "???")
        mcap = coin.get("market_cap") or 0
        liquidity = coin.get("liquidity") or 0
        mint = coin.get("mint")

        msg = f"""🚀 <b>NEW {source.upper()} LAUNCH</b>

💎 <b>{name} ({symbol})</b>
📊 MCAP: ${mcap:,.0f}
💰 Liquidity: ${liquidity:,.0f}
⏰ {datetime.now().strftime("%H:%M:%S")}

🔗 <a href="https://pump.fun/{mint}">Pump.fun</a> | <a href="https://dexscreener.com/solana/{mint}">DexScreener</a>
"""

        bot.send_message(
            chat_id=YOUR_CHAT_ID,
            text=msg,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        logger.info(f"Alert Sent → {name}")
    except Exception as e:
        logger.error(f"Send alert error: {e}")

# ====================== PUMP.FUN SCANNER ======================
def scan_pumpfun():
    logger.info("Scanning Pump.fun for fresh launches...")
    try:
        r = requests.get(
            "https://frontend-api.pump.fun/coins?offset=0&limit=35&sort=created_timestamp&order=DESC",
            timeout=15
        )
        
        if r.status_code != 200:
            return

        coins = r.json()

        for coin in coins[:18]:
            mint = coin.get("mint")
            if not mint or mint in seen:
                continue

            liquidity = coin.get("liquidity") or 0
            mcap = coin.get("market_cap") or 0

            if liquidity < MIN_LIQUIDITY and mcap < MIN_FDV:
                continue

            seen.add(mint)
            send_alert(coin, "Pump.fun")
            time.sleep(0.7)
            
    except Exception as e:
        logger.error(f"Pump.fun scanner failed: {e}")

# ====================== COMMANDS ======================
async def cmd_start(update, context):
    await update.message.reply_text("🔥 <b>Akira is Fully Online</b>\nPrivate Mode Activated", parse_mode=ParseMode.HTML)

async def cmd_status(update, context):
    await update.message.reply_text(f"""<b>AKIRA STATUS</b>

🟢 Running
Min Liquidity: ${MIN_LIQUIDITY:,}
Min FDV: ${MIN_FDV:,}
Mode: Pump.fun Real-time Scanner
    """, parse_mode=ParseMode.HTML)

async def cmd_setliq(update, context):
    global MIN_LIQUIDITY
    if context.args:
        MIN_LIQUIDITY = int(context.args[0])
        await update.message.reply_text(f"✅ Min Liquidity set to ${MIN_LIQUIDITY:,}")
    else:
        await update.message.reply_text("Usage: /setliq 2000")

# ====================== MAIN ======================
def run_scanners():
    schedule.every(20).seconds.do(scan_pumpfun)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    logger.info("Starting Akira Scanner...")
    threading.Thread(target=run_scanners, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("setliq", cmd_setliq))

    logger.info("Bot Polling Started - Ready for Action")
    app.run_polling(drop_pending_updates=True)
