
import telebot
from telebot import types

# ПРЯМАЯ ВСТАВКА БЕЗ ПЕРЕМЕННЫХ
TOKEN = "8646275203:AAGh_s34uGHfrLu36x00YM-j91YIU63cnD4"

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_ru = types.InlineKeyboardButton("🇷🇺 Русский", callback_data='ru')
    btn_en = types.InlineKeyboardButton("🇬🇧 English", callback_data='en')
    btn_pl = types.InlineKeyboardButton("🇵🇱 Polski", callback_data='pl')
    markup.add(btn_ru, btn_en, btn_pl)
    bot.send_message(message.chat.id, "Choose language / Выберите язык / Wybierz język:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data == "ru":
        bot.send_message(call.message.chat.id, "🏠 Бот запущен на русском!")
    elif call.data == "en":
        bot.send_message(call.message.chat.id, "🏠 Bot is running in English!")
    elif call.data == "pl":
        bot.send_message(call.message.chat.id, "🏠 Bot działa po polsku!")

print("--- СИСТЕМА ЗАПУЩЕНА ---")
bot.infinity_polling()
