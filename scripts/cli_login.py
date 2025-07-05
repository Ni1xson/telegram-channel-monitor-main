#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Simple CLI for authenticating Telegram user session."""

import asyncio
from telethon.errors import SessionPasswordNeededError

from config.config import Config
from database.db import Database
from monitor.client import TelegramMonitorClient


async def main() -> None:
    """Authenticate Telegram user via CLI."""
    Config.validate()

    db = Database(Config.DATABASE_PATH)
    await db.init_db()

    monitor_client = TelegramMonitorClient(db)

    phone = input("Phone: ").strip()
    await monitor_client.send_code(phone, force_sms=True)
    code = input("Code: ").strip()

    try:
        await monitor_client.sign_in(phone, code)
    except SessionPasswordNeededError:
        password = input("Password: ").strip()
        await monitor_client.sign_in(phone, code=None, password=password)

    print("✅ Login successful")

    if monitor_client.client:
        await monitor_client.client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
