import pytest
import aiosqlite
import tempfile

from database.models import DatabaseManager


@pytest.mark.asyncio
async def test_init_db_adds_monitoring_enabled_column():
    with tempfile.NamedTemporaryFile(suffix='.sqlite3') as tmp:
        async with aiosqlite.connect(tmp.name) as conn:
            await conn.execute(
                "CREATE TABLE user_settings (\n"
                "    user_id INTEGER PRIMARY KEY,\n"
                "    notification_format TEXT DEFAULT 'full'\n"
                ")"
            )
            await conn.execute("INSERT INTO user_settings (user_id) VALUES (1)")
            await conn.commit()

        manager = DatabaseManager(db_path=tmp.name)
        await manager.init_db()

        async with aiosqlite.connect(tmp.name) as conn:
            async with conn.execute("PRAGMA table_info(user_settings)") as cur:
                cols = [row[1] async for row in cur]
            assert "monitoring_enabled" in cols

            async with conn.execute(
                "SELECT monitoring_enabled FROM user_settings WHERE user_id = 1"
            ) as cur:
                row = await cur.fetchone()
                assert row[0] == 1


@pytest.mark.asyncio
async def test_init_db_adds_sender_columns():
    with tempfile.NamedTemporaryFile(suffix='.sqlite3') as tmp:
        async with aiosqlite.connect(tmp.name) as conn:
            await conn.execute(
                "CREATE TABLE found_messages (\n"
                "    id INTEGER PRIMARY KEY,\n"
                "    user_id INTEGER,\n"
                "    filter_id INTEGER,\n"
                "    channel_id INTEGER,\n"
                "    message_id INTEGER\n"
                ")"
            )
            await conn.execute(
                "CREATE TABLE user_settings (user_id INTEGER PRIMARY KEY)"
            )
            await conn.execute("INSERT INTO user_settings (user_id) VALUES (1)")
            await conn.commit()

        manager = DatabaseManager(db_path=tmp.name)
        await manager.init_db()

        async with aiosqlite.connect(tmp.name) as conn:
            async with conn.execute("PRAGMA table_info(found_messages)") as cur:
                cols = [row[1] async for row in cur]
            assert "sender_id" in cols
            assert "sender_username" in cols

            async with conn.execute("PRAGMA table_info(user_settings)") as cur:
                ucols = [row[1] async for row in cur]
            assert "include_sender_id" in ucols

            async with conn.execute(
                "SELECT include_sender_id FROM user_settings WHERE user_id = 1"
            ) as cur:
                row = await cur.fetchone()
                assert row[0] == 0
