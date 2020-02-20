import asyncio
from threading import Timer

import youtube_dl
import discord
from discord.ext import commands
from discord.utils import get

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
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


async def connect_helper(self, ctx):
    if ctx.message.author.voice is None:
        await ctx.send("Connect to a voice channel to use this command.")
        return None
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

    def __init__(self, client):
        self.client = client

    @commands.command(pass_context=True)
    async def laugh(self, ctx):
        """Ah-Ha-hA"""
        voice = await connect_helper(self, ctx)

        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio("ahhaha.mp3"))
        ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else disconnect_helper(self,
                                                                                                                voice=voice))

        await ctx.send("Ah-Ha-hA")

    # # TODO: ADD queue of songs & youtube playlist fuctionality
    # @commands.command()
    # async def play(self, ctx, url):
    #     """Joins vc and plays audio from youtube link provided"""
    #     async with ctx.typing():
    #         voice = await connect_helper(self, ctx)
    #         player = await YTDLSource.from_url(url, loop=self.client.loop, stream=True)
    #         ctx.voice_client.play(player,
    #                               after=lambda e: print('Player error: %s' % e) if e else disconnect_helper(self,
    #                                                                                                         voice=voice))
    #
    #     await ctx.send('Now playing: {}'.format(player.title))
    #
    # @commands.command()
    # async def stop(self, ctx):
    #     """Stops and disconnects the bot from voice"""
    #
    #     await ctx.voice_client.disconnect()
    #     await ctx.send("Player has been stopped.")
    #
    # # TODO: find command


def setup(client):
    client.add_cog(Misc(client))

