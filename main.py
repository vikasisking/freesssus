import requests
import re
import time
import hashlib
import html
from bs4 import BeautifulSoup
from flask import Flask, Response
import threading
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
import asyncio
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LOGIN_URL = "http://54.37.83.141/ints/signin"
XHR_URL = "http://54.37.83.141/ints/agent/res/data_smscdr.php?fdate1=2025-08-29%2000:00:00&fdate2=2026-08-29%2023:59:59&frange=&fclient=&fnum=&fcli=&fgdate=&fgmonth=&fgrange=&fgclient=&fgnumber=&fgcli=&fg=0&sEcho=1&iColumns=9&sColumns=%2C%2C%2C%2C%2C%2C%2C%2C&iDisplayStart=0&iDisplayLength=25&mDataProp_0=0&sSearch_0=&bRegex_0=false&bSearchable_0=true&bSortable_0=true&mDataProp_1=1&sSearch_1=&bRegex_1=false&bSearchable_1=true&bSortable_1=true&mDataProp_2=2&sSearch_2=&bRegex_2=false&bSearchable_2=true&bSortable_2=true&mDataProp_3=3&sSearch_3=&bRegex_3=false&bSearchable_3=true&bSortable_3=true&mDataProp_4=4&sSearch_4=&bRegex_4=false&bSearchable_4=true&bSortable_4=true&mDataProp_5=5&sSearch_5=&bRegex_5=false&bSearchable_5=true&bSortable_5=true&mDataProp_6=6&sSearch_6=&bRegex_6=false&bSearchable_6=true&bSortable_6=true&mDataProp_7=7&sSearch_7=&bRegex_7=false&bSearchable_7=true&bSortable_7=true&mDataProp_8=8&sSearch_8=&bRegex_8=false&bSearchable_8=true&bSortable_8=false&sSearch=&bRegex=false&iSortCol_0=0&sSortDir_0=desc&iSortingCols=1&_=1756483799946"

USERNAME = os.getenv("USERNAME", "hereee")
PASSWORD = os.getenv("PASSWORD", "hereee")
BOT_TOKEN = os.getenv("BOT_TOKEN", "hereee")
ADMIN_ID = os.getenv("ADMIN_ID", "7761576669")
DEVELOPER_ID = "@hiden_25"
CHANNEL_LINK = "https://t.me/freeotpss"
ALERT_SENDERS = ["HDFC", "TELEGRAM", "SBI", "ICICI", "PAYTM"]
CHAT_IDS = CHAT_IDS = [
    "-1001926462756"
]
PRIVATE_LOG_ID = "-1003033822065"  
USER_IDS_FILE = "user_ids.txt"
OTP_LOG_FILE = "otp_logs.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "http://54.37.83.141/ints/login"
}
AJAX_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "http://54.37.83.141/ints/agent/SMSCDRStats"
}

app = Flask(__name__)
bot = telegram.Bot(token=BOT_TOKEN)
session = requests.Session()

seen = set()
USER_IDS = set()
try:
    if os.path.exists(USER_IDS_FILE):
        with open(USER_IDS_FILE, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    USER_IDS.add(int(line))
        logger.info(f"Loaded {len(USER_IDS)} user ids from {USER_IDS_FILE}")
except Exception as e:
    logger.exception("Failed loading user ids:")

def login():
    try:
        res = session.get("http://54.37.83.141/ints/login", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")

        captcha_text = None
        for string in soup.stripped_strings:
            if "What is" in string and "+" in string:
                captcha_text = string.strip()
                break

        match = re.search(r"What is\s*(\d+)\s*\+\s*(\d+)", captcha_text or "")
        if not match:
            logger.error("Captcha not found on login page.")
            return False

        a, b = int(match.group(1)), int(match.group(2))
        captcha_answer = str(a + b)
        logger.info(f"Captcha solved: {a} + {b} = {captcha_answer}")

        payload = {"username": USERNAME, "password": PASSWORD, "capt": captcha_answer}
        res = session.post(LOGIN_URL, data=payload, headers=HEADERS, timeout=15)
        if "SMSCDRStats" not in res.text:
            logger.error("Login failed - SMSCDRStats not found.")
            return False

        logger.info("Logged in successfully.")
        return True
    except Exception as e:
        logger.exception("Exception during login:")
        return False

def mask_number(number: str) -> str:
    if not number:
        return ""
    number = str(number)
    if len(number) <= 6:
        return number
    mid = len(number) // 2
    start = max(1, mid - 1)
    end = mid + 2
    return number[:start] + "***" + (number[end:] if end < len(number) else "")

def persist_user_id(user_id: int):
    if user_id in USER_IDS:
        return
    USER_IDS.add(user_id)
    try:
        with open(USER_IDS_FILE, "a") as f:
            f.write(str(user_id) + "\n")
    except Exception:
        logger.exception("Failed to persist user id")

async def send_telegram_message(time_, country, number, sender, message):
    public_msg = (
        f"<blockquote>🌍 <b>{country}</b> | 🏷️ <b>{sender}</b><b>OTP Received</b> 🔐</blockquote>\n"
        "<blockquote>━━━━━━━━━━━━━━</blockquote>\n"
        f"<blockquote>⏰ <b>Captured At:</b> <code>{html.escape(str(time_))}</code></blockquote>\n"
        f"<blockquote>🌍 <b>Region:</b> <code>{html.escape(str(country))}</code></blockquote>\n"
        f"<blockquote>📱 <b>Target:</b> <code>{mask_number(number)}</code></blockquote>\n"
        f"<blockquote>🏷️ <b>Service/App:</b> <code>{html.escape(str(sender))}</code></blockquote>\n"
        "<blockquote>💬 <b>Content:</b></blockquote>\n"
        f"<blockquote><code>{html.escape(str(message))}</code></blockquote>\n\n"
        "<blockquote>━━━━━━━━━━━━━━━</blockquote>\n"
        f"<blockquote>👨‍💻 Crafted by <a href='https://t.me/{DEVELOPER_ID.lstrip('@')}'>{DEVELOPER_ID}</a></blockquote>"
        f"<blockquote>🚀 Powered by <a href='{CHANNEL_LINK}'>Free OTPs</a></blockquote>"
    )

    private_msg = (
        f"🔐 <b>Full OTP Log (Private)</b>\n\n"
        f"⏰ Time: {html.escape(str(time_))}\n"
        f"🌍 Region: {html.escape(str(country))}\n"
        f"📱 Number: {html.escape(str(number))}\n"
        f"🏷️ Sender: {html.escape(str(sender))}\n"
        f"💬 Message: {html.escape(str(message))}"
    )

    keyboard = [
        [
            InlineKeyboardButton("👨‍💻 Developer", url=f"https://t.me/{DEVELOPER_ID.lstrip('@')}"),
            InlineKeyboardButton("📢 Channel", url=f"{CHANNEL_LINK}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    for chat_id in CHAT_IDS:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=public_msg,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to send public message to {chat_id}: {e}")

    try:
        await bot.send_message(
            chat_id=PRIVATE_LOG_ID,
            text=private_msg,
            disable_web_page_preview=True,
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Failed to send private log: {e}")

async def send_alert(number, sender, message):
    alert_msg = (
        f"🚨 <b>ALERT: Sensitive OTP Detected</b>\n\n"
        f"📱 Number: {html.escape(str(number))}\n"
        f"🏷️ Sender: {html.escape(str(sender))}\n"
        f"💬 Message: {html.escape(str(message))}"
    )
    try:
        await bot.send_message(PRIVATE_LOG_ID, text=alert_msg, parse_mode="HTML")
    except Exception as e:
        logger.error("Failed to send alert:", exc_info=e)

async def start_command_handler(update: ContextTypes.DEFAULT_TYPE, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        if user:
            user_id = user.id
            persist_user_id(user_id)

        keyboard = [
            [
                InlineKeyboardButton("📂 GitHub Source", url="https://github.com/ceo-developer"),
                InlineKeyboardButton("👨‍💻 Contact", url=f"https://t.me/{DEVELOPER_ID.lstrip('@')}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "✅ Bot is Active & Running!\n\n"
            "⚡ Use the options below for quick access:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    except Exception:
        logger.exception("Error in start_command_handler")

async def broadcast_handler(update: ContextTypes.DEFAULT_TYPE, context: ContextTypes.DEFAULT_TYPE):
    try:
        if str(update.effective_user.id) != str(ADMIN_ID):
            return await update.message.reply_text("❌ You are not authorized.")

        if not context.args:
            return await update.message.reply_text("⚠️ Usage: /broadcast <message>")

        msg = " ".join(context.args)
        sent = 0
        for uid in list(USER_IDS):
            try:
                await bot.send_message(uid, msg)
                sent += 1
            except Exception:
                pass

        await update.message.reply_text(f"✅ Broadcast finished. Sent to {sent} users.")
    except Exception:
        logger.exception("Error in broadcast_handler")

async def export_users_handler(update: ContextTypes.DEFAULT_TYPE, context: ContextTypes.DEFAULT_TYPE):
    try:
        if str(update.effective_user.id) != str(ADMIN_ID):
            return await update.message.reply_text("❌ Unauthorized")

        if not os.path.exists(USER_IDS_FILE):
            return await update.message.reply_text("No user ids file found.")

        with open(USER_IDS_FILE, "rb") as f:
            await update.message.reply_document(document=f, filename=USER_IDS_FILE)
    except Exception:
        logger.exception("Error in export_users_handler")

def fetch_otp_loop():
    logger.info("🔄 Starting OTP fetch loop...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    if not login():
        logger.error("Login failed — OTP loop will not start.")
        return

    while True:
        try:
            res = session.get(XHR_URL, headers=AJAX_HEADERS, timeout=20)
            data = res.json()
            otps = data.get("aaData", [])

            otps = [row for row in otps if isinstance(row[0], str) and ":" in row[0]]

            new_found = False
            with open(OTP_LOG_FILE, "a", encoding="utf-8") as f:
                for row in otps:
                    time_ = row[0]
                    operator = row[1].split("-")[0] if row[1] else ""
                    number = row[2] if len(row) > 2 else ""
                    sender = row[3] if len(row) > 3 else ""
                    message = row[5] if len(row) > 5 else ""

                    hash_id = hashlib.md5((str(number) + str(time_) + str(message)).encode()).hexdigest()
                    if hash_id in seen:
                        continue
                    seen.add(hash_id)
                    new_found = True

                    log_formatted = (
                        f"⏰ Time: {time_}\n"
                        f"📍 Operator: {operator}\n"
                        f"📱 Number: {number}\n"
                        f"🏷️ Sender: {sender}\n"
                        f"💬 Message: {message}\n"
                        f"{'-'*60}\n"
                    )
                    print(log_formatted)
                    f.write(log_formatted + "\n")

                    loop.run_until_complete(send_telegram_message(time_, operator, number, sender, message))

                    try:
                        if str(sender).upper() in ALERT_SENDERS:
                            loop.run_until_complete(send_alert(number, sender, message))
                    except Exception:
                        logger.exception("alerting failed")

            if not new_found:
                logger.debug("⏳ No new OTPs.")
        except Exception:
            logger.exception("❌ Error fetching OTPs")
        time.sleep(2)
@app.route('/health')
def health():
    return Response("OK", status=200)

@app.route('/')
def root():
    logger.info("Root endpoint requested")
    return Response("OK", status=200)
def start_telegram_listener():
    app_builder = Application.builder().token(BOT_TOKEN).build()
    app_builder.add_handler(CommandHandler("start", start_command_handler))
    app_builder.add_handler(CommandHandler("broadcast", broadcast_handler))
    app_builder.add_handler(CommandHandler("export_users", export_users_handler))

    logger.info("Starting Telegram listener (polling)...")
    app_builder.run_polling()

def start_otp_loop_thread():
    t = threading.Thread(target=fetch_otp_loop, daemon=True)
    t.start()
    return t

def start_flask_thread():
    t = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=8080), daemon=True)
    t.start()
    return t
if __name__ == '__main__':
    start_otp_loop_thread()
    start_flask_thread()

    start_telegram_listener()
