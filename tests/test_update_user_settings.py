import pytest
from unittest.mock import AsyncMock, patch

from database.db import Database


@pytest.mark.asyncio
async def test_update_user_settings_invalid_field():
    db = Database(db_path=':memory:')
    with patch('database.db.aiosqlite.connect', new_callable=AsyncMock) as connect:
        result = await db.update_user_settings(1, unknown=True)
        assert result is False
        connect.assert_not_called()


@pytest.mark.asyncio
async def test_update_user_settings_mixed_fields():
    db = Database(db_path=':memory:')
    async_context = AsyncMock()
    async_context.__aenter__.return_value = AsyncMock()
    async_context.__aexit__.return_value = AsyncMock()
    with patch('database.db.aiosqlite.connect', return_value=async_context) as connect:
        execute_mock = async_context.__aenter__.return_value.execute
        execute_mock.return_value = AsyncMock()
        result = await db.update_user_settings(1, include_timestamp=False, bad=True)
        connect.assert_called_once()
        execute_mock.assert_awaited()
        assert result is True
