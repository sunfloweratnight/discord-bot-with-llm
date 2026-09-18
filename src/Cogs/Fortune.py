"""Fortune-telling cog powered by TypeSafe Jev (PROJECT.md §13)."""

from __future__ import annotations

import discord
from discord.ext import commands

from Config import settings
from src.Cogs.Utils import sanitize_args
from src.FortuneSchema import (
    build_fortune_state,
    parse_fortune_answers,
)
from src.JevClient import JevClient, JevClientError


class Fortune(commands.Cog):
    HISTORY_SCAN_LIMIT = 200
    AUTHOR_MESSAGE_LIMIT = 10
    CAUTION_THRESHOLD = 0.6

    def __init__(self, bot, logger) -> None:
        self.bot = bot
        self.logger = logger
        self.jev = JevClient(settings.TYPESAFE_API_KEY)

    def cog_unload(self):
        # Ensure async close is scheduled if event loop is running
        try:
            self.bot.loop.create_task(self.jev.aclose())
        except Exception:
            pass

    @commands.command(name="運勢", aliases=["fortune"])
    @commands.guild_only()
    async def fortune(self, ctx: commands.Context, *args):
        """直近の発言から今日の運勢を占います。"""
        note = sanitize_args(args)
        async with ctx.typing():
            messages = await self._fetch_author_messages(ctx)
            if not messages:
                await ctx.reply(
                    "占うための発言がまだ足りません。"
                    "このチャンネルでもう少し話してからもう一度 `!運勢` してください。"
                )
                return

            state = build_fortune_state(
                display_name=ctx.author.display_name,
                user_id=ctx.author.id,
                channel_name=ctx.channel.name,
                channel_id=ctx.channel.id,
                messages=messages,
                extra=note,
            )

            try:
                answers = await self.jev.evaluate_fortune(state)
                result = parse_fortune_answers(answers)
            except JevClientError as exc:
                self.logger.error(f"Fortune JevClientError: {exc}")
                await ctx.reply(str(exc))
                return
            except Exception as exc:
                self.logger.error(f"Fortune unexpected error: {exc}")
                await ctx.reply("占いに失敗しました。しばらくしてからもう一度試してください。")
                return

            await ctx.reply(embed=self._build_embed(ctx.author.display_name, result))

    async def _fetch_author_messages(self, ctx: commands.Context) -> list[str]:
        collected: list[str] = []
        async for msg in ctx.channel.history(limit=self.HISTORY_SCAN_LIMIT):
            if msg.author.id != ctx.author.id:
                continue
            if msg.author.bot:
                continue
            content = (msg.content or "").strip()
            # Skip the invoking command line itself
            if msg.id == ctx.message.id:
                continue
            if not content:
                continue
            collected.append(content)
            if len(collected) >= self.AUTHOR_MESSAGE_LIMIT:
                break
        collected.reverse()  # oldest → newest
        return collected

    def _build_embed(self, display_name: str, result) -> discord.Embed:
        description = None
        if result.caution >= self.CAUTION_THRESHOLD:
            description = (
                f"⚠️ 慎重モード寄りです（慎重度 {result.caution:.0%}）。"
                "無理せずペースを大切に。"
            )

        embed = discord.Embed(
            title=f"{display_name} さんの今日の運勢",
            description=description,
            color=0xF0C05A,
        )
        embed.add_field(name="総合", value=result.overall, inline=True)
        embed.add_field(name="恋愛・対人", value=result.love, inline=True)
        embed.add_field(name="仕事・勉強", value=result.work, inline=True)
        embed.add_field(name="金運", value=result.money, inline=True)
        embed.add_field(name="健康", value=result.health, inline=True)
        embed.add_field(name="気分", value=result.mood_label, inline=True)
        embed.add_field(name="今日のアドバイス", value=result.advice, inline=False)

        footer_parts = []
        if result.overall_probability is not None:
            footer_parts.append(f"総合の確率 {result.overall_probability:.0%}")
        if result.overall_confidence is not None:
            footer_parts.append(f"確信度 {result.overall_confidence:.0%}")
        footer_parts.append("powered by Jev")
        embed.set_footer(text=" · ".join(footer_parts))
        return embed

    @fortune.error
    async def fortune_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.reply("このコマンドはサーバー内でのみ使えます。")
            return
        self.logger.error(f"Fortune command error: {error}")
        await ctx.reply("占いに失敗しました。しばらくしてからもう一度試してください。")
