import asyncio

import discord
import google.generativeai as genai
from discord.ext import commands

from src.Cogs.Utils import sanitize_args


class Gemini(commands.Cog):
    SAFETY_SETTINGS = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]

    INITIAL_PROMPT = [
        {
            "role": "user",
            "parts": [
                "As a chatbot operating within Discord, your responsibility is to receive and keep track of messages "
                "from various users. For instance, a user's message may appear as 'John: Hello, there!' indicating "
                "that a user named John is reaching out. Now, let's begin. Chi-chan: 'Hi, who am I?'"
            ]
        },
        {
            "role": "model",
            "parts": ["Hi you are Chi-chan, nice to meet you too. What can I do for you today?"]
        },
    ]

    def __init__(self, bot, api_key, logger):
        self.bot = bot
        self.logger = logger

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(safety_settings=self.SAFETY_SETTINGS)
        self.chat = model.start_chat(history=self.INITIAL_PROMPT)

    async def send_chat_message(self, msg):
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                return self.chat.send_message(msg)
            except asyncio.TimeoutError:
                if attempt == max_attempts:
                    return f"Timeout error: The request took too long to complete after {max_attempts} attempts."
            except Exception as e:
                if attempt == max_attempts:
                    return f"An error occurred after {max_attempts} attempts: {str(e)}"

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if len(message.mentions) != 0 and self.bot.user in message.mentions and message.author != self.bot.user:
            parts = message.content.split(' ', 1)
            arguments = ' '.join(parts)
            async with message.channel.typing():
                await self.process_message(arguments, message, message.author.display_name)

    @commands.command()
    @commands.has_any_role("Parent", "Toddler")
    async def gem(self, ctx, *args):
        arguments = sanitize_args(args)
        async with ctx.typing():
            await self.process_message(arguments, ctx, ctx.author.display_name)

    async def process_message(self, arguments, reply_func, author_name):
        if arguments == '':
            await reply_func.reply('どしたん？話きこか？')
            return

        if arguments == 'reset':
            self.logger.info(f"{author_name} is resetting the chat")
            self.chat.history.clear()
            self.chat.history = self.INITIAL_PROMPT
            await reply_func.reply('チャットの履歴をリセットしたお')
            return

        self.logger.info(f"{author_name} is sending message: {arguments}")
        response = self.send_chat_message(f"{author_name}: {arguments}")
        self.logger.info(f"Gemini response: {response}")
        await reply_func.reply(response.text if hasattr(response, 'text') else response)
