import logging
import datetime
import pytz
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# 1. НАСТРОЙКИ
API_TOKEN = '8646275203:AAFenGqJIBpvk1DXrbBqDIOPiOILz3Zyllg'
ADMIN_ID = 6999400196  # Твой ID

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# БАЗА ДАННЫХ
users_db = {} 

# МЕНЮ
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
    
    if user_id not in users_db:
        users_db[user_id] = {'join_date': now_nl, 'lang': None}
    
    await message.answer(
        f"Goeiedag! Eindhoven: {now_nl.strftime('%H:%M')}\nChoose language:",
        reply_markup=get_lang_menu()
    )

# ОБРАБОТКА ВЫБОРА ЯЗЫКА
@dp.message_handler(lambda message: message.text in ['🇷🇺 Русский', '🇬🇧 English', '🇳🇱 Nederlands'])
async def set_lang(message: types.Message):
    user_id = message.from_user.id
    users_db[user_id]['lang'] = message.text
    await message.answer(f"Success! Language set to {message.text}", reply_markup=types.ReplyKeyboardRemove())

# --- АДМИН-ПАНЕЛЬ (РАССЫЛКА) ---

@dp.message_handler(lambda message: message.from_user.id == ADMIN_ID)
async def admin_msg(message: types.Message):
    # Если пишет админ, создаем кнопку "Разослать всем"
    confirm_menu = InlineKeyboardMarkup()
    confirm_menu.add(InlineKeyboardButton("🚀 РАССЫЛКА (Всем)", callback_data="broadcast"))
    confirm_menu.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    
    await message.reply("Хозяин, разослать это сообщение всем юзерам?", reply_markup=confirm_menu)

@dp.callback_query_handler(lambda c: c.data == 'broadcast')
async def process_broadcast(callback_query: types.CallbackQuery):
    msg_text = callback_query.message.reply_to_message.text
    count = 0
    for user_id in users_db:
        try:
            await bot.send_message(user_id, f"📢 НОВОЕ ОБЪЯВЛЕНИЕ:\n\n{msg_text}")
            count += 1
        except Exception:
            pass
    await bot.answer_callback_query(callback_query.id, text=f"Отправлено {count} чел.")
    await bot.send_message(ADMIN_ID, f"✅ Готово! Рассылка завершена ({count} чел.)")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
