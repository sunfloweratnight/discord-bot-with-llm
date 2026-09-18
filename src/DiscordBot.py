import discord
from discord.ext import commands

from Config import settings
from src.Cogs.Gemini import Gemini
from src.Cogs.RoleOperation import RoleOperation
from src.infrastructure.gemini import GeminiChatAdapter
from src.infrastructure.jev import TypesafeJevAdapter
from src.Logger import Logger
from src.presentation.discord.cogs.fortune import Fortune
from src.usecases.chat import ReplyToUserMessage
from src.usecases.fortune import TellFortuneUseCase


class DiscordBot(commands.Bot):
    def __init__(self) -> None:
        self.gemini_api_key = settings.GEMINI_API_KEY
        self.discord_api_key = settings.DISCORD_API_KEY
        self.initial_prompt = settings.INITIAL_PROMPT

        command_prefix = '!'
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(command_prefix, intents=intents)

        logger_factory = Logger('discord')
        self.logger = logger_factory.get_logger()

    async def setup_hook(self):
        self.logger.info('Setting up the cogs')
        await self.add_cog(RoleOperation(self, self.logger))

        chat_adapter = GeminiChatAdapter(self.gemini_api_key, self.initial_prompt)
        reply_use_case = ReplyToUserMessage(chat_adapter)
        await self.add_cog(
            Gemini(
                self,
                self.logger,
                chat_adapter,
                reply_use_case,
                self.initial_prompt,
            )
        )

        decision = TypesafeJevAdapter(settings.TYPESAFE_API_KEY)
        fortune_use_case = TellFortuneUseCase(decision)
        await self.add_cog(Fortune(self, self.logger, fortune_use_case, decision))
        self.logger.info('Cogs are set up')

    async def get_started(self):
        await self.start(self.discord_api_key)
