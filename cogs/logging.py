import asyncio
import datetime

import discord
from discord.ext import commands

import checks
import embeds
import sql
import utils
from cogs.Raiding.logrun import LogRun
from cogs.Raiding.vc_select import VCSelect


class Logging(commands.Cog):
    """Run Logging"""

    def __init__(self, client):
        self.client = client

    @commands.command(usage="pop <key/event/vial/helm/shield/sword> <member> [number]",
                      description="Log when a member pops something for the server.")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def pop(self, ctx, t, member: utils.MemberLookupConverter, number: int = 1):
        kind = t.lower()
        if kind not in ["key", "event", "vial", "helm", "shield", "sword"]:
            embed = discord.Embed(title="Error!", description="Please choose a proper key option!\nUsage: `!pop <key/event/vial/helm/"
                                                              "shield/sword> <@member> {number}`", color=discord.Color.red())
            return await ctx.send(embed=embed)
        if number < -100 or number > 100 or number == 0:
            embed = discord.Embed(title="Error!", description="Please specify a number between -100 and 100!\nUsage: `!pop <key/event/vial/helm/"
                                                              "shield/sword> <@member> {number}`", color=discord.Color.red())
            return await ctx.send(embed=embed)


        col = sql.log_cols.pkey if kind == "key" else sql.log_cols.eventkeys if kind == "event" else sql.log_cols.vials if kind == "vial"\
            else sql.log_cols.helmrunes if kind == "helm" else sql.log_cols.shieldrunes if kind == "shield" else sql.log_cols.swordrunes
        num = await sql.log_runs(self.client.pool, ctx.guild.id, member.id, col, number)

        if kind != 'event':
            await utils.check_pops(self.client, member, number, num, type=kind, ctx=ctx)
        embed = discord.Embed(title="Key Logged!", description=f"Successfully logged {number} popped {kind}(s) for {member.mention}",
                              color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.command(usage="logrun [member (leader)] [num_runs]", description="Log a full run (or multiple runs) manually.")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def logrun(self, ctx, member: utils.MemberLookupConverter=None, number=1):
        if not member:
            member = ctx.author

        setup = VCSelect(self.client, ctx, manual_log=True)
        data = await setup.start()
        if isinstance(data, tuple):
            (raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg) = data
        else:
            return

        try:
            await setup_msg.delete()
        except discord.NotFound:
            pass
        r_msg = await ctx.send(embed=embeds.dungeon_select(manual_log=True))
        def dungeon_check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()

        while True:
            try:
                msg = await self.client.wait_for('message', timeout=60, check=dungeon_check)
            except asyncio.TimeoutError:
                embed = discord.Embed(title="Timed out!", description="You didn't choose a dungeon in time!", color=discord.Color.red())
                await r_msg.clear_reactions()
                return await r_msg.edit(embed=embed)

            if msg.content.isdigit():
                if 0 < int(msg.content) < 56:
                    break
            await ctx.send("Please choose a number between 1-55!", delete_after=7)

        await r_msg.delete()
        dungeon_info = utils.dungeon_info(int(msg.content))
        try:
            await msg.delete()
        except discord.NotFound:
            pass
        dungeontitle = dungeon_info[0]
        emojis = dungeon_info[1]
        guild_db = self.client.guild_db.get(ctx.guild.id)
        logrun = LogRun(self.client, ctx.author, ctx.channel, ctx.guild, emojis, [], dungeontitle, [member.id], guild_db.get(sql.gld_cols.rlroleid), hcchannel,
                        events=inevents, vialreacts=[], helmreacts=[], shieldreacts=[], swordreacts=[], numruns=number, runleader=member)
        await logrun.start()
        
    @commands.command(usage="updateleaderboard", description="Manually updates the leaderboard in this server.")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def updateleaderboard(self, ctx):
        await ctx.message.delete()
        if ctx.guild.id in self.client.serverwleaderboard:
            embed = discord.Embed(title="Success!", description="The leaderboards are being updated & will be posted soon!",
                                  color=discord.Color.green())
            await ctx.send(embed=embed)
            return await update_leaderboard(self.client, ctx.guild.id)
        return await ctx.send("This server does not have leaderboards enabled! Contact Darkmattr#7321 to enable them.", delete_after=7)

    @commands.command(usage='leaderboard <type>', description='Display the top 20 members in a selected logging category.\nValid categories: `keys`, `runes`, `runs`, `led`, '
                                                              '`weeklyled`', aliases=['lb'])
    @commands.guild_only()
    async def leaderboard(self, ctx, type):
        type = type.strip().lower()
        if type not in ['keys', 'runes', 'runs', 'led', 'weeklyled']:
            return await ctx.send("Please choose a valid log type:\nValid categories: `keys`, `runes`, `runs`, `led`, `weeklyled`")

        if type == 'runes':
            helmrunes = await sql.get_top_10_logs(self.client.pool, ctx.guild.id, sql.log_cols.helmrunes, only_10=False)
            swordrunes = await sql.get_top_10_logs(self.client.pool, ctx.guild.id, sql.log_cols.swordrunes, only_10=False)
            shieldrunes = await sql.get_top_10_logs(self.client.pool, ctx.guild.id, sql.log_cols.shieldrunes, only_10=False)
            top_runes = {}
            for r in helmrunes:
                top_runes[r[0]] = (r[0], r[sql.log_cols.helmrunes])
            for r in swordrunes:
                if r[0] in top_runes:
                    top_runes[r[0]] = (r[0], top_runes[r[0]][1] + r[sql.log_cols.swordrunes])
                else:
                    top_runes[r[0]] = (r[0], r[sql.log_cols.swordrunes])
            for r in shieldrunes:
                if r[0] in top_runes:
                    top_runes[r[0]] = (r[0], top_runes[r[0]][1] + r[sql.log_cols.shieldrunes])
                else:
                    top_runes[r[0]] = (r[0], r[sql.log_cols.shieldrunes])
            runes = list(top_runes.values())

            def get_num(elem):
                return elem[1]

            runes.sort(key=get_num, reverse=True)
            top = format_top_data(runes[:20], 1, aslist=True)
        else:
            col = sql.log_cols.pkey if type == 'keys' else sql.log_cols.runsdone if type == 'runs' else sql.log_cols.srunled if type == 'led' else sql.log_cols.weeklyruns
            top = await sql.get_top_10_logs(self.client.pool, ctx.guild.id, column=col, only_10=False, limit=20)
            top = format_top_data(top, col, aslist=True)

        name = 'Keys' if type == 'keys' else "Runes" if type == 'runes' else "Runs Completed" if type == 'runs' else "Runs Led" if type == 'led' else "Weekly Runs Led"
        embed = discord.Embed(title=f"Top {name} in {ctx.guild.name}", color=discord.Color.gold()).add_field(name='Top 10', value="".join(top[:10]), inline=False)
        if len(top) > 10:
            embed.add_field(name="Top 20", value="".join(top[10:]), inline=False)
        embed.set_thumbnail(url=ctx.guild.icon_url)
        embed.timestamp = datetime.datetime.utcnow()
        await ctx.send(embed=embed)

        

def setup(client):
    client.add_cog(Logging(client))


async def update_leaderboards(client):
    while(True):
        startofweek = (datetime.datetime.today() + datetime.timedelta(days=7 - datetime.datetime.today().weekday())).replace(hour=0,
                                                                      minute=0, second=0, microsecond=1)
        await asyncio.sleep((startofweek-datetime.datetime.utcnow()).total_seconds())

        for id in client.serverwleaderboard:
            await update_leaderboard(client, id)
        await asyncio.sleep(10) # Sleep for 10s so don't get repeated messages
  
async def update_leaderboard(client, guild_id):
    guild = client.get_guild(guild_id)
    if guild:
        leaderboardchannel = client.guild_db.get(guild_id)[sql.gld_cols.leaderboardchannel]
        zerorunschannel = client.guild_db.get(guild_id)[sql.gld_cols.zerorunchannel]
        rlrole = client.guild_db.get(guild_id)[sql.gld_cols.rlroleid]

        top_runs = await sql.get_top_10_logs(client.pool, guild_id, sql.log_cols.weeklyruns, False)
        top_runs = clean_rl_data(top_runs, guild, rlrole)
        top_assists = await sql.get_top_10_logs(client.pool, guild_id, sql.log_cols.weeklyassists, False)
        top_assists = clean_rl_data(top_assists, guild, rlrole)
        if guild_id != 660344559074541579:
            top_keys = await sql.get_top_10_logs(client.pool, guild_id, sql.log_cols.pkey)
        else:
            helmrunes = await sql.get_top_10_logs(client.pool, guild_id, sql.log_cols.helmrunes, only_10=False)
            swordrunes = await sql.get_top_10_logs(client.pool, guild_id, sql.log_cols.swordrunes, only_10=False)
            shieldrunes = await sql.get_top_10_logs(client.pool, guild_id, sql.log_cols.shieldrunes, only_10=False)
            top_runes = {}
            for r in helmrunes:
                top_runes[r[0]] = (r[0], r[sql.log_cols.helmrunes])
            for r in swordrunes:
                if r[0] in top_runes:
                    top_runes[r[0]] = (r[0], top_runes[r[0]][1]+r[sql.log_cols.swordrunes])
                else:
                    top_runes[r[0]] = (r[0], r[sql.log_cols.swordrunes])
            for r in shieldrunes:
                if r[0] in top_runes:
                    top_runes[r[0]] = (r[0], top_runes[r[0]][1]+r[sql.log_cols.shieldrunes])
                else:
                    top_runes[r[0]] = (r[0], r[sql.log_cols.shieldrunes])
            ten_runes = list(top_runes.values())
            def get_num(elem):
                return elem[1]
            ten_runes.sort(key=get_num, reverse=True)
            ten_runes = ten_runes[:10]



        embed = discord.Embed(title="Top Runs Led This Week", color=discord.Color.gold())
        embed.add_field(name="Runs Led:", value=format_top_data(top_runs, sql.log_cols.weeklyruns)).add_field(name="Runs Assisted:",
                                                                                                              value=format_top_data(top_assists,
                                                                                                                                    sql.log_cols.weeklyassists))
        await leaderboardchannel.send(embed=embed)
        if guild_id != 660344559074541579:
            embed = discord.Embed(title="Top Keys Popped", color=discord.Color.gold())
            embed.add_field(name="Keys Popped:", value=format_top_data(top_keys, sql.log_cols.pkey))
        else:
            embed = discord.Embed(title="Top Runes Popped", color=discord.Color.gold())
            embed.add_field(name="Runes Popped:", value=format_top_data(ten_runes, 1))
        await leaderboardchannel.send(embed=embed)

        zero_runs = await sql.get_0_runs(client.pool, guild_id)
        zero_runs = clean_rl_data(zero_runs, guild, rlrole, False)

        if zero_runs:
            desc = "".join("<@" + str(r[0]) + "> - (Assists: " + str(r[sql.log_cols.weeklyassists]) + ")\n" for r in zero_runs)
        else:
            desc = "All rl's completed at least 1 run this week."
        embed = discord.Embed(title="RL's With 0 Runs", description=desc, color=discord.Color.orange())
        await zerorunschannel.send(embed=embed)
            

def clean_rl_data(data, guild, rlrole, truncate=True):
    temp = []
    for i, r in enumerate(data):
        member = guild.get_member(r[0])
        if member:
            if member.top_role >= rlrole:
                temp.append(r)
    if truncate:
        temp = temp[:10]
    return temp


def format_top_data(data, col, aslist=False):
    if not aslist:
        top = ""
        for i, r in enumerate(data):
            top += f"#{i+1}. <@{r[0]}> - {r[col]}\n"
        return top
    else:
        top = []
        for i, r in enumerate(data):
            top.append(f"#{i + 1}. <@{r[0]}> - {r[col]}\n")
        return top

