
import telebot
import time

TOKEN = "646275203:AAFenGqJIBpvk1DXrbBqDIOPiOILz3Zyllg"

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Охотник на связи! Бот работает без конфликтов.")

if __name__ == "__main__":
    print("Удаляю старые сообщения и запускаюсь...")
    # skip_pending=True помогает избежать конфликтов при перезапуске
    bot.infinity_polling(skip_pending=True)
