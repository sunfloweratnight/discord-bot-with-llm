from datetime import timezone
import discord
import google.generativeai as genai
from discord.ext import commands
import asyncio
from discord.ext import tasks
import random
import datetime
from typing import List, Optional

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

    def __init__(self, bot, api_key, logger, initial_prompt):
        self.bot = bot
        self.logger = logger
        self.initial_prompt = [
            {"role": "user", "parts": [initial_prompt]}
        ]
        self.BABY_ROOM_CATEGORY_ID = 1150088658947407952  # 赤ちゃん部屋のカテゴリーID

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
        self.last_check_channel = None
        # 定期チェックを開始
        self.periodic_infant_check.start()

    def cog_unload(self):
        """Cogがアンロードされるときにタスクを停止"""
        self.periodic_infant_check.cancel()

    @tasks.loop(minutes=30)  # 30分ごとに実行
    async def periodic_infant_check(self):
        """定期的にInfantメンバーをチェックする"""
        try:
            # 日本時間で深夜0時から朝6時までは実行しない
            jst_hour = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).hour
            if 0 <= jst_hour < 6:
                return

            guild = self.bot.guilds[0]  # Assuming bot is in only one guild
            if not guild:
                self.logger.error("Guild not found")
                return

            # 赤ちゃん部屋カテゴリーのチャンネルをランダムに選択
            category = discord.utils.get(guild.categories, id=self.BABY_ROOM_CATEGORY_ID)
            if not category:
                self.logger.error("Baby room category not found")
                return

            # テキストチャンネルのみをフィルタリング
            text_channels = [c for c in category.channels if isinstance(c, discord.TextChannel)]
            if not text_channels:
                self.logger.error("No text channels found in baby room category")
                return

            channel = random.choice(text_channels)
            
            infant = await self._get_random_infant(guild)
            if not infant:
                self.logger.info("No Infant members found")
                return

            # 最後にチェックしたチャンネルの最近のメッセージを取得
            recent_messages = await self._get_recent_messages(channel)
            
            # 話題について質問するプロンプトを作成
            messages_text = "\n".join(recent_messages[-5:]) if recent_messages else ""
            prompt = f"""
            以下の最近のチャット内容から興味深い話題を1つ選び、
            {infant.display_name}さんに意見を求めるメッセージを作成してください：

            最近のチャット：
            {messages_text}

            条件：
            - フレンドリーで親しみやすい口調で
            - 具体的な質問を含める
            - 短めの文章（100文字以内）
            - 絵文字を1-2個使用
            - 時間帯に応じた挨拶を含める（現在の時間: {jst_hour}時）
            - チャットが空の場合は、一般的な話題（趣味、好きなもの、最近のできごとなど）について質問
            """

            response = await self._generate_response(prompt)
            await channel.send(f"{infant.mention} {response}")
            self.last_check_channel = channel
            self.logger.info(f"Periodic check completed - messaged {infant.display_name} in {channel.name}")

        except Exception as e:
            self.logger.error(f"Error in periodic_infant_check: {e}")

    @periodic_infant_check.before_loop
    async def before_periodic_check(self):
        """Botが準備できるまで待機"""
        await self.bot.wait_until_ready()

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

    async def _generate_response(self, prompt: str) -> str:
        """Generate a response using the chat model"""
        try:
            # Create a new chat for one-off responses
            temp_chat = self.model.start_chat()
            response = await asyncio.get_event_loop().run_in_executor(
                None, temp_chat.send_message, prompt
            )
            return response.text if hasattr(response, 'text') else str(response)
        except Exception as e:
            self.logger.error(f"Error in _generate_response: {str(e)}")
            return "申し訳ありません。応答の生成中にエラーが発生しました。"

    @commands.command()
    @commands.has_role("Parent")
    async def set_check_interval(self, ctx, minutes: float):
        """定期チェックの間隔を設定する"""
        if minutes < 10 or minutes > 1440:  # 10分から24時間（1440分）の間
            await ctx.reply("間隔は10分から1440分（24時間）の間で設定してください。")
            return
        
        self.periodic_infant_check.change_interval(minutes=minutes)
        await ctx.reply(f"定期チェックの間隔を{minutes}分に設定しました。")

    @commands.command()
    @commands.has_role("Parent")
    async def check_status(self, ctx):
        """定期チェックの状態を確認する"""
        status = "実行中" if self.periodic_infant_check.is_running() else "停止中"
        interval = self.periodic_infant_check.hours
        next_iteration = self.periodic_infant_check.next_iteration
        
        if next_iteration:
            # UTCから日本時間に変換
            jst_next = (next_iteration + datetime.timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')
            await ctx.reply(f"定期チェックの状態:\n"
                          f"- 状態: {status}\n"
                          f"- 間隔: {interval}時間\n"
                          f"- 次回実行: {jst_next}")
        else:
            await ctx.reply(f"定期チェックの状態:\n"
                          f"- 状態: {status}\n"
                          f"- 間隔: {interval}時間\n"
                          f"- 次回実行: 未定")

    async def _get_recent_messages(self, channel, limit=10) -> List[str]:
        """Get recent messages from the channel"""
        messages = []
        async for message in channel.history(limit=limit):
            if not message.author.bot and message.content:  # Skip bot messages and empty messages
                messages.append(message.content)
        return messages

    async def _get_random_infant(self, guild) -> Optional[discord.Member]:
        """Get a random member with Infant role"""
        infant_role = discord.utils.get(guild.roles, name="Infant")
        if not infant_role:
            return None
        
        infant_members = [member for member in guild.members 
                         if infant_role in member.roles and not member.bot]
        return random.choice(infant_members) if infant_members else None

    @commands.command()
    @commands.has_role("Parent")
    async def check_infant(self, ctx):
        """ランダムに選んだInfantメンバーに声をかけます"""
        async with ctx.typing():
            infant = await self._get_random_infant(ctx.guild)
            if not infant:
                await ctx.reply("Infantロールのメンバーが見つかりませんでした。")
                return

            prompt = f"""
            以下の条件で、メンバーに声をかけるメッセージを作成してください：
            - メンバー: {infant.display_name}
            - フレンドリーで親しみやすい口調で
            - 調子を尋ねる
            - 短めの文章（100文字以内）
            - 絵文字を1-2個使用
            """
            
            response = await self._generate_response(prompt)
            await ctx.send(f"{infant.mention} {response}")

    @commands.command()
    @commands.has_role("Parent")
    async def discuss_topic(self, ctx):
        """最近のメッセージから話題を見つけて、Infantメンバーに意見を聞きます"""
        async with ctx.typing():
            # 最近のメッセージを取得
            recent_messages = await self._get_recent_messages(ctx.channel)
            if not recent_messages:
                await ctx.reply("最近のメッセージが見つかりませんでした。")
                return

            # ランダムなInfantメンバーを取得
            infant = await self._get_random_infant(ctx.guild)
            if not infant:
                await ctx.reply("Infantロールのメンバーが見つかりませんでした。")
                return

            # 話題を抽出してプロンプトを作成
            messages_text = "\n".join(recent_messages[-5:])  # 直近5件のメッセージを使用
            prompt = f"""
            以下の最近のチャット内容から興味深い話題を1つ選び、
            {infant.display_name}さんに意見を求めるメッセージを作成してください：

            最近のチャット：
            {messages_text}

            条件：
            - フレンドリーで親しみやすい口調で
            - 具体的な質問を含める
            - 短めの文章（100文字以内）
            - 絵文字を1-2個使用
            """

            response = await self._generate_response(prompt)
            await ctx.send(f"{infant.mention} {response}")
