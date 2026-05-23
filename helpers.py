from database import SCOUT_PERCENT, MANAGER_PERCENT, SELLER_PERCENT


def calc_commissions(amount: int) -> dict:
    scout = int(amount * SCOUT_PERCENT)
    manager = int(amount * MANAGER_PERCENT)
    seller = int(amount * SELLER_PERCENT)
    return {
        "scout": scout,
        "manager": manager,
        "seller": seller,
        "scout_pct": int(SCOUT_PERCENT * 100),
        "manager_pct": int(MANAGER_PERCENT * 100),
        "seller_pct": int(SELLER_PERCENT * 100),
    }


def format_price_range(ch) -> str:
    pmin = ch["price_min"] if ch["price_min"] is not None else ch["price"]
    pmax = ch["price_max"] if ch["price_max"] is not None else ch["price"]
    if pmin == pmax:
        return f"{pmin}₽"
    return f"{pmin}–{pmax}₽"


def channel_status_label(status: str, sold: int) -> str:
    if sold:
        return "✅ Продан"
    if status == "checking":
        return "🟡 На проверке"
    if status == "approved":
        return "🟢 В продаже"
    if status == "rejected":
        return "🔴 Отклонён"
    return status


def deal_breakdown_text(amount: int, role: str, commissions: dict) -> str:
    pct_key = f"{role}_pct"
    lines = [
        f"💰 Сумма сделки: {amount}₽",
        f"📊 Ваша доля ({commissions[pct_key]}%): {commissions[role]}₽",
        "",
        "Распределение:",
        f"• Продажник: {commissions['seller']}₽ ({commissions['seller_pct']}%)",
        f"• Скаут: {commissions['scout']}₽ ({commissions['scout_pct']}%)",
        f"• Менеджер: {commissions['manager']}₽ ({commissions['manager_pct']}%)",
        "",
        "Так держать! Смотрите статистику в профиле 👤",
    ]
    return "\n".join(lines)
