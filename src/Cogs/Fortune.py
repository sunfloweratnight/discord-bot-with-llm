"""Fortune-telling cog powered by TypeSafe Jev (PROJECT.md §13)."""

from __future__ import annotations

import discord
from discord.ext import commands

from Config import settings
from src.Cogs.Utils import sanitize_args
from src.FortuneSchema import (
    build_fortune_embed,
    build_fortune_state,
    format_fortune_content,
    parse_fortune_answers,
)
from src.JevClient import JevClient, JevClientError


class Fortune(commands.Cog):
    HISTORY_SCAN_LIMIT = 200
    AUTHOR_MESSAGE_LIMIT = 10

    def __init__(self, bot, logger) -> None:
        self.bot = bot
        self.logger = logger
        self.jev = JevClient(settings.TYPESAFE_API_KEY)

    def cog_unload(self):
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
                    "まだ発言が少なすぎて占えないよ〜 🥺\n"
                    "このチャンネルでもうちょっとしゃべってから "
                    "`!運勢` してね ♡"
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
                await ctx.reply(
                    "あれれ、占いがうまくいかなかったみたい… 😿\n"
                    "ちょっと待ってからもういちど試してね。"
                )
                return

            embed = build_fortune_embed(ctx.author.display_name, result)
            if ctx.author.display_avatar:
                embed.set_thumbnail(url=ctx.author.display_avatar.url)
            await ctx.reply(
                content=format_fortune_content(ctx.author.display_name, result),
                embed=embed,
            )

    async def _fetch_author_messages(self, ctx: commands.Context) -> list[str]:
        collected: list[str] = []
        async for msg in ctx.channel.history(limit=self.HISTORY_SCAN_LIMIT):
            if msg.author.id != ctx.author.id:
                continue
            if msg.author.bot:
                continue
            content = (msg.content or "").strip()
            if msg.id == ctx.message.id:
                continue
            if not content:
                continue
            collected.append(content)
            if len(collected) >= self.AUTHOR_MESSAGE_LIMIT:
                break
        collected.reverse()
        return collected

    @fortune.error
    async def fortune_error(self, ctx: commands.Context, error: Exception):
        if isinstance(error, commands.NoPrivateMessage):
            await ctx.reply("このコマンドはサーバーのなかだけで使えるよ〜 🏠")
            return
        self.logger.error(f"Fortune command error: {error}")
        await ctx.reply(
            "あれれ、占いがうまくいかなかったみたい… 😿\n"
            "ちょっと待ってからもういちど試してね。"
        )
