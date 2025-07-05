from typing import Any, Callable, Dict

from aiogram.dispatcher.middlewares.base import BaseMiddleware

from database.db import Database
from monitor.client import TelegramMonitorClient


class DependencyMiddleware(BaseMiddleware):
    """Inject db and monitor client into handlers."""

    def __init__(self, db: Database, monitor_client: TelegramMonitorClient):
        self.db = db
        self.monitor_client = monitor_client

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Any],
        event: Any,
        data: Dict[str, Any],
    ) -> Any:
        data["db"] = self.db
        data["monitor_client"] = self.monitor_client
        return await handler(event, data)
