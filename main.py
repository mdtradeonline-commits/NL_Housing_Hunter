import logging
import datetime
import sqlite3
import cloudscraper # Используем этот инструмент для обхода защиты
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- 1. НАСТРОЙКИ ---
API_TOKEN = '8646275203:AAFenGqJIBpvk1DXrbBqDIOPiOILz3Zyllg'
ADMIN_ID = 6999400196

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- 2. ПАРСИНГ ---
def get_listings_test():
    scraper = cloudscraper.create_scraper() # Создает сессию как у браузера
    url = "https://www.funda.nl/zoeken/huur/?selected_area=%22eindhoven%22"
    try:
        response = scraper.get(url, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Ищем заголовки, которые обычно имеют класс search-result__header-title
        listings = soup.find_all('h2', class_='search-result__header-title')
        results = [item.text.strip() for item in listings[:5]]
        return results if results else ["Сайт не отдал данные (защита или нет квартир)."]
    except Exception as e:
        return [f"Ошибка: {e}"]

# --- 3. БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('housing.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, join_date TEXT, lang TEXT, city TEXT)')
    conn.commit()
    conn.close()

def add_or_update_user(user_id, lang=None, city=None):
    conn = sqlite3.connect('housing.db')
    cursor = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('INSERT OR IGNORE INTO users (user_id, join_date) VALUES (?, ?)', (user_id, now))
    if lang: cursor.execute('UPDATE users SET lang = ? WHERE user_id = ?', (lang, user_id))
    if city: cursor.execute('UPDATE users SET city = ? WHERE user_id = ?', (city, user_id))
    conn.commit()
    conn.close()

init_db()

# --- 4. ХЕНДЛЕРЫ ---
@dp.message_handler(commands=['check_net'])
async def check_net(message: types.Message):
    await message.answer("Бот онлайн и готов к работе!")

@dp.message_handler(commands=['test_parser'])
async def test_parser(message: types.Message):
    await message.answer("Запускаю парсер Funda...")
    data = get_listings_test()
    await message.answer("Нашел:\n" + "\n".join(data))

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    add_or_update_user(message.from_user.id)
    await message.answer("Привет! Выбери язык:", reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton('🇬🇧 English')))

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
