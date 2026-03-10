import logging
import datetime
import sqlite3
import cloudscraper
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# --- 1. НАСТРОЙКИ ---
API_TOKEN = '8646275203:AAFenGqJIBpvk1DXrbBqDIOPiOILz3Zyllg'
ADMIN_ID = 6999400196

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- 2. ПАРСИНГ (Пробуем Pararius как более стабильный вариант) ---
def get_listings_pararius(city="eindhoven"):
    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})
    # Формируем URL под город (нижний регистр)
    url = f"https://www.pararius.com/apartments/{city.lower()}"
    
    try:
        response = scraper.get(url, timeout=20)
        if response.status_code != 200:
            return [f"Pararius ответил кодом {response.status_code}. Защита."]
            
        soup = BeautifulSoup(response.text, 'html.parser')
        # Ищем заголовки объявлений на Pararius
        listings = soup.find_all('h2', class_='listing-search-item__title')
        results = [item.text.strip() for item in listings[:5]]
        
        return results if results else ["На Pararius пока пусто по этому городу."]
    except Exception as e:
        return [f"Ошибка Pararius: {e}"]

# --- 3. БАЗА ДАННЫХ (с поддержкой Premium) ---
def init_db():
    conn = sqlite3.connect('housing.db')
    cursor = conn.cursor()
    # Добавили поле is_premium (0 - нет, 1 - да)
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, join_date TEXT, lang TEXT, city TEXT, is_premium INTEGER DEFAULT 0)''')
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

# --- 4. КЛАВИАТУРЫ ---
def get_lang_menu():
    menu = ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add(KeyboardButton('🇷🇺 Русский'), KeyboardButton('🇬🇧 English'), KeyboardButton('🇳🇱 Nederlands'))
    return menu

def get_city_menu():
    menu = ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add(KeyboardButton('🇳🇱 Eindhoven'), KeyboardButton('🇳🇱 Amsterdam'))
    menu.add(KeyboardButton('🇳🇱 Rotterdam'), KeyboardButton('🇳🇱 The Hague'))
    menu.add(KeyboardButton('🎓 Delft'), KeyboardButton('🎓 Leiden'))
    menu.add(KeyboardButton('🌍 All NL/BE'))
    return menu

def get_main_menu():
    menu = ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add(KeyboardButton('🔍 Искать жилье (Pararius)'), KeyboardButton('⚙️ Настройки'))
    menu.add(KeyboardButton('💎 Статус подписки'))
    return menu

# --- 5. ХЕНДЛЕРЫ ---
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    add_or_update_user(message.from_user.id)
    await message.answer("Choose your language / Выберите язык:", reply_markup=get_lang_menu())

@dp.message_handler(lambda m: m.text in ['🇷🇺 Русский', '🇬🇧 English', '🇳🇱 Nederlands'])
async def handle_lang(message: types.Message):
    add_or_update_user(message.from_user.id, lang=message.text)
    await message.answer("Выберите город для поиска:", reply_markup=get_city_menu())

@dp.message_handler(lambda m: m.text in ['🇳🇱 Eindhoven', '🇳🇱 Amsterdam', '🇳🇱 Rotterdam', '🇳🇱 The Hague', '🎓 Delft', '🎓 Leiden', '🌍 All NL/BE'])
async def handle_city(message: types.Message):
    # Очищаем название города от эмодзи для парсера
    city_name = message.text.split()[-1]
    add_or_update_user(message.from_user.id, city=city_name)
    await message.answer(f"Город {city_name} сохранен!", reply_markup=get_main_menu())

@dp.message_handler(lambda m: m.text == '🔍 Искать жилье (Pararius)')
async def search_housing(message: types.Message):
    await message.answer("Запускаю поиск на Pararius... Подождите.")
    # Тут можно вытягивать город юзера из БД, но пока для теста возьмем Эйндховен
    data = get_listings_pararius("eindhoven")
    await message.answer("Последние объявления:\n\n" + "\n\n".join(data))

@dp.message_handler(lambda m: m.text == '💎 Статус подписки')
async def check_premium(message: types.Message):
    await message.answer("Ваш статус: **Обычный**\n\nПремиум подписка дает:\n- Уведомления мгновенно\n- Поиск по Kamernet\n- Доступ к закрытым чатам")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
