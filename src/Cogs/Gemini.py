from datetime import timezone
import discord
import google.generativeai as genai
from discord.ext import commands
import asyncio
import os

from src import Entities, Session
from src.Cogs.Utils import sanitize_args
from src.Models import MessagePayload
from src.Repositories import DatabaseRepository

class Gemini(commands.Cog):
    SAFETY_SETTINGS = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    MESSAGE_HISTORY_LIMIT = 50  # Default message history limit
    DEFAULT_MODEL = "gemini-2.0-flash-exp"
    AVAILABLE_MODELS = ["gemini-pro", "gemini-2.0-flash-exp"]

    def __init__(self, bot, api_key, logger, initial_prompt):
        self.bot = bot
        self.logger = logger
        self.initial_prompt = [
            {"role": "user", "parts": [initial_prompt]}
        ]
        self.temperature = float(os.getenv('GEMINI_TEMPERATURE', '1.0'))
        self.top_p = float(os.getenv('GEMINI_TOP_P', '0.95'))
        self.top_k = int(os.getenv('GEMINI_TOP_K', '40'))
        self.max_output_tokens = int(os.getenv('GEMINI_MAX_OUTPUT_TOKENS', '8192'))
        self.model_name = os.getenv('GEMINI_MODEL', self.DEFAULT_MODEL)

        genai.configure(api_key=api_key)
        self.generation_config = {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "max_output_tokens": self.max_output_tokens,
        }
        
        self.model = self._create_model()
        self.chat = self.model.start_chat(history=self.initial_prompt)

    def _create_model(self):
        """Create a new model instance with current configuration"""
        return genai.GenerativeModel(
            model_name=self.model_name,
            generation_config=self.generation_config,
            safety_settings=self.SAFETY_SETTINGS
        )

    @commands.command()
    @commands.has_role("Parent")
    async def set_model(self, ctx, model_name: str):
        """Set the Gemini model to use"""
        if model_name not in self.AVAILABLE_MODELS:
            available_models = ", ".join(self.AVAILABLE_MODELS)
            await ctx.reply(f'利用可能なモデル: {available_models}')
            return
        self.model_name = model_name
        self.model = self._create_model()
        self.chat = self.model.start_chat(history=self.initial_prompt)
        await ctx.reply(f'モデルを {model_name} に変更しました。チャット履歴はリセットされました。')

    @commands.command()
    @commands.has_role("Parent")
    async def set_temperature(self, ctx, temp: float):
        """Set the temperature for text generation (0.0 to 1.0)"""
        if temp < 0.0 or temp > 1.0:
            await ctx.reply('temperatureは0.0から1.0の間で設定してください。')
            return
        self.temperature = temp
        self.generation_config["temperature"] = temp
        self.model = self._create_model()
        await ctx.reply(f'temperatureを{temp}に設定しました。')

    @commands.command()
    @commands.has_any_role("Parent", "Toddler")
    async def show_config(self, ctx):
        """Show current model configuration"""
        config = {
            "モデル": self.model_name,
            "Temperature": self.temperature,
            "Top P": self.top_p,
            "Top K": self.top_k,
            "最大出力トークン": self.max_output_tokens,
            "メッセージ履歴制限": self.MESSAGE_HISTORY_LIMIT
        }
        config_text = "\n".join([f"{k}: {v}" for k, v in config.items()])
        await ctx.reply(f'現在の設定:\n```\n{config_text}\n```')

    async def send_chat_message(self, msg):
        """Asynchronously send a message to the chat with retry logic"""
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                # Wrap the synchronous API call in an executor to make it async
                response = await asyncio.get_event_loop().run_in_executor(
                    None, self.chat.send_message, msg
                )
                return response
            except asyncio.TimeoutError:
                if attempt == max_attempts:
                    return f"Timeout error: The request took too long to complete after {max_attempts} attempts."
                await asyncio.sleep(1)  # Add delay between retries
            except Exception as e:
                if attempt == max_attempts:
                    self.logger.error(f"Error in send_chat_message: {str(e)}")
                    return f"An error occurred after {max_attempts} attempts: {str(e)}"
                await asyncio.sleep(1)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.mentions and self.bot.user in message.mentions \
                and message.author != self.bot.user \
                and message.channel.id != 1173806749757743134:
            content = message.content.replace(f'<@{self.bot.user.id}>', '').strip()
            async with message.channel.typing():
                await self.process_message(content, message, message.author.display_name)

    @commands.command()
    @commands.has_any_role("Parent", "Toddler")
    async def gem(self, ctx, *args):
        arguments = sanitize_args(args)
        async with ctx.typing():
            await self.process_message(arguments, ctx, ctx.author.display_name)

    @commands.command()
    @commands.has_any_role("Parent", "Toddler")
    async def save_message(self, ctx, *args):
        try:
            async with ctx.typing():
                message = MessagePayload(
                    member_id=ctx.author.id,
                    channel_id=ctx.channel.id,
                    msg_id=ctx.message.id,
                    created_at=ctx.message.created_at.astimezone(timezone.utc).replace(tzinfo=None)
                )
                async for session in Session.get_db_session():
                    self.logger.info(f"Saving message: {message.dict()}")
                    repo = DatabaseRepository(Entities.Message, session)
                    await repo.create(message.dict())
                    await ctx.send("Message saved successfully!")
        except Exception as e:
            self.logger.error(f"Error saving message: {str(e)}")
            await ctx.send("Failed to save message. Please try again later.")

    @commands.command()
    @commands.has_any_role("Parent", "Toddler")
    async def get_messages(self, ctx):
        try:
            async with ctx.typing():
                async for session in Session.get_db_session():
                    self.logger.info("Getting all messages")
                    repo = DatabaseRepository(Entities.Message, session)
                    messages = await repo.get_all()
                    if not messages:
                        await ctx.send("No messages found.")
                        return
                    # Format messages in a more readable way
                    formatted_messages = "\n".join(f"Message ID: {msg.msg_id}" for msg in messages[:10])
                    await ctx.send(f"Recent messages:\n{formatted_messages}")
        except Exception as e:
            self.logger.error(f"Error retrieving messages: {str(e)}")
            await ctx.send("Failed to retrieve messages. Please try again later.")

    @commands.command()
    @commands.has_any_role("Parent", "Toddler")
    async def set_history_limit(self, ctx, limit: int):
        """Set the number of previous messages to include in chat context"""
        if limit < 1 or limit > 50:
            await ctx.reply('メッセージ履歴の制限は1から50の間で設定してください。')
            return
        self.MESSAGE_HISTORY_LIMIT = limit
        await ctx.reply(f'メッセージ履歴の制限を{limit}件に設定しました。')

    async def process_message(self, arguments, reply_func, author_name):
        if not arguments:
            await reply_func.reply('どしたん?話きこか?')
            return

        if arguments.lower() == 'reset':
            self.logger.info(f"{author_name} is resetting the chat")
            self.chat = self.model.start_chat(history=self.initial_prompt)
            await reply_func.reply('チャットの履歴をリセットしたお')
            return

        # Fetch messages from the channel using the configurable limit
        channel = reply_func.channel if hasattr(reply_func, 'channel') else reply_func.message.channel
        messages = []
        async for msg in channel.history(limit=self.MESSAGE_HISTORY_LIMIT):
            if msg.author != self.bot.user:  # Only include user messages
                messages.append(f"{msg.author.display_name}: {msg.content}")
        
        # Reverse messages to show oldest first
        messages.reverse()
        
        # Create context with previous messages
        context = "Previous messages:\n" + "\n".join(messages) + "\n\nCurrent message:\n"
        
        self.logger.info(f"{author_name} is sending message: {arguments}")
        response = await self.send_chat_message(f"{context}{author_name}: {arguments}")
        self.logger.info(f"Gemini response: {response}")
        
        response_text = response.text if hasattr(response, 'text') else str(response)
        if len(response_text) > 2000:  # Discord message length limit
            # Split long messages
            chunks = [response_text[i:i+1990] for i in range(0, len(response_text), 1990)]
            for chunk in chunks:
                await reply_func.reply(chunk)
        else:
            await reply_func.reply(response_text)
