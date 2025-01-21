from datetime import timezone
import discord
import google.generativeai as genai
from discord.ext import commands
import asyncio

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

    def __init__(self, bot, api_key, logger, initial_prompt):
        self.bot = bot
        self.logger = logger
        self.initial_prompt = [
            {"role": "user", "parts": [initial_prompt]}
        ]

        genai.configure(api_key=api_key)
        generation_config = {
            "temperature": 1,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 8192,
        }
        
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",  # Updated to use stable release model
            generation_config=generation_config,
            safety_settings=self.SAFETY_SETTINGS  # Added safety settings
        )

        self.chat = self.model.start_chat(history=self.initial_prompt)

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

    async def process_message(self, arguments, reply_func, author_name):
        if not arguments:
            await reply_func.reply('どしたん？話きこか？')
            return

        if arguments.lower() == 'reset':
            self.logger.info(f"{author_name} is resetting the chat")
            self.chat = self.model.start_chat(history=self.initial_prompt)
            await reply_func.reply('チャットの履歴をリセットしたお')
            return

        self.logger.info(f"{author_name} is sending message: {arguments}")
        response = await self.send_chat_message(f"{author_name}: {arguments}")
        self.logger.info(f"Gemini response: {response}")
        
        response_text = response.text if hasattr(response, 'text') else str(response)
        if len(response_text) > 2000:  # Discord message length limit
            # Split long messages
            chunks = [response_text[i:i+1990] for i in range(0, len(response_text), 1990)]
            for chunk in chunks:
                await reply_func.reply(chunk)
        else:
            await reply_func.reply(response_text)
