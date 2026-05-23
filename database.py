import sqlite3
from datetime import datetime

DB_PATH = "agency_bot.db"

# Проценты с сделки
SCOUT_PERCENT = 0.10
MANAGER_PERCENT = 0.05
SELLER_PERCENT = 0.15


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _add_column(cur, table, column, col_type, default=None):
    try:
        sql = f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
        if default is not None:
            sql += f" DEFAULT {default}"
        cur.execute(sql)
    except sqlite3.OperationalError:
        pass


def migrate_db(conn):
    cur = conn.cursor()
    _add_column(cur, "channels", "price_min", "INTEGER")
    _add_column(cur, "channels", "price_max", "INTEGER")
    _add_column(cur, "channels", "assigned_seller", "INTEGER")
    _add_column(cur, "channels", "approved_at", "TEXT")
    _add_column(cur, "clients", "assigned_at", "TEXT")
    _add_column(cur, "clients", "deadline_at", "TEXT")
    _add_column(cur, "deals", "ad_posted_at", "TEXT")
    _add_column(cur, "deals", "scout_check_due", "TEXT")
    _add_column(cur, "deals", "scout_checked", "INTEGER", "0")
    _add_column(cur, "deals", "actual_views", "INTEGER")
    _add_column(cur, "deals", "cost_per_view", "REAL")
    _add_column(cur, "complaints", "complaint_type", "TEXT", "'extend'")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            role TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            total_earned INTEGER DEFAULT 0,
            total_deals INTEGER DEFAULT 0
        )
    """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link TEXT,
            topic TEXT,
            subscribers INTEGER,
            avg_views INTEGER,
            price INTEGER,
            price_min INTEGER,
            price_max INTEGER,
            er REAL,
            comment TEXT,
            added_by INTEGER,
            status TEXT DEFAULT 'checking',
            sold INTEGER DEFAULT 0,
            sold_to INTEGER,
            assigned_seller INTEGER,
            approved_at TEXT,
            created_at TEXT
        )
    """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            topic TEXT,
            budget INTEGER,
            comment TEXT,
            created_by INTEGER,
            assigned_to INTEGER,
            status TEXT DEFAULT 'new',
            channel_id INTEGER,
            deal_closed INTEGER DEFAULT 0,
            deal_amount INTEGER,
            created_at TEXT,
            closed_at TEXT,
            last_activity TEXT,
            assigned_at TEXT,
            deadline_at TEXT
        )
    """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            channel_id INTEGER,
            seller_id INTEGER,
            scout_id INTEGER,
            manager_id INTEGER,
            amount INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            completed_at TEXT,
            ad_posted_at TEXT,
            scout_check_due TEXT,
            scout_checked INTEGER DEFAULT 0,
            actual_views INTEGER,
            cost_per_view REAL
        )
    """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            seller_id INTEGER,
            reason TEXT,
            complaint_type TEXT DEFAULT 'extend',
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            resolved_at TEXT,
            admin_comment TEXT
        )
    """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            created_at TEXT
        )
    """
    )

    migrate_db(conn)
    conn.commit()
    conn.close()
    print("✅ База данных готова")


def add_log(user_id, action, details=""):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO logs (user_id, action, details, created_at) VALUES (?, ?, ?, ?)",
        (user_id, action, details, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
