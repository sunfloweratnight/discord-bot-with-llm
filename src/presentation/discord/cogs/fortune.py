"""Thin Discord presentation for fortune — no business logic."""

from __future__ import annotations

from discord.ext import commands

from src.Cogs.Utils import sanitize_args
from src.domain.decision.models import DecisionConfigError, DecisionUnavailableError
from src.domain.fortune.models import InsufficientHistoryError, TellFortuneCommand
from src.presentation.discord.formatters.fortune_embed import (
    build_fortune_embed,
    format_fortune_content,
)
from src.usecases.fortune import TellFortuneUseCase


class Fortune(commands.Cog):
    HISTORY_SCAN_LIMIT = 200
    AUTHOR_MESSAGE_LIMIT = 10

    def __init__(self, bot, logger, use_case: TellFortuneUseCase, decision_closer) -> None:
        self.bot = bot
        self.logger = logger
        self._use_case = use_case
        self._decision_closer = decision_closer

    def cog_unload(self):
        try:
            self.bot.loop.create_task(self._decision_closer.aclose())
        except Exception:
            pass

    @commands.command(name="運勢", aliases=["fortune"])
    @commands.guild_only()
    async def fortune(self, ctx: commands.Context, *args):
        """直近の発言から今日の運勢を占います。"""
        note = sanitize_args(args)
        async with ctx.typing():
            messages = await self._fetch_author_messages(ctx)
            command = TellFortuneCommand(
                user_id=ctx.author.id,
                display_name=ctx.author.display_name,
                channel_id=ctx.channel.id,
                channel_name=ctx.channel.name,
                recent_messages=messages,
                note=note,
            )
            try:
                result = await self._use_case.execute(command)
            except InsufficientHistoryError:
                await ctx.reply(
                    "まだ発言が少なすぎて占えないよ〜 🥺\n"
                    "このチャンネルでもうちょっとしゃべってから "
                    "`!運勢` してね ♡"
                )
                return
            except DecisionConfigError as exc:
                self.logger.error(f"Fortune DecisionConfigError: {exc}")
                await ctx.reply(str(exc))
                return
            except DecisionUnavailableError as exc:
                self.logger.error(f"Fortune DecisionUnavailableError: {exc}")
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
