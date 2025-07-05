import pytest
import aiosqlite
import tempfile

from database.db import Database

@pytest.mark.asyncio
async def test_get_user_settings_defaults():
    with tempfile.NamedTemporaryFile(suffix='.sqlite3') as tmp:
        async with aiosqlite.connect(tmp.name) as conn:
            await conn.execute(
                "CREATE TABLE user_settings (user_id INTEGER PRIMARY KEY)"
            )
            await conn.execute("INSERT INTO user_settings (user_id) VALUES (1)")
            await conn.commit()

        db = Database(db_path=tmp.name)
        settings = await db.get_user_settings(1)

    assert settings.user_id == 1
    assert settings.notification_format == "full"
    assert settings.include_timestamp is True
    assert settings.include_channel_info is True
    assert settings.include_message_link is True
    assert settings.include_sender_id is False
    assert settings.include_original_formatting is True
    assert settings.forward_as_code is False
    assert settings.monitoring_enabled is True
    assert settings.max_message_length == 4000
