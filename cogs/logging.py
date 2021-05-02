import asyncio
import datetime
import json
import textwrap

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
    async def logrun(self, ctx, member: utils.MemberLookupConverter = None, number: int = 1):
        if ctx.guild.id == 713844220728967228:
            hrl = ctx.guild.get_role(740761925713133673)
            if ctx.author.top_role < hrl:
                raise commands.CheckFailure(message="You must be HRL+ to use this command!")

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
                if 0 < int(msg.content) < 57:
                    break
            await ctx.send("Please choose a number between 1-56!", delete_after=7)

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

    @commands.command(usage="zeroruns", description="Fetch the Zero Runs log for this week.")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def zeroruns(self, ctx, role: discord.Role=None):
        rlrole = self.client.guild_db.get(ctx.guild.id)[sql.gld_cols.rlroleid]
        zerorunschannel: discord.TextChannel = self.client.guild_db.get(ctx.guild.id)[sql.gld_cols.zerorunchannel]

        if not zerorunschannel:
            return await ctx.send("This server does not have a zero-runs channel currently configured!\n"
                                  "Please contact the developer to set this feature up.")

        if ctx.channel != zerorunschannel:
            return await ctx.send(f"Please use this command in the appropriate zero-runs channel ({zerorunschannel.mention})!")

        zero_runs = await sql.get_0_runs(self.client.pool, ctx.guild.id)

        if role:
            temp = []
            for i, r in enumerate(zero_runs):
                member: discord.Member = ctx.guild.get_member(r[0])
                if member:
                    if role == member.top_role:
                        temp.append(r)
            zero_runs = temp
        else:
            zero_runs = clean_rl_data(zero_runs, ctx.guild, rlrole, False)

        if zero_runs:
            desc = "".join("<@" + str(r[0]) + "> - (Assists: " + str(r[sql.log_cols.weeklyassists]) + ")\n" for r in zero_runs)
        else:
            desc = "All rl's completed at least 1 run this week."

        embed = discord.Embed(title="RL's With 0 Runs", color=discord.Color.orange())

        lines = textwrap.wrap(desc, width=1024, replace_whitespace=False, break_on_hyphens=False)  # Wrap message before max len of field of 1024
        for i, l in enumerate(lines):
            embed.add_field(name=f"Zero runs: (pt. {i + 1})", value=l, inline=False)

        try:
            await zerorunschannel.send(embed=embed)
        except discord.HTTPException:
            await zerorunschannel.send("Error: specified role has too many members to display!")

    @commands.command(usage='leaderboard <type>', description='Display the top 20 members in a selected logging category.\nValid categories: `keys`, `runes`, `runs`, `led`, '
                                                              '`weeklyled`, `o3completes`, `o3fails`', aliases=['lb'])
    @commands.guild_only()
    async def leaderboard(self, ctx, type):
        type = type.strip().lower()
        if type not in ['keys', 'runes', 'runs', 'led', 'weeklyled', 'o3completes', 'o3fails']:
            return await ctx.send("Please choose a valid log type:\nValid categories: `keys`, `runes`, `runs`, `led`, `weeklyled`, `o3completes`, `o3fails`")

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
            top = format_top_data(runes[:500], 1, aslist=True)
        else:
            col = sql.log_cols.pkey if type == 'keys' else sql.log_cols.runsdone if type == 'runs' else sql.log_cols.srunled if type == 'led' else sql.log_cols.weeklyruns if \
                type == 'weeklyled' else sql.log_cols.ocompletes if type == 'o3completes' else sql.log_cols.oattempts
            top = await sql.get_top_10_logs(self.client.pool, ctx.guild.id, column=col, only_10=False, limit=500)
            top = format_top_data(top, col, aslist=True)

        name = 'Keys' if type == 'keys' else "Runes" if type == 'runes' else "Runs Completed" if type == 'runs' else "Runs Led" if type == 'led' else "Weekly Runs Led" if type \
               == 'weeklyled' else "Oryx 3 Completes" if type == 'o3completes' else "Oryx 3 Fails"

        for i, r in enumerate(top):
            if int(r.split(" - ")[1]) == 0:
                top = top[:i]
                break

        pages = []
        chunk_size = 20
        for i in range(0, len(top), chunk_size):
            chunk = top[i:i + chunk_size]
            embed = discord.Embed(title=f"Top {name} in {ctx.guild.name}", color=discord.Color.gold()).add_field(name=f'Top {i + chunk_size-10}', value="".join(chunk[:10]),
                                                                                                                 inline=False)
            if len(chunk) > 10:
                embed.add_field(name=f"Top {i + chunk_size}", value="".join(chunk[10:]), inline=False)
            embed.set_thumbnail(url=str(ctx.guild.icon_url))
            embed.timestamp = datetime.datetime.utcnow()
            pages.append(embed)

        paginator = utils.EmbedPaginator(self.client, ctx, pages)
        await paginator.paginate()

    @commands.command(usage='setpointlb', description="Set the Point Leaderboard to run in this channel.")
    @commands.guild_only()
    @commands.check_any(commands.has_permissions(manage_guild=True), commands.is_owner())
    async def setpointlb(self, ctx):
        msg = await ctx.send("Point Leaderboard has been set to this channel! Please wait for an update for the LB to show!")
        await sql.update_guild(self.client.pool, ctx.guild.id, 'pointlbmsg', msg.id)
        await sql.update_guild(self.client.pool, ctx.guild.id, 'pointlbchannel', ctx.channel.id)
        self.client.guild_db[ctx.guild.id][sql.gld_cols.pointlbmsg] = msg.id
        self.client.guild_db[ctx.guild.id][sql.gld_cols.pointlbchannel] = ctx.channel
        

def setup(client):
    client.add_cog(Logging(client))


async def update_points(client, guild, member, type):
    with open("data/guild_variables.json") as f:
        data = json.load(f)

    p_val = data[str(guild.id)]['points'][type] if str(guild.id) in data else data['-1']['points'][type]

    await sql.log_runs(client.pool, guild.id, member.id, sql.log_cols.weeklypoints, p_val)

    await update_point_lb(client, guild, last_action=f"{member.mention} ({type}) - **+{p_val}** points")


async def update_point_lb(client, guild, create_new=False, last_action=""):
    top_weekly_points = await sql.get_top_10_logs(client.pool, guild.id, sql.log_cols.weeklypoints, only_10=False)
    top_total_points = await sql.get_top_10_logs(client.pool, guild.id, sql.log_cols.totalpoints, only_10=True)

    pointrole = client.guild_db.get(guild.id)[sql.gld_cols.pointrole] if client.guild_db.get(guild.id)[sql.gld_cols.pointrole] else \
        client.guild_db.get(guild.id)[sql.gld_cols.securityrole] if client.guild_db.get(guild.id)[sql.gld_cols.securityrole] else \
            client.guild_db.get(guild.id)[sql.gld_cols.rlroleid]
    top_weekly_points = clean_rl_data(top_weekly_points, guild, pointrole, False, True, sql.log_cols.weeklypoints, has_role=True)
    top_total_points = clean_rl_data(top_total_points, guild, pointrole, False, True, sql.log_cols.totalpoints, has_role=True)

    weekly = top = ""
    for i in range(len(top_weekly_points)):
        weekly += top_weekly_points[i] + "\n"
        if i < len(top_total_points) - 1:
            top += top_total_points[i] + "\n"

    weekly = "N/A" if not weekly else weekly
    top = "N/A" if not top else top

    embed = discord.Embed(title="Current Weekly Point Leaderboard", description=f"**Top Weekly:**\n{weekly}", color=discord.Color.teal())
    embed.add_field(name="Top All Time", value=top, inline=True)
    embed.set_author(name=guild.name, icon_url=str(guild.icon_url))
    embed.set_footer(text="Last updated ")
    embed.timestamp = datetime.datetime.utcnow()

    data = client.guild_db.get(guild.id)
    # client_member = guild.get_member(client.user.id)
    if data[sql.gld_cols.pointlbmsg] and data[sql.gld_cols.pointlbchannel]:
        lb_msg = await data[sql.gld_cols.pointlbchannel].fetch_message(data[sql.gld_cols.pointlbmsg])

        if not create_new:
            await lb_msg.edit(content=f"Last Change: {last_action}", embed=embed)
        else:
            msg = await lb_msg.channel.send(embed=embed)
            await sql.update_guild(client.pool, guild.id, sql.gld_cols.pointlbmsg, msg.id)
    else:
        print(f"ERROR: NO DEFINED POINT MSG in {guild.name}")

async def update_leaderboards(client: discord.Client):
    while(True):
        startofweek = (datetime.datetime.today() + datetime.timedelta(days=7 - datetime.datetime.today().weekday())).replace(hour=0,
                                                                      minute=0, second=0, microsecond=1)
        await asyncio.sleep((startofweek-datetime.datetime.utcnow()).total_seconds())

        for id in client.serverwleaderboard:
            await update_leaderboard(client, id)

        for g in client.guilds:
            await update_point_lb(client, g, True, "Reset LB for new week")

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
            

def clean_rl_data(data, guild, rlrole, truncate=True, points=False, col=0, has_role=False):
    temp = []
    num = 0
    for i, r in enumerate(data):
        member: discord.Member = guild.get_member(r[0])
        if member:
            if (member.top_role >= rlrole and has_role is False) or (rlrole in member.roles and has_role is True):
                num += 1
                if points:
                    temp.append(f"#{num}: {member.mention} - __{r[col]}__ points")
                else:
                    temp.append(r)
    if truncate is True:
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

