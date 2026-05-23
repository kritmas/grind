import asyncio
import sqlite3
import threading
import os
from datetime import datetime
from flask import Flask, request
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import Update

from config import BOT_TOKEN, ADMIN_IDS
from database import init_db, add_log
from states import AddChannelStates, AddClientStates, ComplaintStates
from keyboards import get_main_menu, role_keyboard

# Создаём Flask приложение
flask_app = Flask(__name__)

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ========== БАЗОВЫЕ ФУНКЦИИ ==========
def get_db():
    conn = sqlite3.connect("agency_bot.db")
    conn.row_factory = sqlite3.Row
    return conn

def get_user(telegram_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
    conn.close()
    return user

def create_user(telegram_id, username, full_name, role):
    conn = get_db()
    conn.execute(
        "INSERT INTO users (telegram_id, username, full_name, role, created_at, status) VALUES (?, ?, ?, ?, ?, 'pending')",
        (telegram_id, username, full_name, role, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    add_log(telegram_id, "register", f"Роль: {role}")

def update_user_status(telegram_id, status):
    conn = get_db()
    conn.execute("UPDATE users SET status = ? WHERE telegram_id = ?", (status, telegram_id))
    conn.commit()
    conn.close()

def get_pending_users():
    conn = get_db()
    users = conn.execute("SELECT * FROM users WHERE status = 'pending'").fetchall()
    conn.close()
    return users

# ========== FLASK ЭНДПОИНТЫ ==========
@flask_app.route('/')
@flask_app.route('/health')
def health():
    return "OK", 200

@flask_app.route(f'/webhook/{BOT_TOKEN}', methods=['POST'])
async def webhook():
    update = types.Update(**await request.get_json())
    await dp.feed_update(bot, update)
    return "OK", 200

# ========== СТАРТ ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = get_user(message.from_user.id)
    
    if user:
        if user['status'] == 'approved':
            await message.answer(f"👋 С возвращением!", reply_markup=get_main_menu(user['role']))
        elif user['status'] == 'pending':
            await message.answer("⏳ Ваша заявка на подтверждении.")
        else:
            await message.answer("❌ Заявка отклонена.")
    else:
        await message.answer(
            "🌟 Добро пожаловать!\n\nВыберите роль:",
            reply_markup=role_keyboard
        )

@dp.message(F.text.in_(["🕵️ Скаут", "📞 Продажник", "👑 Менеджер"]))
async def role_selected(message: types.Message):
    role_map = {"🕵️ Скаут": "scout", "📞 Продажник": "seller", "👑 Менеджер": "manager"}
    role = role_map[message.text]
    
    create_user(message.from_user.id, message.from_user.username, message.from_user.full_name, role)
    
    for admin_id in ADMIN_IDS:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_{message.from_user.id}"),
             InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{message.from_user.id}")]
        ])
        await bot.send_message(admin_id, f"📋 Новая заявка!\n👤 {message.from_user.full_name}\n🎭 {role}", reply_markup=keyboard)
    
    await message.answer("✅ Заявка отправлена админу!", reply_markup=ReplyKeyboardRemove())

# ========== АДМИН: ЗАЯВКИ ==========
@dp.message(F.text == "👥 Заявки")
async def pending_users(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Нет доступа.")
        return
    
    users = get_pending_users()
    if not users:
        await message.answer("📭 Нет заявок.")
        return
    
    for user in users:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_{user['telegram_id']}"),
             InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user['telegram_id']}")]
        ])
        await message.answer(f"👤 {user['full_name']}\n🎭 {user['role']}\n🆔 {user['telegram_id']}", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith('accept_'))
async def accept_user(callback: types.CallbackQuery):
    user_id = int(callback.data.split('_')[1])
    update_user_status(user_id, 'approved')
    user = get_user(user_id)
    await callback.message.edit_text(f"✅ {user['full_name']} принят!")
    await bot.send_message(user_id, "✅ Заявка одобрена! Нажмите /start", reply_markup=get_main_menu(user['role']))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith('reject_'))
async def reject_user(callback: types.CallbackQuery):
    user_id = int(callback.data.split('_')[1])
    update_user_status(user_id, 'rejected')
    await callback.message.edit_text("❌ Пользователь отклонён")
    await bot.send_message(user_id, "❌ Заявка отклонена")
    await callback.answer()

# ========== СКАУТ ==========
@dp.message(F.text == "➕ Добавить канал")
async def add_channel(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    if user['role'] != 'scout' or user['status'] != 'approved':
        await message.answer("⛔ Нет доступа.")
        return
    await state.set_state(AddChannelStates.link)
    await message.answer("1️⃣ Ссылка на канал:")

@dp.message(AddChannelStates.link)
async def ch_link(message: types.Message, state: FSMContext):
    await state.update_data(link=message.text)
    await state.set_state(AddChannelStates.topic)
    await message.answer("2️⃣ Тематика:")

@dp.message(AddChannelStates.topic)
async def ch_topic(message: types.Message, state: FSMContext):
    await state.update_data(topic=message.text)
    await state.set_state(AddChannelStates.subscribers)
    await message.answer("3️⃣ Подписчиков (число):")

@dp.message(AddChannelStates.subscribers)
async def ch_subs(message: types.Message, state: FSMContext):
    try:
        await state.update_data(subscribers=int(message.text))
        await state.set_state(AddChannelStates.views)
        await message.answer("4️⃣ Средние просмотры:")
    except:
        await message.answer("❌ Введите число!")

@dp.message(AddChannelStates.views)
async def ch_views(message: types.Message, state: FSMContext):
    try:
        await state.update_data(views=int(message.text))
        await state.set_state(AddChannelStates.price)
        await message.answer("5️⃣ Цена рекламы (₽):")
    except:
        await message.answer("❌ Введите число!")

@dp.message(AddChannelStates.price)
async def ch_price(message: types.Message, state: FSMContext):
    try:
        await state.update_data(price=int(message.text))
        await state.set_state(AddChannelStates.er)
        await message.answer("6️⃣ ER (процент):")
    except:
        await message.answer("❌ Введите число!")

@dp.message(AddChannelStates.er)
async def ch_er(message: types.Message, state: FSMContext):
    try:
        await state.update_data(er=float(message.text))
        await state.set_state(AddChannelStates.comment)
        await message.answer("7️⃣ Комментарий:")
    except:
        await message.answer("❌ Введите число!")

@dp.message(AddChannelStates.comment)
async def ch_comment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    conn = get_db()
    conn.execute(
        "INSERT INTO channels (link, topic, subscribers, avg_views, price, er, comment, added_by, created_at, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'checking')",
        (data['link'], data['topic'], data['subscribers'], data['views'], data['price'], data['er'], message.text, message.from_user.id, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer(f"✅ Канал добавлен! Статус: 🟡 На проверке", reply_markup=get_main_menu('scout'))
    
    for admin_id in ADMIN_IDS:
        await bot.send_message(admin_id, f"📢 Новый канал от {message.from_user.full_name}!")

@dp.message(F.text == "📋 Мои каналы")
async def my_channels(message: types.Message):
    user = get_user(message.from_user.id)
    if user['role'] != 'scout':
        return
    
    conn = get_db()
    channels = conn.execute("SELECT * FROM channels WHERE added_by = ?", (message.from_user.id,)).fetchall()
    conn.close()
    
    if not channels:
        await message.answer("📭 У вас нет каналов")
        return
    
    text = "📋 Ваши каналы:\n\n"
    for ch in channels:
        status = "🟡 Проверка" if ch['status'] == 'checking' else "🟢 Одобрен" if ch['status'] == 'approved' else "🔴 Отклонён"
        text += f"• {ch['topic']} | {ch['price']}₽ | {status}\n"
    await message.answer(text)

# ========== ПРОФИЛЬ ==========
@dp.message(F.text == "👤 Профиль")
async def profile(message: types.Message):
    user = get_user(message.from_user.id)
    
    conn = get_db()
    if user['role'] == 'scout':
        channels = conn.execute("SELECT COUNT(*) as total FROM channels WHERE added_by = ?", (message.from_user.id,)).fetchone()
        text = f"👤 Скаут\n📌 {user['full_name']}\n\n📊 KPI:\n• Добавлено каналов: {channels['total']}"
    else:
        text = f"👤 {user['full_name']}\n🎭 Роль: {user['role']}"
    
    conn.close()
    await message.answer(text)

# ========== ЗАПУСК ВЕБ-СЕРВЕРА ==========
def start_bot():
    """Запускает бота в отдельном потоке"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def run():
        await bot.delete_webhook()
        await dp.start_polling(bot)
    
    loop.run_until_complete(run())

if __name__ == '__main__':
    init_db()
    
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    
    # Запускаем Flask сервер
    port = int(os.environ.get('PORT', 10000))
    flask_app.run(host='0.0.0.0', port=port)