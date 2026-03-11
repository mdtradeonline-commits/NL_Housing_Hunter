import os
import asyncio
import sqlite3
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from bs4 import BeautifulSoup

# Запуск через Polling: нам не нужны ни FastAPI, ни Webhook
TOKEN = os.getenv("TELEGRAM_TOKEN")
BOT = Bot(token=TOKEN)
DP = Dispatcher()

# База данных
def init_db():
    conn = sqlite3.connect("/app/data/bot.db")
    conn.execute("CREATE TABLE IF NOT EXISTS seen_ads(link TEXT PRIMARY KEY)")
    conn.commit()
    conn.close()

async def check_pararius():
    url = "https://www.pararius.com/apartments/eindhoven"
    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}) as session:
        async with session.get(url) as resp:
            soup = BeautifulSoup(await resp.text(), "html.parser")
            # Тут будет твоя логика уведомлений
            print("Парсинг выполнен...")

async def main():
    init_db()
    print("Бот запущен в режиме Polling...")
    # Запускаем поллинг (бот будет ждать сообщений сам)
    await DP.start_polling(BOT)

if __name__ == "__main__":
    asyncio.run(main())
