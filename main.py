import asyncio

from keep_alive import keep_alive
from src.DiscordBot import DiscordBot
from src.Migrate import migrate_tables


async def setup():
    bot = DiscordBot()
    await bot.get_started()


async def main():
    await migrate_tables()
    await setup()

keep_alive()
asyncio.run(main())

