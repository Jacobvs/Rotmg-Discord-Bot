from datetime import datetime
from difflib import get_close_matches
from math import ceil

import discord
from discord.ext import tasks, commands

import embeds
import sql
from checks import is_rl_or_higher_check, is_rl_or_higher
from cogs import core


class Raiding(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command(usage="!afk [type of run] [hc_channel_num] <location>")
    @commands.guild_only()
    @commands.check(is_rl_or_higher_check)
    # TODO: ADD Leader check
    # TODO: add check that guild has no running afk up
    async def afk(self, ctx, type, hc_channel_num, *location):
        """Starts an AFK check for the type of run specified. Valid run types are: ```realmclear, fametrain, void, fskipvoid, cult```"""
        if len(location) == 0:
            location = "No location specified."
        else:
            loc = ""
            for s in location:
                loc += s + " "
            location = loc

        # TODO CHECK IF IS OPTION FOR CHANNEL NUM
        guild_db = sql.get_guild(ctx.guild.id)

        if hc_channel_num == '1':
            hc_channel = ctx.guild.get_channel(guild_db[sql.gld_cols.raidhc1])
            vc = ctx.guild.get_channel(guild_db[sql.gld_cols.raidvc1])
        elif hc_channel_num == '2':
            hc_channel = ctx.guild.get_channel(guild_db[sql.gld_cols.raidhc2])
            vc = ctx.guild.get_channel(guild_db[sql.gld_cols.raidvc2])
        elif hc_channel_num == '3':
            hc_channel = ctx.guild.get_channel(guild_db[sql.gld_cols.raidhc3])
            vc = ctx.guild.get_channel(guild_db[sql.gld_cols.raidvc3])
        else:
            return await ctx.send("That channel number is not an option, please choose a channel from 1-3")
        role = discord.utils.get(ctx.guild.roles, id=guild_db[sql.gld_cols.verifiedroleid])

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
        await vc.set_permissions(target=role, connect=True)
        emojis = run_emojis(type)
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

        self.update_afk_loop.start(msg, ctx.guild)

    @tasks.loop(seconds=5.0, count=73)  # loop for 6 mins
    async def update_afk_loop(self, msg, guild):
        if self.update_afk_loop.current_loop == 6:
            await end_afk_check(None, guild, True)
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
    async def headcount(self, ctx, type, hc_channel_num=1):
        """Starts a headcount for the type of run specified. Valid run types are: ```realmclear, fametrain, void, fskipvoid, cult```"""
        guild_db = sql.get_guild(ctx.guild.id)
        if hc_channel_num == 1:
            hc_channel = ctx.guild.get_channel(guild_db[sql.gld_cols.raidhc1])
        elif hc_channel_num == 2:
            hc_channel = ctx.guild.get_channel(guild_db[sql.gld_cols.raidhc2])
        elif hc_channel_num == 3:
            hc_channel = ctx.guild.get_channel(guild_db[sql.gld_cols.raidhc3])
        else:
            return await ctx.send("That channel number is not an option, please choose a channel from 1-3")

        title = run_title(type)
        if title is None:
            return await ctx.send("The specified run type is not an option.")
        if title[1] is True:
            await ctx.send(f"A correction was made, `{type}` was changed to `{title[2]}`")

        keyed_run = True
        if title[0] == 'Realm Clearing' or title[0] == 'Fame Train':
            keyed_run = False
        emojis = run_emojis(type)
        embed = embeds.headcount_base(title[0], ctx.author, keyed_run, emojis)
        msg = await hc_channel.send("@here", embed=embed)
        for e in emojis:
            await msg.add_reaction(e)
        await ctx.send("Your headcount has been started!")

    @commands.command(usage="!lock")
    @commands.guild_only()
    @commands.check(is_rl_or_higher_check)
    async def lock(self, ctx):
        """Locks the raiding voice channel"""
        guild_db = sql.get_guild(ctx.guild.id)
        vc = ctx.guild.get_channel(guild_db[sql.gld_cols.raidvc1])
        role = discord.utils.get(ctx.guild.roles, id=guild_db[sql.gld_cols.verifiedroleid])
        vc_name = vc.name
        if " <-- Join!" in vc_name:
            vc_name = vc_name.split(" <")[0]
            await vc.edit(name=vc_name)
        await vc.set_permissions(role, connect=False, view_channel=True, speak=False)
        await ctx.send("Raiding 1 Has been Locked!")

    @commands.command(usage="!unlock")
    @commands.guild_only()
    @commands.check(is_rl_or_higher_check)
    async def unlock(self, ctx):
        """Unlocks the raiding voice channel"""
        guild_db = sql.get_guild(ctx.guild.id)
        vc = ctx.guild.get_channel(guild_db[sql.gld_cols.raidvc1])
        role = discord.utils.get(ctx.guild.roles, id=guild_db[sql.gld_cols.verifiedroleid])
        await vc.edit(name=vc.name + " <-- Join!")
        await vc.set_permissions(role, connect=True, view_channel=True, speak=False)
        await ctx.send("Raiding 1 Has been unlocked!")


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


def get_state(guild, st):
    """Gets the state for `guild`, creating it if it does not exist."""
    if guild.id in st:
        return st[guild.id]
    else:
        st[guild.id] = GuildRaidState()
        return st[guild.id]


async def end_afk_check(member, guild, auto):
    if auto or await is_rl_or_higher(member, guild):
        state = get_state(guild, core.states)
        guild_db = sql.get_guild(guild.id)
        # Lock VC
        role = discord.utils.get(guild.roles, id=guild_db[sql.gld_cols.verifiedroleid])
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
            if m.id not in state.raiders and not await is_rl_or_higher(m, guild):
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


async def afk_check_reaction_handler(payload, member, guild):
    emoji_id = payload.emoji.id
    state = get_state(guild, core.states)
    if payload.message_id == state.msg.id:
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
            if member.premium_since is not None or await is_rl_or_higher(member, guild):
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


async def confirmed_raiding_reacts(payload, user):
    state = None
    vial = True if payload.emoji.id == 682205784524062730 else False
    for s in core.states.values():
        if user.id in s.vialreacts or user.id in s.keyreacts:
            state = s

    if state == None:
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
        'realmclear': ["<:defaultdungeon:682212333182910503>", "<:trickster:682214467483861023>"],
        'fametrain': ["<:fame:682209281722024044>", "<:sorcerer:682214487490560010>",
                      "<:necromancer:682214503106215966>", "<:sseal:683815374403141651>",
                      "<:paladin:682205688033968141>"],
        'void': ["<:void:682205817424183346>", "<:lhkey:682205801728835656>", "<:vial:682205784524062730>",
                 default_emojis[2], default_emojis[3], default_emojis[4], "<:mseal:682205755754938409>",
                 "<:puri:682205769973760001>", "<:planewalker:682212363889279091>"],
        'fskipvoid': ["<:fskipvoid:682206558075224145>", "<:lhkey:682205801728835656>", "<:vial:682205784524062730>",
                      default_emojis[2], default_emojis[3], default_emojis[4], "<:mseal:682205755754938409>",
                      "<:puri:682205769973760001>", "<:brainofthegolem:682205737492938762>",
                      "<:mystic:682205700918607969>"],
        'cult': ["<:cult:682205832879800388>", "<:lhkey:682205801728835656>", default_emojis[2], default_emojis[3],
                 default_emojis[4], "<:puri:682205769973760001>", "<:planewalker:682212363889279091>"],
        'eventdungeon': default_emojis
    }.get(type, default_emojis)


main_run_emojis = ["<:whitebag:682208350481547267>", "<:fame:682209281722024044>", "<:void:682205817424183346>",
                   "<:fskipvoid:682206558075224145>", "<:cult:682205832879800388>"]
key_emojis = ["<:lhkey:682205801728835656>", "<:vial:682205784524062730>", "<:eventkey:682212349641621506>"]
key_ids = [682205801728835656, 682205784524062730, 682212349641621506]
