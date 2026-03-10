import os
import logging
from aiogram import Bot, Dispatcher, executor, types

# Берем токен из переменной окружения Railway
API_TOKEN = os.getenv('BOT_TOKEN') 

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- НАСТРОЙКИ ---
API_TOKEN = '8646275203:AAFenGqJIBpvk1DXrbBqDIOPiOILz3Zyllg'
ADMIN_ID = 6999400196

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- ПАРСЕРЫ ---
def parse_pararius(city):
    fmt = city.lower().replace("the ", "").replace(" ", "-")
    url = f"https://www.pararius.com/apartments/{fmt}"
    scraper = cloudscraper.create_scraper()
    try:
        resp = scraper.get(url, timeout=20)
        soup = BeautifulSoup(resp.text, 'html.parser')
        items = soup.select('h2.listing-search-item__title a')
        res = [f"🏠 {i.text.strip()}\n🔗 https://www.pararius.com{i['href']}" for i in items[:5]]
        return res if res else ["На Pararius пусто."]
    except Exception as e: return [f"Pararius error: {e}"]

def parse_kamernet(city):
    fmt = city.lower().replace("the ", "").replace(" ", "-")
    url = f"https://kamernet.nl/en/for-rent/rooms-{fmt}"
    scraper = cloudscraper.create_scraper()
    try:
        resp = scraper.get(url, timeout=20)
        soup = BeautifulSoup(resp.text, 'html.parser')
        items = soup.select('.room-item-title')
        res = [f"🎓 {i.text.strip()}" for i in items[:5]]
        return res if res else ["На Kamernet пусто."]
    except Exception as e: return [f"Kamernet error: {e}"]

# --- ФОНОВЫЙ МОНИТОРИНГ ---
seen_links = set()

async def monitor_housing():
    while True:
        try:
            results = parse_pararius("eindhoven")
            for item in results:
                if "🔗" in item:
                    link = item.split("🔗 ")[-1]
                    if link not in seen_links:
                        seen_links.add(link)
                        await bot.send_message(ADMIN_ID, f"🔔 Новая квартира (Эйндховен):\n{item}")
        except Exception as e: logging.error(f"Monitor error: {e}")
        await asyncio.sleep(1800)

# --- МЕНЮ ---
def get_lang_menu():
    m = ReplyKeyboardMarkup(resize_keyboard=True)
    m.add(KeyboardButton('🇷🇺 Русский'), KeyboardButton('🇬🇧 English'))
    return m

def get_city_menu():
    m = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    for c in ['🇳🇱 Eindhoven', '🇳🇱 Amsterdam', '🇳🇱 Rotterdam', '🇳🇱 The Hague', '🎓 Delft', '🎓 Leiden']:
        m.add(KeyboardButton(c))
    return m

def get_main_menu():
    m = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add(KeyboardButton('🏠 Pararius'), KeyboardButton('🎓 Kamernet'))
    m.add(KeyboardButton('⚙️ Сменить город'))
    return m

user_data = {}

# --- ЛОГИКА ---
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    await message.answer("Выберите язык / Choose language:", reply_markup=get_lang_menu())

@dp.message_handler(lambda m: m.text in ['🇷🇺 Русский', '🇬🇧 English'])
async def handle_lang(message: types.Message):
    await message.answer("Язык выбран. Выбери город:", reply_markup=get_city_menu())

@dp.message_handler(lambda m: '🇳🇱' in m.text or '🎓' in m.text)
async def set_city(message: types.Message):
    user_data[message.from_user.id] = message.text.split()[-1]
    await message.answer(f"Город {message.text} зафиксирован.", reply_markup=get_main_menu())

@dp.message_handler(lambda m: m.text in ['🏠 Pararius', '🎓 Kamernet'])
async def search_handler(message: types.Message):
    city = user_data.get(message.from_user.id, 'Eindhoven')
    await message.answer(f"Ищу на {message.text.replace('🏠 ', '').replace('🎓 ', '')}...")
    res = parse_pararius(city) if 'Pararius' in message.text else parse_kamernet(city)
    await message.answer("\n\n".join(res))

@dp.message_handler(lambda m: m.text == '⚙️ Сменить город')
async def change_city(message: types.Message):
    await message.answer("Выберите новый город:", reply_markup=get_city_menu())

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(monitor_housing())
    executor.start_polling(dp, skip_updates=True)
