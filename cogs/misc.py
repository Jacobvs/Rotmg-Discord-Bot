import asyncio
import random
from os import listdir
from os.path import isfile, join
import discord
import psutil
import youtube_dl
from discord.ext import commands
from discord.utils import get

import embeds
from sql import get_num_verified
from checks import in_voice_channel, is_dj, is_rl_or_higher_check

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {'format': 'bestaudio/best', 'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s', 'restrictfilenames': True,
    'noplaylist': True, 'nocheckcertificate': True, 'ignoreerrors': False, 'logtostderr': False, 'quiet': True, 'no_warnings': True,
    'default_search': 'auto', 'source_address': '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
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


    @commands.command(aliases=["ahhaha"], usage="!laugh [1 or 2]")
    @commands.guild_only()
    @commands.check(is_dj)
    @commands.check(in_voice_channel)
    async def laugh(self, ctx, option=1):
        """Ah-Ha-hA"""
        voice = await connect_helper(self, ctx)
        if option != 1 and option != 2:
            option = 1
        option -= 1
        client = ctx.guild.voice_client
        if not client.source:
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(self.laughs[option], options=ffmpeg_options['options']),
                volume=0.75)
            ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else disconnect_helper(self, voice=voice))
            await ctx.send("Ah-Ha-hA")
        else:
            await ctx.send("Audio is already playing!")


    @commands.command(usage="!richard")
    @commands.guild_only()
    @commands.check(is_dj)
    @commands.check(in_voice_channel)
    async def richard(self, ctx):
        """"RICHARD!"""
        voice = await connect_helper(self, ctx)
        client = ctx.guild.voice_client
        if not client.source:
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio("files/richard.mp3", options=ffmpeg_options['options']),
                volume=0.5)
            ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else disconnect_helper(self, voice=voice))
            await ctx.send("What the fuck, Richard?")
        else:
            await ctx.send("Audio is already playing!")


    @commands.command(usage="!oogabooga")
    @commands.check(is_rl_or_higher_check)
    async def oogabooga(self, ctx):
        await ctx.message.delete()
        opts = ["BOOGA OOGA", "ooga boooga", "ooga chacka booga", "boogady oogady", "OOGA BOOGA", "boog.", "oog.", "booga", "ooga"]
        embed = discord.Embed(title=random.choice(opts), description="[Ooga-booga Translator](https://codepen.io/Darkm4tter/full/mNWpBZ)")
        embed.set_image(url="https://i.imgur.com/6z74JCz.png")
        await ctx.send(embed=embed)


    @commands.command(usage="!whatthefuck")
    @commands.check(is_rl_or_higher_check)
    async def whatthefuck(self, ctx):
        await ctx.message.delete()
        embed = discord.Embed(title="w h a t ᵗʰᵉᶠᵘᶜᵏ")
        embed.set_image(url="https://i.imgur.com/qMK83uT.jpg")
        await ctx.send(embed=embed)


    @commands.command(usage="!isitgone")
    @commands.check(is_rl_or_higher_check)
    async def isitgone(self, ctx):
        await ctx.message.delete()
        embed = discord.Embed(title="Is it gone?")
        embed.set_image(url="https://i.imgur.com/tYi5Xjg.jpg")
        await ctx.send(embed=embed)


    @commands.command(usage='!poll "[title]" [option 1] [option 2]...')
    @commands.guild_only()
    @commands.check(is_rl_or_higher_check)
    async def poll(self, ctx, title, *options):
        """Creates a poll with up to 2-10 options"""
        if len(options) < 2:
            await ctx.message.delete()
            await ctx.send("Please specify at least two options for the poll.", delete_after=4)
            return
        if len(options) > 10:
            await ctx.message.delete()
            await ctx.send("Please specify at most 10 options for the poll.", delete_after=4)
            return

        embed = embeds.poll(title, options)
        await ctx.message.delete()
        msg = await ctx.send(embed=embed)
        for i in range(len(options)):
            await msg.add_reaction(self.numbers[i])


    @commands.command(usage="!status")
    async def status(self, ctx):
        """Retrieve the bot's status"""
        embed = discord.Embed(title="Bot Status", color=discord.Color.dark_gold())
        nverified = await get_num_verified(self.client.pool)
        embed.add_field(name="Bot latency:", value=f"**`{round(self.client.latency*1000, 2)}`** Milliseconds.", inline=False)
        embed.add_field(name="Connected Servers:",
                        value=f"**`{len(self.client.guilds)}`** servers with **`{len(list(self.client.get_all_members()))}`** total members.",
                        inline=False)
        embed.add_field(name="Verified Raiders:", value=f"**`{nverified[0]}`** verified raiders.", inline=False)
        embed.add_field(name="Lines of Code:",
                        value=(f"**`{line_count('/home/jacobvs2/Rotmg-Bot/')+line_count('/home/jacobvs2/Rotmg-Bot/cogs')}"
                               "`** lines of code."), inline=False)
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
    file_list = [join(path, file_p) for file_p in listdir(path) if isfile(join(path, file_p))]

    total = 0
    for file_path in file_list:
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
