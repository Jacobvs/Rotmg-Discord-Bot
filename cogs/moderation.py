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
    async def find(self, ctx, name):
        """Find a user by the specified nickname"""
        name = name.strip()
        member = ctx.guild.get_member_named(name)
        if member is not None:
            if member.voice is None:
                vc = '❌'
            else:
                vc = "#" + member.voice.channel.name
            embed = discord.Embed(
                description=f"Found member with the ign: [{member.nick}]"
                            f"(https://www.realmeye.com/player/{member.nick}): {member.mention}"
                            f"\nVoice Channel: {vc}"
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(description=f"No members found with the nickname: `{name}`\nTip: This command is "
            f"case sensitive")
            await ctx.send(embed=embed)

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