import logging
import cloudscraper
import asyncio
import os
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# --- НАСТРОЙКИ ---
API_TOKEN = os.getenv('8646275203:AAFenGqJIBpvk1DXrbBqDIOPiOILz3Zyllg') # Теперь берем токен из переменных Railway!
ADMIN_ID = 6999400196

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- ПАРСЕРЫ ---
def get_scraper():
    return cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True})

def parse_housing(site, city):
    fmt = city.lower().replace("the ", "").replace(" ", "-")
    scraper = get_scraper()
    try:
        if site == 'Pararius':
            url = f"https://www.pararius.com/apartments/{fmt}"
            resp = scraper.get(url, timeout=20)
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('h2.listing-search-item__title a')
            return [f"🏠 {i.text.strip()}\n🔗 https://www.pararius.com{i['href']}" for i in items[:3]]
        
        elif site == 'Kamernet':
            url = f"https://kamernet.nl/en/for-rent/rooms-{fmt}"
            resp = scraper.get(url, timeout=20)
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('.room-item-title')
            return [f"🎓 {i.text.strip()}" for i in items[:3]]
            
        elif site == 'Huurwoningen':
            url = f"https://www.huurwoningen.nl/in/{fmt}/"
            resp = scraper.get(url, timeout=20)
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('.listing-item')
            return [f"🏢 {i.text.strip()}" for i in items[:3]]
    except Exception as e:
        return [f"Ошибка {site}: {str(e)[:20]}"]
    return ["Ничего не найдено."]

# --- МЕНЮ ---
def get_main_menu():
    m = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(KeyboardButton('🏠 Pararius'), KeyboardButton('🎓 Kamernet'), KeyboardButton('🏢 Huurwoningen'))
    m.add(KeyboardButton('⚙️ Сменить город'), KeyboardButton('🔄 В начало'))
    return m

user_data = {}

# --- ЛОГИКА ---
@dp.message_handler(commands=['start', 'language'])
async def start_cmd(message: types.Message):
    await message.answer("Привет! Выбери город:", reply_markup=get_city_menu())

@dp.message_handler(lambda m: '🇳🇱' in m.text or '🎓' in m.text)
async def set_city(message: types.Message):
    user_data[message.from_user.id] = message.text.split(" ", 1)[1]
    await message.answer(f"Город {message.text} зафиксирован.", reply_markup=get_main_menu())

@dp.message_handler(lambda m: m.text in ['🏠 Pararius', '🎓 Kamernet', '🏢 Huurwoningen'])
async def search_handler(message: types.Message):
    city = user_data.get(message.from_user.id, 'Eindhoven')
    site = message.text.replace('🏠 ', '').replace('🎓 ', '').replace('🏢 ', '')
    await message.answer(f"🔎 Ищу {site} в {city}...")
    res = parse_housing(site, city)
    await message.answer("\n\n".join(res) if res else "Пусто.")

@dp.message_handler(lambda m: m.text == '⚙️ Сменить город')
async def change_city(message: types.Message):
    await message.answer("Выберите город:", reply_markup=get_city_menu())

@dp.message_handler(lambda m: m.text == '🔄 В начало')
async def reset_handler(message: types.Message):
    await start_cmd(message)

def get_city_menu():
    m = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for c in ['🇳🇱 Eindhoven', '🇳🇱 Amsterdam', '🇳🇱 Rotterdam', '🎓 Delft']:
        m.add(KeyboardButton(c))
    return m

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.delete_webhook(drop_pending_updates=True))
    executor.start_polling(dp, skip_updates=True)
