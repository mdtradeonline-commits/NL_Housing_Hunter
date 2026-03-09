
import logging
import datetime
import pytz
import sqlite3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import requests # Теперь это будет работать!

@dp.message_handler(commands=['check_net'])
async def check_net(message: types.Message):
    try:
        # Простой запрос к Гуглу, чтобы проверить связь
        response = requests.get("https://www.google.com", timeout=5)
        await message.answer(f"Связь с интернетом есть! Код ответа: {response.status_code}")
    except Exception as e:
        await message.answer(f"Ошибка связи: {e}")

# --- 1. НАСТРОЙКИ ---
API_TOKEN = '8646275203:AAFenGqJIBpvk1DXrbBqDIOPiOILz3Zyllg'
ADMIN_ID = 6999400196

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- 2. РАБОТА С БАЗОЙ ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('housing.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            join_date TEXT,
            lang TEXT,
            city TEXT
        )
    ''')
    conn.commit()
    conn.close()

def add_or_update_user(user_id, lang=None, city=None):
    conn = sqlite3.connect('housing.db')
    cursor = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('INSERT OR IGNORE INTO users (user_id, join_date) VALUES (?, ?)', (user_id, now))
    if lang:
        cursor.execute('UPDATE users SET lang = ? WHERE user_id = ?', (lang, user_id))
    if city:
        cursor.execute('UPDATE users SET city = ? WHERE user_id = ?', (city, user_id))
    conn.commit()
    conn.close()

def get_users_by_city(city):
    conn = sqlite3.connect('housing.db')
    cursor = conn.cursor()
    if city == 'All':
        cursor.execute('SELECT user_id FROM users')
    else:
        cursor.execute('SELECT user_id FROM users WHERE city = ?', (city,))
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

init_db()

# --- 3. КНОПКИ ---
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

# --- 4. ОБРАБОТКА ---
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
    user_id = message.from_user.id
    # 1. Сохраняем город в БД
    add_or_update_user(user_id, city=message.text)
    
    # 2. Безопасно достаем язык из БД, чтобы не было ошибки, если он еще не выбран
    conn = sqlite3.connect('housing.db')
    cursor = conn.cursor()
    cursor.execute('SELECT lang FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    # Если в базе пусто, ставим английский по умолчанию
    lang = result[0] if result and result[0] else '🇬🇧 English'
    conn.close()
    
    # 3. Отвечаем пользователю и подгружаем меню на его языке
    await message.answer(
        f"City set to {message.text}! You will receive notifications.", 
        reply_markup=get_main_menu(lang)
    )

@dp.message_handler(lambda message: message.from_user.id == ADMIN_ID)
async def admin_msg(message: types.Message):
    if message.text.startswith('/'): return
    confirm_menu = InlineKeyboardMarkup()
    confirm_menu.add(InlineKeyboardButton("🚀 Broadcast All", callback_data="broadcast_all"))
    await message.reply(f"Broadcast to everyone?", reply_markup=confirm_menu)

@dp.callback_query_handler(lambda c: c.data == 'broadcast_all')
async def process_broadcast(callback_query: types.CallbackQuery):
    msg_text = callback_query.message.reply_to_message.text
    all_users = get_users_by_city('All')
    for u_id in all_users:
        try: await bot.send_message(u_id, msg_text)
        except: pass
    await callback_query.answer("Sent!")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
