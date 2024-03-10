import logging
import logging.handlers

import discord
from discord.ext import commands

from src.Cogs.Gemini import Gemini
from src.Cogs.RoleOperation import RoleOperation


class DiscordBot(commands.Bot):
    def __init__(self, discord_api_key, gemini_api_key) -> None:
        self.gemini_api_key = gemini_api_key
        self.discord_api_key = discord_api_key

        command_prefix = '!'
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(command_prefix, intents=intents)

        self.logger = logging.getLogger('discord')
        self.logger.setLevel(logging.INFO)

        dt_fmt = '%Y-%m-%d %H:%M:%S'
        formatter = logging.Formatter('[{asctime}] [{levelname:<8}] {name}: {message}', dt_fmt, style='{')

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    async def setup_hook(self):
        self.logger.info('Setting up the cogs')
        await self.add_cog(RoleOperation(self, self.logger))
        await self.add_cog(Gemini(self, self.gemini_api_key, self.logger))
        self.logger.info('Cogs are set up')

    async def get_started(self):
        await self.start(self.discord_api_key)
