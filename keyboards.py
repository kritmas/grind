from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


def get_main_menu(role):
    if role == "scout":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="➕ Добавить канал")],
                [KeyboardButton(text="📋 Мои каналы")],
                [KeyboardButton(text="👤 Профиль")],
            ],
            resize_keyboard=True,
        )
    if role == "seller":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📋 Каналы для продажи")],
                [KeyboardButton(text="🔍 Поиск по нише")],
                [KeyboardButton(text="📞 Мои клиенты")],
                [KeyboardButton(text="👤 Профиль")],
            ],
            resize_keyboard=True,
        )
    if role == "manager":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="➕ Новый клиент")],
                [KeyboardButton(text="📋 Мои клиенты")],
                [KeyboardButton(text="👤 Профиль")],
            ],
            resize_keyboard=True,
        )
    if role == "admin":
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="👥 Заявки")],
                [KeyboardButton(text="📊 Аналитика")],
                [KeyboardButton(text="📂 Все каналы")],
                [KeyboardButton(text="📋 Все клиенты")],
                [KeyboardButton(text="💰 Финансы")],
                [KeyboardButton(text="⚠️ Жалобы")],
                [KeyboardButton(text="👤 Профиль")],
            ],
            resize_keyboard=True,
        )
    return None


role_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🕵️ Скаут")],
        [KeyboardButton(text="📞 Продажник")],
        [KeyboardButton(text="👑 Менеджер")],
    ],
    resize_keyboard=True,
)

topic_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛍 Товарка")],
        [KeyboardButton(text="🔥 Виралка")],
        [KeyboardButton(text="✏️ Своя тема")],
    ],
    resize_keyboard=True,
)


def channel_card_button(ch, prefix="ch_view"):
    price = f"{ch['price_min'] or ch['price']}–{ch['price_max'] or ch['price']}₽"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"📢 {ch['topic']} | {price}",
                    callback_data=f"{prefix}_{ch['id']}",
                )
            ]
        ]
    )


def channel_admin_buttons(channel_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Одобрить", callback_data=f"ch_approve_{channel_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить", callback_data=f"ch_reject_{channel_id}"
                ),
            ]
        ]
    )


def take_client_buttons(client_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📞 Взять клиента", callback_data=f"take_client_{client_id}"
                )
            ]
        ]
    )


def client_work_buttons(client_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Продать канал",
                    callback_data=f"select_channel_for_{client_id}",
                ),
                InlineKeyboardButton(
                    text="⚠️ Проблема", callback_data=f"problem_{client_id}"
                ),
            ]
        ]
    )


def problem_type_buttons(client_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⏳ Продлить срок (клиент пропал)",
                    callback_data=f"prob_extend_{client_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Передать другому",
                    callback_data=f"prob_transfer_{client_id}",
                )
            ],
        ]
    )


def sell_channel_buttons(channel_id, client_id, price):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"💰 Продать за {price}₽",
                    callback_data=f"sell_{channel_id}_{client_id}",
                )
            ]
        ]
    )


def resolve_complaint_buttons(complaint_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Принять (продлить)",
                    callback_data=f"resolve_accept_{complaint_id}",
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"resolve_reject_{complaint_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Передать клиента",
                    callback_data=f"resolve_transfer_{complaint_id}",
                )
            ],
        ]
    )


def mark_ad_posted_button(deal_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📣 Реклама вышла",
                    callback_data=f"ad_posted_{deal_id}",
                )
            ]
        ]
    )


def scout_check_button(deal_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Отчитаться по рекламе",
                    callback_data=f"scout_check_{deal_id}",
                )
            ]
        ]
    )
