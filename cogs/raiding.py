from difflib import get_close_matches

import discord
from discord.ext import commands

import embeds
from checks import is_rl_or_higher_check, is_mm_or_higher_check
from cogs.Raiding.afk_check import AfkCheck
from cogs.Raiding.fametrain import FameTrain
from cogs.Raiding.realmclear import RealmClear
from sql import gld_cols, get_guild


class Raiding(commands.Cog):

    def __init__(self, client):
        self.client = client


    @commands.command(usage="!afk [type of run] [channel] <location>")
    @commands.guild_only()
    @commands.check(is_rl_or_higher_check)
    # TODO: add check that guild has no running afk up
    async def afk(self, ctx, *, location):
        """Starts an AFK check for the type of run specified. \nValid channel types are: ```1, 2, 3,
        vet/veteran```Valid run types are: ```realmclear, fametrain, void, fskipvoid, cult, nest``` """
        afk = AfkCheck(self.client, ctx, location)
        await afk.start()


    @commands.command(usage="!headcount [type of run] [hc_channel_num]", aliases=["hc"])
    @commands.guild_only()
    @commands.check(is_rl_or_higher_check)
    async def headcount(self, ctx, run_type, hc_channel_num='1'):
        """Starts a headcount for the type of run specified. Valid run types are: ```realmclear, fametrain, void, fskipvoid, cult, nest``` """

        guild_db = await get_guild(self.client.pool, ctx.guild.id)
        (hc_channel, vc, role, title) = await get_raid_info(self, ctx, hc_channel_num, guild_db, run_type)

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
        hc_channel, vc, role = await get_raid_info(self, ctx, vc_channel, guild_db)
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
        hc_channel, vc, role = await get_raid_info(self, ctx, vc_channel, guild_db)
        await vc.edit(name=vc.name + " <-- Join!")
        await vc.set_permissions(role, connect=True, view_channel=True, speak=False)
        await ctx.send(f"{vc.name} Has been unlocked!")

    @commands.command(usage="!fametrain <location>", aliases=['ft'])
    @commands.guild_only()
    @commands.check(is_rl_or_higher_check)
    async def fametrain(self, ctx, *, location):
        ft = FameTrain(self.client, ctx, location)
        await ft.start()

    @commands.command(usage="!realmclear [location]", aliases=["rc"])
    @commands.guild_only()
    @commands.check(is_rl_or_higher_check)
    async def realmclear(self, ctx, *, location):  #world_num, channel="1", *location):
        rc = RealmClear(self.client, ctx, location)
        await rc.start()

    @commands.command(usage="!markmap/mm [number(s)]", aliases=["mm"])
    # @commands.cooldown(1, 70, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(is_mm_or_higher_check)
    async def markmap(self, ctx, *numbers):
        await ctx.message.delete()
        if ctx.author.id in self.client.mapmarkers.keys():
            rc = self.client.mapmarkers[ctx.author.id]
            if rc:
                await rc.markmap(ctx, False, numbers)
            else:
                await ctx.send("This realm clearing has ended!")
        else:
            await ctx.send("You aren't marking for any realm clearing sessions!")


    @commands.command(usage="!unmarkmap/umm [number(s)]", aliases=["umm"])
    @commands.guild_only()
    @commands.check(is_mm_or_higher_check)
    async def unmarkmap(self, ctx, *numbers):
        await ctx.message.delete()
        if ctx.author.id in self.client.mapmarkers.keys():
            rc = self.client.mapmarkers[ctx.author.id]
            if rc:
                await rc.markmap(ctx, True, numbers)
            else:
                await ctx.send("This realm clearing has ended!")
        else:
            await ctx.send("You aren't marking for any realm clearing sessions!")


    @commands.command(usage="!eventspawn [event]", aliases=['es'])
    @commands.guild_only()
    @commands.check(is_mm_or_higher_check)
    async def eventspawn(self, ctx, event):
        await ctx.message.delete()
        if ctx.author.id in self.client.mapmarkers.keys():
            rc = self.client.mapmarkers[ctx.author.id]
            if rc:
                await rc.eventspawn(ctx, False, event)
            else:
                await ctx.send("This realm clearing has ended!")
        else:
            await ctx.send("You aren't marking for any realm clearing sessions!")


    @commands.command(usage="!uneventspawn [event]", aliases=['ues'])
    @commands.guild_only()
    @commands.check(is_mm_or_higher_check)
    async def uneventspawn(self, ctx, event):
        await ctx.message.delete()
        if ctx.author.id in self.client.mapmarkers.keys():
            rc = self.client.mapmarkers[ctx.author.id]
            if rc:
                await rc.eventspawn(ctx, True, event)
            else:
                await ctx.send("This realm clearing has ended!")
        else:
            await ctx.send("You aren't marking for any realm clearing sessions!")


def setup(client):
    client.add_cog(Raiding(client))


async def get_raid_info(self, ctx, channel, guild_db, run_type=None):
    if channel == "vet" or channel == "veteran":
        if ctx.author.top_role >= self.client.guild_db.get(ctx.guild.id)[gld_cols.vetrlroleid]:
            hc_channel = ctx.guild.get_channel(guild_db[gld_cols.vethc1])
            vc = ctx.guild.get_channel(guild_db[gld_cols.vetvc1])
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
    if run_type:
        title = run_title(run_type)
        if title is None:
            return await ctx.send("The specified run type is not an option.")
        if title[1] is True:
            await ctx.send(f"A correction was made, `{type}` was changed to `{title[2]}`")
        return hc_channel, vc, role, title
    return hc_channel, vc, role


def run_title(run_type):
    run_types = {'realmclear': "Realm Clearing", 'fametrain': "Fame Train", 'void': "Void", 'fskipvoid': "Full-Skip Void", 'cult': "Cult",
                 'eventdungeon': "Event Dungeon", "nest": "The Nest"}
    result = run_types.get(run_type, None)
    if result is None:
        matches = get_close_matches(run_type, run_types.keys(), n=1, cutoff=0.8)
        if len(matches) == 0:
            return None
        return run_types.get(matches[0]), True, matches[0]
    return result, False


default_emojis = ["<:defaultdungeon:682212333182910503>", "<:eventkey:682212349641621506>", "<:warrior:682204616997208084>",
                  "<:knight:682205672116584459>", "<:paladin:682205688033968141>", "<:priest:682206578908069905>"]


def run_emojis(run_type):
    return {'Realm Clearing': ["<:defaultdungeon:682212333182910503>", "<:trickster:682214467483861023>", "<:Warrior_1:585616162407186433>",
                               "<:ninja_3:585616162151202817>"],
            'Fame Train': ["<:fame:682209281722024044>", "<:sorcerer:682214487490560010>", "<:necromancer:682214503106215966>",
                           "<:sseal:683815374403141651>", "<:paladin:682205688033968141>"],
            'Void': ["<:void:682205817424183346>", "<:lhkey:682205801728835656>", "<:vial:682205784524062730>", default_emojis[2],
                     default_emojis[3], default_emojis[4], "<:mseal:682205755754938409>", "<:puri:682205769973760001>",
                     "<:planewalker:682212363889279091>"],
            'Full-Skip Void': ["<:fskipvoid:682206558075224145>", "<:lhkey:682205801728835656>", "<:vial:682205784524062730>",
                               default_emojis[2], default_emojis[3], default_emojis[4], "<:mseal:682205755754938409>",
                               "<:puri:682205769973760001>", "<:brainofthegolem:682205737492938762>", "<:mystic:682205700918607969>"],
            'Cult': ["<:cult:682205832879800388>", "<:lhkey:682205801728835656>", default_emojis[2], default_emojis[3], default_emojis[4],
                     "<:puri:682205769973760001>", "<:planewalker:682212363889279091>"],
            'The Nest': ["<:Nest:585617025909653524>", "<:NestKey:585617056192266240>", "<:QuiverofThunder:585616162176630784>",
                        default_emojis[2], default_emojis[3], default_emojis[4], "<:mystic:682205700918607969>",
                         "<:puri:682205769973760001>", "<:slow_icon:678792068965072906>"],
            'Event Dungeon': default_emojis}.get(run_type, default_emojis)


main_run_emojis = ["<:whitebag:682208350481547267>", "<:fame:682209281722024044>", "<:void:682205817424183346>",
                   "<:fskipvoid:682206558075224145>", "<:cult:682205832879800388>"]
key_emojis = ["<:lhkey:682205801728835656>", "<:vial:682205784524062730>", "<:eventkey:682212349641621506>", "<:NestKey:585617056192266240>"]
key_ids = [682205801728835656, 682205784524062730, 682212349641621506, 585617056192266240]