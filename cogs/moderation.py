import json

import sql
from discord.ext import commands
import cogs.verification as verification


class Moderation(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command()
    async def change_prefix(self, ctx, prefix):
        """Change the bot's prefix for commands"""
        with open('data/prefixes.json', 'r') as file:
            prefixes = json.load(file)

        prefixes[str(ctx.guild.id)] = prefix

        with open('data/prefixes.json', 'w') as file:
            json.dump(prefixes, file, indent=4)

    @commands.command()
    async def manual_verify(self, ctx, uid):
        guild_data = sql.get_guild(ctx.guild.id)
        member = ctx.guild.get_member(int(uid))
        user_data = sql.get_user(int(uid))

        await verification.complete_verification(ctx.guild, guild_data, member, user_data, True)
        channel = self.client.get_channel(guild_data[sql.gld_cols.manualverifychannel])
        message = await channel.fetch_message(user_data[sql.usr_cols.verifyid])
        await message.delete()
        await ctx.message.delete()
        await channel.send(f"{member.mention} has been manually verified.")


def setup(client):
    client.add_cog(Moderation(client))