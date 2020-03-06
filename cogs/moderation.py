import datetime
import json

import discord
from discord.ext import commands

import sql
from checks import is_rl_or_higher_check
from cogs import verification


class Moderation(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command(usage="!change_prefix [prefix]")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def change_prefix(self, ctx, prefix):
        """Change the bot's prefix for all commands"""
        with open('data/prefixes.json', 'r') as file:
            prefixes = json.load(file)

        prefixes[str(ctx.guild.id)] = prefix

        with open('data/prefixes.json', 'w') as file:
            json.dump(prefixes, file, indent=4)

        await ctx.send(f"The prefix for this server has been changed to '{prefix}'.")

    @commands.command(usage="!find [nickname]")
    @commands.guild_only()
    @commands.check(is_rl_or_higher_check)
    async def find(self, ctx, mem):
        """Find a user by the specified nickname"""
        converter = discord.ext.commands.MemberConverter()
        try:
            member = await converter.convert(ctx, mem)
        except discord.ext.commands.BadArgument:
            if isinstance(mem, str):
                try:
                    member = await converter.convert(ctx, mem.capitalize())
                except discord.ext.commands.BadArgument:
                    embed = discord.Embed(
                        description=f"No members found with the name: `{mem}`\nTip: This command is case-sensitive.",
                        color=discord.Color.red())
                    return await ctx.send(embed=embed)
            else:
                embed = discord.Embed(description=f"No members found with the name: `{mem}`\nTip: This command is case-sensitive.", color=discord.Color.red())
                return await ctx.send(embed=embed)
        if member.voice is None:
            vc = '❌'
        else:
            vc = "#" + member.voice.channel.name

        if member.nick and " | " in member.nick:
            names = member.nick.split(" | ")
            desc = f"Found {member.mention} with the ign's: "
            desc += " | ".join(['['+''.join([n for n in name if n.isalpha()])+'](https://www.realmeye.com/player/'+''.join([n for n in name if n.isalpha()])+")" for name in names])
            desc += f"\nVoice Channel: {vc}"
        else:
            name = ''.join([i for i in member.display_name if i.isalpha()])
            desc = f"Found {member.mention} with the ign: [{name}](https://www.realmeye.com/player/{name})\nVoice Channel: {vc}"
        embed = discord.Embed(
            description=desc,
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

    @commands.command(usage="!purge [num] [ignore_pinned]")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, num=5, ignore_pinned=0):
        """Removes [num] messages from the channel, ignore_pinned = 0 to ignore, 1 to delete pinned"""
        num += 1
        if not isinstance(num, int):
            await ctx.send("Please pass in a number of messages to delete.")
            return

        no_older_than = datetime.datetime.utcnow()-datetime.timedelta(days=14)+datetime.timedelta(seconds=1)
        if ignore_pinned == 0:
            n = len(await ctx.channel.purge(limit=num, check=is_not_pinned, after=no_older_than, bulk=True))
        else:
            n = len(await ctx.channel.purge(limit=num, after=no_older_than, bulk=True))
        if n < num:
            return await ctx.send("You are trying to delete messages that are older than 15 days. Discord API doesn't "
                                  "allow bots to do this!\nYou can use the nuke command to completely clean a "
                                  "channel.", delete_after=10)
        await ctx.send(f"Deleted {n-1} messages.", delete_after=5)

    @commands.command(usage='!nuke "I confirm this action."')
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def nuke(self, ctx, confirmation=""):
        """Deletes all the messages in a channel"""
        if confirmation == "I confirm this action.":
            newc = await ctx.channel.clone()
            await newc.edit(position=ctx.channel.position)
            await ctx.channel.delete()
        else:
            return await ctx.send('Please confirm you would like to do this by running: `!nuke "I confirm this '
                                  'action."`\n**__THIS WILL DELETE ALL MESSAGES IN THE CHANNEL!__**')

    @commands.command(usage="!manual_verify [uid] {optional: ign}")
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def manual_verify(self, ctx, uid, ign=None):
        """Manually verifies user with specified uid"""
        guild_data = sql.get_guild(ctx.guild.id)
        member = ctx.guild.get_member(int(uid))
        user_data = sql.get_user(int(uid))

        if user_data is not None:
            name = user_data[sql.usr_cols.ign]
            status = user_data[sql.usr_cols.status]
            if status != 'verified':
                if status != "stp_1" and status != "stp_2":
                    if status == 'deny_appeal':
                        channel = self.client.get_channel(guild_data[sql.gld_cols.manualverifychannel])
                        message = await channel.fetch_message(user_data[sql.usr_cols.verifyid])
                        await message.delete()
                    if ign is not None:
                        name = ign
                elif ign is not None:
                    name = ign
                else:
                    await ctx.send("Please specify an IGN for this user.")
                    return
            else:
                await ctx.send("The specified member has already been verified.")
        elif ign is not None:
            sql.add_new_user(int(uid), ctx.guild.id, None)
            user_data = sql.get_user(int(uid))
            name = ign
        else:
            await ctx.send("Please specify an IGN for this user.")
            return

        await verification.complete_verification(ctx.guild, guild_data, member, name, user_data, True)
        await ctx.message.delete()
        await ctx.send(f"{member.mention} has been manually verified.")


def setup(client):
    client.add_cog(Moderation(client))

def is_not_pinned(msg):
    return False if msg.pinned else True