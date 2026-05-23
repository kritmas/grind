import threading  # добавьте эту строку
from flask import Flask, request  # добавьте эту строку
import asyncio
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton

from config import BOT_TOKEN, ADMIN_IDS
from database import init_db, add_log
from states import AddChannelStates, AddClientStates, ComplaintStates
from keyboards import get_main_menu, role_keyboard

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
    
    # Отправляем админу сообщение с КНОПКАМИ
    for admin_id in ADMIN_IDS:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_{message.from_user.id}"),
             InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{message.from_user.id}")]
        ])
        await bot.send_message(
            admin_id, 
            f"📋 Новая заявка!\n👤 {message.from_user.full_name}\n🎭 {role}\n🆔 {message.from_user.id}",
            reply_markup=keyboard
        )
    
    await message.answer("✅ Заявка отправлена админу!", reply_markup=ReplyKeyboardRemove())

# ========== ОБРАБОТЧИКИ КНОПОК ==========
@dp.callback_query(lambda c: c.data.startswith('accept_'))
async def accept_user(callback: types.CallbackQuery):
    user_id = int(callback.data.split('_')[1])
    update_user_status(user_id, 'approved')
    user = get_user(user_id)
    
    await callback.message.edit_text(f"✅ {user['full_name']} принят!")
    
    # Отправляем пользователю уведомление
    await bot.send_message(user_id, f"✅ Ваша заявка одобрена! Вы приняты как {user['role']}\nНажмите /start чтобы начать работу.")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith('reject_'))
async def reject_user(callback: types.CallbackQuery):
    user_id = int(callback.data.split('_')[1])
    update_user_status(user_id, 'rejected')
    
    await callback.message.edit_text("❌ Пользователь отклонён")
    await bot.send_message(user_id, "❌ Ваша заявка отклонена администратором.")
    await callback.answer()

# ========== АДМИН: ПРОСМОТР ЗАЯВОК ==========
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

# ========== СКАУТ: ДОБАВИТЬ КАНАЛ ==========
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
    
    elif user['role'] == 'seller':
        clients = conn.execute("SELECT COUNT(*) as total FROM clients WHERE assigned_to = ? AND deal_closed = 0", (message.from_user.id,)).fetchone()
        closed = conn.execute("SELECT COUNT(*) as total FROM clients WHERE assigned_to = ? AND deal_closed = 1", (message.from_user.id,)).fetchone()
        text = (f"👤 Продажник\n📌 {user['full_name']}\n\n"
                f"📊 KPI:\n"
                f"• Активных клиентов: {clients['total']}\n"
                f"• Закрыто сделок: {closed['total']}")
    
    elif user['role'] == 'manager':
        # Получаем список клиентов менеджера
        clients = conn.execute("SELECT id, username, budget, status, assigned_to, deal_closed FROM clients WHERE created_by = ? ORDER BY created_at DESC", (message.from_user.id,)).fetchall()
        
        if clients:
            text = f"👤 Менеджер\n📌 {user['full_name']}\n\n📋 Ваши клиенты:\n\n"
            for client in clients:
                status_emoji = "🟡" if client['status'] == 'new' else "🔵" if client['status'] == 'in_work' else "🟢" if client['deal_closed'] else "⚪"
                seller_info = ""
                if client['assigned_to']:
                    seller = conn.execute("SELECT full_name FROM users WHERE telegram_id = ?", (client['assigned_to'],)).fetchone()
                    seller_info = f"\n   👤 Продажник: {seller['full_name'] if seller else '?'}"
                closed_info = " ✅ ЗАКРЫТА" if client['deal_closed'] else ""
                text += f"{status_emoji} @{client['username']} | {client['budget']}₽{closed_info}{seller_info}\n"
        else:
            text = f"👤 Менеджер\n📌 {user['full_name']}\n\n📋 У вас пока нет клиентов"
    
    else:
        text = f"👤 Админ\n📌 {user['full_name']}"
    
    conn.close()
    await message.answer(text)

# ========== АДМИН КНОПКИ ==========
@dp.message(F.text == "📊 Аналитика")
async def analytics(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    conn = get_db()
    users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    channels = conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0]
    await message.answer(f"📊 Аналитика\n\n👥 Пользователей: {users}\n📢 Каналов: {channels}")
    conn.close()

@dp.message(F.text == "📂 Все каналы")
async def all_channels(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    conn = get_db()
    channels = conn.execute("SELECT * FROM channels").fetchall()
    conn.close()
    await message.answer(f"📢 Всего каналов: {len(channels)}")

# ========== МЕНЕДЖЕР: НОВЫЙ КЛИЕНТ ==========
@dp.message(F.text == "➕ Новый клиент")
async def new_client_start(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    if user['role'] != 'manager' or user['status'] != 'approved':
        await message.answer("⛔ Нет доступа.")
        return
    await state.set_state(AddClientStates.username)
    await message.answer("1️⃣ Введите username клиента:")

@dp.message(AddClientStates.username)
async def client_username(message: types.Message, state: FSMContext):
    await state.update_data(username=message.text.replace("@", ""))
    await state.set_state(AddClientStates.topic)
    await message.answer("2️⃣ Введите тематику:")

@dp.message(AddClientStates.topic)
async def client_topic(message: types.Message, state: FSMContext):
    await state.update_data(topic=message.text)
    await state.set_state(AddClientStates.budget)
    await message.answer("3️⃣ Введите бюджет (₽):")

@dp.message(AddClientStates.budget)
async def client_budget(message: types.Message, state: FSMContext):
    try:
        await state.update_data(budget=int(message.text))
        await state.set_state(AddClientStates.comment)
        await message.answer("4️⃣ Введите комментарий:")
    except:
        await message.answer("❌ Введите число!")

@dp.message(AddClientStates.comment)
async def client_comment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO clients (username, topic, budget, comment, created_by, status, created_at) VALUES (?, ?, ?, ?, ?, 'new', ?)",
        (data['username'], data['topic'], data['budget'], message.text, message.from_user.id, datetime.now().isoformat())
    )
    conn.commit()
    client_id = cur.lastrowid
    conn.close()
    
    await state.clear()
    await message.answer(f"✅ Клиент добавлен! ID: {client_id}", reply_markup=get_main_menu('manager'))
    
    # Уведомить продажников
    conn = get_db()
    sellers = conn.execute("SELECT telegram_id FROM users WHERE role = 'seller' AND status = 'approved'").fetchall()
    conn.close()
    
    for seller in sellers:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📞 Взять клиента", callback_data=f"take_client_{client_id}")]
        ])
        await bot.send_message(seller['telegram_id'], f"🆕 Новый клиент!\n👤 @{data['username']}\n💰 {data['budget']}₽", reply_markup=keyboard)

# ========== ПРОДАЖНИК: ВЗЯТЬ КЛИЕНТА ==========
@dp.callback_query(lambda c: c.data.startswith('take_client_'))
async def take_client(callback: types.CallbackQuery):
    client_id = int(callback.data.split('_')[2])
    
    conn = get_db()
    # Проверяем, не взят ли уже клиент
    client = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
    
    if client['assigned_to']:
        await callback.answer("Клиент уже взят другим продажником!", show_alert=True)
        return
    
    conn.execute("UPDATE clients SET assigned_to = ?, status = 'in_work' WHERE id = ?", (callback.from_user.id, client_id))
    conn.commit()
    conn.close()
    
    await callback.message.edit_text(f"✅ Вы взяли клиента @{client['username']}!")
    await callback.answer()

# ========== ПРОДАЖНИК: МОИ КЛИЕНТЫ ==========
@dp.message(F.text == "📞 Мои клиенты")
async def my_clients_list(message: types.Message):
    user = get_user(message.from_user.id)
    if user['role'] != 'seller':
        return
    
    conn = get_db()
    clients = conn.execute("SELECT * FROM clients WHERE assigned_to = ? AND deal_closed = 0", (message.from_user.id,)).fetchall()
    conn.close()
    
    if not clients:
        await message.answer("📭 Нет активных клиентов")
        return
    
    text = "📋 Ваши активные клиенты:\n\n"
    for client in clients:
        text += f"• @{client['username']} | 💰 {client['budget']}₽ | 📊 {client['topic']}\n"
        if client['comment']:
            text += f"   📝 {client['comment'][:50]}\n"
        text += "\n"
    await message.answer(text)

# ========== МЕНЕДЖЕР: МОИ КЛИЕНТЫ ==========
@dp.message(F.text == "📋 Мои клиенты")
async def manager_clients(message: types.Message):
    user = get_user(message.from_user.id)
    if user['role'] != 'manager':
        return
    
    conn = get_db()
    clients = conn.execute("SELECT id, username, budget, status, assigned_to, deal_closed FROM clients WHERE created_by = ? ORDER BY created_at DESC", (message.from_user.id,)).fetchall()
    conn.close()
    
    if not clients:
        await message.answer("📭 У вас пока нет клиентов")
        return
    
    text = "📋 Ваши клиенты:\n\n"
    for client in clients:
        status_emoji = "🟡" if client['status'] == 'new' else "🔵" if client['status'] == 'in_work' else "🟢"
        status_text = "Новый" if client['status'] == 'new' else "В работе" if client['status'] == 'in_work' else "Закрыт"
        
        if client['deal_closed']:
            status_emoji = "✅"
            status_text = "СДЕЛКА ЗАКРЫТА"
        
        text += f"{status_emoji} @{client['username']}\n   💰 {client['budget']}₽ | {status_text}\n\n"
    
    await message.answer(text)

# ========== ЗАПУСК ==========
async def main():
    init_db()
    print("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

# ========== FLASK ДЛЯ RENDER (ЧТОБЫ НЕ ЗАСЫПАЛ) ==========
from flask import Flask, request

flask_app = Flask(__name__)

@flask_app.route('/')
@flask_app.route('/health')
def health():
    return "OK", 200

@flask_app.route('/webhook', methods=['POST'])
async def webhook():
    update = types.Update(**await request.get_json())
    await dp.feed_update(bot, update)
    return "OK", 200

def run_flask():
    flask_app.run(host='0.0.0.0', port=8080)

# ========== ЗАПУСК ==========
async def main():
    init_db()
    # Запускаем Flask в отдельном потоке
    threading.Thread(target=run_flask, daemon=True).start()
    print("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())