import sqlite3 # Добавили библиотеку базы данных
import logging
import datetime
import pytz
from aiogram import Bot, Dispatcher, executor, types
# ... (остальные импорты те же)

# --- НАСТРОЙКИ ---
API_TOKEN = '8646275203:AAFenGqJIBpvk1DXrbBqDIOPiOILz3Zyllg'
ADMIN_ID = 6999400196

# --- РАБОТА С БАЗОЙ ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('housing.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            join_date TEXT,
            lang TEXT,
            is_premium INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def add_user(user_id, lang=None):
    conn = sqlite3.connect('housing.db')
    cursor = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('INSERT OR IGNORE INTO users (user_id, join_date, lang) VALUES (?, ?, ?)', 
                   (user_id, now, lang))
    if lang: # Если язык уже выбран, обновляем его
        cursor.execute('UPDATE users SET lang = ? WHERE user_id = ?', (lang, user_id))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('housing.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

# Инициализируем базу при запуске
init_db()

# --- МЕНЮ (СПИСОК ФЛАГОВ) ---
def get_lang_menu():
    menu = ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add(KeyboardButton('🇷🇺 Русский'), KeyboardButton('🇬🇧 English'), KeyboardButton('🇳🇱 Nederlands'))
    return menu

# --- НОВОЕ ГЛАВНОЕ МЕНЮ (ПОЯВЛЯЕТСЯ ПОСЛЕ ВЫБОРА ЯЗЫКА) ---
def get_main_menu(lang):
    menu = ReplyKeyboardMarkup(resize_keyboard=True)
    if lang == '🇷🇺 Русский':
        menu.add(KeyboardButton('⚙️ Настройки языка'), KeyboardButton('🏠 Моя подписка'))
    elif lang == '🇬🇧 English':
        menu.add(KeyboardButton('⚙️ Language Settings'), KeyboardButton('🏠 My Subscription'))
    else: # Dutch
        menu.add(KeyboardButton('⚙️ Instellingen'), KeyboardButton('🏠 Mijn abonnement'))
    return menu

# КОМАНДА /START (ОСТАВЛЯЕМ КАК ЕСТЬ)
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

# --- ОБНОВЛЕННАЯ ОБРАБОТКА ВЫБОРА ЯЗЫКА ---
@dp.message_handler(lambda message: message.text in ['🇷🇺 Русский', '🇬🇧 English', '🇳🇱 Nederlands'])
async def set_lang(message: types.Message):
    user_id = message.from_user.id
    lang_choice = message.text
    
    if user_id not in users_db:
        users_db[user_id] = {}
    users_db[user_id]['lang'] = lang_choice
    
    # Тексты подтверждения
    msg = "Язык установлен! 🇷🇺" if lang_choice == '🇷🇺 Русский' else "Language set! 🇬🇧"
    if lang_choice == '🇳🇱 Nederlands': msg = "Taal ingesteld! 🇳🇱"
    
    # Отправляем подтверждение и ГЛАВНОЕ МЕНЮ (теперь кнопки не исчезнут!)
    await message.answer(msg, reply_markup=get_main_menu(lang_choice))

# ОБРАБОТКА КНОПКИ "НАСТРОЙКИ ЯЗЫКА" (Чтобы возвращались флаги)
@dp.message_handler(lambda message: any(x in message.text for x in ["Настройки", "Settings", "Instellingen"]))
async def settings_btn(message: types.Message):
    await message.answer("Select language / Выберите язык:", reply_markup=get_lang_menu())

# 2. АДМИН-ПАНЕЛЬ (Только для тебя и НЕ для кнопок языка)
@dp.message_handler(lambda message: message.from_user.id == ADMIN_ID)
async def admin_msg(message: types.Message):
    # Если это вдруг команда (начинается с /), не предлагаем рассылку
    if message.text.startswith('/'):
        return

    # Предлагаем рассылку для любого другого текста (ссылки, описания)
    confirm_menu = InlineKeyboardMarkup()
    confirm_menu.add(InlineKeyboardButton("🚀 РАССЫЛКА (Всем)", callback_data="broadcast"))
    confirm_menu.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    
    await message.reply(f"Админ, рассылаем это сообщение всем?", reply_markup=confirm_menu)

# 3. ОБРАБОТКА КНОПОК РАССЫЛКИ
@dp.callback_query_handler(lambda c: c.data == 'broadcast')
async def process_broadcast(callback_query: types.CallbackQuery):
    msg_text = callback_query.message.reply_to_message.text
    count = 0
    for user_id in list(users_db.keys()):
        try:
            await bot.send_message(user_id, f"📢 НОВОЕ ОБЪЯВЛЕНИЕ:\n\n{msg_text}")
            count += 1
        except Exception:
            pass
    await bot.answer_callback_query(callback_query.id, text=f"Отправлено {count} чел.")
    await bot.send_message(ADMIN_ID, f"✅ Рассылка завершена ({count} чел.)")

@dp.callback_query_handler(lambda c: c.data == 'cancel')
async def cancel_broadcast(callback_query: types.CallbackQuery):
    await bot.delete_message(callback_query.from_user.id, callback_query.message.message_id)
    await bot.answer_callback_query(callback_query.id, text="Отменено")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
