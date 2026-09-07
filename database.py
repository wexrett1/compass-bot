import os
import asyncpg

# Получаем ссылку на базу из переменной окружения
DATABASE_URL = os.getenv("DATABASE_URL")

# Глобальная переменная для пула подключений
_pool = None


async def get_pool():
    """Возвращает пул подключений к базе данных."""
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL не найден. Проверьте переменные окружения на Render!")
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    return _pool


async def init_db():
    """Создает таблицы в базе данных."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                university TEXT,
                role TEXT,
                stack TEXT,
                format TEXT,
                is_active INTEGER DEFAULT 1,
                socials TEXT,
                phone TEXT,
                projects TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                project_id SERIAL PRIMARY KEY,
                owner_id BIGINT,
                title TEXT,
                description TEXT,
                roles TEXT,
                topic TEXT,
                stage TEXT,
                format TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS responses (
                response_id SERIAL PRIMARY KEY,
                project_id INTEGER,
                applicant_id BIGINT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(project_id, applicant_id)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bookmarks (
                user_id BIGINT,
                project_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, project_id)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_projects (
                user_id BIGINT,
                project_id INTEGER,
                PRIMARY KEY (user_id, project_id)
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                review_id SERIAL PRIMARY KEY,
                reviewer_id BIGINT,
                target_id BIGINT,
                project_id INTEGER,
                text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ База данных подключена и таблицы созданы!")


async def upsert_user(user_id, username, **fields):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT user_id FROM users WHERE user_id = $1", user_id)
        if row:
            if fields:
                keys = ", ".join(f"{k} = ${i+1}" for i, k in enumerate(fields.keys()))
                values = list(fields.values()) + [user_id]
                await conn.execute(f"UPDATE users SET {keys} WHERE user_id = ${len(values)}", *values)
        else:
            columns = ["user_id", "username"] + list(fields.keys())
            placeholders = ", ".join(f"${i+1}" for i in range(len(columns)))
            values = [user_id, username] + list(fields.values())
            await conn.execute(
                f"INSERT INTO users ({', '.join(columns)}) VALUES ({placeholders})",
                *values,
            )


async def get_user(user_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)


async def set_active(user_id, is_active: bool):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET is_active = $1 WHERE user_id = $2", int(is_active), user_id
        )


async def create_project(owner_id, title, description, roles, topic, stage, fmt):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow(
            """
            INSERT INTO projects (owner_id, title, description, roles, topic, stage, format, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 1)
            RETURNING project_id
            """,
            owner_id, title, description, roles, topic, stage, fmt,
        )
        return result["project_id"]


async def get_project(project_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM projects WHERE project_id = $1", project_id)


async def get_user_projects(owner_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchall(
            "SELECT * FROM projects WHERE owner_id = $1 ORDER BY created_at DESC", owner_id
        )


async def get_next_project_for_role(user_id, role):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            """
            SELECT * FROM projects
            WHERE is_active = 1
              AND owner_id != $1
              AND (',' || roles || ',') LIKE $2
              AND project_id NOT IN (
                  SELECT project_id FROM seen_projects WHERE user_id = $1
              )
            ORDER BY created_at DESC
            LIMIT 1
            """,
            user_id, f"%,{role},%",
        )


async def mark_project_seen(user_id, project_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO seen_projects (user_id, project_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            user_id, project_id,
        )


async def add_response(project_id, applicant_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO responses (project_id, applicant_id, status) VALUES ($1, $2, 'pending') ON CONFLICT DO NOTHING",
            project_id, applicant_id,
        )


async def set_response_status(project_id, applicant_id, status):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE responses SET status = $1 WHERE project_id = $2 AND applicant_id = $3",
            status, project_id, applicant_id,
        )


async def get_response(project_id, applicant_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM responses WHERE project_id = $1 AND applicant_id = $2",
            project_id, applicant_id,
        )


async def get_my_responses(applicant_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchall(
            """
            SELECT responses.*, projects.title AS project_title, projects.owner_id AS project_owner_id
            FROM responses
            JOIN projects ON projects.project_id = responses.project_id
            WHERE applicant_id = $1
            ORDER BY responses.created_at DESC
            """,
            applicant_id,
        )


async def add_bookmark(user_id, project_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO bookmarks (user_id, project_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            user_id, project_id,
        )


async def get_bookmarks(user_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchall(
            """
            SELECT projects.* FROM bookmarks
            JOIN projects ON projects.project_id = bookmarks.project_id
            WHERE bookmarks.user_id = $1
            ORDER BY bookmarks.created_at DESC
            """,
            user_id,
        )


async def add_review(reviewer_id, target_id, project_id, text):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO reviews (reviewer_id, target_id, project_id, text) VALUES ($1, $2, $3, $4)",
            reviewer_id, target_id, project_id, text,
        )


async def get_reviews_for_user(target_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchall(
            """
            SELECT reviews.*, users.full_name AS reviewer_name
            FROM reviews
            LEFT JOIN users ON users.user_id = reviews.reviewer_id
            WHERE target_id = $1
            ORDER BY reviews.created_at DESC
            """,
            target_id,
        )
