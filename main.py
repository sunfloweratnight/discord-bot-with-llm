import asyncio
import logging
import logging.handlers
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from src.Cogs.Gemini import Gemini
from src.Cogs.RoleOperation import RoleOperation


async def setup():
    load_dotenv()
    discord_api_key = os.getenv("DISCORD_API_KEY")
    gemini_api_key = os.getenv("GEMINI_API_KEY")

    # try:
    #     with open('system_message.txt', 'r') as f:
    #         system_message = f.read()
    # except FileNotFoundError:
    #     print('File not found')

    logger = logging.getLogger('discord')
    logger.setLevel(logging.INFO)

    dt_fmt = '%Y-%m-%d %H:%M:%S'
    formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True

    bot = commands.Bot(command_prefix='$', intents=intents)
    await bot.add_cog(Gemini(bot, gemini_api_key, logger))
    await bot.add_cog(RoleOperation(bot, logger))
    await bot.start(discord_api_key)


loop = asyncio.get_event_loop()
loop.run_until_complete(setup())
