import logging
import cloudscraper
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

API_TOKEN = '8646275203:AAFenGqJIBpvk1DXrbBqDIOPiOILz3Zyllg'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Словарь для хранения выбранного языка и города (в памяти)
user_data = {}

# 1. Функция парсинга
def get_listings(city):
    city_name = city.replace("🇳🇱 ", "").lower()
    url = f"https://www.pararius.com/apartments/{city_name}"
    scraper = cloudscraper.create_scraper()
    try:
        response = scraper.get(url, timeout=20)
        soup = BeautifulSoup(response.text, 'html.parser')
        listings = soup.select('h2.listing-search-item__title a')
        results = [f"🏠 {item.text.strip()}\n🔗 https://www.pararius.com{item['href']}" for item in listings[:5]]
        return results if results else ["Ничего не нашёл."]
    except Exception as e:
        return [f"Ошибка парсера: {str(e)}"]

# 2. Меню языков
def get_lang_menu():
    menu = ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add(KeyboardButton('🇬🇧 English'), KeyboardButton('🇳🇱 Nederlands'), KeyboardButton('🇷🇺 Русский'))
    return menu

# 3. Меню городов
def get_city_menu():
    menu = ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add(KeyboardButton('🇳🇱 Eindhoven'), KeyboardButton('🇳🇱 Amsterdam'))
    return menu

@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    await message.answer("Выберите язык / Choose language / Kies taal:", reply_markup=get_lang_menu())

@dp.message_handler(lambda m: m.text in ['🇬🇧 English', '🇳🇱 Nederlands', '🇷🇺 Русский'])
async def handle_lang(message: types.Message):
    user_data[message.from_user.id] = {'lang': message.text}
    await message.answer("Язык выбран. Теперь выберите город:", reply_markup=get_city_menu())

@dp.message_handler(lambda m: '🇳🇱' in m.text)
async def handle_city(message: types.Message):
    await message.answer(f"Ищу квартиры в {message.text}...")
    results = get_listings(message.text)
    await message.answer("\n\n".join(results))

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
