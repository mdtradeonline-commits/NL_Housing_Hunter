import asyncio
import aiosqlite
import aiohttp
import random
import re
import os
import logging
from aiohttp import web
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from mollie.api.client import Client
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)

# ================= CONFIG =================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MOLLIE_API_KEY = os.getenv("MOLLIE_API_KEY")
BOT_USERNAME   = os.getenv("BOT_USERNAME", "best_rent_nl_bot")
BASE_URL       = os.getenv("BASE_URL", "https://your-app.up.railway.app")
ADMIN_ID       = 6999400196

STANDARD_DELAY = 900   # 15 минут
CHECK_INTERVAL = 300   # 5 минут

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
]

def get_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

DB_PATH = "/data/bot.db"  # Railway persistent volume

# ================= ТЕКСТЫ =================

TEXTS = {
    "en": {
        "welcome": "🏠 <b>NL Housing Hunter</b>\n\nI monitor new rental listings on Pararius, Kamernet, Huurwoningen and Funda — and send you instant alerts.\n\nChoose your language:",
        "choose_city": "📍 Choose your city:",
        "choose_radius": "📏 Choose search radius:",
        "radius_set": "✅ Radius: <b>{radius} km</b> around {city}",
        "choose_price": "💶 Choose max rent price:",
        "choose_type": "🏠 Choose property type:",
        "choose_plan": (
            "💎 <b>Choose your plan:</b>\n\n"
            "🆓 <b>Demo</b> — 24 hours free\n\n"
            "📦 <b>Standard</b> — €15.90 / 4 weeks\n"
            "• Links to new listings\n"
            "• 15 min after Premium\n"
            "• Notifications 08:00–23:00\n\n"
            "👑 <b>Premium</b>\n"
            "• First to get listings\n"
            "• Ready-made letter to landlord\n"
            "• 24/7 notifications\n"
            "• 2 weeks — €19.90\n"
            "• 4 weeks — €29.90"
        ),
        "demo_activated": "✅ <b>Demo activated!</b>\n\nYou have 24 hours of free Premium access.\nGood luck with your search!",
        "sub_active": "✅ <b>Subscription active</b>\n\nPlan: {plan}\nExpires: {date}\nDays left: {days}",
        "sub_none": "❌ <b>No active subscription</b>\n\nChoose a plan to start receiving alerts:",
        "new_listing": "🏠 <b>New listing!</b>\n\n{title}\n\n🔗 {url}",
        "new_listing_premium": "👑 <b>New listing!</b>\n\n{title}\n\n🔗 {url}\n\n✉️ <b>Ready-made letter to landlord:</b>\n\n{letter}",
        "payment_link": "💳 <b>{plan} — {weeks} weeks (€{price})</b>\n\n👉 <a href='{link}'>Pay now</a>\n\nSubscription activates automatically after payment.",
        "payment_ok": "✅ <b>Payment confirmed!</b>\n\nYour {plan} subscription is active until {date}.",
        "payment_error": "❌ Payment error. Please try again.",
        "remind_24h": "⏰ <b>Your subscription expires in 24 hours!</b>\n\nRenew now to keep receiving alerts.",
        "remind_12h": "⏰ <b>Your subscription expires in 12 hours!</b>\n\nDon't miss new listings — renew now.",
        "night_mode_on": "🌙 Night mode enabled (08:00–23:00)",
        "night_mode_off": "🌟 24/7 mode enabled",
        "settings_saved": "✅ Settings saved: <b>{city}</b> | {radius}km | {price} | {prop_type}",
        "btn_demo": "🆓 Demo (24h free)",
        "btn_std_4w": "📦 Standard — 4 weeks €15.90",
        "btn_prm_2w": "👑 Premium — 2 weeks €19.90",
        "btn_prm_4w": "👑 Premium — 4 weeks €29.90",
        "btn_my_sub": "📋 My subscription",
        "btn_change_city": "📍 Change city",
        "btn_change_lang": "🌍 Language",
        "btn_info": "ℹ️ Info & FAQ",
        "btn_night_mode": "🌙 Night mode",
        "info_msg": "ℹ️ <b>Info & Support</b>\n\nChoose a topic:",
        "faq_btn": "❓ FAQ",
        "disclaimer_btn": "⚖️ Disclaimer",
        "tos_btn": "📄 Terms of Service",
        "privacy_btn": "🔒 Privacy Policy",
        "refund_btn": "💸 Refund Policy",
        "support_btn": "👨‍💻 Support",
        "back_btn": "⬅️ Back",
        "letter": (
            "Dear landlord,\n\n"
            "I came across your listing and I am very interested in renting this property.\n"
            "I am a reliable tenant with a stable income and can provide all necessary documents (proof of income, references, ID).\n"
            "Could we schedule a viewing at your earliest convenience?\n\n"
            "I look forward to hearing from you.\n\n"
            "Kind regards,\n"
            "[YOUR NAME]\n"
            "[YOUR PHONE NUMBER]"
        ),
        "faq": (
            "<b>❓ FAQ</b>\n\n"
            "<b>How fast are alerts?</b>\n"
            "Premium: within seconds. Standard: 15-min delay.\n\n"
            "<b>What is the ready-made letter?</b>\n"
            "A professional rental cover letter in English. Replace [YOUR NAME] and [YOUR PHONE NUMBER] before sending.\n\n"
            "<b>Does the bot guarantee a house?</b>\n"
            "No — it's a monitoring tool. Speed is the advantage.\n\n"
            "<b>What sites are monitored?</b>\n"
            "Pararius, Kamernet, Huurwoningen and Funda."
        ),
        "disclaimer": (
            "<b>⚖️ Disclaimer</b>\n\n"
            "This bot is independent and NOT affiliated with Pararius, Kamernet, Huurwoningen or Funda.\n\n"
            "We do not guarantee rental success or listing accuracy.\n\n"
            "Always verify listings and deal directly with landlords.\n\n"
            "Listing availability may change rapidly."
        ),
        "tos": (
            "<b>📄 Terms of Service</b>\n\n"
            "1. This bot is a monitoring tool — not a rental agency.\n"
            "2. We do not guarantee housing or listing accuracy.\n"
            "3. Subscriptions activate immediately upon payment.\n"
            "4. Refunds only in case of technical failure (see Refund Policy).\n"
            "5. We reserve the right to suspend accounts that abuse the service."
        ),
        "privacy": (
            "<b>🔒 Privacy Policy (AVG/GDPR)</b>\n\n"
            "We collect: Telegram ID, chosen city, subscription data, payment reference.\n\n"
            "We do NOT collect: your name, phone number, or location.\n\n"
            "We do NOT share your data with third parties.\n\n"
            "Data is stored on a secured server and deleted upon account removal.\n\n"
            "Questions? Contact us via Support."
        ),
        "refund": (
            "<b>💸 Refund Policy</b>\n\n"
            "Refunds are only issued if the bot fails to send any notifications due to a technical error on our side within the first 48 hours of your subscription.\n\n"
            "No refunds for change of mind or if the service worked as described.\n\n"
            "To request a refund, contact Support with your payment details."
        ),
    },
    "nl": {
        "welcome": "🏠 <b>NL Housing Hunter</b>\n\nIk monitor nieuwe huurwoningen op Pararius, Kamernet, Huurwoningen en Funda — en stuur je direct een melding.\n\nKies je taal:",
        "choose_city": "📍 Kies je stad:",
        "choose_radius": "📏 Kies zoekradius:",
        "radius_set": "✅ Radius: <b>{radius} km</b> rondom {city}",
        "choose_price": "💶 Kies maximale huurprijs:",
        "choose_type": "🏠 Kies type woning:",
        "choose_plan": (
            "💎 <b>Kies je abonnement:</b>\n\n"
            "🆓 <b>Demo</b> — 24 uur gratis\n\n"
            "📦 <b>Standaard</b> — €15,90 / 4 weken\n"
            "• Links naar nieuwe woningen\n"
            "• 15 min na Premium\n"
            "• Meldingen 08:00–23:00\n\n"
            "👑 <b>Premium</b>\n"
            "• Als eerste nieuwe woningen\n"
            "• Kant-en-klare brief aan verhuurder\n"
            "• 24/7 meldingen\n"
            "• 2 weken — €19,90\n"
            "• 4 weken — €29,90"
        ),
        "demo_activated": "✅ <b>Demo geactiveerd!</b>\n\nJe hebt 24 uur gratis Premium toegang.\nVeel succes met zoeken!",
        "sub_active": "✅ <b>Abonnement actief</b>\n\nAbonnement: {plan}\nVerloopt: {date}\nDagen over: {days}",
        "sub_none": "❌ <b>Geen actief abonnement</b>\n\nKies een abonnement om meldingen te ontvangen:",
        "new_listing": "🏠 <b>Nieuwe woning!</b>\n\n{title}\n\n🔗 {url}",
        "new_listing_premium": "👑 <b>Nieuwe woning!</b>\n\n{title}\n\n🔗 {url}\n\n✉️ <b>Kant-en-klare brief aan verhuurder:</b>\n\n{letter}",
        "payment_link": "💳 <b>{plan} — {weeks} weken (€{price})</b>\n\n👉 <a href='{link}'>Nu betalen</a>\n\nAbonnement wordt automatisch geactiveerd na betaling.",
        "payment_ok": "✅ <b>Betaling bevestigd!</b>\n\nJe {plan} abonnement is actief tot {date}.",
        "payment_error": "❌ Betalingsfout. Probeer het opnieuw.",
        "remind_24h": "⏰ <b>Je abonnement verloopt over 24 uur!</b>\n\nVerleng nu om meldingen te blijven ontvangen.",
        "remind_12h": "⏰ <b>Je abonnement verloopt over 12 uur!</b>\n\nMis geen nieuwe woningen — verleng nu.",
        "night_mode_on": "🌙 Nachtmodus ingeschakeld (08:00–23:00)",
        "night_mode_off": "🌟 24/7 modus ingeschakeld",
        "settings_saved": "✅ Instellingen opgeslagen: <b>{city}</b> | {radius}km | {price} | {prop_type}",
        "btn_demo": "🆓 Demo (24u gratis)",
        "btn_std_4w": "📦 Standaard — 4 weken €15,90",
        "btn_prm_2w": "👑 Premium — 2 weken €19,90",
        "btn_prm_4w": "👑 Premium — 4 weken €29,90",
        "btn_my_sub": "📋 Mijn abonnement",
        "btn_change_city": "📍 Stad wijzigen",
        "btn_change_lang": "🌍 Taal",
        "btn_info": "ℹ️ Info & FAQ",
        "btn_night_mode": "🌙 Nachtmodus",
        "info_msg": "ℹ️ <b>Info & Ondersteuning</b>\n\nKies een onderwerp:",
        "faq_btn": "❓ FAQ",
        "disclaimer_btn": "⚖️ Disclaimer",
        "tos_btn": "📄 Gebruiksvoorwaarden",
        "privacy_btn": "🔒 Privacybeleid",
        "refund_btn": "💸 Terugbetalingsbeleid",
        "support_btn": "👨‍💻 Ondersteuning",
        "back_btn": "⬅️ Terug",
        "letter": (
            "Geachte verhuurder,\n\n"
            "Ik ben uw woning tegengekomen en ben zeer geïnteresseerd in het huren ervan.\n"
            "Ik ben een betrouwbare huurder met een stabiel inkomen en kan alle benodigde documenten overleggen (loonstrook, referenties, ID).\n"
            "Zou het mogelijk zijn om een bezichtiging in te plannen?\n\n"
            "Ik hoor graag van u.\n\n"
            "Met vriendelijke groet,\n"
            "[UW NAAM]\n"
            "[UW TELEFOONNUMMER]"
        ),
        "faq": (
            "<b>❓ FAQ</b>\n\n"
            "<b>Hoe snel zijn de meldingen?</b>\n"
            "Premium: direct. Standaard: 15 min vertraging.\n\n"
            "<b>Wat is de kant-en-klare brief?</b>\n"
            "Een professionele huurbrief in het Nederlands. Vul [UW NAAM] en [UW TELEFOONNUMMER] in voor verzending.\n\n"
            "<b>Garandeert de bot een woning?</b>\n"
            "Nee — het is een monitoringshulpmiddel. Snelheid is het voordeel.\n\n"
            "<b>Welke sites worden gemonitord?</b>\n"
            "Pararius, Kamernet, Huurwoningen en Funda."
        ),
        "disclaimer": (
            "<b>⚖️ Disclaimer</b>\n\n"
            "Deze bot is onafhankelijk en NIET gelieerd aan Pararius, Kamernet, Huurwoningen of Funda.\n\n"
            "Wij garanderen geen huurcontracten of nauwkeurigheid van advertenties.\n\n"
            "Controleer advertenties altijd zelf en deal rechtstreeks met verhuurders.\n\n"
            "Beschikbaarheid van woningen kan snel veranderen."
        ),
        "tos": (
            "<b>📄 Gebruiksvoorwaarden</b>\n\n"
            "1. Deze bot is een monitoringshulpmiddel — geen verhuurbureau.\n"
            "2. Wij garanderen geen woning of nauwkeurigheid van advertenties.\n"
            "3. Abonnementen worden direct geactiveerd na betaling.\n"
            "4. Terugbetaling alleen bij technische storing (zie Terugbetalingsbeleid).\n"
            "5. Wij behouden ons het recht voor accounts te blokkeren bij misbruik."
        ),
        "privacy": (
            "<b>🔒 Privacybeleid (AVG/GDPR)</b>\n\n"
            "Wij verzamelen: Telegram ID, gekozen stad, abonnementsgegevens, betalingsreferentie.\n\n"
            "Wij verzamelen NIET: uw naam, telefoonnummer of locatie.\n\n"
            "Wij delen uw gegevens NIET met derden.\n\n"
            "Gegevens worden opgeslagen op een beveiligde server en verwijderd bij accountverwijdering.\n\n"
            "Vragen? Neem contact op via Ondersteuning."
        ),
        "refund": (
            "<b>💸 Terugbetalingsbeleid</b>\n\n"
            "Terugbetaling is alleen mogelijk als de bot door een technische fout aan onze kant geen meldingen heeft gestuurd binnen de eerste 48 uur van uw abonnement.\n\n"
            "Geen terugbetaling bij van gedachten veranderen of als de service naar behoren heeft gefunctioneerd.\n\n"
            "Neem voor een terugbetalingsverzoek contact op met Ondersteuning met uw betalingsgegevens."
        ),
    },
    "ru": {
        "welcome": "🏠 <b>NL Housing Hunter</b>\n\nМониторю новые объявления аренды на Pararius, Kamernet, Huurwoningen и Funda — и сразу отправляю тебе.\n\nВыбери язык:",
        "choose_city": "📍 Выбери город:",
        "choose_radius": "📏 Выбери радиус поиска:",
        "radius_set": "✅ Радиус: <b>{radius} км</b> вокруг {city}",
        "choose_price": "💶 Выбери максимальную цену аренды:",
        "choose_type": "🏠 Выбери тип жилья:",
        "choose_plan": (
            "💎 <b>Выбери план:</b>\n\n"
            "🆓 <b>Демо</b> — 24 часа бесплатно\n\n"
            "📦 <b>Стандарт</b> — €15.90 / 4 недели\n"
            "• Ссылки на новые объявления\n"
            "• На 15 мин позже Премиума\n"
            "• Уведомления 08:00–23:00\n\n"
            "👑 <b>Премиум</b>\n"
            "• Первым получаешь объявления\n"
            "• Готовое письмо лендлорду\n"
            "• Уведомления 24/7\n"
            "• 2 недели — €19.90\n"
            "• 4 недели — €29.90"
        ),
        "demo_activated": "✅ <b>Демо активировано!</b>\n\nУ тебя 24 часа бесплатного Премиум доступа.\nУдачи в поиске жилья!",
        "sub_active": "✅ <b>Подписка активна</b>\n\nПлан: {plan}\nДо: {date}\nОсталось дней: {days}",
        "sub_none": "❌ <b>Нет активной подписки</b>\n\nВыбери план чтобы начать получать объявления:",
        "new_listing": "🏠 <b>Новое объявление!</b>\n\n{title}\n\n🔗 {url}",
        "new_listing_premium": "👑 <b>Новое объявление!</b>\n\n{title}\n\n🔗 {url}\n\n✉️ <b>Готовое письмо лендлорду:</b>\n\n{letter}",
        "payment_link": "💳 <b>{plan} — {weeks} нед. (€{price})</b>\n\n👉 <a href='{link}'>Оплатить</a>\n\nПодписка активируется автоматически после оплаты.",
        "payment_ok": "✅ <b>Оплата подтверждена!</b>\n\nПодписка {plan} активна до {date}.",
        "payment_error": "❌ Ошибка оплаты. Попробуй ещё раз.",
        "remind_24h": "⏰ <b>Твоя подписка истекает через 24 часа!</b>\n\nПродли сейчас чтобы продолжать получать объявления.",
        "remind_12h": "⏰ <b>Твоя подписка истекает через 12 часов!</b>\n\nНе пропусти новые объявления — продли сейчас.",
        "night_mode_on": "🌙 Ночной режим включён (08:00–23:00)",
        "night_mode_off": "🌟 Режим 24/7 включён",
        "settings_saved": "✅ Настройки сохранены: <b>{city}</b> | {radius}км | {price} | {prop_type}",
        "btn_demo": "🆓 Демо (24ч бесплатно)",
        "btn_std_4w": "📦 Стандарт — 4 недели €15.90",
        "btn_prm_2w": "👑 Премиум — 2 недели €19.90",
        "btn_prm_4w": "👑 Премиум — 4 недели €29.90",
        "btn_my_sub": "📋 Моя подписка",
        "btn_change_city": "📍 Сменить город",
        "btn_change_lang": "🌍 Язык",
        "btn_info": "ℹ️ Инфо & FAQ",
        "btn_night_mode": "🌙 Ночной режим",
        "info_msg": "ℹ️ <b>Инфо & Поддержка</b>\n\nВыбери тему:",
        "faq_btn": "❓ FAQ",
        "disclaimer_btn": "⚖️ Отказ от ответственности",
        "tos_btn": "📄 Условия использования",
        "privacy_btn": "🔒 Политика конфиденциальности",
        "refund_btn": "💸 Политика возврата",
        "support_btn": "👨‍💻 Поддержка",
        "back_btn": "⬅️ Назад",
        "letter": (
            "Dear landlord,\n\n"
            "I came across your listing and I am very interested in renting this property.\n"
            "I am a reliable tenant with a stable income and can provide all necessary documents (proof of income, references, ID).\n"
            "Could we schedule a viewing at your earliest convenience?\n\n"
            "I look forward to hearing from you.\n\n"
            "Kind regards,\n"
            "[YOUR NAME]\n"
            "[YOUR PHONE NUMBER]"
        ),
        "faq": (
            "<b>❓ FAQ</b>\n\n"
            "<b>Как быстро приходят уведомления?</b>\n"
            "Премиум: мгновенно. Стандарт: задержка 15 минут.\n\n"
            "<b>Что такое готовое письмо?</b>\n"
            "Письмо на английском для лендлорда. Замени [YOUR NAME] и [YOUR PHONE NUMBER] перед отправкой.\n\n"
            "<b>Гарантирует ли бот аренду?</b>\n"
            "Нет — это инструмент мониторинга. Скорость — твоё преимущество.\n\n"
            "<b>Какие сайты мониторятся?</b>\n"
            "Pararius, Kamernet, Huurwoningen и Funda."
        ),
        "disclaimer": (
            "<b>⚖️ Отказ от ответственности</b>\n\n"
            "Бот независим и НЕ связан с Pararius, Kamernet, Huurwoningen или Funda.\n\n"
            "Мы не гарантируем аренду или точность объявлений.\n\n"
            "Всегда проверяй объявления самостоятельно и общайся напрямую с лендлордом.\n\n"
            "Доступность жилья может меняться очень быстро."
        ),
        "tos": (
            "<b>📄 Условия использования</b>\n\n"
            "1. Бот является инструментом мониторинга — не агентством аренды.\n"
            "2. Мы не гарантируем жильё или точность объявлений.\n"
            "3. Подписки активируются сразу после оплаты.\n"
            "4. Возврат только при технической неисправности (см. Политику возврата).\n"
            "5. Мы оставляем за собой право блокировать аккаунты при злоупотреблении."
        ),
        "privacy": (
            "<b>🔒 Политика конфиденциальности (AVG/GDPR)</b>\n\n"
            "Мы собираем: Telegram ID, выбранный город, данные подписки, ссылку на платёж.\n\n"
            "Мы НЕ собираем: твоё имя, номер телефона или геолокацию.\n\n"
            "Мы НЕ передаём твои данные третьим лицам.\n\n"
            "Данные хранятся на защищённом сервере и удаляются при удалении аккаунта.\n\n"
            "Вопросы? Обратись в Поддержку."
        ),
        "refund": (
            "<b>💸 Политика возврата</b>\n\n"
            "Возврат возможен только если бот не отправлял уведомления из-за технической ошибки на нашей стороне в течение первых 48 часов подписки.\n\n"
            "Возврат не производится при изменении решения или если сервис работал как описано.\n\n"
            "Для запроса возврата обратись в Поддержку с данными оплаты."
        ),
    }
}

CITIES = [
    "Amsterdam", "Rotterdam", "Den Haag", "Utrecht",
    "Eindhoven", "Groningen", "Tilburg", "Almere",
    "Breda", "Nijmegen", "Leiden", "Haarlem"
]

PLAN_PRICES = {
    "std_4w":  ("15.90", "Standard", 4),
    "prm_2w":  ("19.90", "Premium",  2),
    "prm_4w":  ("29.90", "Premium",  4),
}

def t(lang: str, key: str) -> str:
    return TEXTS.get(lang, TEXTS["en"]).get(key, TEXTS["en"].get(key, ""))

# ================= БАЗА ДАННЫХ =================

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
                demo_used        INTEGER DEFAULT 0,
                night_mode       INTEGER DEFAULT -1
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
            CREATE TABLE IF NOT EXISTS reminders (
                user_id     INTEGER,
                remind_type TEXT,
                PRIMARY KEY (user_id, remind_type)
            );
        """)
        await db.commit()

async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT * FROM users WHERE id=?", (user_id,))
        return await cursor.fetchone()

# Columns: 0=id, 1=language, 2=city, 3=radius, 4=max_price,
#          5=prop_type, 6=plan, 7=subscription_end, 8=demo_used, 9=night_mode

async def add_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
        await db.commit()

async def set_field(user_id: int, field: str, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE users SET {field}=? WHERE id=?", (value, user_id))
        await db.commit()

async def activate_demo(user_id: int):
    end = datetime.now() + timedelta(hours=72)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET plan='Premium', subscription_end=?, demo_used=1, night_mode=-1 WHERE id=?",
            (end.strftime("%Y-%m-%d %H:%M:%S"), user_id)
        )
        await db.commit()

async def update_subscription(user_id: int, plan: str, weeks: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT subscription_end FROM users WHERE id=?", (user_id,))
        row = await cursor.fetchone()
    base = datetime.now()
    if row and row[0]:
        try:
            dt = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
            if dt > base:
                base = dt
        except:
            pass
    end = base + timedelta(weeks=weeks)
    # night_mode default: -1 = not set (Premium=24/7, Standard=night)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET plan=?, subscription_end=?, night_mode=-1 WHERE id=?",
            (plan, end.strftime("%Y-%m-%d %H:%M:%S"), user_id)
        )
        await db.commit()
    return end

async def has_active_subscription(user_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT subscription_end FROM users WHERE id=?", (user_id,))
        row = await cursor.fetchone()
    if not row or not row[0]:
        return False
    try:
        return datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S") > datetime.now()
    except:
        return False

async def save_payment(payment_id: str, user_id: int, plan: str, weeks: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO payments VALUES (?,?,?,?)",
            (payment_id, user_id, plan, weeks)
        )
        await db.commit()

async def get_payment_info(payment_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT user_id, plan, weeks FROM payments WHERE payment_id=?", (payment_id,))
        return await cursor.fetchone()

async def ad_exists(url: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM sent_ads WHERE url=?", (url,))
        return await cursor.fetchone() is not None

async def save_ad(url: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO sent_ads (url, sent_at) VALUES (?,?)",
                         (url, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        await db.commit()

async def add_pending_standard(user_id: int, title: str, url: str):
    send_after = (datetime.now() + timedelta(seconds=STANDARD_DELAY)).strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO pending_standard (user_id, title, url, send_after) VALUES (?,?,?,?)",
                         (user_id, title, url, send_after))
        await db.commit()

async def get_ready_pending():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id, user_id, title, url FROM pending_standard WHERE send_after <= ?", (now,))
        rows = await cursor.fetchall()
        if rows:
            ids = ",".join(str(r[0]) for r in rows)
            await db.execute(f"DELETE FROM pending_standard WHERE id IN ({ids})")
            await db.commit()
    return rows

async def reminder_sent(user_id: int, remind_type: str) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM reminders WHERE user_id=? AND remind_type=?", (user_id, remind_type))
        return await cursor.fetchone() is not None

async def mark_reminder(user_id: int, remind_type: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO reminders VALUES (?,?)", (user_id, remind_type))
        await db.commit()

async def clear_reminders(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM reminders WHERE user_id=?", (user_id,))
        await db.commit()

def is_night_hours() -> bool:
    now = datetime.now().hour
    return now < 8 or now >= 23

def should_notify(user: tuple) -> bool:
    plan      = user[6]
    night_mode = user[9]  # -1=default, 0=24/7, 1=night only
    if night_mode == 0:   # user forced 24/7
        return True
    if night_mode == 1:   # user forced night mode
        return not is_night_hours()
    # default
    if plan == "Premium":
        return True  # Premium 24/7 by default
    else:
        return not is_night_hours()  # Standard 8-23 by default

# ================= КЛАВИАТУРЫ =================

def lang_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇬🇧 English",   callback_data="lang_en"),
        InlineKeyboardButton(text="🇳🇱 Nederlands", callback_data="lang_nl"),
        InlineKeyboardButton(text="🇷🇺 Русский",   callback_data="lang_ru"),
    ]])

def city_keyboard():
    rows = []
    row = []
    for i, city in enumerate(CITIES):
        row.append(InlineKeyboardButton(text=city, callback_data=f"city_{city}"))
        if len(row) == 3:
            rows.append(row); row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)

def radius_keyboard(city: str):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="2 km",  callback_data=f"rad_{city}_2"),
        InlineKeyboardButton(text="5 km",  callback_data=f"rad_{city}_5"),
        InlineKeyboardButton(text="10 km", callback_data=f"rad_{city}_10"),
        InlineKeyboardButton(text="20 km", callback_data=f"rad_{city}_20"),
    ]])

def price_keyboard(city: str, radius: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💶 Any / Elke / Любая", callback_data=f"price_{city}_{radius}_0")],
        [
            InlineKeyboardButton(text="≤ €800",  callback_data=f"price_{city}_{radius}_800"),
            InlineKeyboardButton(text="≤ €1200", callback_data=f"price_{city}_{radius}_1200"),
        ],
        [
            InlineKeyboardButton(text="≤ €1500", callback_data=f"price_{city}_{radius}_1500"),
            InlineKeyboardButton(text="≤ €2000", callback_data=f"price_{city}_{radius}_2000"),
        ],
    ])

def type_keyboard(city: str, radius: int, price: int, lang: str):
    labels = {
        "en": {"any": "🏠 Any type", "room": "🛏 Room", "apartment": "🏢 Apartment", "house": "🏡 House"},
        "nl": {"any": "🏠 Alle types", "room": "🛏 Kamer", "apartment": "🏢 Appartement", "house": "🏡 Huis"},
        "ru": {"any": "🏠 Любой тип", "room": "🛏 Комната", "apartment": "🏢 Квартира", "house": "🏡 Дом"},
    }
    lb = labels.get(lang, labels["en"])
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=lb["any"],       callback_data=f"type_{city}_{radius}_{price}_any")],
        [InlineKeyboardButton(text=lb["room"],      callback_data=f"type_{city}_{radius}_{price}_room")],
        [InlineKeyboardButton(text=lb["apartment"], callback_data=f"type_{city}_{radius}_{price}_apartment")],
        [InlineKeyboardButton(text=lb["house"],     callback_data=f"type_{city}_{radius}_{price}_house")],
    ])

def plan_keyboard(lang: str, demo_used: bool):
    rows = []
    if not demo_used:
        rows.append([InlineKeyboardButton(text=t(lang, "btn_demo"), callback_data="plan_demo")])
    rows.append([InlineKeyboardButton(text=t(lang, "btn_std_4w"), callback_data="plan_std_4w")])
    rows.append([InlineKeyboardButton(text=t(lang, "btn_prm_2w"), callback_data="plan_prm_2w")])
    rows.append([InlineKeyboardButton(text=t(lang, "btn_prm_4w"), callback_data="plan_prm_4w")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def main_keyboard(lang: str):
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_my_sub"))],
            [KeyboardButton(text=t(lang, "btn_change_city")), KeyboardButton(text=t(lang, "btn_night_mode"))],
            [KeyboardButton(text=t(lang, "btn_change_lang")), KeyboardButton(text=t(lang, "btn_info"))],
        ],
        resize_keyboard=True
    )

def info_keyboard(lang: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "faq_btn"),       callback_data="info_faq")],
        [InlineKeyboardButton(text=t(lang, "disclaimer_btn"), callback_data="info_disclaimer")],
        [InlineKeyboardButton(text=t(lang, "tos_btn"),        callback_data="info_tos")],
        [InlineKeyboardButton(text=t(lang, "privacy_btn"),    callback_data="info_privacy")],
        [InlineKeyboardButton(text=t(lang, "refund_btn"),     callback_data="info_refund")],
        [InlineKeyboardButton(text=t(lang, "support_btn"),    url=f"https://t.me/{BOT_USERNAME}")],
    ])

def back_keyboard(lang: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "back_btn"), callback_data="info_back")]
    ])

# ================= MOLLIE =================

mollie = Client()
if MOLLIE_API_KEY:
    mollie.set_api_key(MOLLIE_API_KEY)

async def create_payment(plan_key: str, user_id: int) -> str:
    price, plan_name, weeks = PLAN_PRICES[plan_key]
    payment = mollie.payments.create({
        "amount": {"currency": "EUR", "value": price},
        "description": f"NL Housing Hunter — {plan_name} {weeks}w",
        "redirectUrl": f"https://t.me/{BOT_USERNAME}",
        "webhookUrl":  f"{BASE_URL}/webhook/mollie",
        "method": ["ideal", "bancontact", "banktransfer", "paypal", "creditcard", "applepay"],
        "metadata": {"user_id": str(user_id), "plan": plan_name, "weeks": str(weeks)},
    })
    await save_payment(payment.id, user_id, plan_name, weeks)
    return payment.checkout_url

# ================= ПАРСЕРЫ =================

async def fetch(url: str) -> str | None:
    try:
        async with aiohttp.ClientSession(headers=get_headers()) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=20), allow_redirects=True) as resp:
                if resp.status == 200:
                    return await resp.text()
                logging.warning(f"[Parser] {url} → {resp.status}")
    except Exception as e:
        logging.error(f"[Parser] {url} error: {e}")
    return None

async def parse_pararius(city: str, radius: int) -> list[tuple[str, str]]:
    url  = f"https://www.pararius.com/apartments/{city.lower()}/{radius}km"
    html = await fetch(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    ads  = []
    for sel in [
        "li.search-list__item--listing a.listing-search-item__link--title",
        "section.listing-search-item a[href*='/apartment']",
        "a.listing-search-item__link",
    ]:
        items = soup.select(sel)
        if items:
            for item in items:
                title = item.get_text(strip=True)
                href  = item.get("href", "")
                if title and href:
                    if not href.startswith("http"):
                        href = "https://www.pararius.com" + href
                    ads.append((title, href))
            break
    logging.info(f"[Pararius/{city}] {len(ads)}")
    return ads

async def parse_kamernet(city: str, radius: int) -> list[tuple[str, str]]:
    url  = f"https://kamernet.nl/en/for-rent/rooms-{city.lower()}?radius={radius}"
    html = await fetch(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    ads  = []
    for sel in ["a.search-result-item", "a.tile", "a[href*='/for-rent/']"]:
        items = soup.select(sel)
        if items:
            for item in items:
                title = item.get_text(strip=True)[:120]
                href  = item.get("href", "")
                if title and href:
                    if not href.startswith("http"):
                        href = "https://kamernet.nl" + href
                    ads.append((title, href))
            break
    logging.info(f"[Kamernet/{city}] {len(ads)}")
    return ads

async def parse_huurwoningen(city: str, radius: int) -> list[tuple[str, str]]:
    url  = f"https://www.huurwoningen.nl/in/{city.lower()}/?radius={radius}"
    html = await fetch(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    ads  = []
    seen = set()
    for sel in ["a.listing-search-item__link", "a[href*='/huurwoningen/']"]:
        items = soup.select(sel)
        if items:
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
            break
    logging.info(f"[Huurwoningen/{city}] {len(ads)}")
    return ads

async def parse_funda(city: str, radius: int) -> list[tuple[str, str]]:
    url  = f"https://www.funda.nl/zoeken/huur/?selected_area=%5B%22{city.lower()}%22%5D&radius={radius}"
    html = await fetch(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    ads  = []
    seen = set()
    for sel in [
        "a[data-object-url-tracking]",
        "a[href*='/huur/']",
        "div.search-result__header-title a",
    ]:
        items = soup.select(sel)
        if items:
            for item in items:
                title = item.get_text(strip=True)[:120]
                href  = item.get("href", "")
                if not href or not title:
                    continue
                if not href.startswith("http"):
                    href = "https://www.funda.nl" + href
                if href not in seen:
                    seen.add(href)
                    ads.append((title, href))
            break
    logging.info(f"[Funda/{city}] {len(ads)}")
    return ads

# ================= БОТ =================

bot = Bot(token=TELEGRAM_TOKEN)
dp  = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await add_user(message.from_user.id)
    await message.answer(t("en", "welcome"), reply_markup=lang_keyboard(), parse_mode="HTML")

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    end = datetime.now() + timedelta(days=36500)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET plan='Premium', subscription_end=?, night_mode=0 WHERE id=?",
                         (end.strftime("%Y-%m-%d %H:%M:%S"), message.from_user.id))
        await db.commit()
    await message.answer("👑 <b>Admin: Premium навсегда активирован!</b>", parse_mode="HTML",
                         reply_markup=main_keyboard("ru"))

@dp.message(Command("debug"))
async def cmd_debug(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect(DB_PATH) as db:
        u  = await (await db.execute("SELECT * FROM users WHERE id=?", (message.from_user.id,))).fetchone()
        t1 = await (await db.execute("SELECT COUNT(*) FROM users")).fetchone()
        t2 = await (await db.execute("SELECT COUNT(*) FROM sent_ads")).fetchone()
        t3 = await (await db.execute("SELECT COUNT(*) FROM pending_standard")).fetchone()
    await message.answer(
        f"<b>Debug</b>\n\nUser: {u}\nUsers: {t1[0]}\nSent ads: {t2[0]}\nPending: {t3[0]}",
        parse_mode="HTML"
    )

# --- Язык ---
@dp.callback_query(F.data.startswith("lang_"))
async def cb_language(cb: types.CallbackQuery):
    lang = cb.data.split("_")[1]
    await set_field(cb.from_user.id, "language", lang)
    await cb.message.edit_text(t(lang, "choose_city"), reply_markup=city_keyboard(), parse_mode="HTML")
    await cb.answer()

# --- Город ---
@dp.callback_query(F.data.startswith("city_"))
async def cb_city(cb: types.CallbackQuery):
    city = cb.data.split("_", 1)[1]
    user = await get_user(cb.from_user.id)
    lang = user[1] if user else "en"
    await set_field(cb.from_user.id, "city", city)
    await cb.message.edit_text(t(lang, "choose_radius"), reply_markup=radius_keyboard(city), parse_mode="HTML")
    await cb.answer()

# --- Радиус ---
@dp.callback_query(F.data.startswith("rad_"))
async def cb_radius(cb: types.CallbackQuery):
    _, city, rad = cb.data.split("_")
    radius = int(rad)
    user   = await get_user(cb.from_user.id)
    lang   = user[1] if user else "en"
    await set_field(cb.from_user.id, "radius", radius)
    await cb.message.edit_text(t(lang, "choose_price"), reply_markup=price_keyboard(city, radius), parse_mode="HTML")
    await cb.answer()

# --- Цена ---
@dp.callback_query(F.data.startswith("price_"))
async def cb_price(cb: types.CallbackQuery):
    parts  = cb.data.split("_")
    city, radius, price = parts[1], int(parts[2]), int(parts[3])
    user   = await get_user(cb.from_user.id)
    lang   = user[1] if user else "en"
    await set_field(cb.from_user.id, "max_price", price)
    await cb.message.edit_text(t(lang, "choose_type"), reply_markup=type_keyboard(city, radius, price, lang), parse_mode="HTML")
    await cb.answer()

# --- Тип жилья ---
@dp.callback_query(F.data.startswith("type_"))
async def cb_type(cb: types.CallbackQuery):
    parts = cb.data.split("_")
    city, radius, price, prop_type = parts[1], int(parts[2]), int(parts[3]), parts[4]
    user      = await get_user(cb.from_user.id)
    lang      = user[1] if user else "en"
    demo_used = user[8] if user else 0
    await set_field(cb.from_user.id, "prop_type", prop_type)

    price_lbl = {
        "en": f"≤ €{price}" if price else "Any price",
        "nl": f"≤ €{price}" if price else "Elke prijs",
        "ru": f"≤ €{price}" if price else "Любая цена",
    }.get(lang, f"≤ €{price}")

    type_lbl = {
        "en": {"any": "Any", "room": "Room", "apartment": "Apartment", "house": "House"},
        "nl": {"any": "Alle", "room": "Kamer", "apartment": "Appartement", "house": "Huis"},
        "ru": {"any": "Любой", "room": "Комната", "apartment": "Квартира", "house": "Дом"},
    }.get(lang, {}).get(prop_type, prop_type)

    next_lbl = {"en": "Now choose your plan:", "nl": "Kies nu je abonnement:", "ru": "Теперь выбери план:"}.get(lang)

    await cb.message.edit_text(
        f"✅ <b>{city}</b> | {radius}km | {price_lbl} | {type_lbl}\n\n{next_lbl}",
        reply_markup=plan_keyboard(lang, bool(demo_used)),
        parse_mode="HTML"
    )
    await cb.answer()

# --- План ---
@dp.callback_query(F.data.startswith("plan_"))
async def cb_plan(cb: types.CallbackQuery):
    plan_key  = cb.data.split("_", 1)[1]
    user      = await get_user(cb.from_user.id)
    lang      = user[1] if user else "en"
    demo_used = user[8] if user else 0

    if plan_key == "demo":
        if demo_used:
            await cb.answer("Demo already used!", show_alert=True)
            return
        await activate_demo(cb.from_user.id)
        await cb.message.edit_text(t(lang, "demo_activated"), parse_mode="HTML")
        await cb.message.answer("👇", reply_markup=main_keyboard(lang))
        await cb.answer()
        return

    if plan_key not in PLAN_PRICES:
        await cb.answer()
        return

    try:
        link = await create_payment(plan_key, cb.from_user.id)
        price, plan_name, weeks = PLAN_PRICES[plan_key]
        await cb.message.edit_text(
            t(lang, "payment_link").format(plan=plan_name, weeks=weeks, price=price, link=link),
            parse_mode="HTML",
            disable_web_page_preview=True
        )
    except Exception as e:
        logging.error(f"[Payment] {e}")
        await cb.message.answer(t(lang, "payment_error"))
    await cb.answer()

# --- Info callbacks ---
@dp.callback_query(F.data.startswith("info_"))
async def cb_info(cb: types.CallbackQuery):
    user = await get_user(cb.from_user.id)
    lang = user[1] if user else "en"
    key  = cb.data.split("_", 1)[1]
    if key == "back":
        await cb.message.edit_text(t(lang, "info_msg"), reply_markup=info_keyboard(lang), parse_mode="HTML")
    else:
        text_map = {"faq": "faq", "disclaimer": "disclaimer", "tos": "tos", "privacy": "privacy", "refund": "refund"}
        if key in text_map:
            await cb.message.edit_text(t(lang, text_map[key]), reply_markup=back_keyboard(lang), parse_mode="HTML")
    await cb.answer()

# --- Текстовые кнопки главного меню ---
@dp.message()
async def handle_text(message: types.Message):
    user = await get_user(message.from_user.id)
    if not user:
        await add_user(message.from_user.id)
        await cmd_start(message)
        return

    lang = user[1] or "en"
    text = message.text

    # Моя подписка
    if text in [t(l, "btn_my_sub") for l in ["en", "nl", "ru"]]:
        if await has_active_subscription(message.from_user.id):
            end_dt    = datetime.strptime(user[7], "%Y-%m-%d %H:%M:%S")
            days_left = max((end_dt - datetime.now()).days, 0)
            await message.answer(
                t(lang, "sub_active").format(plan=user[6], date=end_dt.strftime("%d %b %Y"), days=days_left),
                parse_mode="HTML"
            )
        else:
            await message.answer(t(lang, "sub_none"), reply_markup=plan_keyboard(lang, bool(user[8])), parse_mode="HTML")
        return

    # Сменить город
    if text in [t(l, "btn_change_city") for l in ["en", "nl", "ru"]]:
        await message.answer(t(lang, "choose_city"), reply_markup=city_keyboard(), parse_mode="HTML")
        return

    # Язык
    if text in [t(l, "btn_change_lang") for l in ["en", "nl", "ru"]]:
        await message.answer(t("en", "welcome"), reply_markup=lang_keyboard(), parse_mode="HTML")
        return

    # Ночной режим
    if text in [t(l, "btn_night_mode") for l in ["en", "nl", "ru"]]:
        current = user[9]  # -1=default, 0=24/7, 1=night
        plan    = user[6]
        # toggle
        if plan == "Premium":
            # Premium default=24/7 (0), toggle to night (1)
            new_mode = 1 if current != 1 else 0
        else:
            # Standard default=night (1), toggle to 24/7 (0)
            new_mode = 0 if current == 1 or current == -1 else 1
        await set_field(message.from_user.id, "night_mode", new_mode)
        msg = t(lang, "night_mode_on") if new_mode == 1 else t(lang, "night_mode_off")
        await message.answer(msg)
        return

    # Info
    if text in [t(l, "btn_info") for l in ["en", "nl", "ru"]]:
        await message.answer(t(lang, "info_msg"), reply_markup=info_keyboard(lang), parse_mode="HTML")
        return

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
                end  = await update_subscription(user_id, plan, weeks)
                user = await get_user(user_id)
                lang = user[1] if user else "en"
                await clear_reminders(user_id)
                try:
                    await bot.send_message(
                        user_id,
                        t(lang, "payment_ok").format(plan=plan, date=end.strftime("%d %b %Y")),
                        reply_markup=main_keyboard(lang),
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logging.error(f"[Webhook send] {e}")
        return web.Response(status=200)
    except Exception as e:
        logging.error(f"[Webhook] {e}")
        return web.Response(status=500)

async def health(request: web.Request) -> web.Response:
    return web.Response(text="OK")

# ================= ПАРСЕР ЦИКЛ =================

async def parse_and_send():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id, language, city, radius, max_price, prop_type, plan, subscription_end, demo_used, night_mode FROM users")
        all_users = await cursor.fetchall()

    active_users = [u for u in all_users if u[6] and u[7] and await has_active_subscription(u[0])]
    if not active_users:
        return

    city_radius_pairs = list(set((u[2], u[3]) for u in active_users if u[2]))

    all_ads = []
    for city, radius in city_radius_pairs:
        radius = radius or 10
        await asyncio.sleep(random.uniform(1, 3))
        all_ads += await parse_pararius(city, radius)
        await asyncio.sleep(random.uniform(1, 3))
        all_ads += await parse_kamernet(city, radius)
        await asyncio.sleep(random.uniform(1, 3))
        all_ads += await parse_huurwoningen(city, radius)
        await asyncio.sleep(random.uniform(1, 3))
        all_ads += await parse_funda(city, radius)

    for title, url in all_ads:
        if await ad_exists(url):
            continue
        await save_ad(url)

        for user in active_users:
            user_id, lang, city, radius, max_price, prop_type, plan = user[0], user[1], user[2], user[3], user[4], user[5], user[6]

            if not should_notify(user):
                continue

            # Фильтр по цене
            if max_price and max_price > 0:
                found = re.findall(r"[€$]\s*(\d+)", title)
                if found and int(found[0]) > max_price:
                    continue

            if plan == "Premium":
                letter = t("nl" if lang == "nl" else "en", "letter")
                text   = t(lang, "new_listing_premium").format(title=title, url=url, letter=letter)
                try:
                    await bot.send_message(user_id, text, parse_mode="HTML", disable_web_page_preview=True)
                    await asyncio.sleep(0.05)
                except Exception as e:
                    logging.error(f"[Send Premium] {user_id}: {e}")
            elif plan == "Standard":
                await add_pending_standard(user_id, title, url)

async def send_pending_standard():
    rows = await get_ready_pending()
    for _, user_id, title, url in rows:
        user = await get_user(user_id)
        if not user or not await has_active_subscription(user_id):
            continue
        if not should_notify(user):
            # reschedule for next morning
            continue
        lang = user[1] or "en"
        try:
            await bot.send_message(user_id, t(lang, "new_listing").format(title=title, url=url),
                                   parse_mode="HTML", disable_web_page_preview=True)
            await asyncio.sleep(0.05)
        except Exception as e:
            logging.error(f"[Send Standard] {user_id}: {e}")

async def check_reminders():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id, language, subscription_end, plan FROM users WHERE subscription_end IS NOT NULL AND plan IS NOT NULL")
        users  = await cursor.fetchall()

    for user_id, lang, sub_end, plan in users:
        if not sub_end or not await has_active_subscription(user_id):
            continue
        try:
            end_dt    = datetime.strptime(sub_end, "%Y-%m-%d %H:%M:%S")
            hours_left = (end_dt - datetime.now()).total_seconds() / 3600

            if hours_left <= 24 and not await reminder_sent(user_id, "24h"):
                await bot.send_message(user_id, t(lang or "en", "remind_24h"), parse_mode="HTML")
                await mark_reminder(user_id, "24h")

            if hours_left <= 12 and not await reminder_sent(user_id, "12h"):
                await bot.send_message(user_id, t(lang or "en", "remind_12h"), parse_mode="HTML")
                await mark_reminder(user_id, "12h")

        except Exception as e:
            logging.error(f"[Reminder] {user_id}: {e}")

async def scheduler():
    logging.info("[Scheduler] started")
    await asyncio.sleep(15)
    while True:
        try:
            logging.info("[Scheduler] cycle start")
            await parse_and_send()
            await send_pending_standard()
            await check_reminders()
            logging.info("[Scheduler] cycle done")
        except Exception as e:
            logging.error(f"[Scheduler] {e}")
        await asyncio.sleep(CHECK_INTERVAL)

# ================= ЗАПУСК =================

async def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    await init_db()

    app = web.Application()
    app.router.add_post("/webhook/mollie", mollie_webhook)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"[Server] port {port}")

    asyncio.create_task(scheduler())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
