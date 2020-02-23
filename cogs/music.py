import requests
from bs4 import BeautifulSoup as bs
from discord.ext import commands
import discord
import asyncio
import youtube_dl as ytdl
import logging
import math
from checks import audio_playing, in_same_voice_channel, is_audio_requester

YTDL_OPTS = {
    "default_search": "ytsearch",
    "format": "bestaudio/best",
    "quiet": True,
    "extract_flat": "in_playlist"
}

ffmpeg_options = {
    'options': '-vn',
    'before_options': ' -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}


class Video:
    """Class containing information about a particular video."""

    def __init__(self, url_or_search, requested_by):
        """Plays audio from (or searches for) a URL."""
        with ytdl.YoutubeDL(YTDL_OPTS) as ydl:
            video = self._get_info(url_or_search)
            video_format = video["formats"][0]
            self.stream_url = video_format["url"]
            self.video_url = video["webpage_url"]
            self.title = video["title"]
            self.uploader = video["uploader"] if "uploader" in video else ""
            self.thumbnail = video[
                "thumbnail"] if "thumbnail" in video else None
            self.requested_by = requested_by

    def _get_info(self, video_url):
        with ytdl.YoutubeDL(YTDL_OPTS) as ydl:
            info = ydl.extract_info(video_url, download=False)
            video = None
            if "_type" in info and info["_type"] == "playlist":
                return self._get_info(
                    info["entries"][0]["url"])  # get info for first video
            else:
                video = info
            return video

    def get_embed(self):
        """Makes an embed out of this Video's information."""
        embed = discord.Embed(
            title=self.title, description=self.uploader, url=self.video_url)
        embed.set_footer(
            text=f"Requested by {self.requested_by.name}",
            icon_url=self.requested_by.avatar_url)
        if self.thumbnail:
            embed.set_thumbnail(url=self.thumbnail)
        return embed


class Music(commands.Cog):
    """Music Commands"""

    def __init__(self, bot):
        self.bot = bot
        self.states = {}

    def get_state(self, guild):
        """Gets the state for `guild`, creating it if it does not exist."""
        if guild.id in self.states:
            return self.states[guild.id]
        else:
            self.states[guild.id] = GuildState()
            return self.states[guild.id]

    @commands.command(aliases=["stop"], usage="!leave")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def leave(self, ctx):
        """Leaves the voice channel, if currently in one."""
        client = ctx.guild.voice_client
        state = self.get_state(ctx.guild)
        if client and client.channel:
            await client.disconnect()
            state.playlist = []
            state.now_playing = None
        else:
            raise commands.CommandError("Not in a voice channel.")

    @commands.command(aliases=["resume"], usage="!pause")
    @commands.guild_only()
    @commands.check(audio_playing)
    @commands.check(in_same_voice_channel)
    @commands.check(is_audio_requester)
    async def pause(self, ctx):
        """Pauses any currently playing audio."""
        client = ctx.guild.voice_client
        self._pause_audio(client)

    def _pause_audio(self, client):
        if client.is_paused():
            client.resume()
        else:
            client.pause()

    @commands.command(aliases=["vol", "v"], usage="!volume [0-250]")
    @commands.guild_only()
    async def volume(self, ctx, volume: int):
        """Change the volume of currently playing audio."""
        state = self.get_state(ctx.guild)

        # make sure volume is nonnegative
        if volume < 0:
            volume = 0

        max_vol = 250
        if max_vol > -1:  # check if max volume is set
            # clamp volume to [0, max_vol]
            if volume > max_vol:
                volume = max_vol

        client = ctx.guild.voice_client

        state.volume = float(volume) / 100.0
        client.source.volume = state.volume  # update the AudioSource's volume to match
        await ctx.send(f"The volume has been set to: `{volume}`.")

    @commands.command(aliases=["s"], usage="!skip")
    @commands.guild_only()
    @commands.check(audio_playing)
    @commands.check(in_same_voice_channel)
    async def skip(self, ctx):
        """Skips the currently playing song, or votes to skip it."""
        state = self.get_state(ctx.guild)
        client = ctx.guild.voice_client
        if ctx.channel.permissions_for(
                ctx.author).administrator or state.is_requester(ctx.author):
            # immediately skip if requester or admin
            # await state.message.edit(embed=state.playlist[0].get_embed())
            client.stop()
        else:
            # vote to skip song
            channel = client.channel
            await self._vote_skip(channel, ctx.author)
            # announce vote
            users_in_channel = len([
                member for member in channel.members if not member.bot
            ])  # don't count bots
            required_votes = math.ceil(
                0.5 * users_in_channel)
            await ctx.send(
                f"{ctx.author.mention} voted to skip ({len(state.skip_votes)}/{required_votes} votes)"
            )

    async def _vote_skip(self, channel, member):
        """Register a vote for `member` to skip the song playing."""
        logging.info(f"{member.name} votes to skip")
        state = self.get_state(channel.guild)
        state.skip_votes.add(member)
        users_in_channel = len([
            member for member in channel.members if not member.bot
        ])  # don't count bots
        if (float(len(state.skip_votes)) /
            users_in_channel) >= 0.5:
            # enough members have voted to skip, so skip the song
            logging.info(f"Enough votes, skipping...")
            # await state.message.edit(embed=state.playlist[0].get_embed())
            channel.guild.voice_client.stop()

    def _play_song(self, client, state, song):
        state.now_playing = song
        state.skip_votes = set()  # clear skip votes
        asyncio.run_coroutine_threadsafe(state.message.edit(embed=song.get_embed()), self.bot.loop)
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(song.stream_url, options=ffmpeg_options['options'], before_options=ffmpeg_options['before_options']), volume=state.volume)

        def after_playing(err):
            if len(state.playlist) > 0:
                next_song = state.playlist.pop(0)
                self._play_song(client, state, next_song)
            else:
                asyncio.run_coroutine_threadsafe(client.disconnect(),
                                                 self.bot.loop)

        client.play(source, after=after_playing)

    @commands.command(aliases=["np", "playing"], usage="!nowplaying")
    @commands.guild_only()
    @commands.check(audio_playing)
    async def nowplaying(self, ctx):
        """Displays information about the current song."""
        state = self.get_state(ctx.guild)
        message = await ctx.send("", embed=state.now_playing.get_embed())
        state.message = message
        await self._add_reaction_controls(message)

    @commands.command(aliases=["q", "playlist"], usage="!queue")
    @commands.guild_only()
    @commands.check(audio_playing)
    async def queue(self, ctx):
        """Display the current play queue."""
        state = self.get_state(ctx.guild)
        await ctx.send(self._queue_text(state.playlist))

    def _queue_text(self, queue):
        """Returns a block of text describing a given song queue."""
        if len(queue) > 0:
            message = [f"{len(queue)} songs in queue:"]
            message += [
                f"  {index + 1}. **{song.title}** (requested by **{song.requested_by.name}**)"
                for (index, song) in enumerate(queue)
            ]  # add individual songs
            return "\n".join(message)
        else:
            return "The play queue is empty."

    @commands.command(aliases=["cq", "clear"], usage="!clearqueue")
    @commands.guild_only()
    @commands.check(audio_playing)
    @commands.has_permissions(administrator=True)
    async def clearqueue(self, ctx):
        """Clears the play queue without leaving the channel."""
        state = self.get_state(ctx.guild)
        state.playlist = []

    @commands.command(aliases=["jq"], usage="!jumpqueue [index] [new_index]")
    @commands.guild_only()
    @commands.check(audio_playing)
    @commands.has_permissions(administrator=True)
    async def jumpqueue(self, ctx, song: int, new_index: int):
        """Moves song at an index to `new_index` in queue."""
        state = self.get_state(ctx.guild)  # get state for this guild
        if 1 <= song <= len(state.playlist) and 1 <= new_index:
            song = state.playlist.pop(song - 1)  # take song at index...
            state.playlist.insert(new_index - 1, song)  # and insert it.

            await ctx.send(self._queue_text(state.playlist))
        else:
            raise commands.CommandError("You must use a valid index.")

    @commands.command(brief="Plays audio from <url>.", aliases=["p"], usage="!play [url or search term]")
    @commands.guild_only()
    async def play(self, ctx, *, url):
        """Plays audio hosted at <url> (or performs a search for <url> and plays the first result)."""

        client = ctx.guild.voice_client
        state = self.get_state(ctx.guild)  # get the guild's state

        if 'playlist' in url:
            logging.info("Requested song is a playlist")
            r = requests.get(url)
            page = r.text
            soup = bs(page, 'html.parser')
            res = soup.find_all('a', {'class': 'pl-video-title-link'})
            for i, l in enumerate(res):
                link = str("https://www.youtube.com" + l.get("href").split('&')[0])
                logging.info("Added to queue: " + link)
                try:
                    video = Video(link, ctx.author)
                except ytdl.DownloadError as e:
                    logging.warning(f"Error downloading video: {e}")
                    await ctx.send(
                        "There was an error downloading your video, sorry.")
                    return
                state.playlist.append(video)
                if i == 1:
                    message = await ctx.send(embed=video.get_embed())
                    await self._add_reaction_controls(message)
                    state.message = message
                    if client is None:
                        if ctx.author.voice is not None and ctx.author.voice.channel is not None:
                            channel = ctx.author.voice.channel
                            client = await channel.connect()
                            video = state.playlist.pop(0)
                            self._play_song(client, state, video)
                            logging.info(f"Now playing '{video.title}'")
                else:
                    await ctx.send("**" + video.title + "** "
                        "Added to queue.", delete_after=5)
        else:
            try:
                video = Video(url, ctx.author)
            except ytdl.DownloadError as e:
                logging.warning(f"Error downloading video: {e}")
                await ctx.send(
                    "There was an error downloading your video, sorry.")
                return
            state.playlist.append(video)
            message = await ctx.send(
                "Added to queue.", embed=video.get_embed())
            await self._add_reaction_controls(message)
            state.message = message

            if client is None:
                if ctx.author.voice is not None and ctx.author.voice.channel is not None:
                    channel = ctx.author.voice.channel
                    client = await channel.connect()
                    video = state.playlist.pop(0)
                    self._play_song(client, state, video)
                    logging.info(f"Now playing '{video.title}'")


    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Respods to reactions added to the bot's messages, allowing reactions to control playback."""
        message = reaction.message
        if user != self.bot.user and message.author == self.bot.user:
            if message.guild is not None:  # TODO: fix for polls etc as will remove all shitiit
                await message.remove_reaction(reaction, user)
            if message.guild and message.guild.voice_client:
                user_in_channel = user.voice and user.voice.channel and user.voice.channel == message.guild.voice_client.channel
                permissions = message.channel.permissions_for(user)
                guild = message.guild
                state = self.get_state(guild)
                if permissions.administrator or (user_in_channel and state.is_requester(user)):
                    client = message.guild.voice_client
                    if reaction.emoji == "⏯":
                        # pause audio
                        self._pause_audio(client)
                    elif reaction.emoji == "⏭":
                        # skip audio
                        client.stop()
                    elif reaction.emoji == "⏮":
                        state.playlist.insert(
                            0, state.now_playing
                        )  # insert current song at beginning of playlist
                        client.stop()  # skip ahead
                elif reaction.emoji == "⏭" and user_in_channel and message.guild.voice_client and message.guild.voice_client.channel:
                    # ensure that skip was pressed, that vote skipping is enabled, the user is in the channel, and that the bot is in a voice channel
                    voice_channel = message.guild.voice_client.channel
                    await self._vote_skip(voice_channel, user)
                    # announce vote
                    channel = message.channel
                    users_in_channel = len([
                        member for member in voice_channel.members
                        if not member.bot
                    ])  # don't count bots
                    required_votes = math.ceil(
                        0.5 * users_in_channel)
                    await channel.send(
                        f"{user.mention} voted to skip ({len(state.skip_votes)}/{required_votes} votes)"
                    )

    async def _add_reaction_controls(self, message):
        """Adds a 'control-panel' of reactions to a message that can be used to control the bot."""
        CONTROLS = ["⏮", "⏯", "⏭"]
        for control in CONTROLS:
            await message.add_reaction(control)


def setup(client):
    client.add_cog(Music(client))


class GuildState:
    """Helper class managing per-guild state."""

    def __init__(self):
        self.volume = 1.0
        self.playlist = []
        self.skip_votes = set()
        self.now_playing = None
        self.message = None

    def is_requester(self, user):
        return self.now_playing.requested_by == user
