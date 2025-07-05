import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from telethon.tl.types import PeerChannel

from monitor.client import TelegramMonitorClient


@pytest.mark.asyncio
async def test_check_health_gathers_all_tasks():
    client = TelegramMonitorClient(db=MagicMock())
    client.client = MagicMock()
    client.monitored_channels = {1: {10}, 2: {20, 30}}

    async def get_entity(entity):
        if isinstance(entity, PeerChannel):
            if entity.channel_id == 10:
                return object()
            if entity.channel_id == 20:
                raise ValueError("fail")
            if entity.channel_id == 30:
                return object()
        raise ValueError("unexpected")

    client.client.get_entity = AsyncMock(side_effect=get_entity)

    original_gather = asyncio.gather

    async def gather_stub(*tasks, **kwargs):
        gather_stub.received = tasks
        return await original_gather(*tasks, **kwargs)

    with patch(
        "monitor.client.asyncio.gather",
        new=AsyncMock(side_effect=gather_stub),
    ) as gmock:
        result = await client.check_health()

    gmock.assert_awaited_once()
    assert len(gather_stub.received) == 3
    assert result == {1: {10: True}, 2: {20: False, 30: True}}
