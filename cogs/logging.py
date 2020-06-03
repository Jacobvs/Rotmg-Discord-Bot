import asyncio

import discord
from discord.ext import commands

import embeds
import sql
import utils
from checks import is_rl_or_higher_check
from cogs.Raiding.logrun import LogRun


class Logging(commands.Cog):
    """Run Logging"""

    def __init__(self, client):
        self.client = client

    @commands.command(usage="!pop <key/event/vial/helm/shield/sword> <@member> {number}")
    @commands.guild_only()
    @commands.check(is_rl_or_higher_check)
    async def pop(self, ctx, type, member: discord.Member, number: int = 1):
        """Log key pops"""
        type = type.lower()
        if type not in ["key", "event", "vial", "helm", "shield", "sword"]:
            embed = discord.Embed(title="Error!", description="Please choose a proper key option!\nUsage: `!pop <key/event/vial/helm/"
                                                              "shield/sword> <@member> {number}`", color=discord.Color.red())
            return await ctx.send(embed)

        col = sql.log_cols.pkey if type == "key" else sql.log_cols.eventkeys if type == "event" else sql.log_cols.vials if type == "vial"\
            else sql.log_cols.helmrunes if type == "helm" else sql.log_cols.shieldrunes if type == "shield" else sql.log_cols.swordrunes
        await sql.log_runs(self.client.pool, ctx.guild.id, member.id, col, number)

        embed = discord.Embed(title="Key Logged!", description=f"Successfully logged {number} popped {type}(s) for {member.mention}",
                              color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.command(usage="!logrun {@member (leader)} {num_runs}")
    @commands.guild_only()
    @commands.check(is_rl_or_higher_check)
    async def logrun(self, ctx, member:discord.Member=None, number=1):
        """Log a full run manually"""
        if not member:
            member = ctx.author

        msg = await ctx.send(embed=embeds.dungeon_select())
        def dungeon_check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

        while True:
            try:
                msg = await self.client.wait_for('message', timeout=60, check=dungeon_check)
            except asyncio.TimeoutError:
                embed = discord.Embed(title="Timed out!", description="You didn't choose a dungeon in time!", color=discord.Color.red())
                await msg.clear_reactions()
                return await msg.edit(embed=embed)

            if msg.content.isdigit():
                if 0 < int(msg.content) < 51:
                    break
            await ctx.send("Please choose a number between 1-50!", delete_after=7)

        await msg.delete()
        dungeon_info = utils.dungeon_info(int(msg.content))
        dungeontitle = dungeon_info[0]
        emojis = dungeon_info[1]
        guild_db = self.client.guild_db.get(ctx.guild.id)
        logrun = LogRun(self.client, ctx, emojis, [], dungeontitle, [member.id], guild_db.get(sql.gld_cols.rlroleid), numruns=number)
        await logrun.start()


def setup(client):
    client.add_cog(Logging(client))
