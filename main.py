import os
import asyncio
import sqlite3
from datetime import datetime, timedelta

from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.types import BotCommand
from aiogram.filters import CommandStart
from mollie.api.client import Client
from bs4 import BeautifulSoup
import aiohttp

# ================= CONFIG =================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MOLLIE_API_KEY = os.getenv("MOLLIE_API_KEY")
BOT_USERNAME = "your_bot_name"  # пример: housing_bot_mollie
CHECK_INTERVAL = 30  # секунд
PRICE_2W = "19.90"
PRICE_4W = "29.90"

# ================= MOLLIE =================
mollie = Client()
mollie.set_api_key(MOLLIE_API_KEY)

# ================= DATABASE =================
conn = sqlite3.connect("bot.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY,
    language TEXT,
    subscription_end TEXT
)
""")
conn.commit()

def add_user(user_id):
    cursor.execute("INSERT OR IGNORE INTO users(id,language) VALUES (?,?)", (user_id, "en"))
    conn.commit()

def update_subscription(user_id, days):
    end = datetime.now() + timedelta(days=days)
    cursor.execute("UPDATE users SET subscription_end=? WHERE id=?", (end.strftime("%Y-%m-%d %H:%M:%S"), user_id))
    conn.commit()

# ================= PARSERS =================
async def parse_pararius():
    url = "https://www.pararius.com/apartments/netherlands"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            html = await resp.text()
    soup = BeautifulSoup(html,"html.parser")
    ads = []
    for item in soup.select("a.property-listing-link"):
        title = item.get_text(strip=True)
        link = "https://www.pararius.com" + item["href"]
        ads.append((title,link))
    return ads

async def parse_kamernet():
    url = "https://kamernet.nl/en/for-rent/rooms"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            html = await resp.text()
    soup = BeautifulSoup(html,"html.parser")
    ads = []
    for item in soup.select("a.tile"):
        title = item.get_text(strip=True)
        link = "https://kamernet.nl" + item["href"]
        ads.append((title,link))
    return ads

# ================= PAYMENT =================
async def create_payment(plan):
    price = PRICE_2W if plan=="2w" else PRICE_4W
    payment = mollie.payments.create({
        "amount": {"currency":"EUR", "value": price},
        "description":"Housing bot subscription",
        "redirectUrl": f"https://t.me/{BOT_USERNAME}",
        "method":"ideal"
    })
    return payment.checkout_url

# ================= BOT =================
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot)

@dp.message(CommandStart())
async def start(message: types.Message):
    add_user(message.from_user.id)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("2 weeks €19.90", "4 weeks €29.90")
    await message.answer("Welcome to Housing Bot\nChoose subscription:", reply_markup=keyboard)

@dp.message()
async def buy(message: types.Message):
    if message.text == "2 weeks €19.90":
        link = await create_payment("2w")
        await message.answer(f"Pay with iDEAL:\n{link}")
    elif message.text == "4 weeks €29.90":
        link = await create_payment("4w")
        await message.answer(f"Pay with iDEAL:\n{link}")

# ================= FASTAPI SERVER =================
app = FastAPI()

@app.post(f"/{TELEGRAM_TOKEN}")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = types.Update(**data)
    await dp.process_update(update)
    return {"ok": True}

# ================= SCRAPER LOOP =================
async def parser_loop():
    while True:
        ads = []
        ads += await parse_pararius()
        ads += await parse_kamernet()
        users = cursor.execute("SELECT id FROM users").fetchall()
        for ad in ads:
            for user in users:
                try:
                    await bot.send_message(user[0], f"New listing\n\n{ad[0]}\n{ad[1]}")
                except:
                    pass
        await asyncio.sleep(CHECK_INTERVAL)

# ================= RUN =================
if __name__ == "__main__":
    import uvicorn
    loop = asyncio.get_event_loop()
    loop.create_task(parser_loop())
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
