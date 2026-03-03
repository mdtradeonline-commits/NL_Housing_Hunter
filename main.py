
import os
import logging
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Включаем логирование, чтобы видеть ошибки, если они будут
logging.basicConfig(level=logging.INFO)

# Берем токен из настроек Railway (мы его там пропишем)
API_TOKEN = os.getenv('BOT_TOKEN')

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Наши переводы
TEXTS = {
    'ru': {
        'welcome': "🇷🇺 Привет! Я помогу тебе найти жилье в Нидерландах.\nЯ мониторю Funda и Pararius 24/7. Нажми кнопку ниже, чтобы начать.",
        'btn': "⚙️ Настроить фильтры"
    },
    'en': {
        'welcome': "🇬🇧 Hi! I'll help you find housing in the Netherlands.\nI monitor Funda and Pararius 24/7. Click the button below to start.",
        'btn': "⚙️ Set up filters"
    },
    'nl': {
        'welcome': "🇳🇱 Hoi! Ik help je bij het vinden van woonruimte in Nederland.\nIk monitor Funda en Pararius 24/7. Klik op de knop om te beginnen.",
        'btn': "⚙️ Filters instellen"
    }
}

# Стартовая команда: выбор языка
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("🇷🇺 RU", callback_data='lang_ru'),
        InlineKeyboardButton("🇬🇧 EN", callback_data='lang_en'),
        InlineKeyboardButton("🇳🇱 NL", callback_data='lang_nl')
    )
    await message.answer("Please choose your language / Выберите язык / Kies uw taal:", reply_markup=kb)

# Обработка выбора языка
@dp.callback_query_handler(lambda c: c.data.startswith('lang_'))
async def process_lang(callback_query: types.CallbackQuery):
    lang = callback_query.data.split('_')[1]
    
    # Создаем кнопку для следующего шага (фильтры)
    next_kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton(TEXTS[lang]['btn'], callback_data=f'setup_{lang}')
    )
    
    await bot.answer_callback_query(callback_query.id)
    await bot.edit_message_text(
        chat_id=callback_query.from_user.id,
        message_id=callback_query.message.message_id,
        text=TEXTS[lang]['welcome'],
        reply_markup=next_kb
    )

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
