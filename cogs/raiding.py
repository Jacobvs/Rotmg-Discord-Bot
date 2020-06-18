import functools
import io
import re
from difflib import get_close_matches

import cv2
import discord
import numpy as np
from discord.ext import commands
from pytesseract import pytesseract

import checks
from cogs.Raiding.afk_check import AfkCheck
from cogs.Raiding.fametrain import FameTrain
from cogs.Raiding.headcount import Headcount
from cogs.Raiding.realmclear import RealmClear
from cogs.Raiding.vc_select import VCSelect


class Raiding(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command(usage="!afk <location>")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    # TODO: add check that guild has no running afk up
    async def afk(self, ctx, *, location):
        """Starts an AFK check for the location specified."""
        if ctx.author.id in self.client.raid_db[ctx.guild.id]['leaders']:
            return await ctx.send("You cannot start another AFK while an AFK check is still up or a run log has not been completed.")
        self.client.raid_db[ctx.guild.id]['leaders'].append(ctx.author.id)
        setup = VCSelect(self.client, ctx)
        data = await setup.start()
        if isinstance(data, tuple):
            (raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg) = data
        else:
            self.client.raid_db[ctx.guild.id]['leaders'].remove(ctx.author.id)
            return
        afk = AfkCheck(self.client, ctx, location, raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg)
        await afk.start()
        self.client.raid_db[ctx.guild.id]['leaders'].remove(ctx.author.id)


    @commands.command(usage="!headcount", aliases=["hc"])
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def headcount(self, ctx):
        """Starts a headcount for the type of run specified."""
        setup = VCSelect(self.client, ctx, headcount=True)
        data = await setup.start()
        if isinstance(data, tuple):
            (raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg) = data
        else:
            return
        hc = Headcount(self.client, ctx, hcchannel, vcchannel, setup_msg, raidnum, inraiding, invet, inevents, raiderrole, rlrole)
        await hc.start()

    @commands.command(usage="!parse (Attach an image of /who list with this command)")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def parse(self, ctx):
        """Parse through members in the run"""
        if not ctx.message.attachments:
            return await ctx.send("Please attach an image containing only the result of the /who command!", delete_after=10)
        if len(ctx.message.attachments) > 1:
            return await ctx.send("Please only attach 1 image.", delete_after=10)
        attachment = ctx.message.attachments[0]
        if not ".jpg" in attachment.filename and not ".png" in attachment.filename:
            return await ctx.send("Please only attach an image of type 'png' or 'jpg'.", delete_after=10)
        image = io.BytesIO()
        await attachment.save(image, seek_begin=True)
        setup = VCSelect(self.client, ctx, parse=True)
        data = await setup.start()
        if isinstance(data, tuple):
            (raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg) = data
        else:
            return
        await setup_msg.delete()
        msg = await ctx.send("Parsing image. This may take a minute...")
        embed = await self.client.loop.run_in_executor(None, functools.partial(parse_image, ctx.author, image, vcchannel))
        await msg.delete()
        await ctx.send(embed=embed)

    @commands.command(usage="!lock")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def lock(self, ctx):
        """Locks the raiding voice channel"""
        setup = VCSelect(self.client, ctx, lock=True)
        data = await setup.start()
        if isinstance(data, tuple):
            (raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg) = data
        else:
            return
        await setup_msg.delete()
        vc_name = vcchannel.name
        # if " <-- Join!" in vc_name:
        #     vc_name = vc_name.split(" <")[0]
        #     await vcchannel.edit(name=vc_name)
        await vcchannel.set_permissions(raiderrole, connect=False, view_channel=True, speak=False)
        embed = discord.Embed(description=f"{vcchannel.name} Has been Locked!", color=discord.Color.red())
        await ctx.send(embed=embed)


    @commands.command(usage="!unlock")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def unlock(self, ctx):
        """Unlocks the raiding voice channel"""
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

    @commands.command(usage="!clean")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def clean(self, ctx):
        """Clean out & lock a voice channel"""
        setup = VCSelect(self.client, ctx, clean=True)
        data = await setup.start()
        if isinstance(data, tuple):
            (raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg) = data
        else:
            return
        await setup_msg.delete()
        for member in vcchannel.members:
            if member.top_role < rlrole:
                if member.voice:
                    await member.move_to(channel=None)
        vc_name = vcchannel.name
        if " <-- Join!" in vc_name:
            vc_name = vc_name.split(" <")[0]
            await vcchannel.edit(name=vc_name)
        await vcchannel.set_permissions(raiderrole, connect=False, view_channel=True, speak=False)
        embed = discord.Embed(title="Done Cleaning!", description=f"{vcchannel.name} has been cleaned and locked.",
                              color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.command(usage="!fametrain <location>", aliases=['ft'])
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def fametrain(self, ctx, *, location):
        """Start an AFK check for a fametrain"""
        if ctx.author.id in self.client.raid_db[ctx.guild.id]['leaders']:
            return await ctx.send("You cannot start another AFK while an AFK check is still up.")
        self.client.raid_db[ctx.guild.id]['leaders'].append(ctx.author.id)
        setup = VCSelect(self.client, ctx)
        data = await setup.start()
        if isinstance(data, tuple):
            (raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg) = data
        else:
            return
        ft = FameTrain(self.client, ctx, location, raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg)
        await ft.start()
        self.client.raid_db[ctx.guild.id]['leaders'].remove(ctx.author.id)

    @commands.command(usage="!realmclear <location>", aliases=["rc"])
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def realmclear(self, ctx, *, location):
        """Start an AFK Check for Realm Clearing"""
        if ctx.author.id in self.client.raid_db[ctx.guild.id]['leaders']:
            return await ctx.send("You cannot start another AFK while an AFK check is still up.")
        self.client.raid_db[ctx.guild.id]['leaders'].append(ctx.author.id)
        setup = VCSelect(self.client, ctx)
        data = await setup.start()
        if isinstance(data, tuple):
            (raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg) = data
        else:
            return
        rc = RealmClear(self.client, ctx, location, raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel,setup_msg)
        await rc.start()
        self.client.raid_db[ctx.guild.id]['leaders'].remove(ctx.author.id)

    @commands.command(usage="!markmap/mm [number(s)]", aliases=["mm"])
    # @commands.cooldown(1, 70, commands.BucketType.guild)
    @commands.guild_only()
    @checks.is_mm_or_higher_check()
    async def markmap(self, ctx, *numbers):
        """Mark the current map with specified numbers"""
        await ctx.message.delete()
        if ctx.author.id in self.client.mapmarkers:
            rc = self.client.mapmarkers[ctx.author.id]
            if rc:
                await rc.markmap(ctx, False, numbers)
            else:
                await ctx.send("This realm clearing has ended!")
        else:
            await ctx.send("You aren't marking for any realm clearing sessions!")


    @commands.command(usage="!unmarkmap/umm [number(s)]", aliases=["umm"])
    @commands.guild_only()
    @checks.is_mm_or_higher_check()
    async def unmarkmap(self, ctx, *numbers):
        """Unmark the map with specified numbers"""
        await ctx.message.delete()
        if ctx.author.id in self.client.mapmarkers:
            rc = self.client.mapmarkers[ctx.author.id]
            if rc:
                await rc.markmap(ctx, True, numbers)
            else:
                await ctx.send("This realm clearing has ended!")
        else:
            await ctx.send("You aren't marking for any realm clearing sessions!")


    @commands.command(usage="!eventspawn [event]", aliases=['es'])
    @commands.guild_only()
    @checks.is_mm_or_higher_check()
    async def eventspawn(self, ctx, event):
        """Mark when an event spawns"""
        await ctx.message.delete()
        if ctx.author.id in self.client.mapmarkers:
            rc = self.client.mapmarkers[ctx.author.id]
            if rc:
                await rc.eventspawn(ctx, False, event)
            else:
                await ctx.send("This realm clearing has ended!")
        else:
            await ctx.send("You aren't marking for any realm clearing sessions!")


    @commands.command(usage="!uneventspawn [event]", aliases=['ues'])
    @commands.guild_only()
    @checks.is_mm_or_higher_check()
    async def uneventspawn(self, ctx, event):
        """Unmark an event spawn"""
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

def parse_image(author, image, vc):
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
    split_str = re.split(r'(.*)(Players online \([0-9]+\): )', str)
    if len(split_str) < 4:
        print("ERROR - Parsed String: " + str)
        print("INFO - Split String: ")
        print(split_str)
        embed = discord.Embed(title="Error!", description="Could not find the who command in the image you provided.\nPlease re-run the "
                            "command with an image that shows the results of `/who`.", color=discord.Color.red())
        return embed
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
        return "".join(c for c in n if c.isalpha())

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
        if name.strip() not in cleaned_members:
            matches = get_close_matches(name.strip(), cleaned_members, n=1, cutoff=0.6)
            if len(matches) == 0:
                if name.strip() not in alts:
                    crashing.append(name.strip())
            else:
                if matches[0] not in cleaned_members:
                    fixed_names.append((name.strip(), matches[0]))
                else:
                    cleaned_members.remove(matches[0])
        else:
            cleaned_members.remove(name.strip())

    for m in cleaned_members:
        if m != author:
            possible_alts.append(m)

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


