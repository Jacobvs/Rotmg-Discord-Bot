import asyncio
import youtube_dl
import discord
from discord.ext import commands
from discord.utils import get

import embeds
from checks import in_voice_channel, is_dj

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

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

    @commands.command(aliases=["ahhaha"], usage="!laugh")
    @commands.guild_only()
    @commands.check(is_dj)
    @commands.check(in_voice_channel)
    async def laugh(self, ctx):
        """Ah-Ha-hA"""
        voice = await connect_helper(self, ctx)

        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio("ahhaha.mp3", options=ffmpeg_options['options']))
        ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else disconnect_helper(self,
                                                                                                                voice=voice))

        await ctx.send("Ah-Ha-hA")

    @commands.command(usage="!purge [num]")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def purge(self, ctx, num=5):
        """Removes [num] messages from the channel"""
        num += 1
        if not isinstance(num, int):
            await ctx.send("Please pass in a number of messages to delete.")
            return
        await ctx.channel.purge(limit=num)
        await ctx.send(f"Deleted {num-1} messages.", delete_after=5)

    @commands.command(usage='!poll "[title]" [option 1] [option 2]...')
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
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
        numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
        embed=embeds.poll(title, options)
        await ctx.message.delete()
        msg = await ctx.send(embed=embed)
        for i in range(len(options)):
            await msg.add_reaction(numbers[i])


def setup(client):
    client.add_cog(Misc(client))

