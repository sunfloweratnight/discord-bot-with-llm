import asyncio
import os

from dotenv import load_dotenv

from keep_alive import keep_alive
from src.DiscordBot import DiscordBot


async def setup():
    load_dotenv()
    discord_api_key = os.getenv("DISCORD_API_KEY")
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    bot = DiscordBot(discord_api_key, gemini_api_key)
    await bot.get_started()


keep_alive()
loop = asyncio.get_event_loop()
loop.run_until_complete(setup())
