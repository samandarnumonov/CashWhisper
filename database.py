"""CashWhisper database layer — async SQLite via aiosqlite."""

import aiosqlite
from datetime import date
from typing import Optional

_db_path: str = "cashwhisper.db"


def set_db_path(path: str) -> None:
    """Set the database file path (called once at startup)."""
    global _db_path
    _db_path = path


# ── Schema ───────────────────────────────────────────────────────────

async def init_db() -> None:
    """Create tables if they don't exist."""
    db = await aiosqlite.connect(_db_path)
    db.row_factory = aiosqlite.Row
    try:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_user_id INTEGER UNIQUE NOT NULL,
                username        TEXT,
                first_name      TEXT,
                currency        TEXT    DEFAULT 'UZS',
                timezone        TEXT    DEFAULT 'Asia/Tashkent',
                daily_reminder_enabled INTEGER DEFAULT 0,
                daily_reminder_time   TEXT    DEFAULT '21:00',
                created_at      TEXT    DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id          INTEGER NOT NULL REFERENCES users(id),
                created_at       TEXT    DEFAULT (datetime('now')),
                transaction_date TEXT    NOT NULL,
                amount           REAL    NOT NULL,
                currency         TEXT    NOT NULL,
                category         TEXT    NOT NULL,
                description      TEXT,
                source           TEXT    NOT NULL DEFAULT 'text',
                raw_input        TEXT,
                message_id       INTEGER,
                status           TEXT    DEFAULT 'confirmed'
            )
        """)
        # Run migrations for existing databases
        try:
            await db.execute("ALTER TABLE expenses ADD COLUMN message_id INTEGER")
        except aiosqlite.OperationalError:
            pass
        try:
            await db.execute("ALTER TABLE expenses ADD COLUMN status TEXT DEFAULT 'confirmed'")
        except aiosqlite.OperationalError:
            pass
        await db.commit()
    finally:
        await db.close()


# ── User helpers ─────────────────────────────────────────────────────

async def get_or_create_user(
    telegram_user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
) -> dict:
    """Return user dict, creating a new row if needed."""
    db = await aiosqlite.connect(_db_path)
    db.row_factory = aiosqlite.Row
    try:
        cursor = await db.execute(
            "SELECT * FROM users WHERE telegram_user_id = ?",
            (telegram_user_id,),
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)

        await db.execute(
            """INSERT INTO users (telegram_user_id, username, first_name)
               VALUES (?, ?, ?)""",
            (telegram_user_id, username, first_name),
        )
        await db.commit()

        cursor = await db.execute(
            "SELECT * FROM users WHERE telegram_user_id = ?",
            (telegram_user_id,),
        )
        row = await cursor.fetchone()
        return dict(row)
    finally:
        await db.close()


async def update_user_settings(
    telegram_user_id: int,
    currency: Optional[str] = None,
    timezone: Optional[str] = None,
    daily_reminder_enabled: Optional[bool] = None,
    daily_reminder_time: Optional[str] = None,
) -> None:
    """Update user preferences."""
    fields, values = [], []
    if currency is not None:
        fields.append("currency = ?")
        values.append(currency)
    if timezone is not None:
        fields.append("timezone = ?")
        values.append(timezone)
    if daily_reminder_enabled is not None:
        fields.append("daily_reminder_enabled = ?")
        values.append(int(daily_reminder_enabled))
    if daily_reminder_time is not None:
        fields.append("daily_reminder_time = ?")
        values.append(daily_reminder_time)
    if not fields:
        return
    values.append(telegram_user_id)
    db = await aiosqlite.connect(_db_path)
    try:
        await db.execute(
            f"UPDATE users SET {', '.join(fields)} WHERE telegram_user_id = ?",
            tuple(values),
        )
        await db.commit()
    finally:
        await db.close()


async def get_all_users_with_reminders() -> list[dict]:
    """Return users who have daily reminders enabled."""
    db = await aiosqlite.connect(_db_path)
    db.row_factory = aiosqlite.Row
    try:
        cursor = await db.execute(
            "SELECT * FROM users WHERE daily_reminder_enabled = 1"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


# ── Expense helpers ──────────────────────────────────────────────────

async def save_expenses(
    user_id: int,
    expenses: list[dict],
    source: str,
    raw_input: str,
    message_id: Optional[int] = None,
    status: str = "pending",
) -> int:
    """
    Save a list of parsed expenses.
    Each expense dict: {amount, currency, category, description, date}
    Returns the number of rows inserted.
    """
    db = await aiosqlite.connect(_db_path)
    try:
        for exp in expenses:
            await db.execute(
                """INSERT INTO expenses
                   (user_id, transaction_date, amount, currency, category,
                    description, source, raw_input, message_id, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    exp.get("date", str(date.today())),
                    exp["amount"],
                    exp["currency"],
                    exp["category"],
                    exp.get("description", ""),
                    source,
                    raw_input,
                    message_id,
                    status,
                ),
            )
        await db.commit()
    finally:
        await db.close()
    return len(expenses)


async def update_expense_status(user_id: int, message_id: int, status: str) -> int:
    """
    Update the status of expenses tied to a specific message_id.
    Returns the number of rows updated.
    """
    db = await aiosqlite.connect(_db_path)
    try:
        cursor = await db.execute(
            "UPDATE expenses SET status = ? WHERE user_id = ? AND message_id = ?",
            (status, user_id, message_id)
        )
        await db.commit()
        return cursor.rowcount
    finally:
        await db.close()


async def get_expenses_by_range(
    user_id: int,
    start_date: str,
    end_date: str,
) -> list[dict]:
    """Return expenses between start_date and end_date (inclusive, YYYY-MM-DD)."""
    db = await aiosqlite.connect(_db_path)
    db.row_factory = aiosqlite.Row
    try:
        cursor = await db.execute(
            """SELECT * FROM expenses
               WHERE user_id = ?
                 AND transaction_date >= ?
                 AND transaction_date <= ?
                 AND status = 'confirmed'
               ORDER BY transaction_date, created_at""",
            (user_id, start_date, end_date),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_monthly_summary(user_id: int, year: int, month: int) -> dict:
    """
    Return a summary dict for the given month:
    {total, currency, categories: [{name, amount}]}
    """
    start = f"{year:04d}-{month:02d}-01"
    if month == 12:
        end = f"{year + 1:04d}-01-01"
    else:
        end = f"{year:04d}-{month + 1:02d}-01"

    db = await aiosqlite.connect(_db_path)
    db.row_factory = aiosqlite.Row
    try:
        # Total
        cursor = await db.execute(
            """SELECT COALESCE(SUM(amount), 0) as total, currency
               FROM expenses
               WHERE user_id = ? AND transaction_date >= ? AND transaction_date < ?
                 AND status = 'confirmed'
               GROUP BY currency""",
            (user_id, start, end),
        )
        totals_rows = await cursor.fetchall()

        # By category
        cursor = await db.execute(
            """SELECT category, SUM(amount) as amount, currency
               FROM expenses
               WHERE user_id = ? AND transaction_date >= ? AND transaction_date < ?
                 AND status = 'confirmed'
               GROUP BY category, currency
               ORDER BY amount DESC""",
            (user_id, start, end),
        )
        cat_rows = await cursor.fetchall()
    finally:
        await db.close()

    total = sum(r["total"] for r in totals_rows) if totals_rows else 0
    currency = totals_rows[0]["currency"] if totals_rows else "UZS"

    return {
        "month": f"{year:04d}-{month:02d}",
        "total_spent": total,
        "currency": currency,
        "categories": [
            {"name": r["category"], "amount": r["amount"]} for r in cat_rows
        ],
    }
