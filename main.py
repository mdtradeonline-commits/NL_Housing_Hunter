import logging
import datetime
import pytz
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# 1. ТВОЙ ТОКЕН
API_TOKEN = '8646275203:AAFenGqJIBpvk1DXrbBqDIOPiOILz3Zyllg'

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# 2. БАЗА ДАННЫХ (в памяти бота)
users_db = {} 

# 3. МЕНЮ ВЫБОРА ЯЗЫКА
def get_lang_menu():
    menu = ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add(KeyboardButton('🇷🇺 Русский'), KeyboardButton('🇬🇧 English'), KeyboardButton('🇳🇱 Nederlands'))
    return menu

# КОМАНДА /START
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    tz_nl = pytz.timezone('Europe/Amsterdam')
    now_nl = datetime.datetime.now(tz_nl)
    
    # Записываем юзера, если новый
    if user_id not in users_db:
        users_db[user_id] = {
            'join_date': now_nl,
            'lang': None
        }
    
    await message.answer(
        f"Goeiedag! Eindhoven time: {now_nl.strftime('%H:%M')}\n\n"
        "Choose your language / Выберите язык / Kies uw taal:",
        reply_markup=get_lang_menu()
    )

# ОБРАБОТКА ВЫБОРА ЯЗЫКА
@dp.message_handler(lambda message: message.text in ['🇷🇺 Русский', '🇬🇧 English', '🇳🇱 Nederlands'])
async def set_lang(message: types.Message):
    user_id = message.from_user.id
    lang_choice = message.text
    
    # Сохраняем язык
    if user_id in users_db:
        users_db[user_id]['lang'] = lang_choice
    
    responses = {
        '🇷🇺 Русский': "Отлично! Теперь я буду присылать тебе жилье на русском. Твои 24 часа демо начались! 🏠",
        '🇬🇧 English': "Great! I will send you housing options in English. Your 24-hour trial has started! 🏠",
        '🇳🇱 Nederlands': "Geweldig! Ik stuur je woningopties in het Nederlands. Je 24-uurs proefperiode is begonnen! 🏠"
    }
    
    await message.answer(responses[lang_choice], reply_markup=types.ReplyKeyboardRemove())

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
