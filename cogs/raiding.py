import functools
import io
import json
import re
from difflib import get_close_matches

import cv2
import discord
import numpy as np
from discord.ext import commands
from discord.ext.commands import BucketType
from pytesseract import pytesseract

import checks
import sql
import utils
from cogs import logging
from cogs.Raiding.afk_check import AfkCheck
from cogs.Raiding.fametrain import FameTrain
from cogs.Raiding.headcount import Headcount
from cogs.Raiding.queue_afk import QAfk
from cogs.Raiding.realmclear import RealmClear
from cogs.Raiding.runecount import RuneCount
from cogs.Raiding.vc_select import VCSelect


class Raiding(commands.Cog):
    """Commands to organize ROTMG Raids & More!"""
    letters = ["🇦", "🇧", "🇨", "🇩", "🇼", "🇽", "🇾", "🇿"]

    def __init__(self, client):
        self.client = client

    @commands.command(usage='runecount', description="Start a Rune Count for an Oryx 3 run.")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    @checks.only_dungeoneer()
    @commands.max_concurrency(1, per=BucketType.category, wait=False)
    async def runecount(self, ctx):
        setup = VCSelect(self.client, ctx, qafk=True)
        data = await setup.q_start()
        if isinstance(data, tuple):
            (raiderrole, rlrole, hcchannel) = data
        else:
            return
        runecount = RuneCount(self.client, ctx, hcchannel, raiderrole, rlrole)

    @commands.command(usage='togglerune <helm/shield/sword/allon/alloff>', description='Toggle a rune on/off')
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    @checks.only_dungeoneer()
    async def togglerune(self, ctx, rune: str):
        rune = rune.lower()
        if rune not in ['helm', 'shield', 'sword', 'allon', 'alloff']:
            return await ctx.send("Please specify what to toggle: `helm`, 'shield`, `sword`, `allon`, `alloff`")


        with open('data/dungeons.json') as f:
            q_dungeons = json.load(f)

        if rune in ['helm', 'shield', 'sword']:
            selector = 2 if rune == 'helm' else 1 if rune == 'sword' else 0
            current = q_dungeons.get('0')[selector][1]
            q_dungeons['0'][selector][1] = 0 if current == 1 else 1
            await ctx.send(f"**__{rune.capitalize()}__** was turned {'ON' if current == 0 else 'OFF'}!")
        else:
            for i, r in enumerate(q_dungeons['0']):
                q_dungeons['0'][i][1] = 1 if rune == 'allon' else 0
            await ctx.send(f"Every Rune was turned {'ON' if rune == 'allon' else 'OFF'}!")

        with open('data/dungeons.json', 'w') as f:
            json.dump(q_dungeons, f, indent=4)

        str = "Rune Status:\n"
        for i, r in enumerate(q_dungeons['0']):
            name = "Shield" if i == 0 else "Sword" if i == 1 else "Helm"
            str += f"{name} Rune ({r[0]}): {'ON ✅' if r[1] == 1 else 'OFF ❌'}\n"
        await ctx.send(str)


    @commands.command(usage='qafk', description="Start a Queue afk check for the location specified.")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    @checks.only_dungeoneer()
    @commands.max_concurrency(1, per=BucketType.guild, wait=False)
    async def qafk(self, ctx):
        if ctx.author.id in self.client.raid_db[ctx.guild.id]['leaders']:
            return await ctx.send("You cannot start another AFK while an AFK check is still up or a run log has not been completed.")


        setup = VCSelect(self.client, ctx, qafk=True)
        data = await setup.q_start()
        if isinstance(data, tuple):
            (raiderrole, rlrole, hcchannel) = data
        else:
            return

        qafk = QAfk(self.client, ctx, "Location has not been set yet.", hcchannel, raiderrole, rlrole, True)
        await qafk.start()

    @commands.command(usage='position', description="Check your position to join the next raid!", aliases=['queue'])
    @commands.guild_only()
    @checks.only_dungeoneer()
    async def position(self, ctx):
        try:
            await ctx.message.delete()
        except discord.NotFound or discord.HTTPException:
            pass

        if ctx.channel.id != 738632101523619901 and ctx.channel.id != 751898060358942841:
            return await ctx.send(f"{ctx.author.mention} Please use this command in <#738632101523619901>.", delete_after=10)


        if ctx.author.id in self.client.active_raiders:
            await ctx.send("You are currently in a raid! This command is used to check your position when waiting for a raid to start.")
        elif ctx.author.id in self.client.morder[ctx.guild.id] and self.client.morder[ctx.guild.id][ctx.author.id] is not None:
            d = self.client.morder[ctx.guild.id][ctx.author.id]
            npriority = self.client.morder[ctx.guild.id]['npriority']
            nnormal = self.client.morder[ctx.guild.id]['nnormal']
            nvc = self.client.morder[ctx.guild.id]['nvc']
            if d is not None:
                s = f"💎 - #{d[1]} in the **priority** queue." if d[0] else f"✅ - #{d[1]} in the **normal** queue."
                s += f" Queue lengths - (**{npriority}** 💎 | **{nnormal}** ✅ | {nvc} in VC). {ctx.author.mention}"
            else:
                s = "An issue occured retrieving your position status. Most likely the bot is moving people into the raid VC at the moment - but contact Darkmatter#7321 if " \
                    "this issue persists."
            await ctx.send(s)
        else:
            d = await sql.get_missed(self.client.pool, ctx.author.id)
            if d and d[1]:
                await ctx.send(f"💎 - You weren't moved in for the last raid so you were given **priority** queuing for the next run. {ctx.author.mention}")
            else:
                await ctx.send(f"You aren't in the queue for an active raid & do not have priority queuing for the next raid. {ctx.author.mention}")

    @commands.command(usage='leaverun', description="Leave a run if you nexus", aliases=['leaveraid'])
    @commands.guild_only()
    @checks.only_dungeoneer()
    async def leaverun(self, ctx):
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass

        if ctx.author.id in self.client.active_raiders:
            self.client.active_raiders.pop(ctx.author.id, None)
            await ctx.send(f"{ctx.author.mention} - You have been removed from the raid.")
        else:
            await ctx.send(f"You are not currently in a raid or waiting for one!")

    @commands.command(usage="findloc", description="Find a good location to start an O3 run in.")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    #@commands.check_any(commands.has_permissions(administrator=True), commands.is_owner())
    async def findloc(self, ctx):
        print('Findloc')
        if not await checks.is_bot_commands_channel(ctx):
            try:
                await ctx.message.delete()
            except discord.Forbidden or discord.NotFound:
                pass
            return await ctx.send("This command must be used in a bot-commands channel only.")
        servers = await utils.get_good_realms(self.client, 8)
        server_opts = {}
        if servers:
            desc = ""
            num = 0

            for l in servers[0]:
                event = l[3] if l[3] else "N/A"
                desc += f"{self.letters[num]} - __**{l[0]}**__\n**{l[1]}** People | **{l[2]}** Heroes\n`{event}`\n**{l[4]}** ago\n\n"
                server_opts[self.letters[num]] = l[0]
                num += 1
            if not desc:
                desc = "No suitable US servers found."
            embed = discord.Embed(title="Locations", description="Possible locations in which to start an O3 Raid.", color=discord.Color.gold())
            embed.add_field(name="Top US Servers", value=desc, inline=True)
            embed.add_field(name='\u200B', value='\u200B', inline=True)
            num = 4
            desc = ""
            for l in servers[1]:
                event = l[3] if l[3] else "N/A"
                desc += f"{self.letters[num]} - __**{l[0]}**__\n**{l[1]}** People | **{l[2]}** Heroes\n`{event}`\n**{l[4]}** ago\n\n"
                server_opts[self.letters[num]] = l[0]
                num += 1
            if not desc:
                desc = "No suitable EU servers found."
            embed.add_field(name="Top EU Servers", value=desc, inline=True)

        else:
            embed = discord.Embed(title="Error!", description="No suitable locations found. Please scout a location yourself.", color=discord.Color.red())

        await ctx.send(embed=embed)

    @commands.command(usage="findrc [max_in_realm]", description="Find a good location to start a Realm Clearing run in.")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    #@commands.check_any(commands.has_permissions(administrator=True), commands.is_owner())
    async def findrc(self, ctx, max=20):
        if not await checks.is_bot_commands_channel(ctx):
            try:
                await ctx.message.delete()
            except discord.Forbidden or discord.NotFound:
                pass
            return await ctx.send("This command must be used in a bot-commands channel only.")
        servers = await utils.get_good_realms(self.client, max, 100)
        server_opts = {}
        if servers:
            desc = ""
            num = 0

            for l in servers[0]:
                event = l[3] if l[3] else "N/A"
                desc += f"{self.letters[num]} - __**{l[0]}**__\n**{l[1]}** People | **{l[2]}** Heroes\n`{event}`\n**{l[4]}** ago\n\n"
                server_opts[self.letters[num]] = l[0]
                num += 1
            if not desc:
                desc = "No suitable US servers found."
            embed = discord.Embed(title="Locations", description=f"Possible locations in which to start realm clearing with a server population < **{max}**",
                                  color=discord.Color.gold())
            embed.add_field(name="Top US Servers", value=desc, inline=True)
            embed.add_field(name='\u200B', value='\u200B', inline=True)
            num = 4
            desc = ""
            for l in servers[1]:
                event = l[3] if l[3] else "N/A"
                desc += f"{self.letters[num]} - __**{l[0]}**__\n**{l[1]}** People | **{l[2]}** Heroes\n`{event}`\n**{l[4]}** ago\n\n"
                server_opts[self.letters[num]] = l[0]
                num += 1
            if not desc:
                desc = "No suitable EU servers found."
            embed.add_field(name="Top EU Servers", value=desc, inline=True)

        else:
            embed = discord.Embed(title="Error!", description="No suitable locations found. Please scout a location yourself.", color=discord.Color.red())

        await ctx.send(embed=embed)

    @commands.command(usage='event <type>', description="Find all realms with a specified event.")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    #@commands.check_any(commands.has_permissions(administrator=True), commands.is_owner())
    async def event(self, ctx, *, event_alias):
        if not await checks.is_bot_commands_channel(ctx):
            try:
                await ctx.message.delete()
            except discord.Forbidden or discord.NotFound:
                pass
            return await ctx.send("This command must be used in a bot-commands channel only.")

        event = event_type(event_alias)
        if not event:
            return await ctx.send(f"The specified event type: `{event_alias}` is not valid. Please enter a valid event.")

        data = await utils.get_event_servers(self.client, event)
        if not data:
            embed = discord.Embed(title="Error!", description=f"No servers were found with the current event of `{event}`.", color=discord.Color.red())
        else:
            desc = ""
            num = 0
            for l in data:
                event = l[3] if l[3] else "N/A"
                desc += f"{self.letters[num]} - __**{l[0]}**__\n**{l[1]}** People | **{l[2]}** Heroes\n`{event}`\n**{l[4]}** ago\n\n"
                num += 1
            if not desc:
                desc = "No suitable US servers found."
            embed = discord.Embed(title="Locations", description=f"Possible locations that contain the event: `{event}`.", color=discord.Color.gold())
            embed.add_field(name="Top Servers", value=desc, inline=True)
        await ctx.send(embed=embed)

    @commands.command(usage="afk <location>", description="Starts an AFK check for the location specified.", aliases=['afkcheck', 'startafk'])
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    # @checks.exclude_dungeoneer()
    @commands.max_concurrency(1, per=BucketType.guild, wait=False)
    async def afk(self, ctx, *, location):
        if ctx.author.id in self.client.raid_db[ctx.guild.id]['leaders']:
            return await ctx.send("You cannot start another AFK while an AFK check is still up or a run log has not been completed.")
        # self.client.raid_db[ctx.guild.id]['leaders'].append(ctx.author.id)
        setup = VCSelect(self.client, ctx)
        data = await setup.start()
        if isinstance(data, tuple):
            (raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg) = data
        else:
            # if ctx.author.id in self.client.raid_db[ctx.guild.id]:
            #     self.client.raid_db[ctx.guild.id]['leaders'].remove(ctx.author.id)
            return
        afk = AfkCheck(self.client, ctx, location, raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg)
        await afk.start()

    @commands.command(usage="headcount", aliases=["hc"], description="Starts a headcount.")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    # @commands.max_concurrency(1, per=BucketType.guild, wait=False)
    async def headcount(self, ctx):
        setup = VCSelect(self.client, ctx, headcount=True)
        data = await setup.start()
        if isinstance(data, tuple):
            (raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg) = data
        else:
            return
        hc = Headcount(self.client, ctx, hcchannel, vcchannel, setup_msg, raidnum, inraiding, invet, inevents, raiderrole, rlrole)
        await hc.start()

    @commands.command(usage="parse (Attach an image of /who list with this command)",
                      description="Parse through members in the run to find crashers.")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def parse(self, ctx):
        if not ctx.message.attachments:
            return await ctx.send("Please attach an image containing only the result of the /who command!", delete_after=10)
        if len(ctx.message.attachments) > 1:
            return await ctx.send("Please only attach 1 image.", delete_after=10)
        attachment = ctx.message.attachments[0]
        if not attachment.height or 'mp4' in attachment.filename.lower() or 'mov' in attachment.filename.lower():
            return await ctx.send("Please only attach an image of type 'png' or 'jpg'.", delete_after=10)
        image = io.BytesIO()
        await attachment.save(image, seek_begin=True)
        if ctx.author.voice:
            vcchannel = ctx.author.voice.channel
        else:
            setup = VCSelect(self.client, ctx, parse=True)
            data = await setup.start()
            if isinstance(data, tuple):
                (raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg) = data
            else:
                return
            await setup_msg.delete()
        msg = await ctx.send("Parsing image. This may take a minute...")
        print("parsing in vc: " + str(vcchannel))
        embed = await self.client.loop.run_in_executor(None, functools.partial(parse_image, ctx.author, image, vcchannel))
        await msg.delete()
        await ctx.send(embed=embed)

        await logging.update_points(self.client, ctx.guild, ctx.author, 'parse')

    @commands.command(usage='yoink <channel_name>', description='Move all people from specified VC into channel you are in.')
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def yoink(self, ctx, *, channel: discord.VoiceChannel):
        if not ctx.author.voice:
            return await ctx.send("Please join a voice channel before using this command.")

        n = len(channel.members)
        m = 0
        for member in channel.members:
            if member.voice:
                try:
                    await member.move_to(channel=ctx.author.voice.channel)
                    m += 1
                except discord.Forbidden or discord.HTTPException:
                    continue

        await ctx.send(f"Yoinked {m}/{n} members to {ctx.author.voice.channel.name}!")


    @commands.command(usage='parsemembers (Attach an image of /who list with this command)',
                      description="Parse through members in a realm to find crashers.", aliases=['pm'])
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def parsemembers(self, ctx):
        if not ctx.message.attachments:
            return await ctx.send("Please attach an image containing only the result of the /who command!", delete_after=10)
        if len(ctx.message.attachments) > 1:
            return await ctx.send("Please only attach 1 image.", delete_after=10)
        attachment = ctx.message.attachments[0]
        if not attachment.height or 'mp4' in attachment.filename.lower() or 'mov' in attachment.filename.lower():
            return await ctx.send("Please only attach an image of type 'png' or 'jpg'.", delete_after=10)
        image = io.BytesIO()
        await attachment.save(image, seek_begin=True)
        if ctx.author.voice:
            vcchannel = ctx.author.voice.channel
        else:
            setup = VCSelect(self.client, ctx, parse=True)
            data = await setup.start()
            if isinstance(data, tuple):
                (raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg) = data
            else:
                return
            await setup_msg.delete()
        msg: discord.Message = await ctx.send("Parsing image. This may take a minute...")
        res = await self.client.loop.run_in_executor(None, functools.partial(parse_image, ctx.author, image, vcchannel, True))
        if not res:
            embed = discord.Embed(title="Error!", description="Could not find the who command in the image you provided.\nPlease re-run the "
                                                              "command with an image that shows the results of `/who`.", color=discord.Color.red())
            await msg.delete()
            return await ctx.send(embed=embed)

        crashing, possible_alts, fixed_names = res
        await msg.edit(content="Parsing members. Please wait...")
        n_crashers = len(crashing)
        crashing_members = []
        converter = utils.MemberLookupConverter()
        pages = []
        nm_crashing = []
        crashing_players = []
        for n in crashing:
            try:
                mem = await converter.convert(ctx, n)
            except discord.ext.commands.BadArgument:
                crashing_players.append(n)
        for m in crashing_members:
            n_suspensions = 0
            active_suspension = "❌"
            pdata = await sql.get_users_punishments(self.client.pool, m.id, ctx.guild.id)
            bdata = await sql.get_blacklist(self.client.pool, m.id, ctx.guild.id)
            pembed = discord.Embed(description=f"**Punishment Log for {m.mention}** - `{m.display_name}`")
            if pdata:
                for i, r in enumerate(pdata, start=1):
                    requester = ctx.guild.get_member(r[sql.punish_cols.r_uid])
                    active = "✅" if r[sql.punish_cols.active] else "❌"
                    starttime = f"Issued at: `{r[sql.punish_cols.starttime].strftime('%b %d %Y %H:%M:%S')}`"
                    endtime = f"\nEnded at: `{r[sql.punish_cols.endtime].strftime('%b %d %Y %H:%M:%S')}`" if r[sql.punish_cols.endtime] else ""
                    ptype = r[sql.punish_cols.type].capitalize()
                    pembed.add_field(name=f"{ptype} #{i} | Active {active}",
                                     value=f"Issued by: {requester.mention if requester else '(Issuer left server)'}\nReason:\n{r[sql.punish_cols.reason]}\n{starttime}\n"
                                           f"{endtime}",
                                     inline=False)
                    if r[sql.punish_cols.active] and ptype == 'Suspend':
                        active_suspension = active
                    if ptype == 'Suspend':
                        n_suspensions += 1
            if bdata:
                for i, r in enumerate(bdata, start=1):
                    requester = ctx.guild.get_member(r[sql.blacklist_cols.rid])
                    active = "✅"
                    starttime = f"Issued at: `{r[sql.blacklist_cols.issuetime].strftime('%b %d %Y %H:%M:%S')}`"
                    btype = r[sql.blacklist_cols.type].capitalize()
                    pembed.add_field(name=f"{btype} #{i} issued by {requester.mention if requester else '(Issuer left server)'} | Active {active}",
                                     value=f"Reason:\n{r[sql.punish_cols.reason]}\n{starttime}")
            if pdata or bdata:
                pembed.description += f"\nFound `{len(pdata)}` Punishments in this user's history.\nFound `{len(bdata)}` Blacklists in this users history."
                pages.append(pembed)

            nm_crashing.append((m, n_suspensions, active_suspension))

        mstring = ""
        nm_crashing = sorted(nm_crashing, key=lambda x: x[1], reverse=True)
        for r in nm_crashing:
            mstring += f"{r[0].mention} **-** `{r[0].display_name}`\nSuspensions: **{r[1]}** | Active: {r[2]}\n"
        if not mstring:
            mstring = "No members crashing!"

        embed = discord.Embed(title=f"Parsing Results for {vcchannel.name}", description=f"Possible Crashers: **{n_crashers}**",
                              color=discord.Color.orange())
        if len(mstring) > 1024:
            lines = mstring.splitlines(keepends=True)
            curr_str = ""
            n_sections = 1
            for l in lines:
                if len(l) + len(curr_str) >= 1024:
                    embed.add_field(name=f"Members Crashing (in the server) ({n_sections}):", value=curr_str, inline=True)
                    curr_str = l
                    n_sections += 1
                else:
                    curr_str += l
            embed.add_field(name=f"Members Crashing (in the server) ({n_sections}):", value=curr_str, inline=True)
        else:
            embed.add_field(name="Members Crashing (in the server):", value=mstring, inline=True)
        pstring = "\n".join(crashing_players) if crashing_players else 'No players who are not in the server crashing.'
        embed.add_field(name="Players Crashing (not in server):", value=pstring, inline=False)

        if fixed_names:
            fixedlist = "     Fixed Name | Original Parse".join("`/kick " + fixed + "` | (" + orig + ")\n" for (orig, fixed) in fixed_names)
            embed.add_field(name="Possible Fixed Names", value=fixedlist, inline=True)
        if possible_alts:
            altlist = "".join("`" + name + "`\n" for name in possible_alts)
            embed.add_field(name="Possible Alts (In VC but not in game)", value=altlist, inline=True)

        pages.insert(0, embed)
        await logging.update_points(self.client, ctx.guild, ctx.author, 'parse')

        await msg.delete()
        paginator = utils.EmbedPaginator(self.client, ctx, pages)
        await paginator.paginate()

    @commands.command(usage='addrusher <name>', description="Adds the rusher role to someone.")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def addrusher(self, ctx, member: utils.MemberLookupConverter):
        rusherrole = self.client.guild_db.get(ctx.guild.id)[sql.gld_cols.rusherrole]
        if not rusherrole:
            return await ctx.send("This server does not have a rusher role configured! Contact Darkmattr if you believe this to "
                                  "be a mistake!")

        try:
            await member.add_roles(rusherrole)
        except discord.Forbidden:
            return await ctx.send(f"A permissions error occcured while adding the rusher role to {member.mention}.")

        embed = discord.Embed(title="Success!", description=f"{member.mention} was given the rusher role by {ctx.author.display_name}!",
                              color=discord.Color.green())
        await ctx.send(embed=embed)
        try:
            embed.title = "Congratulations!"
            await member.send(content=member.mention, embed=embed)
        except discord.Forbidden:
            pass

    @commands.command(usage="lock", description="Locks the raiding voice channel")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def lock(self, ctx):
        setup = VCSelect(self.client, ctx, lock=True)
        data = await setup.start()
        if isinstance(data, tuple):
            (raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg) = data
        else:
            return
        await setup_msg.delete()
        # vc_name = vcchannel.name
        # if " <-- Join!" in vc_name:
        #     vc_name = vc_name.split(" <")[0]
        #     await vcchannel.edit(name=vc_name)
        await vcchannel.set_permissions(raiderrole, connect=False, view_channel=True, speak=False)
        embed = discord.Embed(description=f"{vcchannel.name} Has been Locked!", color=discord.Color.red())
        await ctx.send(embed=embed)

    @commands.command(usage="unlock", description="Unlocks the raiding voice channel.")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def unlock(self, ctx):
        setup = VCSelect(self.client, ctx, unlock=True)
        data = await setup.start()
        if isinstance(data, tuple):
            (raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg) = data
        else:
            return
        await setup_msg.delete()
        await vcchannel.set_permissions(raiderrole, connect=True, view_channel=True, speak=False)
        embed = discord.Embed(description=f"{vcchannel.name} Has been Unlocked!", color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.command(usage='changecap <new_cap>', description="Changes the max cap of raiding VC's. (Choose -1 to make it unlimited).")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def changecap(self, ctx, new_cap: int):
        if new_cap < -1 or new_cap == 0 or new_cap > 99:
            return await ctx.send("Please set the channel cap to a number between 1-99 or -1 for unlimited")
        if new_cap == -1:
            new_cap = None
        setup = VCSelect(self.client, ctx, change_limit=True)
        data = await setup.start()
        if isinstance(data, tuple):
            (raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg) = data
        else:
            return
        await setup_msg.delete()
        await vcchannel.edit(user_limit=new_cap)
        embed = discord.Embed(description=f"{vcchannel.name} now has a user limit of **{f'{new_cap}' if new_cap else 'Unlimited'}!**", color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.command(usage="clean", description="Clean out & lock a voice channel.")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    @commands.max_concurrency(1, per=BucketType.guild, wait=False)
    async def clean(self, ctx, channel: discord.VoiceChannel = None):
        vcchannel = channel
        if not channel:
            setup = VCSelect(self.client, ctx, clean=True)
            data = await setup.start()
            if isinstance(data, tuple):
                (raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg) = data
            else:
                return
            await setup_msg.delete()

            await vcchannel.set_permissions(raiderrole, connect=False, view_channel=True, speak=False)

            for member in vcchannel.members:
                if member.top_role < rlrole:
                    if member.voice:
                        await member.move_to(channel=None)

        for member in vcchannel.members:
            if member.voice:
                await member.move_to(channel=None)

        embed = discord.Embed(title="Done Cleaning!", description=f"{vcchannel.name} has been cleaned and locked.",
                              color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.command(usage="fametrain <location>", aliases=['ft'], description="Start an AFK check for a fametrain.")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def fametrain(self, ctx, *, location):
        if ctx.author.id in self.client.raid_db[ctx.guild.id]['leaders']:
            return await ctx.send("You cannot start another AFK while an AFK check is still up.")
        # self.client.raid_db[ctx.guild.id]['leaders'].append(ctx.author.id)
        setup = VCSelect(self.client, ctx)
        data = await setup.start()
        if isinstance(data, tuple):
            (raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg) = data
        else:
            return
        ft = FameTrain(self.client, ctx, location, raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg)
        await ft.start()
        # self.client.raid_db[ctx.guild.id]['leaders'].remove(ctx.author.id)

    @commands.command(usage="realmclear <location>", aliases=["rc"], description="Start an AFK Check for Realm Clearing.")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def realmclear(self, ctx, *, location):
        if ctx.author.id in self.client.raid_db[ctx.guild.id]['leaders']:
            return await ctx.send("You cannot start another AFK while an AFK check is still up.")
        # self.client.raid_db[ctx.guild.id]['leaders'].append(ctx.author.id)
        setup = VCSelect(self.client, ctx)
        data = await setup.start()
        if isinstance(data, tuple):
            (raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg) = data
        else:
            return
        rc = RealmClear(self.client, ctx, location, raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg)
        await rc.start()
        # self.client.raid_db[ctx.guild.id]['leaders'].remove(ctx.author.id)

    @commands.command(usage="markmap <number(s)>", aliases=["mm"], description="Mark the current map with specified numbers.")
    @commands.guild_only()
    @checks.is_mm_or_higher_check()
    async def markmap(self, ctx, *numbers):
        await ctx.message.delete()
        if ctx.author.id in self.client.mapmarkers:
            rc = self.client.mapmarkers[ctx.author.id]
            if rc:
                await rc.markmap(ctx, False, numbers)
            else:
                await ctx.send("This realm clearing has ended!")
        else:
            await ctx.send("You aren't marking for any realm clearing sessions!")

    @commands.command(usage="unmarkmap <number(s)>", aliases=["umm"], description="Unmark the map with specified numbers.")
    @commands.guild_only()
    @checks.is_mm_or_higher_check()
    async def unmarkmap(self, ctx, *numbers):
        await ctx.message.delete()
        if ctx.author.id in self.client.mapmarkers:
            rc = self.client.mapmarkers[ctx.author.id]
            if rc:
                await rc.markmap(ctx, True, numbers)
            else:
                await ctx.send("This realm clearing has ended!")
        else:
            await ctx.send("You aren't marking for any realm clearing sessions!")

    @commands.command(usage="eventspawn <event>", aliases=['es'], description="Mark when an event spawns.")
    @commands.guild_only()
    @checks.is_mm_or_higher_check()
    async def eventspawn(self, ctx, event):
        await ctx.message.delete()
        if ctx.author.id in self.client.mapmarkers:
            rc = self.client.mapmarkers[ctx.author.id]
            if rc:
                await rc.eventspawn(ctx, False, event)
            else:
                await ctx.send("This realm clearing has ended!")
        else:
            await ctx.send("You aren't marking for any realm clearing sessions!")

    @commands.command(usage="uneventspawn <event>", aliases=['ues'], description="Unmark an event spawn.")
    @commands.guild_only()
    @checks.is_mm_or_higher_check()
    async def uneventspawn(self, ctx, event):
        await ctx.message.delete()
        if ctx.author.id in self.client.mapmarkers:
            rc = self.client.mapmarkers[ctx.author.id]
            if rc:
                await rc.eventspawn(ctx, True, event)
            else:
                await ctx.send("This realm clearing has ended!")
        else:
            await ctx.send("You aren't marking for any realm clearing sessions!")


def setup(client):
    client.add_cog(Raiding(client))


defaultnames = ["darq", "deyst", "drac", "drol", "eango", "eashy", "eati", "eendi", "ehoni", "gharr", "iatho", "iawa", "idrae", "iri", "issz", "itani", "laen", "lauk", "lorz",
                "oalei", "odaru", "oeti", "orothi", "oshyu", "queq", "radph", "rayr", "ril", "rilr", "risrr", "saylt", "scheev", "sek", "serl", "seus", "tal", "tiar", "uoro",
                "urake", "utanu", "vorck", "vorv", "yangu", "yimi", "zhiar"]


def parse_image(author, image, vc, members=False):
    res = get_crasher_lists(image, author, vc)
    if members:
        return res
    else:
        if not res:
            embed = discord.Embed(title="Error!", description="Could not find the who command in the image you provided.\nPlease re-run the "
                                                              "command with an image that shows the results of `/who`.", color=discord.Color.red())
            return embed
        else:
            crashing, possible_alts, fixed_names = res

        kicklist = "".join("`/kick " + m + "`\n" for m in crashing)
        if not kicklist:
            kicklist = "No members crashing!"
        if fixed_names:
            fixedlist = "     Fixed Name | Original Parse".join("`/kick " + fixed + "` | (" + orig + ")\n" for (orig, fixed) in fixed_names)
        if possible_alts:
            altlist = "".join("`" + name + "`\n" for name in possible_alts)
        if len(kicklist) > 2000:
            kicklist = "Too many characters (>2000)!\nTry again with a smaller list!"
        embed = discord.Embed(title=f"Parsing Results for {vc.name}", description=f"Possible Crashers: **{len(crashing)}**",
                              color=discord.Color.orange()).add_field(name="Members in run but not in vc:", value=kicklist, inline=True)
        if fixed_names:
            embed.add_field(name="Possible Fixed Names", value=fixedlist)
        if possible_alts:
            embed.add_field(name="Possible Alts (In VC but not in game)", value=altlist)
        return embed

def get_crasher_lists(image, author, vc):
    file_bytes = np.asarray(bytearray(image.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    width = img.shape[:2][1]
    factor = 700 / width
    img = cv2.resize(img, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # define range of yellow color in HSV
    lower = np.array([27, 130, 180])
    upper = np.array([31, 255, 255])
    # Threshold the HSV image to get only yellow colors
    mask = cv2.inRange(hsv, lower, upper)
    # cv2.imwrite("mask.jpg", mask)
    # invert the mask to get yellow letters on white background
    res = cv2.bitwise_not(mask)
    # cv2.imwrite("res.jpg", res)
    kernel = np.ones((2, 2), np.uint8)
    res = cv2.erode(res, kernel, iterations=1)
    blur = cv2.GaussianBlur(res, (3, 3), 0)

    str = pytesseract.image_to_string(blur, lang='eng')
    str = str.replace("\n", " ")
    str = str.replace("}", ")")
    str = str.replace("{", "(")
    str = str.replace(";", ":")
    str = str.replace('.', ',')
    split_str = re.split(r'(.*)(Players online \([0-9]+\): )', str)
    if len(split_str) < 4:
        print("ERROR - Parsed String: " + str)
        print("INFO - Split String: ")
        print(split_str)
        return None
    names = split_str[3].split(", ")
    cleaned_members = []
    alts = []

    def clean_member(m):
        if " | " in m:
            names = m.split(" | ")
            for i, name in enumerate(names):
                if i == 0:
                    cleaned_members.append(clean_name(name))
                else:
                    alts.append(clean_name(name))
        else:
            cleaned_members.append(clean_name(m))

    def clean_name(n):
        return "".join(c for c in n.lower() if c.isalpha())

    for m in vc.members:
        if not m.bot:
            clean_member(m.display_name)

    crashing = []
    possible_alts = []
    fixed_names = []
    author = clean_name(author.display_name)
    for name in names:
        if " " in name:
            names = name.split(" ")
            name = names[0]
        lname = name.lower().strip()
        if name.lower() not in defaultnames:
            if lname not in cleaned_members:
                matches = get_close_matches(lname, cleaned_members, n=1, cutoff=0.6)
                if len(matches) == 0:
                    if lname not in alts:
                        crashing.append(name.strip())
                else:
                    if matches[0] not in cleaned_members:
                        fixed_names.append((name.strip(), matches[0]))
                    else:
                        cleaned_members.remove(matches[0])
            else:
                cleaned_members.remove(lname)

    for m in cleaned_members:
        if m != author:
            possible_alts.append(m)

    return crashing, possible_alts, fixed_names



def event_type(type):
    event_types = {'ava': 'Avatar of the Forgotten King', 'avatar': 'Avatar of the Forgotten King', 'cube': 'Cube God',
                   'cubegod': 'Cube God', 'gship': 'Ghost Ship', 'sphinx': 'Grand Sphinx', 'hermit': 'Hermit God', 'herm': 'Hermit God',
                   'lotll': 'Lord of the Lost Lands', 'lord': 'Lord of the Lost Lands', 'pent': 'Pentaract', 'penta': 'Pentaract',
                   'drag': 'Rock Dragon', 'rock': 'Rock Dragon', 'skull': 'Skull Shrine', 'shrine': 'Skull Shrine',
                   'skullshrine': 'Skull Shrine', 'miner': 'Dwarf Miner', 'dwarf': 'Dwarf Miner', 'sentry': 'Lost Sentry',
                   'nest': 'Killer Bee Hive', 'hive': 'Killer Bee Hive', 'statues': 'Temple Statues', 'keyper': 'Keyper', 'keyper towers': 'Keyper Crystal Spawn',
                   'last ent': 'Last Ent', 'ent': 'Ent Ancient',
                   'red demon': 'Red Demon', 'demon': 'Red Demon', 'cyclops': 'Cyclops God', 'lich': 'Lich King', 'last lich': 'Last Lich', 'beach': 'Beach Bum'}
    result = event_types.get(type, None)
    if result is None:
        matches = get_close_matches(type, event_types.keys(), n=1, cutoff=0.8)
        if len(matches) == 0:
            return None
        return event_types.get(matches[0])
    return result
