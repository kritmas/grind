import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = "8090432779:AAGB8fTSo3gvs8REan1aWR6SKmrZjsUHDGU"
ADMIN_IDS = [8083118398]

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ========== ХРАНИЛИЩА ==========
pending_users = {}
approved_users = {}
user_channels = {}
channels_for_approve = []
approved_channels = []
leads = []
deals = []

# ========== КЛАВИАТУРЫ ==========
def get_main_menu(role):
    if role == "scout":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📢 Добавить канал")],
                [KeyboardButton(text="📋 Мои каналы")],
                [KeyboardButton(text="👤 Профиль")]
            ],
            resize_keyboard=True
        )
    elif role == "seller":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="💰 База каналов")],
                [KeyboardButton(text="🎯 Доступные лиды")],
                [KeyboardButton(text="📋 Мои лиды")],
                [KeyboardButton(text="👤 Профиль")]
            ],
            resize_keyboard=True
        )
    elif role == "manager":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="➕ Новый клиент")],
                [KeyboardButton(text="📋 Мои клиенты")],
                [KeyboardButton(text="👤 Профиль")]
            ],
            resize_keyboard=True
        )
    elif role == "admin":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="👥 Заявки на роли")],
                [KeyboardButton(text="📢 Каналы на проверке")],
                [KeyboardButton(text="📊 Статистика")],
                [KeyboardButton(text="👤 Профиль")]
            ],
            resize_keyboard=True
        )
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="👤 Профиль")]], resize_keyboard=True)

role_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🕵️ Скаут")],
        [KeyboardButton(text="📞 Продажник")],
        [KeyboardButton(text="👑 Менеджер")]
    ],
    resize_keyboard=True
)

# ========== СОСТОЯНИЯ ==========
class AddChannel(StatesGroup):
    link = State()
    topic = State()
    subscribers = State()
    avg_views = State()
    er = State()
    price = State()
    comment = State()

class AddLead(StatesGroup):
    username = State()
    topic = State()
    link = State()
    budget = State()
    comment = State()

class CloseDeal(StatesGroup):
    lead_id = State()
    channel_id = State()

# ========== ПРИВЕТСТВЕННЫЕ СООБЩЕНИЯ ==========
def get_welcome_message(role):
    if role == "scout":
        return (
            f"🕵️ **Приветствую тебя, Скаут!**\n\n"
            f"Добро пожаловать в команду! 🎉\n\n"
            f"📌 **Вот группа для скаутов:**\n"
            f"[👉🏻 Вступить в группу скаутов](https://t.me/+______) ⬅️\n\n"
            f"📚 **Здесь ты найдёшь:**\n"
            f"• Гайды по поиску каналов\n"
            f"• Разборы ошибок и находок\n"
            f"• Эфиры с топ-скаутами\n\n"
            f"💡 **Что делать дальше?**\n"
            f"1️⃣ Изучи гайды в группе\n"
            f"2️⃣ Начни добавлять каналы через бота\n"
            f"3️⃣ Зарабатывай 15% с каждой продажи твоего канала"
        )
    elif role == "seller":
        return (
            f"📞 **Приветствую тебя, Продажник!**\n\n"
            f"Добро пожаловать в команду! 🎉\n\n"
            f"📌 **Вот группа для продажников:**\n"
            f"[👉🏻 Вступить в группу продажников](https://t.me/+______) ⬅️\n\n"
            f"📚 **Здесь ты найдёшь:**\n"
            f"• Скрипты продаж\n"
            f"• Разборы возражений\n"
            f"• Эфиры с топ-продажниками\n\n"
            f"💡 **Что делать дальше?**\n"
            f"1️⃣ Изучи скрипты в группе\n"
            f"2️⃣ Бери лидов через бота\n"
            f"3️⃣ Зарабатывай 35% с каждой сделки"
        )
    elif role == "manager":
        return (
            f"👑 **Приветствую тебя, Менеджер!**\n\n"
            f"Добро пожаловать в команду! 🎉\n\n"
            f"📌 **Вот группа для менеджеров:**\n"
            f"[👉🏻 Вступить в группу менеджеров](https://t.me/+______) ⬅️\n\n"
            f"📚 **Здесь ты найдёшь:**\n"
            f"• Гайды по привлечению клиентов\n"
            f"• Разборы ошибок\n"
            f"• Эфиры с топ-менеджерами\n\n"
            f"💡 **Что делать дальше?**\n"
            f"1️⃣ Изучи гайды в группе\n"
            f"2️⃣ Добавляй клиентов через бота\n"
            f"3️⃣ Зарабатывай 15% с каждой сделки твоего клиента"
        )
    return "✅ Добро пожаловать! Нажми /start чтобы начать работу."

# ========== ФОНОВАЯ ПРОВЕРКА ЛИДОВ ==========
async def check_expired_leads():
    """Проверяет лиды каждые 30 минут"""
    while True:
        await asyncio.sleep(1800)  # 30 минут
        now = datetime.now()
        
        for lead in leads:
            if lead['status'] == "taken" and lead['taken_at']:
                taken_time = datetime.fromisoformat(lead['taken_at'])
                hours_passed = (now - taken_time).total_seconds() / 3600
                
                # Если прошло 23 часа (за 1 час до окончания) — уведомление о продлении
                if 23 <= hours_passed < 24:
                    if not lead.get('extend_notified', False):
                        lead['extend_notified'] = True
                        kb = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="✅ Продлить на 24 часа", callback_data=f"extend_lead_{lead['id']}"),
                             InlineKeyboardButton(text="❌ Не продлевать", callback_data=f"no_extend_lead_{lead['id']}")]
                        ])
                        try:
                            await bot.send_message(
                                lead['seller_id'],
                                f"⚠️ **Внимание!**\n\n"
                                f"Через 1 час лид @{lead['username']} станет доступен другим продажникам!\n\n"
                                f"Хочешь продлить время работы с ним ещё на 24 часа?",
                                reply_markup=kb,
                                parse_mode="Markdown"
                            )
                        except:
                            pass
                
                # Если прошло больше 24 часов — освобождаем
                elif hours_passed >= 24:
                    old_seller = lead['seller_id']
                    lead['status'] = "available"
                    lead['seller_id'] = None
                    lead['taken_at'] = None
                    lead['taken_by'] = None
                    lead['extend_notified'] = False
                    
                    try:
                        await bot.send_message(old_seller, f"⚠️ **Лид @{lead['username']} освобождён!**\nТы не закрыл сделку за 24 часа.", parse_mode="Markdown")
                    except:
                        pass
                    
                    for uid, role in approved_users.items():
                        if role == "seller":
                            try:
                                await bot.send_message(uid, f"🆕 **Лид @{lead['username']} снова доступен!**\n💰 Бюджет: {lead['budget']:,}₽", parse_mode="Markdown")
                            except:
                                pass
                
                # Если прошло больше 1 часа, но меньше 24 — убираем приоритет
                elif hours_passed >= 1:
                    if lead.get('taken_by') == lead['seller_id']:
                        lead['taken_by'] = None
# ========== СТАРТ ==========
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id

    if user_id in ADMIN_IDS and user_id not in approved_users:
        approved_users[user_id] = "admin"
        await message.answer("👑 **Администратор**\n\nДобро пожаловать!", parse_mode="Markdown", reply_markup=get_main_menu("admin"))
        return

    if user_id in approved_users:
        role = approved_users[user_id]
        await message.answer(f"👋 С возвращением, {message.from_user.full_name}!", reply_markup=get_main_menu(role))
    elif user_id in pending_users:
        await message.answer("⏳ Твоя заявка на рассмотрении")
    else:
        await message.answer("🌟 **Добро пожаловать!**\n\nВыбери роль:", parse_mode="Markdown", reply_markup=role_kb)

# ========== ВЫБОР РОЛИ ==========
@dp.message(F.text.in_(["🕵️ Скаут", "📞 Продажник", "👑 Менеджер"]))
async def role_selected(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id

    if user_id in approved_users or user_id in pending_users:
        await message.answer("❌ Ты уже зарегистрирован или отправил заявку")
        return

    role_map = {"🕵️ Скаут": "scout", "📞 Продажник": "seller", "👑 Менеджер": "manager"}
    role = role_map[message.text]

    pending_users[user_id] = {"name": message.from_user.full_name, "role": role}

    for admin_id in ADMIN_IDS:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Принять", callback_data=f"approve_role_{user_id}"),
             InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_role_{user_id}")]
        ])
        await bot.send_message(admin_id, f"📋 Новая заявка!\n👤 {message.from_user.full_name}\n🎭 {message.text}", reply_markup=kb)

    await message.answer("✅ **Заявка отправлена!**\n\nОжидай подтверждения.", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())

# ========== АДМИН ==========
@dp.callback_query(lambda c: c.data.startswith('approve_role_'))
async def approve_role(callback: types.CallbackQuery):
    user_id = int(callback.data.split('_')[2])
    user_data = pending_users.pop(user_id, None)
    if not user_data:
        await callback.answer("Заявка не найдена")
        return
    
    approved_users[user_id] = user_data["role"]
    await callback.message.edit_text(f"✅ {user_data['name']} принят как {user_data['role']}")
    
    welcome_text = get_welcome_message(user_data["role"])
    await bot.send_message(user_id, welcome_text, parse_mode="Markdown", reply_markup=get_main_menu(user_data["role"]))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith('reject_role_'))
async def reject_role(callback: types.CallbackQuery):
    user_id = int(callback.data.split('_')[2])
    user_data = pending_users.pop(user_id, None)
    await callback.message.edit_text(f"❌ {user_data['name']} отклонён")
    await bot.send_message(user_id, "❌ **Заявка отклонена**")
    await callback.answer()

@dp.message(F.text == "👥 Заявки на роли")
async def show_pending_roles(message: types.Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in ADMIN_IDS:
        return
    if not pending_users:
        await message.answer("📭 Нет заявок")
        return
    for user_id, data in pending_users.items():
        profile_link = f"tg://user?id={user_id}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👤 Открыть профиль", url=profile_link)],
            [InlineKeyboardButton(text="✅ Принять", callback_data=f"approve_role_{user_id}"),
             InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_role_{user_id}")]
        ])
        await message.answer(
            f"📋 **Новая заявка!**\n\n"
            f"👤 **Имя:** {data['name']}\n"
            f"🎭 **Роль:** {data['role']}\n"
            f"🆔 **ID:** `{user_id}`",
            reply_markup=kb,
            parse_mode="Markdown"
        )
# ========== ПРОДЛЕНИЕ ЛИДА ==========
@dp.callback_query(lambda c: c.data.startswith('extend_lead_'))
async def extend_lead(callback: types.CallbackQuery):
    lead_id = int(callback.data.split('_')[2])
    lead = next((l for l in leads if l['id'] == lead_id), None)
    
    if not lead:
        await callback.answer("❌ Лид не найден!", show_alert=True)
        return
    
    # Продлеваем время на 24 часа
    lead['taken_at'] = datetime.now().isoformat()
    lead['extend_notified'] = False
    
    await callback.message.edit_text(
        f"✅ **Лид @{lead['username']} продлён ещё на 24 часа!**\n\n"
        f"Теперь у тебя есть дополнительное время для закрытия сделки.\n"
        f"💰 Бюджет: {lead['budget']:,}₽",
        parse_mode="Markdown"
    )
    await callback.answer()


# ========== СКАУТ ==========
@dp.message(F.text == "📢 Добавить канал")
async def add_channel_start(message: types.Message, state: FSMContext):
    if approved_users.get(message.from_user.id) != "scout":
        await message.answer("⛔ Нет доступа")
        return
    await state.set_state(AddChannel.link)
    await message.answer("🔗 **Ссылка на канал**\nНапример: @durov или https://t.me/durov\n\n_можно отменить — нажми другую кнопку_", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())

@dp.message(AddChannel.link)
async def add_channel_link(message: types.Message, state: FSMContext):
    link = message.text.strip()
    if not (link.startswith("@") or link.startswith("https://t.me/")):
        await message.answer("❌ Ошибка! Ссылка должна быть @username или https://t.me/username\nПопробуй ещё раз:")
        return
    await state.update_data(link=link)
    await state.set_state(AddChannel.topic)
    await message.answer("📊 **Тематика канала**\nНапример: Криптовалюты, Бизнес, Юмор", parse_mode="Markdown")

@dp.message(AddChannel.topic)
async def add_channel_topic(message: types.Message, state: FSMContext):
    if len(message.text.strip()) < 3:
        await message.answer("❌ Слишком коротко. Попробуй ещё раз:")
        return
    await state.update_data(topic=message.text.strip())
    await state.set_state(AddChannel.subscribers)
    await message.answer("👥 **Количество подписчиков**\nТолько число, например: 15000", parse_mode="Markdown")

@dp.message(AddChannel.subscribers)
async def add_channel_subs(message: types.Message, state: FSMContext):
    try:
        await state.update_data(subscribers=int(message.text.strip()))
        await state.set_state(AddChannel.avg_views)
        await message.answer("👁 **Средние просмотры**\nТолько число, например: 3000", parse_mode="Markdown")
    except:
        await message.answer("❌ Введи число!")

@dp.message(AddChannel.avg_views)
async def add_channel_views(message: types.Message, state: FSMContext):
    try:
        await state.update_data(avg_views=int(message.text.strip()))
        await state.set_state(AddChannel.er)
        await message.answer("📈 **ER (вовлечённость)**\nПроцент, например: 5.2", parse_mode="Markdown")
    except:
        await message.answer("❌ Введи число!")

@dp.message(AddChannel.er)
async def add_channel_er(message: types.Message, state: FSMContext):
    try:
        await state.update_data(er=float(message.text.strip().replace(',', '.')))
        await state.set_state(AddChannel.price)
        await message.answer("💰 **Цена рекламы (₽)**\nТолько число, например: 1500", parse_mode="Markdown")
    except:
        await message.answer("❌ Введи число!")

@dp.message(AddChannel.price)
async def add_channel_price(message: types.Message, state: FSMContext):
    try:
        await state.update_data(price=int(message.text.strip()))
        await state.set_state(AddChannel.comment)
        await message.answer("📝 **Комментарий к каналу**\n(можно пропустить, напиши «пропустить»)", parse_mode="Markdown")
    except:
        await message.answer("❌ Введи число!")

@dp.message(AddChannel.comment)
async def add_channel_comment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id

    # Проверка на дубликат канала
    for scout_id, channels in user_channels.items():
        for ch in channels:
            if ch['link'] == data['link']:
                await message.answer(
                    f"❌ **Ошибка!**\n\nКанал с такой ссылкой **{data['link']}** уже существует!\n\n📢 Тема: {ch['topic']}\n👤 Добавил скаут ID: {scout_id}",
                    parse_mode="Markdown",
                    reply_markup=get_main_menu("scout")
                )
                await state.clear()
                return

    comment = message.text.strip()
    if comment.lower() in ["пропустить", "-", "skip"]:
        comment = ""

    if user_id not in user_channels:
        user_channels[user_id] = []

    channel = {
        "link": data['link'],
        "topic": data['topic'],
        "subscribers": data['subscribers'],
        "avg_views": data['avg_views'],
        "er": data['er'],
        "price": data['price'],
        "comment": comment,
        "status": "pending"
    }
    user_channels[user_id].append(channel)
    channels_for_approve.append({"id": len(channels_for_approve)+1, "data": channel, "scout_id": user_id})

    await state.clear()

    await message.answer(
        f"✅ **Канал добавлен!**\n\n"
        f"📢 **Название:** {data['topic']}\n"
        f"🔗 **Ссылка:** {data['link']}\n"
        f"👥 **Подписчики:** {data['subscribers']:,}\n"
        f"👁 **Просмотры:** {data['avg_views']:,}\n"
        f"📈 **ER:** {data['er']}%\n"
        f"💰 **Цена:** {data['price']:,}₽\n"
        f"📝 **Комментарий:** {comment or '—'}\n\n"
        f"🟡 **Статус:** На проверке",
        parse_mode="Markdown",
        reply_markup=get_main_menu("scout")
    )

    for admin_id in ADMIN_IDS:
        await bot.send_message(admin_id, f"📢 Новый канал!\n🔗 {data['link']}\n📊 {data['topic']}\n💰 {data['price']}₽")

@dp.message(F.text == "📋 Мои каналы")
async def my_channels(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    channels = user_channels.get(user_id, [])
    if not channels:
        await message.answer("📭 У тебя пока нет каналов", reply_markup=get_main_menu("scout"))
        return
    text = "📋 **Твои каналы**\n\n"
    for ch in channels:
        status = "🟡 На проверке" if ch['status'] == 'pending' else "🟢 Одобрен"
        text += f"• **{ch['topic']}**\n"
        text += f"   🔗 {ch['link']}\n"
        text += f"   👥 {ch['subscribers']} подп.\n"
        text += f"   📈 ER: {ch['er']}%\n"
        text += f"   💰 {ch['price']}₽\n"
        text += f"   📊 Статус: {status}\n\n"
    await message.answer(text, parse_mode="Markdown", reply_markup=get_main_menu("scout"))

# ========== МЕНЕДЖЕР ==========
@dp.message(F.text == "➕ Новый клиент")
async def new_lead_start(message: types.Message, state: FSMContext):
    if approved_users.get(message.from_user.id) != "manager":
        await message.answer("⛔ Нет доступа")
        return
    await state.set_state(AddLead.username)
    await message.answer("👤 **Username клиента**\nНапример: @durov\n\n_можно отменить — нажми другую кнопку_", parse_mode="Markdown", reply_markup=ReplyKeyboardRemove())

@dp.message(AddLead.username)
async def new_lead_username(message: types.Message, state: FSMContext):
    await state.update_data(username=message.text.strip().replace("@", ""))
    await state.set_state(AddLead.topic)
    await message.answer("📊 **Что интересует клиента?** (тематика)\nНапример: Крипта, Бизнес, Юмор", parse_mode="Markdown")

@dp.message(AddLead.topic)
async def new_lead_topic(message: types.Message, state: FSMContext):
    if len(message.text.strip()) < 3:
        await message.answer("❌ Слишком коротко. Попробуй ещё раз:")
        return
    await state.update_data(topic=message.text.strip())
    await state.set_state(AddLead.link)
    await message.answer("🔗 **Ссылка на канал клиента**\nНапример: @durov или https://t.me/durov", parse_mode="Markdown")

@dp.message(AddLead.link)
async def new_lead_link(message: types.Message, state: FSMContext):
    await state.update_data(link=message.text.strip())
    await state.set_state(AddLead.budget)
    await message.answer("💰 **Бюджет клиента (₽)**\nТолько число, например: 50000", parse_mode="Markdown")

@dp.message(AddLead.budget)
async def new_lead_budget(message: types.Message, state: FSMContext):
    try:
        await state.update_data(budget=int(message.text.strip()))
        await state.set_state(AddLead.comment)
        await message.answer("📝 **Комментарий**\n(можно пропустить, напиши «пропустить»)", parse_mode="Markdown")
    except:
        await message.answer("❌ Введи число!")

@dp.message(AddLead.comment)
async def new_lead_comment(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id

    comment = message.text.strip()
    if comment.lower() in ["пропустить", "-", "skip"]:
        comment = ""

    # Проверка на дубликат клиента
    existing_lead = next((l for l in leads if l['username'] == data['username']), None)
    if existing_lead:
        await message.answer(
            f"❌ **Ошибка!**\n\nКлиент @{data['username']} уже существует!\n\n📊 Статус: {existing_lead['status']}\n👤 Менеджер ID: {existing_lead['manager_id']}",
            parse_mode="Markdown",
            reply_markup=get_main_menu("manager")
        )
        await state.clear()
        return

    lead = {
        "id": len(leads) + 1,
        "username": data['username'],
        "topic": data['topic'],
        "link": data['link'],
        "budget": data['budget'],
        "comment": comment,
        "manager_id": user_id,
        "seller_id": None,
        "status": "available",
        "taken_at": None,
        "taken_by": None,
        "extend_notified": False
    }
    leads.append(lead)

    await state.clear()

    await message.answer(
        f"✅ **Клиент добавлен!**\n\n"
        f"👤 @{data['username']}\n"
        f"📊 {data['topic']}\n"
        f"🔗 {data['link']}\n"
        f"💰 Бюджет: {data['budget']:,}₽\n"
        f"📝 {comment or '—'}\n\n"
        f"🔒 Клиент навсегда закреплён за тобой!",
        parse_mode="Markdown",
        reply_markup=get_main_menu("manager")
    )

    for uid, role in approved_users.items():
        if role == "seller":
            await bot.send_message(uid, f"🆕 **Новый клиент!**\n👤 @{data['username']}\n💰 {data['budget']:,}₽")

@dp.message(F.text == "📋 Мои клиенты")
async def my_clients(message: types.Message, state: FSMContext):
    await state.clear()
    if approved_users.get(message.from_user.id) != "manager":
        return
    my = [l for l in leads if l.get('manager_id') == message.from_user.id]
    if not my:
        await message.answer("📭 У тебя нет клиентов", reply_markup=get_main_menu("manager"))
        return
    text = "📋 **Твои клиенты**\n\n"
    for l in my:
        if l['status'] == "available":
            status = "🟢 Доступен"
        elif l['status'] == "taken":
            status = "🔵 В работе у продажника"
        else:
            status = "✅ Сделка закрыта"
        text += f"👤 @{l['username']}\n   📊 {l['topic']}\n   💰 {l['budget']}₽ | {status}\n\n"
    await message.answer(text, parse_mode="Markdown", reply_markup=get_main_menu("manager"))

# ========== ПРОДАЖНИК ==========
@dp.message(F.text == "💰 База каналов")
async def show_channels(message: types.Message, state: FSMContext):
    await state.clear()
    if approved_users.get(message.from_user.id) != "seller":
        return
    if not approved_channels:
        await message.answer("📭 База каналов пуста", reply_markup=get_main_menu("seller"))
        return
    text = "💰 **База каналов**\n\n"
    for ch in approved_channels:
        text += f"📢 **{ch['data']['topic']}**\n"
        text += f"   👥 {ch['data']['subscribers']} подп.\n"
        text += f"   👁 {ch['data']['avg_views']} просм.\n"
        text += f"   📈 ER: {ch['data']['er']}%\n"
        text += f"   💰 {ch['data']['price']}₽\n"
        text += f"   🔗 {ch['data']['link']}\n\n"
    await message.answer(text, parse_mode="Markdown", reply_markup=get_main_menu("seller"))

@dp.message(F.text == "🎯 Доступные лиды")
async def available_leads(message: types.Message, state: FSMContext):
    await state.clear()
    if approved_users.get(message.from_user.id) != "seller":
        await message.answer("⛔ Нет доступа")
        return

    available = [l for l in leads if l['status'] == "available"]
    if not available:
        await message.answer("📭 **Нет доступных лидов**", parse_mode="Markdown", reply_markup=get_main_menu("seller"))
        return

    for lead in available:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Взять лида", callback_data=f"take_lead_{lead['id']}"),
             InlineKeyboardButton(text="❌ Не брать", callback_data=f"skip_lead_{lead['id']}")]
        ])
        await message.answer(
            f"🎯 **Клиент #{lead['id']}**\n\n"
            f"👤 @{lead['username']}\n"
            f"📊 {lead['topic']}\n"
            f"🔗 {lead['link']}\n"
            f"💰 Бюджет: {lead['budget']:,}₽\n"
            f"📝 {lead['comment'] or '—'}",
            reply_markup=kb,
            parse_mode="Markdown"
        )

@dp.callback_query(lambda c: c.data.startswith('take_lead_'))
async def take_lead(callback: types.CallbackQuery):
    lead_id = int(callback.data.split('_')[2])
    lead = next((l for l in leads if l['id'] == lead_id), None)

    if not lead:
        await callback.answer("❌ Лид не найден!", show_alert=True)
        return

    # Проверка: если лид уже взят другим, но прошло больше 1 часа — освобождаем
    if lead['status'] == "taken" and lead['taken_at']:
        time_passed = datetime.now() - datetime.fromisoformat(lead['taken_at'])
        if time_passed > timedelta(hours=1):
            lead['status'] = "available"
            lead['seller_id'] = None
            lead['taken_at'] = None
            lead['taken_by'] = None
            try:
                await bot.send_message(lead['seller_id'], f"⚠️ Приоритет на лида @{lead['username']} истёк! Теперь его может взять другой продажник.")
            except:
                pass

    if lead['status'] != "available":
        await callback.answer("❌ Этот лид уже кто-то взял! Подожди 1 час.", show_alert=True)
        return

    lead['status'] = "taken"
    lead['seller_id'] = callback.from_user.id
    lead['taken_at'] = datetime.now().isoformat()
    lead['taken_by'] = callback.from_user.id

    await callback.message.edit_text(
        f"✅ **Лид @{lead['username']} закреплён за тобой!**\n\n"
        f"📊 {lead['topic']}\n"
        f"💰 Бюджет: {lead['budget']:,}₽\n\n"
        f"📈 **Твой процент:** 85%\n"
        f"⏰ **У тебя есть 1 час приоритета!**\n"
        f"⚠️ **Через 24 часа лид станет доступен другим, если не закроешь сделку**\n"
        f"💡 После закрытия сделки ты можешь снова взять этого клиента для повторного сотрудничества",
        parse_mode="Markdown"
    )

    await bot.send_message(lead['manager_id'], f"📞 **Клиент @{lead['username']} взят в работу!**\nПродажник: {callback.from_user.full_name}")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith('skip_lead_'))
async def skip_lead(callback: types.CallbackQuery):
    lead_id = int(callback.data.split('_')[2])
    lead = next((l for l in leads if l['id'] == lead_id), None)

    if not lead:
        await callback.answer("❌ Лид не найден!", show_alert=True)
        return

    if lead['status'] != "available":
        await callback.answer("❌ Лид уже недоступен!", show_alert=True)
        return

    await callback.message.edit_text(f"⏭️ **Лид @{lead['username']} пропущен**", parse_mode="Markdown")
    await callback.answer()

# ========== ПРОДЛЕНИЕ ЛИДА ==========
@dp.callback_query(lambda c: c.data.startswith('extend_lead_'))
async def extend_lead(callback: types.CallbackQuery):
    lead_id = int(callback.data.split('_')[2])
    lead = next((l for l in leads if l['id'] == lead_id), None)
    
    if not lead:
        await callback.answer("❌ Лид не найден!", show_alert=True)
        return
    
    lead['taken_at'] = datetime.now().isoformat()
    lead['extend_notified'] = False
    
    await callback.message.edit_text(
        f"✅ **Лид @{lead['username']} продлён ещё на 24 часа!**\n\n"
        f"Теперь у тебя есть дополнительное время для закрытия сделки.\n"
        f"💰 Бюджет: {lead['budget']:,}₽",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith('no_extend_lead_'))
async def no_extend_lead(callback: types.CallbackQuery):
    lead_id = int(callback.data.split('_')[3])
    lead = next((l for l in leads if l['id'] == lead_id), None)
    
    if not lead:
        await callback.answer("❌ Лид не найден!", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"⏭️ **Лид @{lead['username']} не будет продлён**\n\n"
        f"Через 1 час он станет доступен другим продажникам.",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.message(F.text == "📋 Мои лиды")
async def my_leads(message: types.Message, state: FSMContext):
    await state.clear()
    if approved_users.get(message.from_user.id) != "seller":
        await message.answer("⛔ Нет доступа")
        return

    my_leads_list = [l for l in leads if l.get('seller_id') == message.from_user.id and l['status'] == 'taken']
    if not my_leads_list:
        await message.answer("📭 **У тебя пока нет взятых лидов**", parse_mode="Markdown", reply_markup=get_main_menu("seller"))
        return

    for lead in my_leads_list:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Закрыть сделку", callback_data=f"close_deal_{lead['id']}"),
             InlineKeyboardButton(text="🔄 Передать лида", callback_data=f"transfer_lead_{lead['id']}")]
        ])
        await message.answer(
            f"📋 **Твой лид**\n\n"
            f"👤 @{lead['username']}\n"
            f"📊 {lead['topic']}\n"
            f"🔗 {lead['link']}\n"
            f"💰 Бюджет: {lead['budget']:,}₽",
            reply_markup=kb,
            parse_mode="Markdown"
        )

# ========== ЗАКРЫТИЕ СДЕЛКИ ==========
@dp.callback_query(lambda c: c.data.startswith('close_deal_'))
async def close_deal_start(callback: types.CallbackQuery, state: FSMContext):
    lead_id = int(callback.data.split('_')[2])
    lead = next((l for l in leads if l['id'] == lead_id), None)

    if not lead:
        await callback.answer("❌ Лид не найден!")
        return

    await state.update_data(lead_id=lead_id)
    await state.set_state(CloseDeal.channel_id)

    if not approved_channels:
        await callback.message.answer("❌ Нет доступных каналов для продажи")
        await state.clear()
        return

    text = "💰 **Выбери канал для продажи:**\n\n"
    for ch in approved_channels:
        text += f"📢 **ID {ch['id']}** — {ch['data']['topic']}\n   💰 {ch['data']['price']}₽\n\n"
    text += "📝 **Введи ID канала** (только число)"
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.message(CloseDeal.channel_id)
async def close_deal_channel(message: types.Message, state: FSMContext):
    try:
        channel_id = int(message.text.strip())
    except:
        await message.answer("❌ Введи число — ID канала")
        return

    channel = next((ch for ch in approved_channels if ch['id'] == channel_id), None)
    if not channel:
        await message.answer("❌ Канал с таким ID не найден")
        return

    data = await state.get_data()
    lead_id = data['lead_id']
    lead = next((l for l in leads if l['id'] == lead_id), None)

    if not lead:
        await message.answer("❌ Клиент не найден")
        await state.clear()
        return

    deals.append({
        "lead_id": lead_id,
        "channel_id": channel_id,
        "channel_data": channel['data'],
        "seller_id": message.from_user.id,
        "manager_id": lead['manager_id'],
        "scout_id": channel['data'].get('scout_id'),
        "amount": channel['data']['price'],
        "status": "completed"
    })

    lead['status'] = "closed"

    await message.answer(
        f"✅ **СДЕЛКА ЗАКРЫТА!**\n\n"
        f"👤 Клиент: @{lead['username']}\n"
        f"📢 Канал: {channel['data']['topic']}\n"
        f"💰 Сумма: {channel['data']['price']:,}₽\n\n"
        f"📈 **Распределение:**\n"
        f"• Продажник (85%): {int(channel['data']['price'] * 0.85)}₽\n"
        f"• Скаут (10%): {int(channel['data']['price'] * 0.1)}₽\n"
        f"• Менеджер (5%): {int(channel['data']['price'] * 0.05)}₽\n\n"
        f"🔄 **Хочешь продолжить сотрудничество с @{lead['username']}?**\n"
        f"Напиши «да», если клиент хочет новый канал",
        parse_mode="Markdown"
    )
    
    # Ждём ответа про повторное сотрудничество
    @dp.message()
    async def wait_for_repeat(response: types.Message):
        if response.text.lower() in ["да", "конечно", "давай", "yes", "+"]:
            lead['status'] = "available"
            lead['seller_id'] = None
            lead['taken_at'] = None
            lead['taken_by'] = None
            await response.answer(f"🔄 **Лид @{lead['username']} снова доступен для новой сделки!**\nТы можешь взять его снова.", parse_mode="Markdown")
        else:
            await response.answer(f"✅ Понял. Лид @{lead['username']} закрыт. Если захочешь вернуться — пиши.", parse_mode="Markdown")
    # ========== КОНЕЦ НОВОГО КОДА ==========

    await bot.send_message(lead['manager_id'], f"💰 **Сделка закрыта!**\nКлиент @{lead['username']} купил рекламу на {channel['data']['price']}₽")
    if channel['data'].get('scout_id'):
        await bot.send_message(channel['data']['scout_id'], f"💰 **Твой канал продан!**\n📢 {channel['data']['topic']}\n💰 {channel['data']['price']}₽")
    
    await state.clear()
    await message.answer("✅ Готово!", reply_markup=get_main_menu("seller"))
# ========== ПЕРЕДАЧА ЛИДА ==========
@dp.callback_query(lambda c: c.data.startswith('transfer_lead_'))
async def transfer_lead(callback: types.CallbackQuery):
    lead_id = int(callback.data.split('_')[2])
    lead = next((l for l in leads if l['id'] == lead_id), None)

    if not lead:
        await callback.answer("❌ Лид не найден!")
        return

    lead['status'] = "available"
    lead['seller_id'] = None
    lead['taken_at'] = None
    lead['taken_by'] = None

    await callback.message.edit_text(f"🔄 **Лид @{lead['username']} передан обратно в общий доступ**", parse_mode="Markdown")
    await bot.send_message(lead['manager_id'], f"🔄 **Клиент @{lead['username']} возвращён в общий доступ**")
    await callback.answer()

# ========== АДМИН: ПРОВЕРКА КАНАЛОВ ==========
@dp.message(F.text == "📢 Каналы на проверке")
async def admin_channels(message: types.Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in ADMIN_IDS:
        return
    if not channels_for_approve:
        await message.answer("📭 Нет каналов на проверке")
        return
    for ch in channels_for_approve:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_channel_{ch['id']}"),
             InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_channel_{ch['id']}")]
        ])
        await message.answer(
            f"📢 **Канал на проверке**\n\n"
            f"🔗 {ch['data']['link']}\n"
            f"📊 {ch['data']['topic']}\n"
            f"👥 {ch['data']['subscribers']} подп.\n"
            f"👁 {ch['data']['avg_views']} просм.\n"
            f"📈 ER: {ch['data']['er']}%\n"
            f"💰 {ch['data']['price']}₽",
            reply_markup=kb,
            parse_mode="Markdown"
        )

@dp.callback_query(lambda c: c.data.startswith('approve_channel_'))
async def approve_channel(callback: types.CallbackQuery):
    channel_id = int(callback.data.split('_')[2])
    channel = next((ch for ch in channels_for_approve if ch['id'] == channel_id), None)
    if not channel:
        await callback.answer("Канал не найден")
        return

    for ch in user_channels.get(channel['scout_id'], []):
        if ch['link'] == channel['data']['link']:
            ch['status'] = 'approved'

    approved_channels.append({
        "id": len(approved_channels) + 1,
        "data": channel['data'],
        "scout_id": channel['scout_id']
    })

    channels_for_approve.remove(channel)

    await callback.message.edit_text(f"✅ **Канал #{channel_id} одобрен!**\n\n📢 {channel['data']['topic']}\n💰 {channel['data']['price']}₽")

    await bot.send_message(
        channel['scout_id'],
        f"✅ **Твой канал одобрен!**\n\n"
        f"📢 {channel['data']['topic']}\n"
        f"💰 {channel['data']['price']}₽\n\n"
        f"Теперь он появится в базе продажников.",
        parse_mode="Markdown"
    )

    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith('reject_channel_'))
async def reject_channel(callback: types.CallbackQuery):
    channel_id = int(callback.data.split('_')[2])
    channel = next((ch for ch in channels_for_approve if ch['id'] == channel_id), None)
    if not channel:
        await callback.answer("Канал не найден")
        return
    channels_for_approve.remove(channel)
    await callback.message.edit_text(f"❌ Канал отклонён")
    await callback.answer()

# ========== СТАТИСТИКА ==========
@dp.message(F.text == "📊 Статистика")
async def admin_stats(message: types.Message, state: FSMContext):
    await state.clear()
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer(
        f"📊 **Статистика**\n\n"
        f"👥 Пользователей: {len(approved_users)}\n"
        f"📢 Каналов в базе: {len(approved_channels)}\n"
        f"📋 Всего лидов: {len(leads)}\n"
        f"• Доступно: {len([l for l in leads if l['status'] == 'available'])}\n"
        f"• В работе: {len([l for l in leads if l['status'] == 'taken'])}\n"
        f"• Закрыто: {len([l for l in leads if l['status'] == 'closed'])}\n"
        f"💰 Выручка: {sum([d['amount'] for d in deals]):,}₽",
        parse_mode="Markdown"
    )

# ========== ПРОФИЛЬ ==========
@dp.message(F.text == "👤 Профиль")
async def profile(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id

    if user_id in ADMIN_IDS:
        await message.answer(
            f"👑 **Админ**\n\n"
            f"📊 Заявок на роли: {len(pending_users)}\n"
            f"📢 Каналов на проверке: {len(channels_for_approve)}",
            parse_mode="Markdown",
            reply_markup=get_main_menu("admin")
        )
        return

    if user_id not in approved_users:
        await message.answer("❌ Ты не зарегистрирован")
        return

    role = approved_users[user_id]

    if role == "scout":
        channels = user_channels.get(user_id, [])
        earnings = 0
        for deal in deals:
            if deal.get('scout_id') == user_id:
                earnings += int(deal['amount'] * 0.1)

        text = f"👤 **Скаут**\n\n"
        text += f"📊 **Статистика:**\n"
        text += f"• Добавлено каналов: {len(channels)}\n"
        text += f"• Одобрено: {len([c for c in channels if c['status'] == 'approved'])}\n"
        text += f"💰 **Заработано:** {earnings:,}₽\n\n"
        text += f"🔒 **Твои закреплённые каналы:**\n"

        for ch in channels:
            status_emoji = "🟢" if ch['status'] == 'approved' else "🟡"
            text += f"   {status_emoji} {ch['topic']} — 💰 {ch['price']}₽\n"
        if not channels:
            text += f"   ❌ Нет закреплённых каналов\n"

        await message.answer(text, parse_mode="Markdown", reply_markup=get_main_menu("scout"))

    elif role == "seller":
        my_closed_deals = [d for d in deals if d.get('seller_id') == user_id]
        earnings = 0
        for deal in my_closed_deals:
            earnings += int(deal['amount'] * 0.85)

        text = f"👤 **Продажник**\n\n"
        text += f"📊 **Статистика:**\n"
        text += f"• Закрыто сделок: {len(my_closed_deals)}\n"
        text += f"💰 **Заработано:** {earnings:,}₽\n\n"
        text += f"🔒 **У тебя нет закреплённых лидов**\n"
        text += f"⚠️ Ты получаешь процент ТОЛЬКО за конкретную закрытую сделку"

        await message.answer(text, parse_mode="Markdown", reply_markup=get_main_menu("seller"))

    elif role == "manager":
        my_clients = [l for l in leads if l.get('manager_id') == user_id]
        closed = [l for l in my_clients if l.get('status') == 'closed']
        earnings = 0
        for deal in deals:
            if deal.get('manager_id') == user_id:
                earnings += int(deal['amount'] * 0.05)

        text = f"👤 **Менеджер**\n\n"
        text += f"📊 **Статистика:**\n"
        text += f"• Приведено клиентов: {len(my_clients)}\n"
        text += f"• Закрыто сделок: {len(closed)}\n"
        text += f"💰 **Заработано:** {earnings:,}₽\n\n"
        text += f"🔒 **Твои закреплённые клиенты:**\n"

        for client in my_clients:
            status_emoji = "🟢" if client['status'] == 'available' else "🔵" if client['status'] == 'taken' else "✅"
            text += f"   {status_emoji} @{client['username']} — 📊 {client['topic']} | 💰 {client['budget']:,}₽\n"
        if not my_clients:
            text += f"   ❌ Нет закреплённых клиентов\n"

        await message.answer(text, parse_mode="Markdown", reply_markup=get_main_menu("manager"))

# ========== ОТМЕНА ДЕЙСТВИЯ ==========
@dp.message(F.text.in_([
    "📢 Добавить канал", "📋 Мои каналы", "👤 Профиль",
    "💰 База каналов", "🎯 Доступные лиды", "📋 Мои лиды",
    "➕ Новый клиент", "📋 Мои клиенты",
    "👥 Заявки на роли", "📢 Каналы на проверке", "📊 Статистика"
]))
async def cancel_on_menu_button(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
        await message.answer("❌ **Действие отменено**", parse_mode="Markdown")
    user = approved_users.get(message.from_user.id)
    if user:
        await message.answer("✅ Готово!", reply_markup=get_main_menu(user))
    else:
        await message.answer("Напиши /start", reply_markup=role_kb)

# ========== ЗАПУСК ==========
async def main():
    asyncio.create_task(check_expired_leads())
    print("✅ Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
