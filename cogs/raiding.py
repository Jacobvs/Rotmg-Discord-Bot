import io
import os
from datetime import datetime
from difflib import get_close_matches
import aiohttp
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from matplotlib.patches import Circle
import json

import discord
from discord.ext import tasks, commands
from math import ceil

import embeds

from checks import is_rl_or_higher_check, is_vet_rl_or_higher, is_mm_or_higher_check, is_role_or_higher
from cogs import core
from sql import gld_cols, get_guild

load_dotenv()
imgurid = os.getenv('IMGUR_ID')

class Raiding(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command(usage="!afk [type of run] [channel] <location>")
    @commands.guild_only()
    @commands.check(is_rl_or_higher_check)
    # TODO: ADD Leader check
    # TODO: add check that guild has no running afk up
    async def afk(self, ctx, type, channel='1', *location):
        """Starts an AFK check for the type of run specified. \nValid channel types are: ```1, 2, 3, vet/veteran```Valid run types are: ```realmclear, fametrain, void, fskipvoid, cult```"""
        if len(location) == 0:
            location = "No location specified."
        else:
            location = " ".join(location)

        # TODO CHECK IF IS OPTION FOR CHANNEL NUM
        guild_db = await get_guild(self.client.pool, ctx.guild.id)
        if channel == "vet" or channel == "veteran":
            if await is_vet_rl_or_higher(self.client.pool, ctx.author, ctx.guild):
                hc_channel = ctx.guild.get_channel(guild_db[gld_cols.vethcid])
                vc = ctx.guild.get_channel(guild_db[gld_cols.vetvcid])
                role = discord.utils.get(ctx.guild.roles, id=guild_db[gld_cols.vetroleid])
            else:
                return await ctx.send("You have to be a vet rl to use this command.")
        else:
            role = discord.utils.get(ctx.guild.roles, id=guild_db[gld_cols.verifiedroleid])
            if channel == '1':
                hc_channel = ctx.guild.get_channel(guild_db[gld_cols.raidhc1])
                vc = ctx.guild.get_channel(guild_db[gld_cols.raidvc1])
            elif channel == '2':
                hc_channel = ctx.guild.get_channel(guild_db[gld_cols.raidhc2])
                vc = ctx.guild.get_channel(guild_db[gld_cols.raidvc2])
            elif channel == '3':
                hc_channel = ctx.guild.get_channel(guild_db[gld_cols.raidhc3])
                vc = ctx.guild.get_channel(guild_db[gld_cols.raidvc3])
            else:
                return await ctx.send("That channel number is not an option, please choose a channel from 1-3 or 'vet'/'veteran'")


        # TODO: Create run object for guild -- give lock on command until
        # TODO: Send control panel embed to ctx channel
        # TODO: Lock & unlock channel dynamically
        title = run_title(type)
        if title is None:
            return await ctx.send("The specified run type is not an option.")
        if title[1] is True:
            await ctx.send(f"A correction was made, `{type}` was changed to `{title[2]}`")

        keyed_run = True
        if title[0] == 'Realm Clearing' or title[0] == 'Fame Train':
            keyed_run = False

        if " <-- Join!" not in vc.name:
            await vc.edit(name=vc.name + " <-- Join!")
        await vc.set_permissions(target=role, connect=True, view_channel=True, speak=False)
        emojis = run_emojis(title[0])
        state = get_state(ctx.guild, core.states)
        if title[0] == 'Fame Train':
            embed = embeds.afk_check_base(title[0], ctx.author, keyed_run, emojis, location)
        else:
            embed = embeds.afk_check_base(title[0], ctx.author, keyed_run, emojis)
        msg = await hc_channel.send(f"@here `{title[0]}` {emojis[0]} started by {ctx.author.mention} in {vc.name}",
                                    embed=embed)
        embed = embeds.afk_check_control_panel(msg.jump_url, location, title[0], emojis[1], keyed_run)
        cpmsg = await ctx.send(embed=embed)
        start_run(state, title, keyed_run, emojis, vc, msg, cpmsg, location, self.update_afk_loop)
        for e in emojis:
            await msg.add_reaction(e)
        await msg.add_reaction('<:shard:682365548465487965>')
        await msg.add_reaction('❌')

        # TODO keep track of running tasks and don't allow if running
        self.update_afk_loop.start(msg, ctx.guild)

    @tasks.loop(seconds=5.0, count=72)  # loop for 6 mins
    async def update_afk_loop(self, msg, guild):
        if self.update_afk_loop.current_loop == 71:
            await end_afk_check(self.client.pool, None, guild, True)
        else:
            uptime = (self.update_afk_loop.current_loop + 2) * 5
            minutes = 6 - ceil(uptime / 60)
            seconds = 60 - uptime % 60
            state = get_state(guild, core.states)
            embed = msg.embeds[0]
            embed.set_footer(
                text=f"Time Remaining: {minutes} minutes and {seconds} seconds | Raiders accounted for: {len(state.raiders)}")
            await msg.edit(embed=embed)


    @commands.command(usage="!headcount [type of run] [hc_channel_num]", aliases=["hc"])
    @commands.guild_only()
    @commands.check(is_rl_or_higher_check)
    async def headcount(self, ctx, type, hc_channel_num='1'):
        """Starts a headcount for the type of run specified. Valid run types are: ```realmclear, fametrain, void, fskipvoid, cult```"""
        guild_db = await get_guild(self.client.pool, ctx.guild.id)
        if hc_channel_num == "vet" or hc_channel_num == "veteran":
            if await is_vet_rl_or_higher(self.client.pool, ctx.author, ctx.guild):
                hc_channel = ctx.guild.get_channel(guild_db[gld_cols.vethcid])
            else:
                return await ctx.send("You have to be a vet rl to use this command.")
        elif hc_channel_num == '1':
            hc_channel = ctx.guild.get_channel(guild_db[gld_cols.raidhc1])
        elif hc_channel_num == '2':
            hc_channel = ctx.guild.get_channel(guild_db[gld_cols.raidhc2])
        elif hc_channel_num == '3':
            hc_channel = ctx.guild.get_channel(guild_db[gld_cols.raidhc3])
        else:
            return await ctx.send(
                "That channel number is not an option, please choose a channel from 1-3 or 'vet'/'veteran'")

        title = run_title(type)
        if title is None:
            return await ctx.send("The specified run type is not an option.")
        if title[1] is True:
            await ctx.send(f"A correction was made, `{type}` was changed to `{title[2]}`")

        keyed_run = True
        if title[0] == 'Realm Clearing' or title[0] == 'Fame Train':
            keyed_run = False
        emojis = run_emojis(title[0])
        embed = embeds.headcount_base(title[0], ctx.author, keyed_run, emojis)
        msg = await hc_channel.send("@here", embed=embed)
        for e in emojis:
            await msg.add_reaction(e)
        await ctx.send("Your headcount has been started!")

    @commands.command(usage="!lock [vc_channel]")
    @commands.guild_only()
    @commands.check(is_rl_or_higher_check)
    async def lock(self, ctx, vc_channel):
        """Locks the raiding voice channel"""
        guild_db = await get_guild(self.client.pool, ctx.guild.id)
        if vc_channel == "vet" or vc_channel == "veteran":
            if await is_vet_rl_or_higher(self.client.pool, ctx.author, ctx.guild):
                vc = ctx.guild.get_channel(guild_db[gld_cols.vetvcid])
                role = discord.utils.get(ctx.guild.roles, id=guild_db[gld_cols.vetroleid])
            else:
                return await ctx.send("You have to be a vet rl to use this command.")
        else:
            role = discord.utils.get(ctx.guild.roles, id=guild_db[gld_cols.verifiedroleid])
            if vc_channel == '1':
                vc = ctx.guild.get_channel(guild_db[gld_cols.raidvc1])
            elif vc_channel == '2':
                vc = ctx.guild.get_channel(guild_db[gld_cols.raidvc2])
            elif vc_channel == '3':
                vc = ctx.guild.get_channel(guild_db[gld_cols.raidvc3])
            else:
                return await ctx.send("That channel number is not an option, please choose a channel from 1-3 or 'vet'/'veteran'")
        vc_name = vc.name
        if " <-- Join!" in vc_name:
            vc_name = vc_name.split(" <")[0]
            await vc.edit(name=vc_name)
        await vc.set_permissions(role, connect=False, view_channel=True, speak=False)
        await ctx.send(f"{vc.name} Has been Locked!")

    @commands.command(usage="!unlock [vc_channel]")
    @commands.guild_only()
    @commands.check(is_rl_or_higher_check)
    async def unlock(self, ctx, vc_channel):
        """Unlocks the raiding voice channel"""
        guild_db = await get_guild(self.client.pool, ctx.guild.id)
        if vc_channel == "vet" or vc_channel == "veteran":
            if await is_vet_rl_or_higher(self.client.pool, ctx.author, ctx.guild):
                vc = ctx.guild.get_channel(guild_db[gld_cols.vetvcid])
                role = discord.utils.get(ctx.guild.roles, id=guild_db[gld_cols.vetroleid])
            else:
                return await ctx.send("You have to be a vet rl to use this command.")
        else:
            role = discord.utils.get(ctx.guild.roles, id=guild_db[gld_cols.verifiedroleid])
            if vc_channel == '1':
                vc = ctx.guild.get_channel(guild_db[gld_cols.raidvc1])
            elif vc_channel == '2':
                vc = ctx.guild.get_channel(guild_db[gld_cols.raidvc2])
            elif vc_channel == '3':
                vc = ctx.guild.get_channel(guild_db[gld_cols.raidvc3])
            else:
                return await ctx.send(
                    "That channel number is not an option, please choose a channel from 1-3 or 'vet'/'veteran'")
        await vc.edit(name=vc.name + " <-- Join!")
        await vc.set_permissions(role, connect=True, view_channel=True, speak=False)
        await ctx.send(f"{vc.name} Has been unlocked!")

    @commands.command(usage="!realmclear [world #] [hc_channel_num] [location]")
    @commands.guild_only()
    @commands.check(is_rl_or_higher_check)
    async def realmclear(self, ctx, world_num, channel="1", *location):
        #TODO: Check world number

        if len(location) == 0:
            location = "No location specified."
        else:
            location = " ".join(location)

        # TODO CHECK IF IS OPTION FOR CHANNEL NUM
        guild_db = await get_guild(self.client.pool, ctx.guild.id)
        if channel == "vet" or channel == "veteran":
            if await is_vet_rl_or_higher(self.client.pool, ctx.author, ctx.guild):
                hc_channel = ctx.guild.get_channel(guild_db[gld_cols.vethcid])
                vc = ctx.guild.get_channel(guild_db[gld_cols.vetvcid])
                role = discord.utils.get(ctx.guild.roles, id=guild_db[gld_cols.vetroleid])
            else:
                return await ctx.send("You have to be a vet rl to use this command.")
        else:
            role = discord.utils.get(ctx.guild.roles, id=guild_db[gld_cols.verifiedroleid])
            if channel == '1':
                hc_channel = ctx.guild.get_channel(guild_db[gld_cols.raidhc1])
                vc = ctx.guild.get_channel(guild_db[gld_cols.raidvc1])
            elif channel == '2':
                hc_channel = ctx.guild.get_channel(guild_db[gld_cols.raidhc2])
                vc = ctx.guild.get_channel(guild_db[gld_cols.raidvc2])
            elif channel == '3':
                hc_channel = ctx.guild.get_channel(guild_db[gld_cols.raidhc3])
                vc = ctx.guild.get_channel(guild_db[gld_cols.raidvc3])
            else:
                return await ctx.send("That channel number is not an option, please choose a channel from 1-3 or 'vet'/'veteran'")

        if " <-- Join!" not in vc.name:
            await vc.edit(name=vc.name + " <-- Join!")
        await vc.set_permissions(target=role, connect=True, view_channel=True, speak=False)
        emojis = run_emojis("Realm Clearing")
        embed = embeds.afk_check_base("Realm Clearing", ctx.author, False, emojis)
        msg = await hc_channel.send(f"@here `Realm Clearing` {emojis[0]} started by {ctx.author.mention} in {vc.name}",
                                    embed=embed)

        embed = embeds.afk_check_control_panel(msg.jump_url, location, "Realm Clearing", emojis[1], False) # TODO: CHANGE TO ADD marked #'s
        state = get_rcstate(ctx.guild, core.rcstates)
        cpmsg = await ctx.send(embed=embed)
        for e in emojis:
            await msg.add_reaction(e)
        await msg.add_reaction('<:shard:682365548465487965>')
        # await msg.add_reaction('❌')
        world_num = world_num.lower()
        if "w" in world_num:
            world_num = world_num.replace("w", "")
        #image = self.client.imgur.upload_image(f"world-maps/world_{world_num}.png")
        img_data = await imgur_upload(open(f"world-maps/world_{world_num}.png", 'rb'))
        embed = discord.Embed(
            title="Current Map:",
            description="`Spawns left: All -- 0% Cleared`",
        )
        embed.set_image(url=img_data["link"])
        mapmsg = await hc_channel.send(embed=embed)
        start_rc(state, world_num, mapmsg, hc_channel, cpmsg, msg, location)
        #TODO set in sql as well

    @commands.command(usage="!markmap/mm [number(s)]", aliases=["mm"])
    @commands.guild_only()
    @commands.check(is_mm_or_higher_check)
    async def markmap(self, ctx, *numbers):
        await mapmarkhelper(ctx, numbers, False)

    @commands.command(usage="!unmarkmap/umm [number(s)]", aliases=["umm"])
    @commands.guild_only()
    @commands.check(is_mm_or_higher_check)
    async def unmarkmap(self, ctx, *numbers):
        await mapmarkhelper(ctx, numbers, True)


def setup(client):
    client.add_cog(Raiding(client))


class GuildRaidState:
    """Helper class managing per-guild raiding state."""

    def __init__(self):
        self.runtitle = ""
        self.keyedrun = None
        self.emojis = None
        self.vc = None
        self.msg = None
        self.cpmessage = None
        self.starttime = None
        self.raiders = []
        self.mainkey = None
        self.backupkey1 = None
        self.keyreacts = []
        self.mainvial = None
        self.backupvial = None
        self.vialreacts = []
        self.location = "No location specified."
        self.nitroboosters = []
        self.loop = None

class GuildRealmClearState:
    def __init__(self):
        self.markednums = []
        self.worldnum = None
        self.mapmsg = None
        self.hcchannel = None
        self.cpmsg = None
        self.msg = None
        self.location = None
        self.nitroboosters = []


def start_run(state, title, keyed_run, emojis, vc, msg, cpmsg, location, loop):
    state.runtitle = title
    state.keyedrun = keyed_run
    state.emojis = emojis
    state.vc = vc
    state.msg = msg
    state.cpmessage = cpmsg
    state.starttime = datetime.utcnow()
    state.raiders = []
    state.mainkey = None
    state.backupkey1 = None
    state.keyreacts = []
    state.mainvial = None
    state.backupvial = None
    state.vialreacts = []
    state.location = location
    state.nitroboosters = []
    state.loop = loop

def start_rc(state, worldnum, mapmsg, hcchannel, cpmsg, msg, location):
    state.markednums = []
    state.worldnum = worldnum
    state.mapmsg = mapmsg
    state.hcchannel = hcchannel
    state.cpmsg = cpmsg
    state.msg = msg
    state.location = location
    state.nitroboosters = []

#TODO : Add getter/setter state methods to manage sql queries

def get_state(guild, st):
    """Gets the state for `guild`, creating it if it does not exist."""
    if guild.id in st:
        return st[guild.id]
    else:
        st[guild.id] = GuildRaidState()
        return st[guild.id]

def get_rcstate(guild, st):
    if guild.id in st:
        return st[guild.id]
    else:
        st[guild.id] = GuildRealmClearState()
        return st[guild.id]

async def mapmarkhelper(ctx, numbers, remove):
    # TODO: CHECK IF CLEARING IS HAPPENING ATM
    state = get_rcstate(ctx.guild, core.rcstates)
    with open("data/world_data_clean.json") as file:
        data = json.load(file)
    badnumbers = []
    limit = data[f"world_{state.worldnum}.png"]["range"]
    for num in numbers:
        if "-" in num:
            lower = int(num.split("-")[0])
            upper = int(num.split("-")[1])+1
        else:
            lower = int(num)
            upper = int(num)+1
        for n in range(lower, upper):
            ismarked = n in state.markednums
            if n-1 < 0 or n-1 > limit or (ismarked and not remove) or (not ismarked and remove):
                badnumbers.append(n)
            else:
                if not remove:
                    state.markednums.append(n)
                else:
                    state.markednums.remove(n)

    if len(badnumbers) >= 1:
        await ctx.send(f"Some of the numbers provided were out of range or already cleared. Bad numbers: `{badnumbers}`", delete_after=5)
    img = plt.imread(f"world-maps/world_{state.worldnum}.png")
    fig, ax = plt.subplots(1)
    ax.set_aspect('equal')
    ax.axis("off")
    ax.imshow(img)
    for n in state.markednums:
        point = data[f"world_{state.worldnum}.png"][str(n-1)]
        circ = Circle((point["x"], point["y"]), 30, color='#0000FFC8')
        ax.add_patch(circ)
    file = io.BytesIO()
    plt.savefig(file, transparent=True, bbox_inches='tight', pad_inches=0, format='png', dpi=500)
    file.seek(0)
    try:
        await ctx.message.delete()
    except discord.errors.NotFound:
        print("Message not found")
    spawns_left = (limit+1) - len(state.markednums)
    percent = len(state.markednums)/(limit+1)
    embed = state.cpmsg.embeds[0]
    embed.set_field_at(1, name="Cleared Numbers:", value=f"`{state.markednums.sort()}`", inline=False)
    await state.cpmsg.edit(embed=embed)

    img_data = await imgur_upload(file.read())
    embed = state.mapmsg.embeds[0]
    embed.set_image(url=img_data["link"])
    embed.description = f"Current Map:\n`Spawns left: {spawns_left} -- {percent:.0%} Cleared`"
    await state.mapmsg.edit(embed=embed)


async def end_afk_check(pool, member, guild, auto):
    guild_db = await get_guild(pool, guild.id)
    rl_role = guild_db[gld_cols.rlroleid]
    if auto or await is_role_or_higher(pool, member, guild, rl_role):
        state = get_state(guild, core.states)

        # Lock VC
        role = discord.utils.get(guild.roles, id=guild_db[gld_cols.verifiedroleid])
        if state.loop:
            state.loop.cancel()
        vc_name = state.vc.name
        if " <-- Join!" in vc_name:
            vc_name = vc_name.split(" <")[0]
            await state.vc.edit(name=vc_name)
        await state.vc.set_permissions(role, connect=False, view_channel=True, speak=False)
        # Edit msg to post afk
        embed = state.msg.embeds[0]
        embed.description = (
            "__**Post Afk move-in!**__\nIf you got disconnected or simply missed the AFK check, **first** join lounge - **then** react with "
            f"{state.emojis[0]} to get moved in.\n__Time Remaining:__ 30 Seconds.")
        if auto:
            embed.set_footer(text=f"The afk check has been ended due to the time running out.")
        else:
            embed.set_footer(text=f"The afk check has been ended by {member.nick}")
        embed.timestamp = datetime.utcnow()
        await state.msg.edit(content=None, embed=embed)
        await state.msg.clear_reaction('❌')
        # Kick members who haven't reacted
        for m in state.vc.members:
            if m.id not in state.raiders and not await is_role_or_higher(pool, m, guild, rl_role):
                try:
                    await m.edit(voice_channel=None)
                except discord.errors.Forbidden:
                    print(f"Missing perms to move member out: {m.nick}")
        post_afk_loop.start(state, guild.id)


@tasks.loop(seconds=5.0, count=7)  # 35s
async def post_afk_loop(state, guild_id):
    embed = state.msg.embeds[0]
    if post_afk_loop.current_loop == 6:
        embed.description = f"The AFK Check has ended.\nWe are currently running a raid with {len(state.raiders)} raiders."
        await state.msg.edit(embed=embed)
        # TODO: LOG STATE FOR RUN COMPLETION -- EDIT CP_MSG to reaction for correct log & log_run command
        core.states.pop(guild_id)
    else:
        uptime = (post_afk_loop.current_loop + 2) * 5
        seconds = 35 - uptime % 60
        embed.description = embed.description.split("Remaining:__")[0] + f"Remaining:__ {seconds} seconds."
        await state.msg.edit(embed=embed)


async def afk_check_reaction_handler(pool, payload, member, guild):
    emoji_id = payload.emoji.id
    state = get_state(guild, core.states)
    guild_db = await get_guild(pool, guild.id)
    rl_role = guild_db[gld_cols.rlroleid]
    if state.msg is not None and payload.message_id == state.msg.id:
        if str(emoji_id) == state.emojis[0].split(":")[2].split(">")[0]:
            if member.id not in state.raiders:
                state.raiders.append(member.id)
            if member.voice:
                try:
                    await member.edit(voice_channel=state.vc)
                except discord.errors.Forbidden:
                    print(f"Missing perms to move member out: {member.nick}")
        elif emoji_id in key_ids:
            if emoji_id == 682205784524062730:  # If emoji is vial
                if member.id not in state.vialreacts:
                    state.vialreacts.append(member.id)
                msg = await member.send("Do you have a vial and are willing to pop it? If so, react to the vial.")
                await msg.add_reaction('<:vial:682205784524062730>')
            else:
                if member.id not in state.keyreacts:
                    state.keyreacts.append(member.id)
                msg = await member.send("Do you have a key and are willing to pop it? If so, react to the key.")
                await msg.add_reaction(state.emojis[1])

        elif emoji_id == 682365548465487965:  # if react is nitro
            if member.premium_since is not None or await is_role_or_higher(pool, member, guild, rl_role):
                if state.location != "No location specified.":
                    await member.send(f"The location for this run is: __{state.location}__")
                else:
                    await member.send(
                        f"The location has not been set yet. Wait for the rl to set the location, then re-react.")
                if member.nick not in state.nitroboosters:
                    state.nitroboosters.append(member.nick)
                if state.cpmessage is not None:
                    embed = state.cpmessage.embeds[0]
                    index = 1
                    index += 1 if state.keyedrun else 0
                    index += 1 if state.runtitle[0] == "Void" or state.runtitle[0] == "Full-Skip Void" else 0
                    embed.set_field_at(index, name="Nitro Boosters with location:", value=f"`{state.nitroboosters}`",
                                       inline=False)
                    await state.cpmessage.edit(embed=embed)
    else:
        rcstate = get_rcstate(guild, core.rcstates)
        if payload.message_id == rcstate.msg.id:
            if emoji_id == 682365548465487965:  # if react is nitro
                if member.premium_since is not None or await is_role_or_higher(pool, member, guild, rl_role):
                    if rcstate.location != "No location specified.":
                        await member.send(f"The location for this run is: __{rcstate.location}__")
                    else:
                        await member.send(
                            f"The location has not been set yet. Wait for the rl to set the location, then re-react.")
                    if member.nick not in rcstate.nitroboosters:
                        rcstate.nitroboosters.append(member.nick)
                    if rcstate.cpmsg is not None:
                        embed = rcstate.cpmsg.embeds[0]
                        embed.set_field_at(2, name="Nitro Boosters with location:", value=f"`{rcstate.nitroboosters}`",
                                           inline=False)
                        await rcstate.cpmsg.edit(embed=embed)


async def imgur_upload(binary):
    payload = {'image': binary, 'type': 'file'}
    header = {"Authorization": f"Client-ID {imgurid}"}
    async with aiohttp.ClientSession(headers=header) as cs:
        async with cs.post("https://api.imgur.com/3/image", data=payload) as r:
            res = await r.json()  # returns dict
    return res["data"]


async def confirmed_raiding_reacts(payload, user):
    state = None
    vial = True if payload.emoji.id == 682205784524062730 else False
    for s in core.states.values():
        if user.id in s.vialreacts or user.id in s.keyreacts:
            state = s

    if state is None:
        return

    embed = state.cpmessage.embeds[0]
    if vial:
        if state.mainvial is None:
            embed.set_field_at(1, name="Vials:",
                               value=f"Main <:vial:682205784524062730>: {user.mention}\nBackup <:vial:682205784524062730>: None",
                               inline=False)
            await state.cpmessage.edit(embed=embed)
            state.mainvial = user
        elif state.backupvial is None and state.mainvial != user:
            embed.set_field_at(1, name="Vials:",
                               value=f"Main <:vial:682205784524062730>: {state.mainvial.mention}\nBackup <:vial:682205784524062730>: {user.mention}",
                               inline=False)
            await state.cpmessage.edit(embed=embed)
            state.backupvial = user
        else:
            return await user.send("There are already enough vials")
    else:
        key_emoji = key_emojis[key_ids.index(payload.emoji.id)]
        if state.mainkey is None:
            embed.set_field_at(0, name="Current Keys:",
                               value=f"Main {key_emoji}: {user.mention}\nBackup {key_emoji}: None", inline=False)
            await state.cpmessage.edit(embed=embed)
            state.mainkey = user
        elif state.backupvial is None and state.mainvial != user:
            embed.set_field_at(0, name="Current Keys:",
                               value=f"Main {key_emoji}: {state.mainkey.mention}\nBackup {key_emoji}: {user.mention}",
                               inline=False)
            await state.cpmessage.edit(embed=embed)
            state.backupkey = user
        else:
            return await user.send("There are already enough keys")

    if state.location != "No location specified.":
        await user.send(f"The location for this run is: __{state.location}__")
    else:
        await user.send(f"The location has not been set yet. Message the RL to get location.")


def run_title(type):
    run_types = {
        'realmclear': "Realm Clearing",
        'fametrain': "Fame Train",
        'void': "Void",
        'fskipvoid': "Full-Skip Void",
        'cult': "Cult",
        'eventdungeon': "Event Dungeon"
    }
    result = run_types.get(type, None)
    if result is None:
        matches = get_close_matches(type, run_types.keys(), n=1, cutoff=0.8)
        if len(matches) == 0:
            return None
        return (run_types.get(matches[0]), True, matches[0])
    return (result, False)


default_emojis = ["<:defaultdungeon:682212333182910503>", "<:eventkey:682212349641621506>",
                  "<:warrior:682204616997208084>", "<:knight:682205672116584459>", "<:paladin:682205688033968141>",
                  "<:priest:682206578908069905>"]


def run_emojis(type):
    return {
        'Realm Clearing': ["<:defaultdungeon:682212333182910503>", "<:trickster:682214467483861023>"],
        'Fame Train': ["<:fame:682209281722024044>", "<:sorcerer:682214487490560010>",
                      "<:necromancer:682214503106215966>", "<:sseal:683815374403141651>",
                      "<:paladin:682205688033968141>"],
        'Void': ["<:void:682205817424183346>", "<:lhkey:682205801728835656>", "<:vial:682205784524062730>",
                 default_emojis[2], default_emojis[3], default_emojis[4], "<:mseal:682205755754938409>",
                 "<:puri:682205769973760001>", "<:planewalker:682212363889279091>"],
        'Full-Skip Void': ["<:fskipvoid:682206558075224145>", "<:lhkey:682205801728835656>", "<:vial:682205784524062730>",
                      default_emojis[2], default_emojis[3], default_emojis[4], "<:mseal:682205755754938409>",
                      "<:puri:682205769973760001>", "<:brainofthegolem:682205737492938762>",
                      "<:mystic:682205700918607969>"],
        'Cult': ["<:cult:682205832879800388>", "<:lhkey:682205801728835656>", default_emojis[2], default_emojis[3],
                 default_emojis[4], "<:puri:682205769973760001>", "<:planewalker:682212363889279091>"],
        'Event Dungeon': default_emojis
    }.get(type, default_emojis)


main_run_emojis = ["<:whitebag:682208350481547267>", "<:fame:682209281722024044>", "<:void:682205817424183346>",
                   "<:fskipvoid:682206558075224145>", "<:cult:682205832879800388>"]
key_emojis = ["<:lhkey:682205801728835656>", "<:vial:682205784524062730>", "<:eventkey:682212349641621506>"]
key_ids = [682205801728835656, 682205784524062730, 682212349641621506]
