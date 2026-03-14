import asyncio
import aiosqlite
import aiohttp
import logging
import os
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from mollie.api.client import Client

# ================= НАСТРОЙКА ЛОГИРОВАНИЯ =================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ================= CONFIG =================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MOLLIE_API_KEY = os.getenv("MOLLIE_API_KEY")
BOT_USERNAME   = os.getenv("BOT_USERNAME")
RAILWAY_URL    = os.getenv("RAILWAY_URL")

STANDARD_DELAY = 900
CHECK_INTERVAL = 300
DB_PATH = "bot.db"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

# Глобальная сессия
http_session: aiohttp.ClientSession = None

# ================= MOLLIE =================
mollie = Client()
if MOLLIE_API_KEY:
    mollie.set_api_key(MOLLIE_API_KEY)

# ================= ТЕКСТЫ (ПОЛНЫЕ) =================
TEXTS = {
    "en": {
        "welcome": "🏠 <b>Housing Bot Netherlands</b>\n\nI monitor new rental listings on Pararius, Kamernet and Huurwoningen and send you instant alerts.\n\nChoose your language:",
        "choose_city": "📍 Choose your city:",
        "choose_plan": "💎 <b>Choose your plan:</b>\n\n🆓 <b>Demo</b> — 24 hours free\n\n📦 <b>Standard</b>\n• 15 min after Premium\n• 2 weeks — €9.90\n• 4 weeks — €15.90\n\n👑 <b>Premium</b>\n• First to get listings\n• Ready-made letter\n• 2 weeks — €19.90\n• 4 weeks — €29.90",
        "demo_activated": "✅ <b>Demo activated!</b>\nYou have 24 hours of free Premium access.",
        "sub_active": "✅ <b>Subscription active</b>\n\nPlan: {plan}\nExpires: {date}\nDays left: {days}",
        "sub_none": "❌ <b>No active subscription</b>\n\nChoose a plan:",
        "new_listing": "🏠 <b>New listing!</b>\n\n{title}\n\n🔗 {url}",
        "new_listing_premium": "👑 <b>New listing!</b>\n\n{title}\n\n🔗 {url}\n\n✉️ <b>Ready-made letter:</b>\n\n{letter}",
        "payment_ok": "✅ <b>Payment confirmed!</b>\nYour {plan} subscription is now active until {date}.",
        "payment_error": "❌ Payment error. Please try again.",
        "letter": "Dear landlord,\n\nI am very interested in renting this property. I am a reliable tenant and can provide all documents.\n\nBest regards",
        "city_set": "✅ City set to: <b>{city}</b>\n\nNow choose your plan:",
        "btn_demo": "🆓 Demo (24h free)",
        "btn_std_2w": "📦 Standard — 2 weeks €9.90",
        "btn_std_4w": "📦 Standard — 4 weeks €15.90",
        "btn_prm_2w": "👑 Premium — 2 weeks €19.90",
        "btn_prm_4w": "👑 Premium — 4 weeks €29.90",
        "btn_my_sub": "📋 My subscription",
        "btn_change_city": "📍 Change city",
    },
    "ru": {
        "welcome": "🏠 <b>Housing Bot Нидерланды</b>\n\nМониторю новые объявления на Pararius, Kamernet и Huurwoningen.\n\nВыбери язык:",
        "choose_city": "📍 Выбери город:",
        "choose_plan": "💎 <b>Выбери план:</b>\n\n🆓 <b>Демо</b> — 24 часа бесплатно\n\n📦 <b>Стандарт</b>\n• На 15 мин позже Премиума\n• 2 недели — €9.90\n• 4 недели — €15.90\n\n👑 <b>Премиум</b>\n• Первым получаешь объявления\n• Готовое письмо лендлорду\n• 2 недели — €19.90\n• 4 недели — €29.90",
        "demo_activated": "✅ <b>Демо активировано!</b>\nУ тебя 24 часа бесплатного Премиум доступа.",
        "sub_active": "✅ <b>Подписка активна</b>\n\nПлан: {plan}\nДо: {date}\nОсталось дней: {days}",
        "sub_none": "❌ <b>Нет активной подписки</b>\n\nВыбери план:",
        "new_listing": "🏠 <b>Новое объявление!</b>\n\n{title}\n\n🔗 {url}",
        "new_listing_premium": "👑 <b>Новое объявление!</b>\n\n{title}\n\n🔗 {url}\n\n✉️ <b>Готовое письмо лендлорду:</b>\n\n{letter}",
        "payment_ok": "✅ <b>Оплата подтверждена!</b>\nПодписка {plan} активна до {date}.",
        "payment_error": "❌ Ошибка оплаты. Попробуй ещё раз.",
        "letter": "Geachte verhuurder,\n\nI am very interested in renting this property. I am a reliable tenant and can provide all necessary documents.\n\nBest regards",
        "city_set": "✅ Город выбран: <b>{city}</b>\n\nТеперь выбери план:",
        "btn_demo": "🆓 Демо (24ч бесплатно)",
        "btn_std_2w": "📦 Стандарт — 2 недели €9.90",
        "btn_std_4w": "📦 Стандарт — 4 недели €15.90",
        "btn_prm_2w": "👑 Премиум — 2 недели €19.90",
        "btn_prm_4w": "👑 Премиум — 4 недели €29.90",
        "btn_my_sub": "📋 Моя подписка",
        "btn_change_city": "📍 Сменить город",
    },
    "nl": {
        "welcome": "🏠 <b>Housing Bot Nederland</b>\n\nIk monitor nieuwe woningen на Pararius, Kamernet en Huurwoningen.\n\nKies je taal:",
        "choose_city": "📍 Kies je stad:",
        "choose_plan": "💎 <b>Kies je abonnement:</b>\n\n🆓 <b>Demo</b> — 24 uur gratis\n\n📦 <b>Standaard</b>\n• 15 min na Premium\n• 2 weken — €9,90\n• 4 weken — €15,90\n\n👑 <b>Premium</b>\n• Als eerste nieuwe woningen\n• Kant-en-klare brief\n• 2 weken — €19,90\n• 4 weken — €29,90",
        "demo_activated": "✅ <b>Demo geactiveerd!</b>\nJe hebt 24 uur gratis Premium toegang.",
        "sub_active": "✅ <b>Abonnement actief</b>\n\nPlan: {plan}\nVerloopt: {date}\nDagen over: {days}",
        "sub_none": "❌ <b>Geen actief abonnement</b>\n\nKies een abonnement:",
        "new_listing": "🏠 <b>Nieuwe woning!</b>\n\n{title}\n\n🔗 {url}",
        "new_listing_premium": "👑 <b>Nieuwe woning!</b>\n\n{title}\n\n🔗 {url}\n\n✉️ <b>Kant-en-klare brief:</b>\n\n{letter}",
        "payment_ok": "✅ <b>Betaling bevestigd!</b>\nJe {plan} abonnement is actief tot {date}.",
        "payment_error": "❌ Betalingsfout. Probeer het opnieuw.",
        "letter": "Geachte verhuurder,\n\nIk ben zeer geïnteresseerd in het huren van deze woning. Ik ben een betrouwbare huurder.\n\nMet vriendelijke groet",
        "city_set": "✅ Stad ingesteld op: <b>{city}</b>\n\nKies nu je abonnement:",
        "btn_demo": "🆓 Demo (24u gratis)",
        "btn_std_2w": "📦 Standaard — 2 weken €9,90",
        "btn_std_4w": "📦 Standaard — 4 weken €15,90",
        "btn_prm_2w": "👑 Premium — 2 weken €19,90",
        "btn_prm_4w": "👑 Premium — 4 weken €29,90",
        "btn_my_sub": "📋 Mijn abonnement",
        "btn_change_city": "📍 Stad wijzigen",
    }
}

CITIES = ["Amsterdam", "Rotterdam", "Den Haag", "Utrecht", "Eindhoven", "Groningen", "Tilburg", "Almere", "Breda", "Nijmegen", "Leiden", "Haarlem"]

PLAN_PRICES = {
    "std_2w": ("9.90", "Standard", 2),
    "std_4w": ("15.90", "Standard", 4),
    "prm_2w": ("19.90", "Premium", 2),
    "prm_4w": ("29.90", "Premium", 4),
}

# ================= БАЗА ДАННЫХ =================

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                language TEXT DEFAULT 'en',
                city TEXT,
                plan TEXT,
                subscription_end TEXT,
                demo_used INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS sent_ads (
                url TEXT PRIMARY KEY,
                sent_at TEXT
            );
            CREATE TABLE IF NOT EXISTS pending_standard (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                url TEXT,
                send_after TEXT
            );
            CREATE TABLE IF NOT EXISTS payments (
                payment_id TEXT PRIMARY KEY,
                user_id INTEGER,
                plan TEXT,
                weeks INTEGER
            );
        """)
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users WHERE id=?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def has_active_sub(user_id: int):
    user = await get_user(user_id)
    if not user or not user['subscription_end']: return False
    return datetime.strptime(user['subscription_end'], "%Y-%m-%d %H:%M:%S") > datetime.now()

async def update_subscription(user_id: int, plan: str, weeks: int):
    user = await get_user(user_id)
    now = datetime.now()
    if user and user['subscription_end']:
        try:
            current_end = datetime.strptime(user['subscription_end'], "%Y-%m-%d %H:%M:%S")
            base = max(current_end, now)
        except: base = now
    else: base = now
    new_end = base + timedelta(weeks=weeks)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET plan=?, subscription_end=? WHERE id=?", 
                       (plan, new_end.strftime("%Y-%m-%d %H:%M:%S"), user_id))
        await db.commit()
    return new_end

# ================= КЛАВИАТУРЫ =================

def lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇬🇧 EN", callback_data="lang_en"),
        InlineKeyboardButton(text="🇳🇱 NL", callback_data="lang_nl"),
        InlineKeyboardButton(text="🇷🇺 RU", callback_data="lang_ru")
    ]])

def city_kb():
    buttons = []
    row = []
    for city in CITIES:
        row.append(InlineKeyboardButton(text=city, callback_data=f"city_{city}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row: buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def plan_kb(lang, demo_used):
    buttons = []
    if not demo_used:
        buttons.append([InlineKeyboardButton(text=TEXTS[lang]["btn_demo"], callback_data="plan_demo")])
    buttons.append([InlineKeyboardButton(text=TEXTS[lang]["btn_std_2w"], callback_data="plan_std_2w")])
    buttons.append([InlineKeyboardButton(text=TEXTS[lang]["btn_std_4w"], callback_data="plan_std_4w")])
    buttons.append([InlineKeyboardButton(text=TEXTS[lang]["btn_prm_2w"], callback_data="plan_prm_2w")])
    buttons.append([InlineKeyboardButton(text=TEXTS[lang]["btn_prm_4w"], callback_data="plan_prm_4w")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def main_kb(lang):
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=TEXTS[lang]["btn_my_sub"])],
        [KeyboardButton(text=TEXTS[lang]["btn_change_city"])]
    ], resize_keyboard=True)

# ================= ПАРСЕРЫ =================

async def fetch_html(url):
    try:
        async with http_session.get(url, headers=HEADERS, timeout=20) as r:
            if r.status == 200: return await r.text()
    except Exception as e: logger.error(f"Fetch error {url}: {e}")
    return None

async def parse_pararius(city):
    url = f"https://www.pararius.com/apartments/{city.lower()}" if city else "https://www.pararius.com/apartments/netherlands"
    html = await fetch_html(url)
    if not html: return []
    soup = BeautifulSoup(html, "html.parser")
    return [(a.get_text(strip=True), "https://www.pararius.com" + a.get("href")) for a in soup.select("section.listing-search-item a[href*='/apartment']")]

async def parse_kamernet(city):
    url = f"https://kamernet.nl/en/for-rent/rooms-{city.lower()}" if city else "https://kamernet.nl/en/for-rent/rooms"
    html = await fetch_html(url)
    if not html: return []
    soup = BeautifulSoup(html, "html.parser")
    return [(a.get_text(strip=True)[:100], "https://kamernet.nl" + a.get("href")) for a in soup.select("a.search-result-item")]

# ================= ХЕНДЛЕРЫ БОТА =================

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(m: types.Message):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (m.from_user.id,))
        await db.commit()
    await m.answer(TEXTS["en"]["welcome"], reply_markup=lang_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("lang_"))
async def cb_lang(c: types.CallbackQuery):
    lang = c.data.split("_")[1]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET language=? WHERE id=?", (lang, c.from_user.id))
        await db.commit()
    await c.message.edit_text(TEXTS[lang]["choose_city"], reply_markup=city_kb(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("city_"))
async def cb_city(c: types.CallbackQuery):
    city = c.data.split("_", 1)[1]
    user = await get_user(c.from_user.id)
    lang = user['language'] if user else "en"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET city=? WHERE id=?", (city, c.from_user.id))
        await db.commit()
    await c.message.edit_text(TEXTS[lang]["city_set"].format(city=city), reply_markup=plan_kb(lang, bool(user['demo_used'])), parse_mode="HTML")

@dp.callback_query(F.data.startswith("plan_"))
async def cb_plan(c: types.CallbackQuery):
    plan_key = c.data.split("_", 1)[1]
    user = await get_user(c.from_user.id)
    lang = user['language']
    
    if plan_key == "demo":
        if user['demo_used']: return await c.answer("Demo already used!", show_alert=True)
        end = datetime.now() + timedelta(hours=24)
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE users SET plan='Premium', subscription_end=?, demo_used=1 WHERE id=?", (end.strftime("%Y-%m-%d %H:%M:%S"), c.from_user.id))
            await db.commit()
        await c.message.edit_text(TEXTS[lang]["demo_activated"], parse_mode="HTML")
        await c.message.answer("🏠", reply_markup=main_kb(lang))
        return

    price_val, plan_name, weeks = PLAN_PRICES[plan_key]
    payment = mollie.payments.create({
        "amount": {"currency": "EUR", "value": price_val},
        "description": f"Housing Bot - {plan_name}",
        "redirectUrl": f"https://t.me/{BOT_USERNAME}",
        "webhookUrl": f"{RAILWAY_URL}/webhook/mollie",
        "method": "ideal",
        "metadata": {"user_id": str(c.from_user.id), "plan": plan_name, "weeks": str(weeks)}
    })
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO payments (payment_id, user_id, plan, weeks) VALUES (?,?,?,?)", (payment.id, c.from_user.id, plan_name, weeks))
        await db.commit()
    
    await c.message.edit_text(f"💳 <b>{plan_name}</b>\n\n<a href='{payment.checkout_url}'>Pay with iDEAL</a>", parse_mode="HTML", disable_web_page_preview=True)

@dp.message()
async def handle_text(m: types.Message):
    user = await get_user(m.from_user.id)
    if not user: return
    lang = user['language']
    
    if m.text in [TEXTS[l]["btn_my_sub"] for l in TEXTS]:
        if await has_active_sub(m.from_user.id):
            end_dt = datetime.strptime(user['subscription_end'], "%Y-%m-%d %H:%M:%S")
            days = (end_dt - datetime.now()).days
            await m.answer(TEXTS[lang]["sub_active"].format(plan=user['plan'], date=end_dt.strftime("%d %b %Y"), days=days), parse_mode="HTML")
        else:
            await m.answer(TEXTS[lang]["sub_none"], reply_markup=plan_kb(lang, bool(user['demo_used'])), parse_mode="HTML")
            
    elif m.text in [TEXTS[l]["btn_change_city"] for l in TEXTS]:
        await m.answer(TEXTS[lang]["choose_city"], reply_markup=city_kb(), parse_mode="HTML")

# ================= WEBHOOK И ШЕДУЛЕР =================

async def mollie_webhook(request):
    data = await request.post()
    payment = mollie.payments.get(data.get("id"))
    if payment.is_paid():
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM payments WHERE payment_id=?", (payment.id,)) as c:
                info = await c.fetchone()
        if info:
            end_dt = await update_subscription(info['user_id'], info['plan'], info['weeks'])
            user = await get_user(info['user_id'])
            await bot.send_message(info['user_id'], TEXTS[user['language']]["payment_ok"].format(plan=info['plan'], date=end_dt.strftime("%d %b %Y")), parse_mode="HTML")
    return web.Response(status=200)

async def parse_and_send():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM users") as c:
            users = await c.fetchall()
    
    active_users = [u for u in users if u['subscription_end'] and datetime.strptime(u['subscription_end'], "%Y-%m-%d %H:%M:%S") > datetime.now()]
    cities = set(u['city'] for u in active_users if u['city'])
    
    for city in cities:
        ads_results = await asyncio.gather(parse_pararius(city), parse_kamernet(city), return_exceptions=True)
        all_ads = [a for sub in ads_results if isinstance(sub, list) for a in sub]
        
        for title, url in all_ads:
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute("SELECT 1 FROM sent_ads WHERE url=?", (url,)) as c:
                    if await c.fetchone(): continue
                await db.execute("INSERT INTO sent_ads (url, sent_at) VALUES (?,?)", (url, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                await db.commit()

            for u in [user for user in active_users if user['city'] == city]:
                if u['plan'] == "Premium":
                    text = TEXTS[u['language']]["new_listing_premium"].format(title=title, url=url, letter=TEXTS[u['language']]["letter"])
                    await bot.send_message(u['id'], text, parse_mode="HTML", disable_web_page_preview=True)
                else:
                    after = (datetime.now() + timedelta(seconds=STANDARD_DELAY)).strftime("%Y-%m-%d %H:%M:%S")
                    async with aiosqlite.connect(DB_PATH) as db:
                        await db.execute("INSERT INTO pending_standard (user_id, title, url, send_after) VALUES (?,?,?,?)", (u['id'], title, url, after))
                        await db.commit()
                await asyncio.sleep(0.05)

async def send_pending():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM pending_standard WHERE send_after <= ?", (now_str,)) as c:
            rows = await c.fetchall()
        for r in rows:
            user = await get_user(r['user_id'])
            if user:
                await bot.send_message(r['user_id'], TEXTS[user['language']]["new_listing"].format(title=r['title'], url=r['url']), parse_mode="HTML")
            await db.execute("DELETE FROM pending_standard WHERE id=?", (r['id'],))
            await db.commit()

async def scheduler():
    while True:
        try:
            await parse_and_send()
            await send_pending()
        except Exception as e: logger.error(f"Scheduler error: {e}")
        await asyncio.sleep(CHECK_INTERVAL)

# ================= ЗАПУСК =================

async def main():
    await init_db()
    global http_session
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        http_session = session
        app = web.Application()
        app.router.add_post("/webhook/mollie", mollie_webhook)
        app.router.add_get("/health", lambda r: web.Response(text="OK"))
        runner = web.AppRunner(app)
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", int(os.environ.get("PORT", 8080))).start()
        asyncio.create_task(scheduler())
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
