import aiosqlite
from datetime import datetime
from config import settings


async def init_db() -> None:
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_seen DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_activity DATETIME,
                total_tzs INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS technical_specs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                content TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS generation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                type TEXT CHECK(type IN ('tz','image','code_audit','deploy')),
                model_used TEXT,
                success INTEGER,
                tokens_used INTEGER,
                rating INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.commit()


async def upsert_user(user_id: int, username: str | None) -> None:
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, first_seen, last_activity)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                last_activity = excluded.last_activity
        """, (user_id, username, now, now))
        await db.commit()


async def save_tz(user_id: int, content: str) -> None:
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute(
            "INSERT INTO technical_specs (user_id, content) VALUES (?, ?)",
            (user_id, content)
        )
        await db.execute("""
            DELETE FROM technical_specs
            WHERE user_id = ? AND id NOT IN (
                SELECT id FROM technical_specs
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 5
            )
        """, (user_id, user_id))
        await db.execute(
            "UPDATE users SET total_tzs = total_tzs + 1 WHERE user_id = ?",
            (user_id,)
        )
        await db.commit()


async def get_user_tzs(user_id: int) -> list[dict]:
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, content, created_at FROM technical_specs WHERE user_id = ? ORDER BY created_at DESC LIMIT 5",
            (user_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def log_generation(
    user_id: int,
    gen_type: str,
    model: str,
    success: bool,
    tokens: int = 0,
    rating: int | None = None
) -> None:
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute(
            "INSERT INTO generation_logs (user_id, type, model_used, success, tokens_used, rating) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, gen_type, model, int(success), tokens, rating)
        )
        await db.commit()


async def update_tz_rating(user_id: int, rating: int) -> None:
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("""
            UPDATE generation_logs SET rating = ?
            WHERE user_id = ? AND type = 'tz'
            ORDER BY created_at DESC LIMIT 1
        """, (rating, user_id))
        await db.commit()
