import os
import logging
from aiogram import Bot, Dispatcher, executor, types

# Берем токен из переменных окружения
API_TOKEN = os.getenv'8646275203:AAFenGqJIBpvk1DXrbBqDIOPiOILz3Zyllg'

# Проверка: если токен не нашелся, бот напишет об этом в логи
if not API_TOKEN:
    print("ОШИБКА: Переменная BOT_TOKEN не найдена в системе!")
else:
    print(f"Токен найден! Начинается на: {API_TOKEN[:5]}...")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
