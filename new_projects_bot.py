import os
import requests
import time
import logging
import schedule
import threading
from datetime import datetime

from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode

# ===================== CONFIG =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
YOUR_CHAT_ID = int(os.getenv("YOUR_CHAT_ID"))

# Filters
MIN_LIQUIDITY = int(os.getenv("MIN_LIQUIDITY", 1500))
MIN_FDV = int(os.getenv("MIN_FDV", 3500))
BLACKLIST = ["test", "fake", "scam", "rug", "honeypot"]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
seen = set()

print("🚀 Akira Max Mode Activated - Private Scanner")

# ===================== CORE FUNCTIONS =====================
def is_blacklisted(name: str) -> bool:
    return any(word in name.lower() for word in BLACKLIST)

def send_alert(coin: dict, source: str):
    try:
        name = coin.get("name", "Unknown")
        symbol = coin.get("symbol", "???")
        mcap = coin.get("market_cap") or coin.get("usd_market_cap", 0)
        liquidity = coin.get("liquidity", 0)
        mint = coin.get("mint")
        
        if is_blacklisted(name):
            return

        msg = f"""🚀 <b>NEW {source.upper()} LAUNCH</b>

💎 <b>{name} ({symbol})</b>
📊 MCAP: ${mcap:,.0f}
💰 Liquidity: ${liquidity:,.0f}
⏰ Detected: {datetime.now().strftime('%H:%M:%S')}

🔗 <a href='https://pump.fun/{mint}'>Pump.fun</a> | <a href='https://dexscreener.com/solana/{mint}'>DexScreener</a>
        """

        bot.send_message(
            chat_id=YOUR_CHAT_ID,
            text=msg,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        logger.info(f"✅ Alert Sent → {name}")
    except Exception as e:
        logger.error(f"Alert failed: {e}")

# ===================== MAIN SCANNER =====================
def scan_pumpfun():
    logger.info("Scanning Pump.fun for new launches...")
    try:
        r = requests.get(
            "https://frontend-api.pump.fun/coins?offset=0&limit=40&sort=created_timestamp&order=DESC",
            timeout=15
        )
        
        if r.status_code != 200:
            logger.warning("Pump.fun API not responding")
            return
            
        coins = r.json()

        for coin in coins[:20]:
            mint = coin.get("mint")
            if not mint or mint in seen:
                continue

            mcap = coin.get("market_cap") or 0
            liquidity = coin.get("liquidity") or 0

            if liquidity < MIN_LIQUIDITY and mcap < MIN_FDV:
                continue

            seen.add(mint)
            send_alert(coin, "Pump.fun")
            time.sleep(0.6)
            
    except Exception as e:
        logger.error(f"Pump.fun scanner error: {e}")

# ===================== COMMANDS =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 <b>Akira Max Mode Activated</b>\nPrivate Scanner Running...", parse_mode=ParseMode.HTML)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"""<b>AKIRA STATUS</b>

🟢 Status: Online
📊 Min Liquidity: ${MIN_LIQUIDITY:,}
📈 Min FDV: ${MIN_FDV:,}
🔍 Scanning: Pump.fun (Real-time)
🛡️ Blacklist: Active
        """, parse_mode=ParseMode.HTML)

async def setminliq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global MIN_LIQUIDITY
    try:
        MIN_LIQUIDITY = int(context.args[0])
        await update.message.reply_text(f"✅ Minimum Liquidity updated to ${MIN_LIQUIDITY:,}")
    except:
        await update.message.reply_text("Usage: /setminliq 2000")

async def setminfdv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global MIN_FDV
    try:
        MIN_FDV = int(context.args[0])
        await update.message.reply_text(f"✅ Minimum FDV updated to ${MIN_FDV:,}")
    except:
        await update.message.reply_text("Usage: /setminfdv 5000")

# ===================== MAIN =====================
def run_scanners():
    schedule.every(18).seconds.do(scan_pumpfun)
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    if not BOT_TOKEN or not YOUR_CHAT_ID:
        logger.error("Missing BOT_TOKEN or YOUR_CHAT_ID in Variables!")
        exit(1)

    threading.Thread(target=run_scanners, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("setminliq", setminliq))
    app.add_handler(CommandHandler("setminfdv", setminfdv))

    logger.info("Akira Sophisticated Scanner Started Successfully")
    app.run_polling(drop_pending_updates=True)