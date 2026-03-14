import asyncio
import aiosqlite
import aiohttp
from aiohttp import web
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from mollie.api.client import Client
from datetime import datetime, timedelta
import os

# ================= CONFIG =================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8646275203:AAFenGqJIBpvk1DXrbBqDIOPiOILz3Zyllg")
MOLLIE_API_KEY = os.getenv("MOLLIE_API_KEY", "live_PDmrMrKdm2MCU2h8whmqcsHgxzxEM9")
BOT_USERNAME   = os.getenv("BOT_USERNAME", "best_rent_nl_bot")
RAILWAY_URL    = os.getenv("RAILWAY_URL", "https://nlhousinghunter-production.up.railway.app")

STANDARD_DELAY = 900   # 15 минут задержки для Стандарт (в секундах)
CHECK_INTERVAL = 300   # проверка каждые 5 минут

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# ================= ТЕКСТЫ =================

TEXTS = {
    "en": {
        "welcome": (
            "🏠 <b>Housing Bot Netherlands</b>\n\n"
            "I monitor new rental listings on Pararius, Kamernet and Huurwoningen "
            "and send you instant alerts.\n\n"
            "Choose your language:"
        ),
        "choose_city": "📍 Choose your city:",
        "choose_plan": (
            "💎 <b>Choose your plan:</b>\n\n"
            "🆓 <b>Demo</b> — 24 hours free\n\n"
            "📦 <b>Standard</b>\n"
            "• Links to new listings\n"
            "• 15 min after Premium\n"
            "• 2 weeks — €9.90\n"
            "• 4 weeks — €15.90\n\n"
            "👑 <b>Premium</b>\n"
            "• First to get listings\n"
            "• Ready-made letter to landlord\n"
            "• 2 weeks — €19.90\n"
            "• 4 weeks — €29.90"
        ),
        "demo_activated": (
            "✅ <b>Demo activated!</b>\n\n"
            "You have 24 hours of free Premium access.\n"
            "Enjoy the listings!"
        ),
        "sub_active": "✅ <b>Subscription active</b>\n\nPlan: {plan}\nExpires: {date}\nDays left: {days}",
        "sub_none": "❌ <b>No active subscription</b>\n\nChoose a plan:",
        "new_listing": "🏠 <b>New listing!</b>\n\n{title}\n\n🔗 {url}",
        "new_listing_premium": (
            "👑 <b>New listing!</b>\n\n"
            "{title}\n\n"
            "🔗 {url}\n\n"
            "✉️ <b>Ready-made letter to landlord:</b>\n\n"
            "{letter}"
        ),
        "payment_ok": (
            "✅ <b>Payment confirmed!</b>\n\n"
            "Your {plan} subscription is now active until {date}."
        ),
        "payment_error": "❌ Payment error. Please try again.",
        "letter": (
            "Dear landlord,\n\n"
            "I came across your listing and I am very interested in renting this property.\n"
            "I am a reliable tenant and can provide all necessary documents.\n"
            "Could we schedule a viewing at your earliest convenience?\n\n"
            "Looking forward to your reply.\n\n"
            "Best regards"
        ),
        "city_set": "✅ City set to: <b>{city}</b>\n\nNow choose your plan:",
        "btn_demo": "🆓 Demo (24h free)",
        "btn_std_2w": "📦 Standard — 2 weeks €9.90",
        "btn_std_4w": "📦 Standard — 4 weeks €15.90",
        "btn_prm_2w": "👑 Premium — 2 weeks €19.90",
        "btn_prm_4w": "👑 Premium — 4 weeks €29.90",
        "btn_my_sub": "📋 My subscription",
        "btn_change_city": "📍 Change city",
        "btn_change_lang": "🌍 Change language",
        "btn_info": "ℹ️ Info & FAQ",
        "choose_price": "💶 Choose max rent price:",
        "choose_type": "🏠 Choose property type:",
        "sub_expiring": "⚠️ <b>Your subscription expires in 3 days!</b>\n\nRenew now to keep receiving alerts.",
        "info_msg": "ℹ️ <b>Info & Support</b>",
        "faq_btn": "❓ FAQ",
        "disclaimer_btn": "⚖️ Disclaimer",
        "choose_radius": "📏 Choose search radius:",
        "radius_set": "✅ Radius set to <b>{radius} km</b> around {city}",
    },
    "nl": {
        "welcome": (
            "🏠 <b>Housing Bot Nederland</b>\n\n"
            "Ik monitor nieuwe huurwoningen op Pararius, Kamernet en Huurwoningen "
            "en stuur je direct een melding.\n\n"
            "Kies je taal:"
        ),
        "choose_city": "📍 Kies je stad:",
        "choose_plan": (
            "💎 <b>Kies je abonnement:</b>\n\n"
            "🆓 <b>Demo</b> — 24 uur gratis\n\n"
            "📦 <b>Standaard</b>\n"
            "• Links naar nieuwe woningen\n"
            "• 15 min na Premium\n"
            "• 2 weken — €9,90\n"
            "• 4 weken — €15,90\n\n"
            "👑 <b>Premium</b>\n"
            "• Als eerste nieuwe woningen\n"
            "• Kant-en-klare brief aan verhuurder\n"
            "• 2 weken — €19,90\n"
            "• 4 weken — €29,90"
        ),
        "demo_activated": (
            "✅ <b>Demo geactiveerd!</b>\n\n"
            "Je hebt 24 uur gratis Premium toegang.\n"
            "Veel succes met zoeken!"
        ),
        "sub_active": "✅ <b>Abonnement actief</b>\n\nAbonnement: {plan}\nVerloopt: {date}\nDagen over: {days}",
        "sub_none": "❌ <b>Geen actief abonnement</b>\n\nKies een abonnement:",
        "new_listing": "🏠 <b>Nieuwe woning!</b>\n\n{title}\n\n🔗 {url}",
        "new_listing_premium": (
            "👑 <b>Nieuwe woning!</b>\n\n"
            "{title}\n\n"
            "🔗 {url}\n\n"
            "✉️ <b>Kant-en-klare brief aan verhuurder:</b>\n\n"
            "{letter}"
        ),
        "payment_ok": (
            "✅ <b>Betaling bevestigd!</b>\n\n"
            "Je {plan} abonnement is actief tot {date}."
        ),
        "payment_error": "❌ Betalingsfout. Probeer het opnieuw.",
        "letter": (
            "Geachte verhuurder,\n\n"
            "Ik ben uw woning tegengekomen en ben zeer geïnteresseerd in het huren ervan.\n"
            "Ik ben een betrouwbare huurder en kan alle benodigde documenten overleggen.\n"
            "Zou het mogelijk zijn om een bezichtiging in te plannen?\n\n"
            "Met vriendelijke groet"
        ),
        "city_set": "✅ Stad ingesteld op: <b>{city}</b>\n\nKies nu je abonnement:",
        "btn_demo": "🆓 Demo (24u gratis)",
        "btn_std_2w": "📦 Standaard — 2 weken €9,90",
        "btn_std_4w": "📦 Standaard — 4 weken €15,90",
        "btn_prm_2w": "👑 Premium — 2 weken €19,90",
        "btn_prm_4w": "👑 Premium — 4 weken €29,90",
        "btn_my_sub": "📋 Mijn abonnement",
        "btn_change_city": "📍 Stad wijzigen",
        "btn_change_lang": "🌍 Taal wijzigen",
        "btn_info": "ℹ️ Info & FAQ",
        "choose_price": "💶 Choose max rent price:",
        "choose_type": "🏠 Choose property type:",
        "sub_expiring": "⚠️ <b>Your subscription expires in 3 days!</b>\n\nRenew now to keep receiving alerts.",
        "info_msg": "ℹ️ <b>Info & Support</b>",
        "faq_btn": "❓ FAQ",
        "disclaimer_btn": "⚖️ Disclaimer",
        "choose_radius": "📏 Kies zoekradius:",
        "radius_set": "✅ Radius ingesteld op <b>{radius} km</b> rondom {city}",
    },
    "ru": {
        "welcome": (
            "🏠 <b>Housing Bot Нидерланды</b>\n\n"
            "Мониторю новые объявления аренды на Pararius, Kamernet и Huurwoningen "
            "и сразу отправляю тебе.\n\n"
            "Выбери язык:"
        ),
        "choose_city": "📍 Выбери город:",
        "choose_plan": (
            "💎 <b>Выбери план:</b>\n\n"
            "🆓 <b>Демо</b> — 24 часа бесплатно\n\n"
            "📦 <b>Стандарт</b>\n"
            "• Ссылки на новые объявления\n"
            "• На 15 мин позже Премиума\n"
            "• 2 недели — €9.90\n"
            "• 4 недели — €15.90\n\n"
            "👑 <b>Премиум</b>\n"
            "• Первым получаешь объявления\n"
            "• Готовое письмо лендлорду\n"
            "• 2 недели — €19.90\n"
            "• 4 недели — €29.90"
        ),
        "demo_activated": (
            "✅ <b>Демо активировано!</b>\n\n"
            "У тебя 24 часа бесплатного Премиум доступа.\n"
            "Удачи в поиске жилья!"
        ),
        "sub_active": "✅ <b>Подписка активна</b>\n\nПлан: {plan}\nДо: {date}\nОсталось дней: {days}",
        "sub_none": "❌ <b>Нет активной подписки</b>\n\nВыбери план:",
        "new_listing": "🏠 <b>Новое объявление!</b>\n\n{title}\n\n🔗 {url}",
        "new_listing_premium": (
            "👑 <b>Новое объявление!</b>\n\n"
            "{title}\n\n"
            "🔗 {url}\n\n"
            "✉️ <b>Готовое письмо лендлорду:</b>\n\n"
            "{letter}"
        ),
        "payment_ok": (
            "✅ <b>Оплата подтверждена!</b>\n\n"
            "Подписка {plan} активна до {date}."
        ),
        "payment_error": "❌ Ошибка оплаты. Попробуй ещё раз.",
        "letter": (
            "Geachte verhuurder,\n\n"
            "I came across your listing and I am very interested in renting this property.\n"
            "I am a reliable tenant and can provide all necessary documents.\n"
            "Could we schedule a viewing at your earliest convenience?\n\n"
            "Looking forward to your reply.\n\n"
            "Best regards"
        ),
        "city_set": "✅ Город выбран: <b>{city}</b>\n\nТеперь выбери план:",
        "btn_demo": "🆓 Демо (24ч бесплатно)",
        "btn_std_2w": "📦 Стандарт — 2 недели €9.90",
        "btn_std_4w": "📦 Стандарт — 4 недели €15.90",
        "btn_prm_2w": "👑 Премиум — 2 недели €19.90",
        "btn_prm_4w": "👑 Премиум — 4 недели €29.90",
        "btn_my_sub": "📋 Моя подписка",
        "btn_change_city": "📍 Сменить город",
        "btn_change_lang": "🌍 Сменить язык",
        "btn_info": "ℹ️ Инфо & FAQ",
        "info_msg": "ℹ️ <b>Инфо & Поддержка</b>",
        "faq_btn": "❓ FAQ",
        "disclaimer_btn": "⚖️ Отказ от ответственности",
        "choose_price": "💶 Выбери максимальную цену:",
        "choose_type": "🏠 Выбери тип жилья:",
        "sub_expiring": "⚠️ <b>Твоя подписка истекает через 3 дня!</b>\n\nПродли сейчас чтобы продолжать получать объявления.",
        "choose_radius": "📏 Выбери радиус поиска:",
        "radius_set": "✅ Радиус <b>{radius} км</b> вокруг {city}",
    }
}


# ================= FAQ & DISCLAIMER =================

FAQ_TEXTS = {
    "en": {
        "faq": (
            "<b>❓ FAQ</b>\n\n"
            "<b>Q: How fast is the bot?</b>\n"
            "A: Premium users get alerts within seconds. Standard — 15-min delay.\n\n"
            "<b>Q: What is the Ready-made letter?</b>\n"
            "A: A professional rental cover letter in Dutch.\n"
            "💡 <i>Replace [YOUR NAME] and [PHONE NUMBER] before sending!</i>\n\n"
            "<b>Q: Does the bot guarantee a house?</b>\n"
            "A: No, it is a notification tool."
        ),
        "disclaimer": (
            "<b>⚖️ Disclaimer</b>\n\n"
            "<b>1. Service Scope:</b> This bot is independent and NOT affiliated with Pararius or Kamernet.\n\n"
            "<b>2. No Guarantees:</b> We do not guarantee rental success or listing accuracy.\n\n"
            "<b>3. User Responsibility:</b> Verify listings and deal directly with landlords.\n\n"
            "<b>4. Payments:</b> Fees are non-refundable once subscription is activated."
        ),
    },
    "nl": {
        "faq": (
            "<b>❓ FAQ</b>\n\n"
            "<b>V: Hoe snel is de bot?</b>\n"
            "A: Premium direct, Standard 15 min vertraging.\n\n"
            "<b>V: Wat is de brief?</b>\n"
            "A: Een professionele huurbrief in het Nederlands.\n"
            "💡 <i>Vul je naam en telefoonnummer in de [ ] in!</i>\n\n"
            "<b>V: Garandeert de bot een woning?</b>\n"
            "A: Nee, het is een hulpmiddel."
        ),
        "disclaimer": (
            "<b>⚖️ Disclaimer</b>\n\n"
            "<b>1. Servicedoel:</b> Deze bot is onafhankelijk en NIET gelieerd aan Pararius of Kamernet.\n\n"
            "<b>2. Geen garanties:</b> Wij garanderen geen huurcontracten.\n\n"
            "<b>3. Verantwoordelijkheid:</b> Controleer woningen zelf.\n\n"
            "<b>4. Betalingen:</b> Na activering is restitutie niet mogelijk."
        ),
    },
    "ru": {
        "faq": (
            "<b>❓ FAQ</b>\n\n"
            "<b>В: Как быстро работает бот?</b>\n"
            "О: Premium — мгновенно, Standard — задержка 15 минут.\n\n"
            "<b>В: Что такое готовое письмо?</b>\n"
            "О: Письмо на нидерландском для лендлорда.\n"
            "💡 <i>Подставь имя и телефон в [ ] перед отправкой!</i>\n\n"
            "<b>В: Гарантирует ли бот аренду?</b>\n"
            "О: Нет, бот — инструмент мониторинга."
        ),
        "disclaimer": (
            "<b>⚖️ Отказ от ответственности</b>\n\n"
            "<b>1. Статус:</b> Бот независим и НЕ связан с Pararius или Kamernet.\n\n"
            "<b>2. Без гарантий:</b> Мы не гарантируем аренду.\n\n"
            "<b>3. Ответственность:</b> Проверяй объявления самостоятельно.\n\n"
            "<b>4. Оплата:</b> После активации возврат не предусмотрен."
        ),
    },
}

CITIES = [
    "Amsterdam", "Rotterdam", "Den Haag", "Utrecht",
    "Eindhoven", "Groningen", "Tilburg", "Almere",
    "Breda", "Nijmegen", "Leiden", "Haarlem"
]

# ================= MOLLIE =================

mollie = Client()
if MOLLIE_API_KEY:
    mollie.set_api_key(MOLLIE_API_KEY)

# ================= БАЗА ДАННЫХ =================

DB_PATH = "bot.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id               INTEGER PRIMARY KEY,
                language         TEXT    DEFAULT 'en',
                city             TEXT,
                radius           INTEGER DEFAULT 10,
                max_price        INTEGER DEFAULT 0,
                prop_type        TEXT    DEFAULT 'any',
                plan             TEXT,
                subscription_end TEXT,
                demo_used        INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS sent_ads (
                url     TEXT PRIMARY KEY,
                sent_at TEXT
            );
            CREATE TABLE IF NOT EXISTS pending_standard (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER,
                title      TEXT,
                url        TEXT,
                send_after TEXT
            );
            CREATE TABLE IF NOT EXISTS payments (
                payment_id TEXT PRIMARY KEY,
                user_id    INTEGER,
                plan       TEXT,
                weeks      INTEGER
            );
        """)
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT * FROM users WHERE id=?", (user_id,))
        return await cursor.fetchone()

async def add_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
        await db.commit()

async def set_language(user_id: int, lang: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET language=? WHERE id=?", (lang, user_id))
        await db.commit()

async def set_city(user_id: int, city: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET city=? WHERE id=?", (city, user_id))
        await db.commit()

async def set_radius(user_id: int, radius: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET radius=? WHERE id=?", (radius, user_id))
        await db.commit()

async def set_price(user_id: int, price: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET max_price=? WHERE id=?", (price, user_id))
        await db.commit()

async def set_prop_type(user_id: int, prop_type: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET prop_type=? WHERE id=?", (prop_type, user_id))
        await db.commit()

async def activate_demo(user_id: int):
    end = datetime.now() + timedelta(hours=24)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET plan='Premium', subscription_end=?, demo_used=1 WHERE id=?",
            (end.strftime("%Y-%m-%d %H:%M:%S"), user_id)
        )
        await db.commit()

async def update_subscription(user_id: int, plan: str, weeks: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT subscription_end FROM users WHERE id=?", (user_id,))
        row = await cursor.fetchone()
    if row and row[0] and datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S") > datetime.now():
        base = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
    else:
        base = datetime.now()
    end = base + timedelta(weeks=weeks)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET plan=?, subscription_end=? WHERE id=?",
            (plan, end.strftime("%Y-%m-%d %H:%M:%S"), user_id)
        )
        await db.commit()
    return end

async def has_active_subscription(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT subscription_end FROM users WHERE id=?", (user_id,)
        )
        row = await cursor.fetchone()
    if not row or not row[0]:
        return False
    return datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S") > datetime.now()

async def save_payment(payment_id: str, user_id: int, plan: str, weeks: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO payments (payment_id, user_id, plan, weeks) VALUES (?,?,?,?)",
            (payment_id, user_id, plan, weeks)
        )
        await db.commit()

async def get_payment_info(payment_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id, plan, weeks FROM payments WHERE payment_id=?", (payment_id,)
        )
        return await cursor.fetchone()

async def ad_exists(url: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM sent_ads WHERE url=?", (url,))
        return await cursor.fetchone() is not None

async def save_ad(url: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO sent_ads (url, sent_at) VALUES (?,?)",
            (url, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        await db.commit()

async def add_pending_standard(user_id: int, title: str, url: str):
    send_after = (datetime.now() + timedelta(seconds=STANDARD_DELAY)).strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO pending_standard (user_id, title, url, send_after) VALUES (?,?,?,?)",
            (user_id, title, url, send_after)
        )
        await db.commit()

async def get_ready_pending():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, user_id, title, url FROM pending_standard WHERE send_after <= ?", (now,)
        )
        rows = await cursor.fetchall()
        if rows:
            ids = [str(r[0]) for r in rows]
            await db.execute(f"DELETE FROM pending_standard WHERE id IN ({','.join(ids)})")
            await db.commit()
    return rows

def t(lang: str, key: str) -> str:
    return TEXTS.get(lang, TEXTS["en"]).get(key, "")

# ================= КЛАВИАТУРЫ =================

def lang_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
            InlineKeyboardButton(text="🇳🇱 Nederlands", callback_data="lang_nl"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
        ]
    ])

def city_keyboard():
    buttons = []
    row = []
    for i, city in enumerate(CITIES):
        row.append(InlineKeyboardButton(text=city, callback_data=f"city_{city}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def radius_keyboard(city: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📍 2 km",  callback_data=f"radius_{city}_2"),
            InlineKeyboardButton(text="📍 5 km",  callback_data=f"radius_{city}_5"),
            InlineKeyboardButton(text="📍 10 km", callback_data=f"radius_{city}_10"),
            InlineKeyboardButton(text="📍 20 km", callback_data=f"radius_{city}_20"),
        ]
    ])

def price_keyboard(city: str, radius: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💶 Any price",  callback_data=f"price_{city}_{radius}_0"),
        ],
        [
            InlineKeyboardButton(text="≤ €800",  callback_data=f"price_{city}_{radius}_800"),
            InlineKeyboardButton(text="≤ €1200", callback_data=f"price_{city}_{radius}_1200"),
        ],
        [
            InlineKeyboardButton(text="≤ €1500", callback_data=f"price_{city}_{radius}_1500"),
            InlineKeyboardButton(text="≤ €2000", callback_data=f"price_{city}_{radius}_2000"),
        ],
    ])

def type_keyboard(city: str, radius: int, price: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Any type",   callback_data=f"type_{city}_{radius}_{price}_any")],
        [InlineKeyboardButton(text="🛏 Room",        callback_data=f"type_{city}_{radius}_{price}_room")],
        [InlineKeyboardButton(text="🏢 Apartment",  callback_data=f"type_{city}_{radius}_{price}_apartment")],
        [InlineKeyboardButton(text="🏡 House",      callback_data=f"type_{city}_{radius}_{price}_house")],
    ])

def plan_keyboard(lang: str, demo_used: bool):
    buttons = []
    if not demo_used:
        buttons.append([InlineKeyboardButton(text=t(lang, "btn_demo"), callback_data="plan_demo")])
    buttons.append([InlineKeyboardButton(text=t(lang, "btn_std_2w"), callback_data="plan_std_2w")])
    buttons.append([InlineKeyboardButton(text=t(lang, "btn_std_4w"), callback_data="plan_std_4w")])
    buttons.append([InlineKeyboardButton(text=t(lang, "btn_prm_2w"), callback_data="plan_prm_2w")])
    buttons.append([InlineKeyboardButton(text=t(lang, "btn_prm_4w"), callback_data="plan_prm_4w")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def main_keyboard(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_my_sub"))],
            [KeyboardButton(text=t(lang, "btn_change_city"))],
            [KeyboardButton(text=t(lang, "btn_change_lang"))],
            [KeyboardButton(text=t(lang, "btn_info"))],
        ],
        resize_keyboard=True
    )

# ================= ПАРСЕРЫ =================

async def parse_pararius(city: str = None, radius: int = 10) -> list[tuple[str, str]]:
    base = "https://www.pararius.com/apartments/netherlands"
    if city:
        base = f"https://www.pararius.com/apartments/{city.lower()}/{radius}km"
    ads = []
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(base, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    return []
                html = await resp.text()
        soup  = BeautifulSoup(html, "html.parser")
        items = (
            soup.select("li.search-list__item--listing a.listing-search-item__link--title")
            or soup.select("section.listing-search-item a[href*='/apartment']")
            or soup.select("a.property-listing-link")
        )
        for item in items:
            title = item.get_text(strip=True)
            href  = item.get("href", "")
            if href and title:
                ads.append((title, "https://www.pararius.com" + href))
        print(f"[Pararius/{city}] {len(ads)}")
    except Exception as e:
        print(f"[Pararius] ошибка: {e}")
    return ads


async def parse_kamernet(city: str = None, radius: int = 10) -> list[tuple[str, str]]:
    base = "https://kamernet.nl/en/for-rent/rooms"
    if city:
        base = f"https://kamernet.nl/en/for-rent/rooms-{city.lower()}?radius={radius}"
    ads = []
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(base, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    return []
                html = await resp.text()
        soup  = BeautifulSoup(html, "html.parser")
        items = (
            soup.select("a.search-result-item")
            or soup.select("a.tile")
        )
        for item in items:
            title = item.get_text(strip=True)[:120]
            href  = item.get("href", "")
            if href and title:
                ads.append((title, "https://kamernet.nl" + href))
        print(f"[Kamernet/{city}] {len(ads)}")
    except Exception as e:
        print(f"[Kamernet] ошибка: {e}")
    return ads


async def parse_huurwoningen(city: str = None, radius: int = 10) -> list[tuple[str, str]]:
    base = "https://www.huurwoningen.nl/aanbod/huurwoningen/"
    if city:
        base = f"https://www.huurwoningen.nl/in/{city.lower()}/?radius={radius}"
    ads = []
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(base, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    return []
                html = await resp.text()
        soup  = BeautifulSoup(html, "html.parser")
        items = (
            soup.select("a.listing-search-item__link")
            or soup.select("a[href*='/huurwoningen/']")
        )
        seen = set()
        for item in items:
            title = item.get_text(strip=True)[:120]
            href  = item.get("href", "")
            if not href or not title:
                continue
            if not href.startswith("http"):
                href = "https://www.huurwoningen.nl" + href
            if href not in seen:
                seen.add(href)
                ads.append((title, href))
        print(f"[Huurwoningen/{city}] {len(ads)}")
    except Exception as e:
        print(f"[Huurwoningen] ошибка: {e}")
    return ads

# ================= СОЗДАНИЕ ПЛАТЕЖА =================

PLAN_PRICES = {
    "std_2w":  ("9.90",  "Standard", 2),
    "std_4w":  ("15.90", "Standard", 4),
    "prm_2w":  ("19.90", "Premium",  2),
    "prm_4w":  ("29.90", "Premium",  4),
}

async def create_payment(plan_key: str, user_id: int) -> str:
    price, plan_name, weeks = PLAN_PRICES[plan_key]
    payment = mollie.payments.create({
        "amount": {"currency": "EUR", "value": price},
        "description": f"Housing Bot — {plan_name} {weeks} weeks",
        "redirectUrl": f"https://t.me/{BOT_USERNAME}",
        "webhookUrl":  f"{RAILWAY_URL}/webhook/mollie",
        "method": "ideal",
        "metadata": {"user_id": str(user_id), "plan": plan_name, "weeks": str(weeks)},
    })
    await save_payment(payment.id, user_id, plan_name, weeks)
    return payment.checkout_url

# ================= БОТ =================

bot = Bot(token=TELEGRAM_TOKEN)
dp  = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await add_user(message.from_user.id)
    await message.answer(
        t("en", "welcome"),
        reply_markup=lang_keyboard(),
        parse_mode="HTML"
    )


# --- Выбор языка ---
@dp.callback_query(F.data.startswith("lang_"))
async def cb_language(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    await set_language(callback.from_user.id, lang)
    await callback.message.edit_text(
        t(lang, "choose_city"),
        reply_markup=city_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


# --- Выбор города ---
@dp.callback_query(F.data.startswith("city_"))
async def cb_city(callback: types.CallbackQuery):
    city = callback.data.split("_", 1)[1]
    user  = await get_user(callback.from_user.id)
    lang  = user[1] if user else "en"
    demo_used = user[5] if user else 0
    await set_city(callback.from_user.id, city)
    await callback.message.edit_text(
        t(lang, "choose_radius"),
        reply_markup=radius_keyboard(city),
        parse_mode="HTML"
    )
    await callback.answer()


# --- Выбор радиуса ---
@dp.callback_query(F.data.startswith("radius_"))
async def cb_radius(callback: types.CallbackQuery):
    parts  = callback.data.split("_")   # radius_Amsterdam_10
    city   = parts[1]
    radius = int(parts[2])
    user   = await get_user(callback.from_user.id)
    lang   = user[1] if user else "en"
    demo_used = user[5] if user else 0
    await set_radius(callback.from_user.id, radius)
    await callback.message.edit_text(
        t(lang, "choose_price"),
        reply_markup=price_keyboard(city, radius),
        parse_mode="HTML"
    )
    await callback.answer()



# --- Выбор цены ---
@dp.callback_query(F.data.startswith("price_"))
async def cb_price(callback: types.CallbackQuery):
    parts  = callback.data.split("_")  # price_Amsterdam_10_800
    city   = parts[1]
    radius = int(parts[2])
    price  = int(parts[3])
    user   = await get_user(callback.from_user.id)
    lang   = user[1] if user else "en"
    await set_price(callback.from_user.id, price)
    await callback.message.edit_text(
        t(lang, "choose_type"),
        reply_markup=type_keyboard(city, radius, price),
        parse_mode="HTML"
    )
    await callback.answer()


# --- Выбор типа жилья ---
@dp.callback_query(F.data.startswith("type_"))
async def cb_type(callback: types.CallbackQuery):
    parts     = callback.data.split("_")  # type_Amsterdam_10_800_room
    city      = parts[1]
    radius    = int(parts[2])
    price     = int(parts[3])
    prop_type = parts[4]
    user      = await get_user(callback.from_user.id)
    lang      = user[1] if user else "en"
    demo_used = user[5] if user else 0
    await set_prop_type(callback.from_user.id, prop_type)
    type_labels = {"any": "Any", "room": "Room", "apartment": "Apartment", "house": "House"}
    price_label = f"≤ €{price}" if price > 0 else "Any price"
    await callback.message.edit_text(
        f"✅ <b>{city}</b> | {radius}km | {price_label} | {type_labels[prop_type]}\n\nNow choose your plan:",
        reply_markup=plan_keyboard(lang, bool(demo_used)),
        parse_mode="HTML"
    )
    await callback.answer()

# --- Выбор плана ---
@dp.callback_query(F.data.startswith("plan_"))
async def cb_plan(callback: types.CallbackQuery):
    plan_key = callback.data.split("_", 1)[1]
    user     = await get_user(callback.from_user.id)
    lang     = user[1] if user else "en"
    demo_used = user[5] if user else 0

    if plan_key == "demo":
        if demo_used:
            await callback.answer("Demo already used!", show_alert=True)
            return
        await activate_demo(callback.from_user.id)
        await callback.message.edit_text(
            t(lang, "demo_activated"),
            reply_markup=None,
            parse_mode="HTML"
        )
        await callback.message.answer(
            "👇",
            reply_markup=main_keyboard(lang)
        )
        await callback.answer()
        return

    if plan_key not in PLAN_PRICES:
        await callback.answer()
        return

    try:
        link = await create_payment(plan_key, callback.from_user.id)
        _, plan_name, weeks = PLAN_PRICES[plan_key]
        price = PLAN_PRICES[plan_key][0]
        await callback.message.edit_text(
            f"💳 <b>{plan_name} — {weeks} {'week' if weeks==1 else 'weeks'} (€{price})</b>\n\n"
            f"👉 <a href='{link}'>Pay with iDEAL</a>\n\n"
            "Subscription activates automatically after payment.",
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"[Payment] error: {e}")
        await callback.message.answer(t(lang, "payment_error"))
    await callback.answer()


# --- Моя подписка ---
@dp.message()
async def handle_text(message: types.Message):
    user = await get_user(message.from_user.id)
    if not user:
        await add_user(message.from_user.id)
        await cmd_start(message)
        return

    lang = user[1] or "en"

    # Кнопка "Моя подписка"
    if message.text in [t(l, "btn_my_sub") for l in ["en", "nl", "ru"]]:
        if await has_active_subscription(message.from_user.id):
            end_str   = user[4]
            end_dt    = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")
            days_left = max((end_dt - datetime.now()).days, 0)
            await message.answer(
                t(lang, "sub_active").format(
                    plan=user[3] or "-",
                    date=end_dt.strftime("%d %b %Y"),
                    days=days_left
                ),
                parse_mode="HTML"
            )
        else:
            demo_used = user[5] or 0
            await message.answer(
                t(lang, "sub_none"),
                reply_markup=plan_keyboard(lang, bool(demo_used)),
                parse_mode="HTML"
            )
        return

    # Кнопка "Сменить город"
    if message.text in [t(l, "btn_change_city") for l in ["en", "nl", "ru"]]:
        await message.answer(
            t(lang, "choose_city"),
            reply_markup=city_keyboard(),
            parse_mode="HTML"
        )
        return

    # Кнопка "Сменить язык"
    if message.text in [t(l, "btn_change_lang") for l in ["en", "nl", "ru"]]:
        await message.answer(
            t("en", "welcome"),
            reply_markup=lang_keyboard(),
            parse_mode="HTML"
        )
        return

    # Кнопка "Info & FAQ"
    if message.text in [t(l, "btn_info") for l in ["en", "nl", "ru"]]:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "faq_btn"),        callback_data="info_faq")],
            [InlineKeyboardButton(text=t(lang, "disclaimer_btn"), callback_data="info_disclaimer")],
            [InlineKeyboardButton(text="👨‍💻 Support", url="https://t.me/best_rent_nl_bot")],
        ])
        await message.answer(t(lang, "info_msg"), reply_markup=kb, parse_mode="HTML")
        return


# --- FAQ / Disclaimer callbacks ---
@dp.callback_query(F.data.startswith("info_"))
async def cb_info(callback: types.CallbackQuery):
    user = await get_user(callback.from_user.id)
    lang = user[1] if user else "en"
    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Back", callback_data="info_back")]
    ])
    if callback.data == "info_faq":
        await callback.message.edit_text(FAQ_TEXTS[lang]["faq"], reply_markup=back_kb, parse_mode="HTML")
    elif callback.data == "info_disclaimer":
        await callback.message.edit_text(FAQ_TEXTS[lang]["disclaimer"], reply_markup=back_kb, parse_mode="HTML")
    elif callback.data == "info_back":
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "faq_btn"),        callback_data="info_faq")],
            [InlineKeyboardButton(text=t(lang, "disclaimer_btn"), callback_data="info_disclaimer")],
            [InlineKeyboardButton(text="👨‍💻 Support", url="https://t.me/best_rent_nl_bot")],
        ])
        await callback.message.edit_text(t(lang, "info_msg"), reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# ================= WEBHOOK MOLLIE =================

async def mollie_webhook(request: web.Request) -> web.Response:
    try:
        data       = await request.post()
        payment_id = data.get("id")
        if not payment_id:
            return web.Response(status=400)

        payment = mollie.payments.get(payment_id)
        if payment.is_paid():
            info = await get_payment_info(payment_id)
            if info:
                user_id, plan, weeks = info
                end = await update_subscription(user_id, plan, weeks)
                user = await get_user(user_id)
                lang = user[1] if user else "en"
                try:
                    await bot.send_message(
                        user_id,
                        t(lang, "payment_ok").format(
                            plan=plan,
                            date=end.strftime("%d %b %Y")
                        ),
                        reply_markup=main_keyboard(lang),
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"[Webhook] send error: {e}")

        return web.Response(status=200)
    except Exception as e:
        print(f"[Webhook] error: {e}")
        return web.Response(status=500)


async def health(request: web.Request) -> web.Response:
    return web.Response(text="OK")

# ================= ЦИКЛ ПАРСЕРА =================

async def parse_and_send():
    # Собираем всех активных пользователей и их города
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, language, city, plan FROM users"
        )
        all_users = await cursor.fetchall()

    active_users = [u for u in all_users if await has_active_subscription(u[0])]
    if not active_users:
        return

    # Уникальные комбинации город+радиус
    city_radius_pairs = list(set((u[2], u[3]) for u in active_users if u[2]))

    all_ads = []
    for city, radius in city_radius_pairs:
        radius = radius or 10
        all_ads += await parse_pararius(city, radius)
        all_ads += await parse_kamernet(city, radius)
        all_ads += await parse_huurwoningen(city, radius)

    for title, url in all_ads:
        if await ad_exists(url):
            continue
        await save_ad(url)

        for user_id, lang, city, plan in active_users:
            # Фильтр по цене
            user_data = await get_user(user_id)
            max_price = user_data[4] if user_data else 0
            if max_price > 0:
                import re
                prices_found = re.findall(r"[€$]\s*(\d+)", title)
                if prices_found:
                    listing_price = int(prices_found[0])
                    if listing_price > max_price:
                        continue

            if plan == "Premium":
                letter = t(lang if lang in ["en", "nl"] else "en", "letter")
                text   = t(lang, "new_listing_premium").format(
                    title=title, url=url, letter=letter
                )
                try:
                    await bot.send_message(
                        user_id, text,
                        parse_mode="HTML",
                        disable_web_page_preview=True
                    )
                    await asyncio.sleep(0.05)
                except Exception as e:
                    print(f"[Send Premium] {user_id}: {e}")

            elif plan == "Standard":
                # Отправляем через 15 минут
                await add_pending_standard(user_id, title, url)


async def send_pending_standard():
    rows = await get_ready_pending()
    for row_id, user_id, title, url in rows:
        user = await get_user(user_id)
        if not user or not await has_active_subscription(user_id):
            continue
        lang = user[1] or "en"
        try:
            await bot.send_message(
                user_id,
                t(lang, "new_listing").format(title=title, url=url),
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            await asyncio.sleep(0.05)
        except Exception as e:
            print(f"[Send Standard] {user_id}: {e}")


async def check_expiring_subscriptions():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id, language, subscription_end, plan FROM users WHERE subscription_end IS NOT NULL")
        users = await cursor.fetchall()
    for user_id, lang, sub_end, plan in users:
        if not sub_end:
            continue
        try:
            end_dt = datetime.strptime(sub_end, "%Y-%m-%d %H:%M:%S")
            days_left = (end_dt - datetime.now()).days
            if days_left == 3:
                await bot.send_message(
                    user_id,
                    t(lang or "en", "sub_expiring"),
                    parse_mode="HTML"
                )
        except Exception as e:
            print(f"[Expiry] error for {user_id}: {e}")


async def scheduler():
    await asyncio.sleep(10)
    while True:
        try:
            await parse_and_send()
            await send_pending_standard()
            await check_expiring_subscriptions()
        except Exception as e:
            print(f"[Scheduler] error: {e}")
        await asyncio.sleep(CHECK_INTERVAL)

# ================= ЗАПУСК =================

async def main():
    await init_db()

    app = web.Application()
    app.router.add_post("/webhook/mollie", mollie_webhook)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"[Server] started on port {port}")

    asyncio.create_task(scheduler())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
