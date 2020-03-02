from datetime import datetime
from difflib import get_close_matches

import discord
from discord.ext import commands

import embeds
import sql
from cogs import core


class Raiding(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command(usage="!afk [type of run] [hc_channel_num] <location>")
    @commands.guild_only()
    @commands.has_permissions(manage_nicknames=True)
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

        # await vc.edit(name=vc.name + " <-- Join!")
        # await vc.set_permissions(role, connect=True)
        emojis = run_emojis(type)
        state = get_state(ctx.guild, core.states)
        if title[0] == 'Fame Train':
            embed = embeds.afk_check_base(title[0], ctx.author.nick, keyed_run, emojis, location)
        else:
            embed = embeds.afk_check_base(title[0], ctx.author.nick, keyed_run, emojis)
        msg = await hc_channel.send(f"@here `{title[0]}` {emojis[0]} started by {ctx.author.mention} in {vc.name}",
                                    embed=embed)
        embed = embeds.afk_check_control_panel(msg.jump_url, location, title[0], emojis[1], keyed_run)
        cpmsg = await ctx.send(embed=embed)
        start_run(state, title, keyed_run, emojis[1], msg.id, cpmsg, location)
        for e in emojis:
            await msg.add_reaction(e)
        await msg.add_reaction('<:shard:682365548465487965>')
        await msg.add_reaction('❌')

    @commands.command(usage="!headcount [type of run] [hc_channel_num]", aliases=["hc"])
    @commands.guild_only()
    @commands.has_permissions(manage_nicknames=True)
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
        embed = embeds.headcount_base(title[0], ctx.author.nick, keyed_run, emojis)
        msg = await hc_channel.send("@here", embed=embed)
        for e in emojis:
            await msg.add_reaction(e)
        await ctx.send("Your headcount has been started!")

    @commands.command(usage="!lock")
    @commands.has_permissions(manage_nicknames=True)
    @commands.guild_only()
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
    @commands.has_permissions(manage_nicknames=True)
    @commands.guild_only()
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
        self.keyemoji = None
        self.msgid = 0
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


def start_run(state, title, keyed_run, emoji, msg_id, cpmsg, location):
    state.runtitle = title
    state.keyedrun = keyed_run
    state.keyemoji = emoji
    state.msgid = msg_id
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


def get_state(guild, st):
    """Gets the state for `guild`, creating it if it does not exist."""
    if guild.id in st:
        return st[guild.id]
    else:
        st[guild.id] = GuildRaidState()
        return st[guild.id]


async def afk_check_reaction_handler(payload, user, guild):
    emoji_id = payload.emoji.id
    state = get_state(guild, core.states)
    if payload.message_id == state.msgid:
        # if emoji_id in main_run_emojis:
        #     # TODO: if user in vc move to vc 1 and add to verified logs
        if emoji_id in key_ids:
            if emoji_id == 682205784524062730:  # If emoji is vial
                if user.id not in state.vialreacts:
                    state.vialreacts.append(user.id)
                msg = await user.send("Do you have a vial and are willing to pop it? If so, react to the vial.")
                await msg.add_reaction('<:vial:682205784524062730>')
            else:
                if user.id not in state.keyreacts:
                    state.keyreacts.append(user.id)
                msg = await user.send("Do you have a key and are willing to pop it? If so, react to the key.")
                await msg.add_reaction(state.keyemoji)

        elif emoji_id == 682365548465487965:  # if react is nitro
            if payload.member.premium_since is not None or int(payload.member.id) == 196282885601361920:
                if state.location != "No location specified.":
                    await user.send(f"The location for this run is: `{state.location}`")
                else:
                    await user.send(
                        f"The location has not been set yet. Wait for the rl to set the location, then re-react.")
                if payload.member.nick not in state.nitroboosters:
                    state.nitroboosters.append(payload.member.nick)
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
        await user.send(f"The location for this run is: `{state.location}`")
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
