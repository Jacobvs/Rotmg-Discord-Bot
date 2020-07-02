import asyncio
import random
from datetime import datetime
from os import listdir
from os.path import isfile, join

import aiohttp
import discord
import psutil
import youtube_dl
from discord.ext import commands
from discord.utils import get

import checks
import embeds
import sql
import utils
from checks import is_dj, is_rl_or_higher_check, is_bot_owner
from sql import get_num_verified

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {'format': 'bestaudio/best', 'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s', 'restrictfilenames': True,
                       'noplaylist': True, 'nocheckcertificate': True, 'ignoreerrors': False, 'logtostderr': False, 'quiet': True,
                       'no_warnings': True, 'default_search': 'auto', 'source_address': '0.0.0.0'
                       # bind to ipv4 since ipv6 addresses cause issues sometimes
                       }

ffmpeg_options = {'options': '-vn', 'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


async def connect_helper(self, ctx):
    if ctx.message.guild is None:
        await ctx.message.author.send("This command can only be used in a server when connected to a VC.")
        return None

    channel = ctx.message.author.voice.channel
    voice = get(self.client.voice_clients, guild=ctx.guild)

    if voice and voice.is_connected():
        await voice.move_to(channel)
    else:
        voice = await channel.connect()

    return voice


def disconnect_helper(self, voice):
    coroutine = voice.disconnect()
    task = asyncio.run_coroutine_threadsafe(coroutine, self.client.loop)
    try:
        task.result()
    except:
        pass


class Misc(commands.Cog):
    """Miscellaneous Commands"""


    def __init__(self, client):
        self.client = client
        self.laughs = ["files/ahhaha.mp3", "files/jokerlaugh.mp3"]
        self.numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']


    @commands.command(usage="stats [member]", description="Check your or someone else's run stats.")
    async def stats(self, ctx, member: utils.MemberLookupConverter=None):
        author = member if member else ctx.author
        if not ctx.guild:
            servers = []
            for g in self.client.guilds:
                if g.get_member(author.id):
                    servers.append(g)
            serverstr = ""
            for i, s in enumerate(servers[:10]):
                serverstr += self.numbers[i] + " - " + s.name + "\n"
            embed = discord.Embed(description="What server would you like to check stats for?\n"+serverstr, color=discord.Color.gold())
            msg = await author.send(embed=embed)
            for e in self.numbers[:len(servers)]:
                await msg.add_reaction(e)

            def check(react, usr):
                return usr == ctx.author and react.message.id == msg.id and str(react.emoji) in self.numbers[:len(servers)]
            try:
                reaction, user = await self.client.wait_for('reaction_add', timeout=1800, check=check)  # Wait 1/2 hr max
            except asyncio.TimeoutError:
                embed = discord.Embed(title="Timed out!", description="You didn't choose a server in time!", color=discord.Color.red())
                await msg.clear_reactions()
                return await msg.edit(embed=embed)

            serverid = servers[self.numbers.index(str(reaction.emoji))].id
            author = servers[self.numbers.index(str(reaction.emoji))].get_member(author.id)
            await msg.delete()
        else:
            await ctx.message.delete()
            if member:
                converter = discord.ext.commands.MemberConverter()
                try:
                    author = await converter.convert(ctx, str(member.id))
                except discord.ext.commands.BadArgument:
                    pass
            serverid = ctx.guild.id

        data = await sql.get_log(self.client.pool, serverid, author.id)
        embed = discord.Embed(title=f"Stats for {author.display_name}", color=discord.Color.green())
        embed.set_thumbnail(url=author.avatar_url)
        embed.add_field(name="__**Key Stats**__", value="Popped: "
                        f"**{data[sql.log_cols.pkey]}**\nEvent Keys: **{data[sql.log_cols.eventkeys]}**\nVials: "
                        f"**{data[sql.log_cols.vials]}**\nSword Runes: **{data[sql.log_cols.swordrunes]}**\nShield Runes: "
                        f"**{data[sql.log_cols.shieldrunes]}**\nHelm Runes: **{data[sql.log_cols.helmrunes]}**", inline=False)\
                        .add_field(name="__**Run Stats**__", value=f"Completed: **{data[sql.log_cols.runsdone]}**\nEvents Completed: "
                        f"**{data[sql.log_cols.eventsdone]}**", inline=False)
        erl = self.client.guild_db.get(serverid)[sql.gld_cols.eventrlid]
        role = erl if erl else self.client.guild_db.get(serverid)[sql.gld_cols.rlroleid]
        if author.top_role >= role:
            embed.add_field(name="__**Leading Stats**__", value="Successful Runs: "
                        f"**{data[sql.log_cols.srunled]}**\nFailed Runs: **{data[sql.log_cols.frunled]}**\nAssisted: "
                        f"**{data[sql.log_cols.runsassisted]}**\nEvents: **{data[sql.log_cols.eventled]}**\nEvents Assisted: "
                        f"**{data[sql.log_cols.eventsassisted]}**\nWeekly Runs Led: **{data[sql.log_cols.weeklyruns]}**\n"
                        f"Weekly Runs Assisted: **{data[sql.log_cols.weeklyassists]}**", inline=False)
        embed.timestamp = datetime.utcnow()
        if ctx.guild:
            return await ctx.send(embed=embed)
        await author.send(embed=embed)


    @commands.command(aliases=["ahhaha"], usage="laugh", description="Ah-Ha-hA")
    @commands.guild_only()
    @commands.check_any(is_dj(), is_bot_owner())
    @checks.in_voice_channel()
    async def laugh(self, ctx):
        voice = await connect_helper(self, ctx)
        client = ctx.guild.voice_client
        if not client.source:
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio("files/ahhaha.mp3", options=ffmpeg_options['options']),
                                                  volume=1)
            ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else disconnect_helper(self, voice=voice))
            await ctx.send("Ah-Ha-hA")
        else:
            await ctx.send("Audio is already playing!")


    @commands.command(usage="bully", description="Why you bully me?")
    @commands.guild_only()
    @commands.check_any(is_dj(), is_bot_owner())
    @checks.in_voice_channel()
    async def bully(self, ctx):
        voice = await connect_helper(self, ctx)
        client = ctx.guild.voice_client
        if not client.source:
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio("files/bully-me.mp3", options=ffmpeg_options['options']),
                                                  volume=1)
            ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else disconnect_helper(self, voice=voice))
            await ctx.send("Why you bully me?")
        else:
            await ctx.send("Audio is already playing!")


    @commands.command(usage="roll", description="Not quite sure what this is.")
    @commands.guild_only()
    @commands.check_any(is_dj(), is_bot_owner())
    @checks.in_voice_channel()
    async def roll(self, ctx):
        voice = await connect_helper(self, ctx)
        client = ctx.guild.voice_client
        if not client.source:
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio("files/roll.mp3", options=ffmpeg_options['options']), volume=1)
            ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else disconnect_helper(self, voice=voice))
            await ctx.send("youtube.com/watch?v=dQw4w9WgXcQ")
        else:
            await ctx.send("Audio is already playing!")


    @commands.command(usage="fbi", description="FBI, OPEN UP.")
    @commands.guild_only()
    @commands.check_any(is_dj(), is_bot_owner())
    @checks.in_voice_channel()
    async def fbi(self, ctx):
        voice = await connect_helper(self, ctx)
        client = ctx.guild.voice_client
        if not client.source:
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio("files/fbi.mp3", options=ffmpeg_options['options']), volume=1)
            ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else disconnect_helper(self, voice=voice))
            await ctx.send("FBI, OPEN UP")
        else:
            await ctx.send("Audio is already playing!")


    @commands.command(usage="richard", description="RICHARD!")
    @commands.guild_only()
    @commands.check_any(is_dj(), is_bot_owner())
    @checks.in_voice_channel()
    async def richard(self, ctx):
        voice = await connect_helper(self, ctx)
        client = ctx.guild.voice_client
        if not client.source:
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio("files/richard.mp3", options=ffmpeg_options['options']),
                                                  volume=1)
            ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else disconnect_helper(self, voice=voice))
            await ctx.send("What the fuck, Richard?")
        else:
            await ctx.send("Audio is already playing!")


    @commands.command(usage="oogabooga", description="The only command you ever need.")
    @commands.check_any(is_rl_or_higher_check(), is_bot_owner())
    async def oogabooga(self, ctx):
        await ctx.message.delete()
        opts = ["BOOGA OOGA", "ooga boooga", "ooga chacka booga", "boogady oogady", "OOGA BOOGA", "boog.", "oog.", "booga", "ooga"]
        embed = discord.Embed(title=random.choice(opts), description="[Ooga-booga Translator](https://codepen.io/Darkm4tter/full/mNWpBZ)")
        embed.set_image(url="https://i.imgur.com/6z74JCz.png")
        await ctx.send(embed=embed)


    @commands.command(usage="whatthefuck", description="????")
    @commands.check_any(is_rl_or_higher_check(), is_bot_owner())
    async def whatthefuck(self, ctx):
        await ctx.message.delete()
        embed = discord.Embed(title="w h a t ᵗʰᵉᶠᵘᶜᵏ")
        embed.set_image(url="https://i.imgur.com/qMK83uT.jpg")
        await ctx.send(embed=embed)


    @commands.command(usage="isitgone", description="Spooky...")
    @commands.check_any(is_rl_or_higher_check(), is_bot_owner())
    async def isitgone(self, ctx):
        await ctx.message.delete()
        embed = discord.Embed(title="Is it gone?")
        embed.set_image(url="https://i.imgur.com/tYi5Xjg.jpg")
        await ctx.send(embed=embed)

    @commands.command(usage="comic", description="Get random XKCD Comic.")
    async def comic(self, ctx):
        num = random.randint(0, 2326)
        async with aiohttp.ClientSession() as cs:
            async with cs.get(f'https://xkcd.com/{num}/info.0.json', ssl=False) as r:
                data = await r.json()

        if data:
            embed = discord.Embed(title=data['title'])
            embed.set_image(url=data['img'])
            await ctx.send(embed=embed)
        else:
            await ctx.send("XKCD's servers couldn't be reached. Try again later.")


    @commands.command(usage='poll <title> <option 1> <option 2> [option 3]...',
                      description="Creates a poll with up to 2-10 options\n"
                                  "For options/titles with more than one word, surround the text with quotes.")
    @commands.guild_only()
    @commands.check_any(is_rl_or_higher_check(), is_bot_owner())
    async def poll(self, ctx, title, *options):
        if len(options) < 2:
            await ctx.message.delete()
            await ctx.send("Please specify at least two options for the poll.", delete_after=4)
            return
        if len(options) > 10:
            await ctx.message.delete()
            await ctx.send("Please specify at most 10 options for the poll.", delete_after=4)
            return

        embed = embeds.poll(title, options)  # Get poll embed
        await ctx.message.delete()  # delete command message
        msg = await ctx.send(embed=embed)
        for i in range(len(options)):  # add reactions to poll
            await msg.add_reaction(self.numbers[i])
        # TODO: Implement counter, add check to only allow reactions to 1 option (remove all but last react from each person)
        # TODO: add option to ping @here or @everyone


    @commands.command(usage="status", description="Retrieve the bot's status.")
    async def status(self, ctx):
        embed = discord.Embed(title="Bot Status", color=discord.Color.dark_gold())
        nverified = await get_num_verified(self.client.pool)
        embed.add_field(name="Bot latency:", value=f"**`{round(self.client.latency*1000, 2)}`** Milliseconds.", inline=False)
        embed.add_field(name="Connected Servers:",
                        value=f"**`{len(self.client.guilds)}`** servers with **`{len(list(self.client.get_all_members()))}`** total members.",
                        inline=False)
        embed.add_field(name="Verified Raiders:", value=f"**`{nverified[0]}`** verified raiders.", inline=False)
        lines = line_count('/home/pi/Rotmg-Bot/')+line_count('/home/pi/Rotmg-Bot/cogs')+line_count('/home/pi/Rotmg-Bot/cogs/Raiding')+\
                line_count('/home/pi/Rotmg-Bot/cogs/Minigames')
        embed.add_field(name="Lines of Code:",
                        value=(f"**`{lines}`** lines of code."), inline=False)
        embed.add_field(name="Server Status:",
                        value=(f"```yaml\nServer: Google Cloud Compute (US East)\nCPU: {psutil.cpu_percent()}% utilization."
                               f"\nMemory: {psutil.virtual_memory().percent}% utilization."
                               f"\nDisk: {psutil.disk_usage('/').percent}% utilization."
                               f"\nNetwork: {round(psutil.net_io_counters().bytes_recv*0.000001)} MB in "
                               f"/ {round(psutil.net_io_counters().bytes_sent*0.000001)} MB out.```"))
        if ctx.guild:
            appinfo = await self.client.application_info()
            embed.add_field(name=f"Bot author:", value=f"{appinfo.owner.mention} - DM me if something's broken or to request a feature!",
                            inline=False)
        else:
            embed.add_field(name=f"Bot author:", value="__Darkmatter#7321__ - DM me if something's broken or to request a feature!",
                            inline=False)
        await ctx.send(embed=embed)


def setup(client):
    client.add_cog(Misc(client))


def line_count(path):
    """Count total lines of code in specified path"""
    file_list = [join(path, file_p) for file_p in listdir(path) if isfile(join(path, file_p))]
    total = 0
    for file_path in file_list:
        if file_path[-3:] == ".py":  # Ensure only python files are counted
            try:
                count = 0
                with open(file_path, encoding="ascii", errors="surrogateescape") as current_file:
                    for line in current_file:
                        count += 1
            except IOError:
                return -1
            if count >= 0:
                total += count
    return total
