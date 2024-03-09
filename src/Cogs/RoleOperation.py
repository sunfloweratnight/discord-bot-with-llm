import re

import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal, Optional


class RoleOperation(commands.Cog):
    def __init__(self, bot, logger):
        self.log_channel = None
        self.members = []
        self.public_channels = []
        self.private_channels = []
        self.bot = bot
        self.logger = logger
        self.log_channel = 1148894899358404618
        self.guild_id = 1030501230797131887
        self.guild = None
        self.history = []

    @commands.Cog.listener()
    async def on_ready(self):
        self.logger.info(f"Connecting to the channel")
        self.guild = self.bot.get_guild(self.guild_id)
        await self.bot.tree.sync(guild=discord.Object(id=self.guild_id))
        self.logger.info(f'Connected to {self.guild.name}')

        async for member in self.guild.fetch_members(limit=None):
            if not member.bot and [role for role in member.roles if role.name != 'Parent']:
                self.members.append(member)

        for channel in self.guild.text_channels:
            if channel.overwrites == {}:
                self.public_channels.append(channel)
            else:
                self.private_channels.append(channel)

            # async for message in channel.history(limit=None):
            #     self.logger.info(f'getting {message}')
            #     self.history.append(message)

        self.log_channel = self.guild.get_channel(self.log_channel)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        self.logger.info(f'{member.name} joined the server')
        await self.log_channel.send(f'{member.mention} joined the server! Hello Baby!')
        await self.assign_role(member.guild, member, 'Infant')

    @commands.Cog.listener()
    async def on_message(self, message):
        author, content = message.author, message.content
        sanitized_content = re.sub("<@\d+>", "", content).strip()
        member_roles = [role.name for role in author.roles]
        public_channels_ids = [channel.id for channel in self.public_channels]

        is_message_empty = len(sanitized_content) == 0
        is_author_bot = author.bot
        is_in_public_channels = message.channel.id in public_channels_ids
        is_author_infant = "Infant" in member_roles

        if not is_message_empty and not is_author_bot and is_in_public_channels and is_author_infant:
            self.logger.info(f'{author.display_name} said {message.content}')
            await self.assign_role(message.guild, author, 'Toddler')
            await self.remove_role(message.guild, author, 'Infant')
            await self.log_channel.send(
                f'{author.mention} said their first word! They are Toddler now! {message.jump_url}')

    @app_commands.command(name="shutdown", description="Shutting down the bot.")
    @app_commands.guilds(1030501230797131887)
    async def shutdown(self, interaction: discord.Interaction):
        self.logger.info(f"Shutting down the bot")
        await self.log_channel.send(f"Shutting down the bot")
        await self.bot.close()

    @commands.command()
    @commands.guild_only()
    @commands.is_owner()
    async def sync(self, ctx: commands.Context, guilds: commands.Greedy[discord.Object],
                   spec: Optional[Literal["~", "*", "^"]] = None) -> None:
        async with ctx.typing():
            if not guilds:
                if spec == "~":
                    self.logger.info(f"Syncing the tree to the current guild")
                    synced = await ctx.bot.tree.sync(guild=ctx.guild)
                elif spec == "*":
                    self.logger.info(f"Syncing the tree globally")
                    ctx.bot.tree.copy_global_to(guild=ctx.guild)
                    synced = await ctx.bot.tree.sync(guild=ctx.guild)
                elif spec == "^":
                    self.logger.info(f"Clearing the tree to the current guild and syncing it.")
                    ctx.bot.tree.clear_commands(guild=ctx.guild)
                    await ctx.bot.tree.sync(guild=ctx.guild)
                    synced = []
                else:
                    synced = await ctx.bot.tree.sync()

                self.logger.info(
                    f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}")
                await ctx.send(
                    f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
                )
                return

            ret = 0
            for guild in guilds:
                try:
                    await ctx.bot.tree.sync(guild=guild)
                except discord.HTTPException:
                    pass
                else:
                    ret += 1

            self.logger.info(f"Synced the tree to {ret}/{len(guilds)}.")
            await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

    @staticmethod
    async def remove_role(guild, member, role_name):
        role = discord.utils.get(guild.roles, name=role_name)
        await member.remove_roles(role)

    @staticmethod
    async def assign_role(guild, member, role_name):
        role = discord.utils.get(guild.roles, name=role_name)
        await member.add_roles(role)
