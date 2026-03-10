import logging
import cloudscraper
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

API_TOKEN = '8646275203:AAFenGqJIBpvk1DXrbBqDIOPiOILz3Zyllg'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- ПАРСЕРЫ ---
def parse_pararius(city):
    # Pararius для квартир
    url = f"https://www.pararius.com/apartments/{city.lower()}"
    scraper = cloudscraper.create_scraper()
    try:
        resp = scraper.get(url, timeout=20)
        soup = BeautifulSoup(resp.text, 'html.parser')
        items = soup.select('h2.listing-search-item__title a')
        res = [f"🏠 {i.text.strip()}\n🔗 https://www.pararius.com{i['href']}" for i in items[:5]]
        return res if res else ["На Pararius пусто."]
    except Exception as e: return [f"Ошибка Pararius: {e}"]

def parse_kamernet(city):
    # Kamernet для комнат
    url = f"https://kamernet.nl/en/for-rent/rooms-{city.lower()}"
    scraper = cloudscraper.create_scraper()
    try:
        resp = scraper.get(url, timeout=20)
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Селектор для Kamernet (может меняться, проверяем заголовки)
        items = soup.select('.room-item-title') 
        res = [f"🎓 {i.text.strip()}" for i in items[:5]]
        return res if res else ["На Kamernet пусто."]
    except Exception as e: return [f"Ошибка Kamernet: {e}"]

# --- МЕНЮ ---
def get_main_menu():
    menu = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    menu.add(KeyboardButton('🏠 Pararius (Квартиры)'), KeyboardButton('🎓 Kamernet (Комнаты)'))
    menu.add(KeyboardButton('⚙️ Сменить город'))
    return menu

def get_city_menu():
    menu = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    cities = ['🇳🇱 Eindhoven', '🇳🇱 Amsterdam', '🇳🇱 Rotterdam', '🇳🇱 The Hague', '🎓 Delft', '🎓 Leiden']
    for city in cities: menu.add(KeyboardButton(city))
    return menu

# --- ЛОГИКА ---
user_data = {}

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    await message.answer("Привет! Выбери город для поиска:", reply_markup=get_city_menu())

@dp.message_handler(lambda m: '🇳🇱' in m.text or '🎓' in m.text)
async def set_city(message: types.Message):
    clean_city = message.text.split()[-1].lower().replace("hague", "the-hague")
    user_data[message.from_user.id] = clean_city
    await message.answer(f"Город {message.text} выбран. Что ищем?", reply_markup=get_main_menu())

@dp.message_handler(lambda m: m.text == '🏠 Pararius (Квартиры)')
async def search_pararius(message: types.Message):
    city = user_data.get(message.from_user.id, 'eindhoven')
    await message.answer("Ищу на Pararius...")
    res = parse_pararius(city)
    await message.answer("\n\n".join(res))

@dp.message_handler(lambda m: m.text == '🎓 Kamernet (Комнаты)')
async def search_kamernet(message: types.Message):
    city = user_data.get(message.from_user.id, 'eindhoven')
    await message.answer("Ищу на Kamernet...")
    res = parse_kamernet(city)
    await message.answer("\n\n".join(res))

@dp.message_handler(lambda m: m.text == '⚙️ Сменить город')
async def change_city(message: types.Message):
    await message.answer("Выберите новый город:", reply_markup=get_city_menu())

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
