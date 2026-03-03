
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# ВАЖНО: Вставь свой токен ниже
API_TOKEN = '8646275203:AAFenGqJIBpvk1DXrbBqDIOPiOILz3Zyllg'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Кнопки для меню
btn_market = KeyboardButton('В магазине 🛒')
btn_flags = KeyboardButton('Флаги 🇳🇱')
main_menu = ReplyKeyboardMarkup(resize_keyboard=True).add(btn_market, btn_flags)

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Hoi! Теперь я твой личный помощник в Нидерландах. Что учим сегодня?", reply_markup=main_menu)

@dp.message_handler(lambda message: message.text == 'В магазине 🛒')
async def shop_phrases(message: types.Message):
    text = (
        "Полезные фразы:\n"
        "🔸 **Alstublieft** — Пожалуйста / Вот, возьмите\n"
        "🔸 **Dank u wel** — Большое спасибо\n"
        "🔸 **Mag ik een bonnetje?** — Можно мне чек?\n"
        "🔸 **Pinnen?** — Оплата картой?"
    )
    await message.answer(text, parse_mode='Markdown')

@dp.message_handler(lambda message: message.text == 'Флаги 🇳🇱')
async def show_flags(message: types.Message):
    await message.answer("🇳🇱 Нидерланды\n🇧🇪 Бельгия\n🇱🇺 Люксембург")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
