import asyncio

import discord
from discord import Member
from discord.ext import commands
from discord.utils import get


class Misc(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.command(pass_context=True)
    async def ahhaha(self, ctx):
        global voice
        if ctx.message.author.voice is None:
            await ctx.send("Connect to a voice channel to use this command.")
            return
        if ctx.message.guild is None:
            print("ree")
            await ctx.message.author.send("This command can only be used in a server when connected to a VC.")
            return

        channel = ctx.message.author.voice.channel
        voice = get(self.client.voice_clients, guild=ctx.guild)

        if voice and voice.is_connected():
            await voice.move_to(channel)
        else:
            voice = await channel.connect()

        def disconnect_helper():
            coro = voice.disconnect()
            fut = asyncio.run_coroutine_threadsafe(coro, self.client.loop)
            try:
                fut.result()
            except:
                pass

        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio("ahhaha.mp3"))
        ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else disconnect_helper())

        await ctx.send("Ah-Ha-hA")


def setup(client):
    client.add_cog(Misc(client))