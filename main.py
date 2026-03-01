
import telebot
from telebot import types

TOKEN = "8646275203:AAGh_s34uGHfrLu36x00YM-j91YIU63cnD4"
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_ru = types.InlineKeyboardButton("🇷🇺 Русский", callback_data='ru')
    btn_en = types.InlineKeyboardButton("🇬🇧 English", callback_data='en')
    btn_pl = types.InlineKeyboardButton("🇵🇱 Polski", callback_data='pl')
    markup.add(btn_ru, btn_en, btn_pl)
    
    bot.send_message(message.chat.id, "Select language / Выберите язык:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    # Создаем кнопки со ссылками
    links = types.InlineKeyboardMarkup(row_width=2)
    funda = types.InlineKeyboardButton("🏠 Funda", url="https://www.funda.nl/")
    pararius = types.InlineKeyboardButton("🔑 Pararius", url="https://www.pararius.com/")
    kamernet = types.InlineKeyboardButton("🛌 Kamernet", url="https://kamernet.nl/")
    links.add(funda, pararius, kamernet)

    if call.data == "ru":
        text = "🏠 **Привет, Охотник за жильем!**\n\nЯ помогу тебе найти квартиру в Нидерландах. Вот основные сайты для старта:"
    elif call.data == "en":
        text = "🏠 **Hello, Housing Hunter!**\n\nI'll help you find a place in NL. Here are the main websites to start:"
    else:
        text = "🏠 **Cześć, Łowco Mieszkań!**\n\nPomogę Ci znaleźć mieszkanie w Holandii. Oto główne strony na start:"

    # Удаляем кнопки выбора языка и шлем новый текст с полезными ссылками
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
                         text=text, reply_markup=links, parse_mode='Markdown')

print("--- БОТ-ОХОТНИК ЗАПУЩЕН ---")
bot.infinity_polling()
