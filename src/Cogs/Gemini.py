from datetime import timezone
import discord
import google.generativeai as genai
from discord.ext import commands
import asyncio
from discord.ext import tasks
import random
import datetime
from typing import List, Optional
import re

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
        self.default_initial_prompt = initial_prompt  # デフォルトのプロンプトを保存
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
        # 定期チェックはデフォルトでは開始しない
        self.periodic_infant_check.stop()

    def cog_unload(self):
        """Cogがアンロードされるときにタスクを停止"""
        if self.periodic_infant_check.is_running():
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
    async def stop_periodic_check(self, ctx):
        """定期チェックを停止する"""
        if not self.periodic_infant_check.is_running():
            await ctx.reply("定期チェックは既に停止しています。")
            return
        
        self.periodic_infant_check.cancel()
        await ctx.reply("定期チェックを停止しました。")

    @commands.command()
    @commands.has_role("Parent")
    async def start_periodic_check(self, ctx):
        """定期チェックを開始する"""
        if self.periodic_infant_check.is_running():
            await ctx.reply("定期チェックは既に実行中です。")
            return
        
        self.periodic_infant_check.start()
        await ctx.reply("定期チェックを開始しました。")

    @commands.command()
    @commands.has_role("Parent")
    async def check_status(self, ctx):
        """定期チェックの状態を確認する"""
        status = "実行中" if self.periodic_infant_check.is_running() else "停止中"
        interval = self.periodic_infant_check.minutes  # Changed from hours to minutes
        next_iteration = self.periodic_infant_check.next_iteration
        
        if next_iteration:
            # UTCから日本時間に変換
            jst_next = (next_iteration + datetime.timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')
            await ctx.reply(f"定期チェックの状態:\n"
                          f"- 状態: {status}\n"
                          f"- 間隔: {interval}分\n"
                          f"- 次回実行: {jst_next}")
        else:
            await ctx.reply(f"定期チェックの状態:\n"
                          f"- 状態: {status}\n"
                          f"- 間隔: {interval}分\n"
                          f"- 次回実行: 未定")

    @commands.command()
    @commands.has_role("Parent")
    async def list_channels(self, ctx, category_id: Optional[int] = None):
        """カテゴリーのチャンネル一覧と権限同期状態を表示"""
        try:
            if category_id:
                # 特定のカテゴリーのチャンネルを表示
                category = discord.utils.get(ctx.guild.categories, id=category_id)
                if not category:
                    await ctx.reply(f"指定されたカテゴリー(ID: {category_id})が見つかりませんでした。")
                    return
                
                channels_info = [f"📁 {category.name} のチャンネル一覧:"]
                for channel in category.channels:
                    is_synced = channel.permissions_synced
                    sync_status = "🔄" if is_synced else "❌"
                    channels_info.append(f"{sync_status} {channel.name} (ID: {channel.id})")
            else:
                # すべてのカテゴリーとチャンネルを表示
                channels_info = ["📋 サーバーのチャンネル一覧:"]
                for category in ctx.guild.categories:
                    channels_info.append(f"\n📁 {category.name} (ID: {category.id}):")
                    for channel in category.channels:
                        is_synced = channel.permissions_synced
                        sync_status = "🔄" if is_synced else "❌"
                        channels_info.append(f"  {sync_status} {channel.name} (ID: {channel.id})")

            # メッセージが2000文字を超える場合は分割して送信
            message = "\n".join(channels_info)
            if len(message) > 1990:
                chunks = [message[i:i+1990] for i in range(0, len(message), 1990)]
                for chunk in chunks:
                    await ctx.reply(f"```\n{chunk}\n```")
            else:
                await ctx.reply(f"```\n{message}\n```")

        except Exception as e:
            self.logger.error(f"Error in list_channels: {e}")
            await ctx.reply("チャンネル一覧の取得中にエラーが発生しました。")

    @commands.command()
    @commands.has_role("Parent")
    async def list_categories(self, ctx):
        """サーバーのカテゴリー一覧を表示"""
        try:
            categories = ctx.guild.categories
            if not categories:
                await ctx.reply("カテゴリーが見つかりませんでした。")
                return

            category_info = ["📋 サーバーのカテゴリー一覧:"]
            for category in categories:
                channel_count = len(category.channels)
                category_info.append(f"📁 {category.name} (ID: {category.id}) - チャンネル数: {channel_count}")

            await ctx.reply("\n".join(category_info))

        except Exception as e:
            self.logger.error(f"Error in list_categories: {e}")
            await ctx.reply("カテゴリー一覧の取得中にエラーが発生しました。")

    @commands.command()
    @commands.has_role("Parent")
    async def sync_all_permissions(self, ctx):
        """サーバー内のすべてのチャンネルの権限をそれぞれのカテゴリーの権限に同期させる"""
        try:
            results = {}  # カテゴリーごとの結果を保存
            total_synced = 0
            total_failed = 0

            # 進捗メッセージを送信
            status_msg = await ctx.reply("🔄 すべてのチャンネルの権限を同期中...")

            # すべてのカテゴリーを処理
            for category in ctx.guild.categories:
                synced_channels = []
                failed_channels = []

                for channel in category.channels:
                    try:
                        await channel.edit(sync_permissions=True)
                        synced_channels.append(channel.name)
                        total_synced += 1
                    except Exception as e:
                        self.logger.error(f"Error syncing permissions for channel {channel.name} in category {category.name}: {e}")
                        failed_channels.append(channel.name)
                        total_failed += 1

                results[category.name] = {
                    "synced": synced_channels,
                    "failed": failed_channels
                }

            # 結果をフォーマット
            response = ["📋 権限同期の結果:"]
            response.append(f"\n📊 統計:\n- ✅ 成功: {total_synced}\n- ❌ 失敗: {total_failed}")

            for category_name, result in results.items():
                if result["synced"] or result["failed"]:
                    response.append(f"\n📁 {category_name}:")
                    if result["synced"]:
                        response.append(f"  ✅ 同期成功: {', '.join(result['synced'])}")
                    if result["failed"]:
                        response.append(f"  ❌ 同期失敗: {', '.join(result['failed'])}")

            # 結果が長い場合は分割して送信
            formatted_response = "\n".join(response)
            if len(formatted_response) > 1990:
                # 進捗メッセージを更新
                await status_msg.edit(content="✅ 同期完了！詳細な結果を送信します...")
                
                # 結果を分割して送信
                chunks = [formatted_response[i:i+1990] for i in range(0, len(formatted_response), 1990)]
                for i, chunk in enumerate(chunks):
                    if i == 0:
                        await ctx.reply(f"```\n{chunk}\n```")
                    else:
                        await ctx.send(f"```\n{chunk}\n```")
            else:
                # 進捗メッセージを結果で更新
                await status_msg.edit(content=f"```\n{formatted_response}\n```")

        except Exception as e:
            self.logger.error(f"Error in sync_all_permissions: {e}")
            await ctx.reply("❌ 権限の同期中にエラーが発生しました。")

    @commands.command()
    @commands.has_role("Parent")
    async def sync_permissions(self, ctx, category_id: Optional[int] = None, channel_id: Optional[int] = None):
        """チャンネルの権限をカテゴリーの権限に同期させる"""
        try:
            if channel_id and not category_id:
                # チャンネルIDのみ指定された場合、そのチャンネルを検索
                channel = ctx.guild.get_channel(channel_id)
                if not channel:
                    await ctx.reply(f"指定されたチャンネル(ID: {channel_id})が見つかりませんでした。")
                    return
                category = channel.category
            elif category_id:
                # カテゴリーIDが指定された場合
                category = discord.utils.get(ctx.guild.categories, id=category_id)
                if not category:
                    await ctx.reply(f"指定されたカテゴリー(ID: {category_id})が見つかりませんでした。")
                    return
            else:
                # 両方とも指定されていない場合は赤ちゃん部屋カテゴリーを使用
                category = discord.utils.get(ctx.guild.categories, id=self.BABY_ROOM_CATEGORY_ID)
                if not category:
                    await ctx.reply("赤ちゃん部屋カテゴリーが見つかりませんでした。")
                    return

            if channel_id:
                # 特定のチャンネルのみ同期
                channel = discord.utils.get(category.channels, id=channel_id)
                if not channel:
                    await ctx.reply(f"指定されたチャンネル(ID: {channel_id})が見つかりませんでした。")
                    return
                await channel.edit(sync_permissions=True)
                await ctx.reply(f"チャンネル {channel.name} の権限をカテゴリーと同期しました。")
            else:
                # カテゴリー内のすべてのチャンネルを同期
                synced_channels = []
                failed_channels = []
                for channel in category.channels:
                    try:
                        await channel.edit(sync_permissions=True)
                        synced_channels.append(channel.name)
                    except Exception as e:
                        self.logger.error(f"Error syncing permissions for channel {channel.name}: {e}")
                        failed_channels.append(channel.name)

                # 結果を報告
                response = [f"カテゴリー「{category.name}」の権限同期結果:"]
                if synced_channels:
                    response.append(f"✅ 同期成功: {', '.join(synced_channels)}")
                if failed_channels:
                    response.append(f"❌ 同期失敗: {', '.join(failed_channels)}")
                await ctx.reply("\n".join(response))

        except Exception as e:
            self.logger.error(f"Error in sync_permissions: {e}")
            await ctx.reply("権限の同期中にエラーが発生しました。")

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
    async def help_command(self, ctx):
        """利用可能なコマンドの一覧を表示します"""
        # コマンドの説明を辞書で定義
        commands_help = {
            "gem": "AIと会話します",
            "save_message": "メッセージをデータベースに保存します",
            "get_messages": "保存されたメッセージを表示します",
            "set_history_limit": "チャット履歴の制限を設定します (1-50の間)",
            "set_check_interval": "定期チェックの間隔を設定します (10-1440分の間)",
            "stop_periodic_check": "定期チェックを停止します",
            "start_periodic_check": "定期チェックを開始します",
            "check_status": "定期チェックの状態を確認します",
            "list_channels": "チャンネル一覧と権限同期状態を表示します",
            "list_categories": "カテゴリー一覧を表示します",
            "sync_all_permissions": "すべてのチャンネルの権限を同期します",
            "sync_permissions": "指定したチャンネルまたはカテゴリーの権限を同期します",
            "check_infant": "ランダムなInfantメンバーに声をかけます",
            "discuss_topic": "最近の話題についてInfantメンバーに意見を聞きます",
            "help_command": "このヘルプメッセージを表示します"
        }

        # ユーザーの権限に基づいてコマンドをフィルタリング
        available_commands = []
        is_parent = discord.utils.get(ctx.author.roles, name="Parent") is not None
        is_toddler = discord.utils.get(ctx.author.roles, name="Toddler") is not None

        for cmd_name, cmd_desc in commands_help.items():
            # Parent専用コマンド
            if cmd_name in ["set_check_interval", "stop_periodic_check", "start_periodic_check", 
                          "check_status", "list_channels", "list_categories", "sync_all_permissions", 
                          "sync_permissions", "check_infant", "discuss_topic"]:
                if is_parent:
                    available_commands.append((cmd_name, cmd_desc))
            # Parent/Toddler共用コマンド
            elif cmd_name in ["gem", "save_message", "get_messages", "set_history_limit"]:
                if is_parent or is_toddler:
                    available_commands.append((cmd_name, cmd_desc))
            # 誰でも使えるコマンド
            else:
                available_commands.append((cmd_name, cmd_desc))

        # ヘルプメッセージを構築
        help_lines = ["📋 **利用可能なコマンド一覧**\n"]
        help_lines.append("各コマンドは `!` プレフィックスを付けて使用します。\n")
        
        for cmd_name, cmd_desc in available_commands:
            help_lines.append(f"**!{cmd_name}**\n└ {cmd_desc}\n")

        # メッセージが2000文字を超える場合は分割して送信
        help_message = "\n".join(help_lines)
        if len(help_message) > 1990:
            chunks = [help_message[i:i+1990] for i in range(0, len(help_message), 1990)]
            for chunk in chunks:
                await ctx.reply(chunk)
        else:
            await ctx.reply(help_message)

    @commands.command()
    async def show_prompt(self, ctx):
        """現在のinitial promptを表示します"""
        try:
            # DMでの実行を許可するが、サーバーでは権限チェックを行う
            if ctx.guild is not None:  # サーバーでの実行
                if not discord.utils.get(ctx.author.roles, name="Parent"):
                    await ctx.reply("このコマンドを実行する権限がありません。")
                    return

            current_prompt = self.initial_prompt[0]["parts"][0]
            await ctx.reply(f"📝 **現在のinitial prompt**:\n```\n{current_prompt}\n```")
        except Exception as e:
            self.logger.error(f"Error in show_prompt: {e}")
            await ctx.reply("initial promptの取得中にエラーが発生しました。")

    @commands.command()
    async def set_prompt(self, ctx, *, new_prompt: str):
        """initial promptを新しい内容に設定します"""
        try:
            # DMでの実行を許可するが、サーバーでは権限チェックを行う
            if ctx.guild is not None:  # サーバーでの実行
                if not discord.utils.get(ctx.author.roles, name="Parent"):
                    await ctx.reply("このコマンドを実行する権限がありません。")
                    return

            self.initial_prompt = [{"role": "user", "parts": [new_prompt]}]
        except Exception as e:
            self.logger.error(f"Error in set_prompt: {e}")
            await ctx.reply("initial promptの更新中にエラーが発生しました。")

    @commands.command()
    async def reset_prompt(self, ctx):
        """initial promptをデフォルトの内容に戻します"""
        try:
            # DMでの実行を許可するが、サーバーでは権限チェックを行う
            if ctx.guild is not None:  # サーバーでの実行
                if not discord.utils.get(ctx.author.roles, name="Parent"):
                    await ctx.reply("このコマンドを実行する権限がありません。")
                    return

            self.initial_prompt = [{"role": "user", "parts": [self.default_initial_prompt]}]
            # デフォルトのプロンプトでチャットを初期化
            self.chat = self.model.start_chat(history=self.initial_prompt)
            await ctx.reply("✅ initial promptをデフォルトの内容に戻し、チャットを初期化しました。\n"
                          "現在のプロンプトの内容を確認するには `!show_prompt` を使用してください。")
        except Exception as e:
            self.logger.error(f"Error in reset_prompt: {e}")
            await ctx.reply("initial promptのリセット中にエラーが発生しました。")

    async def _try_natural_language_command(self, text: str, ctx) -> bool:
        """自然言語コマンドを処理する"""
        # サーバーでの実行時のみ権限チェックを行う
        is_parent = False
        if ctx.guild is not None:
            is_parent = discord.utils.get(ctx.author.roles, name="Parent") is not None

        # コマンドのマッピングを定義
        command_patterns = {
            # プロンプト関連のパターンを追加
            ("プロンプト 表示", "プロンプト 確認", "設定 確認"): 
                (self.show_prompt, "現在のプロンプトを表示します"),
            ("プロンプト リセット", "設定 リセット", "デフォルト 戻す"): 
                (self.reset_prompt, "プロンプトをデフォルトに戻します"),
        }

        # プロンプトの更新は特別な処理が必要なため、別途チェック
        if any(pattern in text.lower() for pattern in ["プロンプト 変更", "プロンプト 設定", "設定 変更"]):
            # サーバーでの実行時は権限チェック
            if ctx.guild is not None and not is_parent:
                await ctx.reply("このコマンドを実行する権限がありません。")
                return True

            # "プロンプト変更"の後の文字列を抽出
            import re
            match = re.search(r'(?:プロンプト|設定)(?:変更|設定)[：:]\s*(.+)', text)
            if match:
                new_prompt = match.group(1).strip()
                if new_prompt:
                    try:
                        await self.set_prompt(ctx, new_prompt=new_prompt)
                        return True
                    except Exception as e:
                        self.logger.error(f"Error processing prompt update command: {e}")
                        await ctx.reply("プロンプトの更新中にエラーが発生しました。")
                        return True

        # ユーザーメッセージ削除用のパターン
        purge_patterns = [
            # 通常の削除パターン（チャンネル内）
            r"(.*)(?:の|)メッセージ(?:を|)(.*)[0-9]+件(?:|削除|消去|クリア)(?:して|)",
            r"(.*)(?:の|)メッセージ(?:を|)(?:|削除|消去|クリア)(?:して|)",
            r"(.*)(?:の|発言|コメント)(?:を|全部|すべて)(?:|削除|消去|クリア)(?:して|)",
            
            # サーバー全体からの削除パターン
            r"(.*)(?:の|)メッセージ(?:を|)(?:サーバー全体|サーバー内|すべての?チャンネル)(?:から|で|)(.*)[0-9]+件(?:|削除|消去|クリア)(?:して|)",
            r"(.*)(?:の|)メッセージ(?:を|)(?:サーバー全体|サーバー内|すべての?チャンネル)(?:から|で|)(?:|削除|消去|クリア)(?:して|)",
            r"(.*)(?:の|発言|コメント)(?:を|)(?:サーバー全体|サーバー内|すべての?チャンネル)(?:から|で|全部|すべて)(?:|削除|消去|クリア)(?:して|)",
        ]
        
        for pattern in purge_patterns:
            match = re.search(pattern, text)
            if match:
                # ユーザー名を抽出
                user_name = match.group(1).strip()
                if not user_name:
                    continue
                    
                # 権限チェック
                if hasattr(ctx, 'guild') and ctx.guild:
                    if not any(role.name == "Parent" for role in ctx.author.roles):
                        await ctx.reply("この操作にはParent権限が必要です。")
                        return True
                
                # ユーザーまたはBotを検索
                found_member = None
                for member in ctx.guild.members:
                    if (user_name.lower() in member.display_name.lower() or 
                        user_name.lower() in member.name.lower() or 
                        (member.nick and user_name.lower() in member.nick.lower())):
                        found_member = member
                        break
                
                if found_member:
                    # 数値を抽出
                    num_match = re.search(r'([0-9]+)件', text)
                    limit = int(num_match.group(1)) if num_match else 100
                    
                    # サーバー全体かどうかを判断
                    server_wide = any(keyword in text for keyword in ["サーバー全体", "サーバー内", "すべてのチャンネル", "全チャンネル"])
                    
                    # コマンド実行
                    if server_wide:
                        ctx.command = self.bot.get_command('purge_user_server')
                        await self.purge_user_server(ctx, found_member, limit)
                    else:
                        ctx.command = self.bot.get_command('purge_user')
                        await self.purge_user(ctx, found_member, limit)
                    return True
        
        # 既存のreturn False
        return False

    @commands.command()
    @commands.has_role("Parent")
    async def purge_user(self, ctx, user: discord.Member = None, limit: int = 100, *, server_wide: bool = False):
        """指定したユーザーまたはBotのメッセージを一括削除します
        
        引数:
        user: 削除対象のユーザーまたはBot
        limit: 削除するメッセージの最大件数 (デフォルト: 100)
        server_wide: サーバー全体から検索して削除するかどうか (デフォルト: False)
        """
        # DMでの使用を検出してエラーメッセージを表示
        if not ctx.guild:
            await ctx.send("❌ このコマンドはサーバー内でのみ使用できます。DMでは使用できません。")
            return
            
        if user is None:
            await ctx.send("❌ 削除対象のユーザーまたはBotを指定してください。\n使用例: `!purge_user @ユーザー名 100`")
            return
            
        if limit <= 0 or limit > 1000:
            await ctx.send("削除するメッセージ数は1から1000の間で指定してください。")
            return
            
        # 警告メッセージの準備
        target_scope = "サーバー全体" if server_wide else "このチャンネル"
        user_type = "Bot" if user.bot else "ユーザー"
        warning_text = f"⚠️ **{target_scope}**から**{user.display_name}**({user_type})のメッセージを最大{limit}件削除しますか？\n"
        
        if server_wide:
            warning_text += "**⚠️ 警告: この操作はサーバー内のすべてのチャンネルに影響します！⚠️**\n"
            warning_text += "処理には時間がかかる場合があります。\n"
        
        warning_text += f"確認するには「yes」、キャンセルするには「no」と返信してください。\n"
        warning_text += f"30秒後にタイムアウトします。"
        
        # 確認メッセージを送信
        confirm_msg = await ctx.send(warning_text)
        
        # リアクションの代わりにテキスト応答を待つ
        def check_reply(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["yes", "no", "はい", "いいえ"]
        
        try:
            reply = await self.bot.wait_for('message', timeout=30.0, check=check_reply)
            
            # 確認応答を削除（オプション）
            try:
                await reply.delete()
            except:
                pass
                
            if reply.content.lower() in ["yes", "はい"]:
                user_type_str = "Bot" if user.bot else "ユーザー"
                status_msg = await ctx.send(f"🔍 {user.display_name}({user_type_str})のメッセージを検索中...")
                
                def is_user(m):
                    return m.author.id == user.id  # IDで比較するように変更
                
                deleted_count = 0
                error_channels = []
                
                if server_wide:
                    # サーバー全体の処理
                    progress_msg = await ctx.send("0% 完了")
                    total_channels = len(ctx.guild.text_channels)
                    processed_channels = 0
                    
                    for channel in ctx.guild.text_channels:
                        try:
                            # チャンネルにアクセスできるか確認
                            if not channel.permissions_for(ctx.guild.me).manage_messages:
                                error_channels.append(f"{channel.name} (権限不足)")
                                continue
                                
                            # 進捗状況を更新（レート制限を避けるため更新頻度を下げる）
                            processed_channels += 1
                            if processed_channels % 5 == 0 or processed_channels == total_channels:
                                progress = int((processed_channels / total_channels) * 100)
                                await progress_msg.edit(content=f"{progress}% 完了 - {channel.name}を処理中...")
                            
                            # メッセージ削除
                            try:
                                # 一度に取得するメッセージ数を制限して複数回に分ける
                                batch_size = 100
                                total_deleted = 0
                                
                                for i in range(0, limit, batch_size):
                                    current_limit = min(batch_size, limit - total_deleted)
                                    if current_limit <= 0:
                                        break
                                        
                                    # メッセージを取得して手動でフィルタリング
                                    messages = []
                                    async for msg in channel.history(limit=200):  # 多めに取得
                                        if len(messages) >= current_limit:
                                            break
                                        if msg.author.id == user.id:
                                            messages.append(msg)
                                    
                                    if messages:
                                        # 14日以上前のメッセージは一括削除できないので個別に削除
                                        now = datetime.datetime.now(datetime.timezone.utc)  # タイムゾーン付きで現在時刻を取得
                                        old_messages = []
                                        new_messages = []
                                        
                                        for msg in messages:
                                            # メッセージの作成時刻をUTC with timezoneに統一
                                            msg_time = msg.created_at
                                            if msg_time.tzinfo is None:
                                                msg_time = msg_time.replace(tzinfo=datetime.timezone.utc)
                                                
                                            # 14日以上前かどうかを判定
                                            if (now - msg_time).days >= 14:
                                                old_messages.append(msg)
                                            else:
                                                new_messages.append(msg)
                                        
                                        # 新しいメッセージは一括削除
                                        if new_messages:
                                            await channel.delete_messages(new_messages)
                                            
                                        # 古いメッセージは個別に削除
                                        for msg in old_messages:
                                            try:
                                                await msg.delete()
                                                # レート制限を避けるため少し待機
                                                await asyncio.sleep(0.5)
                                            except Exception as e:
                                                self.logger.error(f"Error deleting old message: {e}")
                                        
                                        total_deleted += len(messages)
                                        deleted_count += len(messages)
                                    
                                    # バッチ間で待機
                                    await asyncio.sleep(1)
                                    
                                    if total_deleted >= limit:
                                        break
                            except discord.Forbidden:
                                error_channels.append(f"{channel.name} (権限不足)")
                            except discord.HTTPException as e:
                                self.logger.error(f"HTTP error in {channel.name}: {e}")
                                error_channels.append(f"{channel.name} (HTTPエラー)")
                            except Exception as e:
                                self.logger.error(f"Error deleting messages in {channel.name}: {e}")
                                error_channels.append(f"{channel.name} (エラー: {str(e)})")
                            
                            # APIレート制限を考慮して少し待機
                            await asyncio.sleep(1)
                            
                        except discord.Forbidden:
                            error_channels.append(f"{channel.name} (権限不足)")
                        except Exception as e:
                            self.logger.error(f"Error accessing channel {channel.name}: {e}")
                            error_channels.append(f"{channel.name} (エラー: {str(e)})")
                    
                    # 進捗メッセージを削除
                    try:
                        await progress_msg.delete()
                    except:
                        pass
                else:
                    # 単一チャンネルの処理
                    try:
                        # 一度に取得するメッセージ数を制限して複数回に分ける
                        batch_size = 100
                        total_deleted = 0
                        
                        for i in range(0, limit, batch_size):
                            current_limit = min(batch_size, limit - total_deleted)
                            if current_limit <= 0:
                                break
                                
                            # メッセージを取得して手動でフィルタリング
                            messages = []
                            async for msg in ctx.channel.history(limit=200):  # 多めに取得
                                if len(messages) >= current_limit:
                                    break
                                if msg.author.id == user.id:
                                    messages.append(msg)
                            
                            if messages:
                                # 14日以上前のメッセージは一括削除できないので個別に削除
                                now = datetime.datetime.now(datetime.timezone.utc)  # タイムゾーン付きで現在時刻を取得
                                old_messages = []
                                new_messages = []
                                
                                for msg in messages:
                                    # メッセージの作成時刻をUTC with timezoneに統一
                                    msg_time = msg.created_at
                                    if msg_time.tzinfo is None:
                                        msg_time = msg_time.replace(tzinfo=datetime.timezone.utc)
                                        
                                    # 14日以上前かどうかを判定
                                    if (now - msg_time).days >= 14:
                                        old_messages.append(msg)
                                    else:
                                        new_messages.append(msg)
                                
                                # 新しいメッセージは一括削除
                                if new_messages:
                                    await ctx.channel.delete_messages(new_messages)
                                    
                                # 古いメッセージは個別に削除
                                for msg in old_messages:
                                    try:
                                        await msg.delete()
                                        # レート制限を避けるため少し待機
                                        await asyncio.sleep(0.5)
                                    except Exception as e:
                                        self.logger.error(f"Error deleting old message: {e}")
                                
                                total_deleted += len(messages)
                                deleted_count += len(messages)
                            
                            # バッチ間で待機
                            await asyncio.sleep(1)
                            
                            if total_deleted >= limit:
                                break
                    except discord.Forbidden:
                        await status_msg.edit(content="❌ メッセージを削除する権限がありません。")
                        return
                    except discord.HTTPException as e:
                        self.logger.error(f"HTTP error: {e}")
                        await status_msg.edit(content=f"❌ HTTPエラーが発生しました: {str(e)}")
                        return
                    except Exception as e:
                        self.logger.error(f"Error purging messages: {e}")
                        await status_msg.edit(content=f"❌ エラーが発生しました: {str(e)}")
                        return
                
                # 結果報告
                user_type_str = "Bot" if user.bot else "ユーザー"
                result_msg = f"✅ {user.display_name}({user_type_str})のメッセージを{deleted_count}件削除しました。"
                if error_channels:
                    result_msg += f"\n⚠️ 以下のチャンネルでエラーが発生しました：\n" + "\n".join(error_channels[:10])
                    if len(error_channels) > 10:
                        result_msg += f"\n...他{len(error_channels) - 10}チャンネル"
                
                await status_msg.edit(content=result_msg)
            else:
                await ctx.send("操作をキャンセルしました。")
                
        except asyncio.TimeoutError:
            await ctx.send("タイムアウトしました。操作をキャンセルします。")
        
        # 確認メッセージを削除
        try:
            await confirm_msg.delete()
        except:
            pass

    @commands.command()
    @commands.has_role("Parent")
    async def purge_user_server(self, ctx, user: discord.Member = None, limit: int = 100):
        """サーバー全体から指定したユーザーのメッセージを一括削除します"""
        # DMでの使用を検出してエラーメッセージを表示
        if not ctx.guild:
            await ctx.send("❌ このコマンドはサーバー内でのみ使用できます。DMでは使用できません。")
            return
            
        if user is None:
            await ctx.send("❌ 削除対象のユーザーを指定してください。\n使用例: `!purge_user_server @ユーザー名 100`")
            return
            
        await self.purge_user(ctx, user, limit, server_wide=True)
