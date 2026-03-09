import logging
import datetime
import pytz
import sqlite3
import requests
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# --- 1. НАСТРОЙКИ ---
API_TOKEN = '8646275203:AAFenGqJIBpvk1DXrbBqDIOPiOILz3Zyllg'
ADMIN_ID = 6999400196

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- 2. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def get_listings_test():
    url = "https://www.funda.nl/zoeken/huur/?selected_area=%22eindhoven%22"
   def get_listings_test():
    url = "https://www.funda.nl/zoeken/huur/?selected_area=%22eindhoven%22"
    
    # Вот сюда вставляй заголовки
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Referer": "https://www.google.com/"
    }
    
    session = requests.Session()
    session.headers.update(headers) # Передаем заголовки в сессию
    
    try:
        response = session.get(url, timeout=10)
        # ... дальше твой остальной код с BeautifulSoup
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Попробуем найти все ссылки на объекты (они обычно стабильнее заголовков)
        links = soup.find_all('a', href=True)
        # Выберем те, что ведут на объекты аренды
        found = [a['href'] for a in links if '/huur/' in a['href']][:5]
        
        return found if found else ["Сайт отдал пустую страницу или сменил защиту."]
    except Exception as e:
        return [f"Ошибка: {e}"]

def init_db():
    conn = sqlite3.connect('housing.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, join_date TEXT, lang TEXT, city TEXT)''')
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

def get_users_by_city(city):
    conn = sqlite3.connect('housing.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users') if city == 'All' else cursor.execute('SELECT user_id FROM users WHERE city = ?', (city,))
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

init_db()

# --- 3. МЕНЮ ---
def get_lang_menu():
    menu = ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add(KeyboardButton('🇷🇺 Русский'), KeyboardButton('🇬🇧 English'), KeyboardButton('🇳🇱 Nederlands'))
    return menu

def get_city_menu():
    menu = ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add(KeyboardButton('🇳🇱 Eindhoven'), KeyboardButton('🇳🇱 Amsterdam'), KeyboardButton('🇧🇪 Brussels'))
    menu.add(KeyboardButton('🌍 All NL/BE'))
    return menu

def get_main_menu(lang):
    menu = ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add(KeyboardButton('⚙️ Settings'), KeyboardButton('🏠 Subscription'))
    return menu

# --- 4. ХЕНДЛЕРЫ ---
@dp.message_handler(commands=['check_net'])
async def check_net(message: types.Message):
    response = requests.get("https://www.google.com", timeout=5)
    await message.answer(f"Связь есть! Код: {response.status_code}")

@dp.message_handler(commands=['test_parser'])
async def test_parser(message: types.Message):
    await message.answer("Ищу квартиры в Эйндховене...")
    data = get_listings_test()
    await message.answer("Результаты:\n" + "\n".join(data))

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    add_or_update_user(message.from_user.id)
    await message.answer("Choose your language:", reply_markup=get_lang_menu())

@dp.message_handler(lambda m: m.text in ['🇷🇺 Русский', '🇬🇧 English', '🇳🇱 Nederlands'])
async def handle_lang(message: types.Message):
    add_or_update_user(message.from_user.id, lang=message.text)
    await message.answer("Select your city:", reply_markup=get_city_menu())

@dp.message_handler(lambda m: m.text in ['🇳🇱 Eindhoven', '🇳🇱 Amsterdam', '🇧🇪 Brussels', '🌍 All NL/BE'])
async def handle_city(message: types.Message):
    add_or_update_user(message.from_user.id, city=message.text)
    await message.answer(f"City set to {message.text}!", reply_markup=get_main_menu('English'))

@dp.message_handler(lambda message: message.from_user.id == ADMIN_ID)
async def admin_msg(message: types.Message):
    if message.text.startswith('/'): return
    confirm_menu = InlineKeyboardMarkup().add(InlineKeyboardButton("🚀 Broadcast All", callback_data="broadcast_all"))
    await message.reply("Broadcast to everyone?", reply_markup=confirm_menu)

@dp.callback_query_handler(lambda c: c.data == 'broadcast_all')
async def process_broadcast(callback_query: types.CallbackQuery):
    all_users = get_users_by_city('All')
    for u_id in all_users:
        try: await bot.send_message(u_id, callback_query.message.reply_to_message.text)
        except: pass
    await callback_query.answer("Sent!")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
