import re

import discord
from discord.ext import commands


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

    @staticmethod
    async def remove_role(guild, member, role_name):
        role = discord.utils.get(guild.roles, name=role_name)
        await member.remove_roles(role)

    @staticmethod
    async def assign_role(guild, member, role_name):
        role = discord.utils.get(guild.roles, name=role_name)
        await member.add_roles(role)
