import asyncio
import random

import aiohttp
import discord
import youtube_dl
from discord.ext import commands
from discord.ext.commands import BucketType

import sql
import utils

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {'format': 'bestaudio/best', 'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s', 'restrictfilenames': True,
                       'noplaylist': True, 'nocheckcertificate': True, 'ignoreerrors': False, 'logtostderr': False, 'quiet': True,
                       'no_warnings': True, 'default_search': 'auto', 'source_address': '0.0.0.0'
                       # bind to ipv4 since ipv6 addresses cause issues sometimes
                       }

ffmpeg_options = {'options': '-vn', 'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


async def connect_helper(self, ctx, vc=None):
    if ctx.message.guild is None:
        await ctx.message.author.send("This command can only be used in a server when connected to a VC.")
        return None

    if not vc:
        vc = ctx.message.author.voice.channel
    voice = discord.utils.get(self.client.voice_clients, guild=ctx.guild)

    if voice and voice.is_connected():
        await voice.move_to(vc)
    else:
        voice = await vc.connect()

    return voice


def disconnect_helper(self, voice):
    coroutine = voice.disconnect()
    task = asyncio.run_coroutine_threadsafe(coroutine, self.client.loop)
    try:
        task.result()
    except:
        pass


class Patreon(commands.Cog):
    """Patreon Only Commands!"""

    def __init__(self, client):
        self.client = client

    async def cog_check(self, ctx):
        is_rl = False
        if ctx.guild:
            is_rl = ctx.author.top_role >= self.client.guild_db[ctx.guild.id][sql.gld_cols.eventrlid] if self.client.guild_db[ctx.guild.id][sql.gld_cols.eventrlid] \
                else ctx.author.top_role >= self.client.guild_db[ctx.guild.id][sql.gld_cols.rlroleid]
        res = ctx.author.id in self.client.patreon_ids or is_rl
        if not res:
            await ctx.send("This is a Patreon Only Command! Run `!patreon` if you want more info.")
        return res

    @commands.command(usage="p_report", description="Report a bug or suggest a new feature here!", aliases=['p_suggest', 'patreonreport', 'patreonsuggest'])
    @commands.guild_only()
    async def p_report(self, ctx):
        blacklisted = await sql.get_blacklist(self.client.pool, ctx.author.id, ctx.guild.id, 'reporting')
        if blacklisted:
            return await ctx.author.send("You have been blacklisted from sending a report or suggestion! Contact a security+ if you believe this to be a mistake!")
        embed = discord.Embed(title="Is this a report a feature or a bug?", description="Select 💎 if it's a feature, 🦟 if it's a bug.\n❌ to cancel.", color=discord.Color.gold())
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("💎")
        await msg.add_reaction("🦟")
        await msg.add_reaction("❌")

        def check(react, usr):
            return usr.id == ctx.author.id and react.message.id == msg.id and str(react.emoji) in ["💎", "🦟", "❌"]

        try:
            reaction, user = await self.client.wait_for('reaction_add', timeout=1800, check=check)  # Wait 1/2 hr max
        except asyncio.TimeoutError:
            embed = discord.Embed(title="Timed out!", description="You didn't choose an option in time!",
                                  color=discord.Color.red())
            await msg.delete()
            return await ctx.send(embed=embed)

        if str(reaction.emoji) == '💎':
            label = 'Feature'
        elif str(reaction.emoji) == '❌':
            embed = discord.Embed(title="Cancelled!", description="You cancelled this report!",
                                  color=discord.Color.red())
            return await msg.edit(embed=embed)
        else:
            label = 'Bug'

        if label == 'Feature':
            desc = "```**Is your feature request related to a problem? Please describe.**\nA clear and concise description of what the problem is. " \
                   "Ex. I'm always frustrated when [...]\n\n**How would the feature work? Describe**\nAdd a description about how the feature would work " \
                   "(e.g. commands, interactions, etc)\n\n**Describe the ideal implementation.**\nA clear and concise description of what you want to happen.\n\n" \
                   "**Describe alternatives you've considered**\nA clear and concise description of any alternative solutions or features you've considered.\n\n" \
                   "**Additional context**\nAdd any other context or a screenshot about the feature request here.\n```"
        else:
            desc = "```**Describe the bug**\nA clear and concise description of what the bug is.\n\n**To Reproduce**\nSteps to reproduce the behavior:\n1. (list all steps)\n" \
                   "**Expected behavior**\nA clear and concise description of what you expected to happen.\n\n**Screenshot**\nIf applicable, add a screenshot/image to help " \
                   "explain your problem.\n\n**What server & channel did this occur in?**\nServer:\nChannel:\n```"
        embed = discord.Embed(title="Please copy the template & fill it out -- Send CANCEL to cancel.", description=desc, color=discord.Color.gold())
        await msg.clear_reactions()
        await msg.edit(embed=embed)

        while True:
            imageb = None

            def member_check(m):
                return m.author.id == ctx.author.id and m.channel == msg.channel

            try:
                issuemsg = await self.client.wait_for('message', timeout=1800, check=member_check)
            except asyncio.TimeoutError:
                embed = discord.Embed(title="Timed out!", description="You didn't write your report in time!", color=discord.Color.red())
                await msg.edit(embed=embed)

            content = str(issuemsg.content)
            if 'cancel' in content.strip().lower():
                embed = discord.Embed(title="Cancelled!", description="You cancelled this report!",
                                      color=discord.Color.red())
                return await msg.edit(embed=embed)
            if not content:
                content = "No issue content provided."
            if issuemsg.attachments:
                imageb = issuemsg.attachments[0] if issuemsg.attachments[0].height else None
                if not imageb:
                    await ctx.send("Please only send images as attachments.", delete_after=7)
                    continue
                else:
                    imageb = await imageb.read()
                    await issuemsg.delete()
                    break
            else:
                await issuemsg.delete()
                break

        if imageb:
            img_data = await utils.image_upload(imageb, ctx, is_rc=False)
            if not img_data:
                return await ctx.send(
                    "There was an issue communicating with the image server, try again and if the issue persists – contact the developer.",
                    delete_after=10)

            image = img_data["secure_url"]
            content += f"\n\nUploaded Image:\n{image}"

        title = '[PATREON] [FEATURE] ' if label == 'Feature' else '[PATREON] [BUG] '
        title += f'Submitted by {ctx.author.display_name}'

        header = {'Authorization': f'token {self.client.gh_token}'}
        payload = {
            "title": title,
            'body': content,
            'assignee': 'Jacobvs',
            'labels': [label]
        }
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(10)) as cs:
                async with cs.request("POST", "https://api.github.com/repos/Jacobvs/Rotmg-Discord-Bot/issues", json=payload, headers=header) as r:
                    if r.status != 201:
                        print("GH ISSUE UPLOAD ERROR:")
                        print(r)
                        print(await r.json())
                        return None
                    else:
                        res = await r.json()
        except asyncio.TimeoutError:
            return await ctx.send("There was an issue uploading the issue, please retry the command.", delete_after=10)

        embed = discord.Embed(title="Thank You!", description="I (Darkmattr) appreciate that you took the time to fill out a report/suggestion!\nI've been notified & will get to "
                                                              f"it as soon as possible.\n\nTrack the status of your issue here:\n{res['html_url']}", color=discord.Color.green())
        await msg.edit(embed=embed)



    @commands.command(usage='bean <member>', description="Lorlie's Custom Patreon Command")
    @commands.guild_only()
    @commands.cooldown(1, 1800, BucketType.member)
    async def bean(self, ctx, member: utils.MemberLookupConverter):
        if member.bot:
            commands.Command.reset_cooldown(ctx.command, ctx)
            return await ctx.send(f'Cannot bean `{member.display_name}` (is a bot).')
        if ctx.author.id != self.client.owner_id:
            if member.guild_permissions.manage_guild and ctx.author.id not in self.client.owner_ids:
                commands.Command.reset_cooldown(ctx.command, ctx)
                return await ctx.send(f'Cannot bean `{member.display_name}` due to roles.')
        if member.id in self.client.beaned_ids:
            commands.Command.reset_cooldown(ctx.command, ctx)
            return await ctx.send(f"{member.display_name}__ is already Beaned!")
        self.client.beaned_ids.add(member.id)
        await ctx.send(f"Lorlie's Custom Patreon Command!\n__{member.display_name}__ was Beaned!")
        await asyncio.sleep(240)
        if member.id in self.client.beaned_ids:
            self.client.beaned_ids.remove(member.id)
            await ctx.send(f"Lorlie's Custom Patreon Command!\n__{member.display_name}__ was automatically Un-Beaned!")

    @commands.command(usage='soundboard <soundname>', description='Play a sound effect! (Must be in VC)', aliases=['sb'])
    @commands.guild_only()
    @commands.cooldown(1, 600, type=BucketType.member)
    async def soundboard(self, ctx, soundname="", voice_channel: discord.VoiceChannel = None):
        if ctx.author.id != self.client.owner_id:
            if not ctx.author.voice:
                commands.Command.reset_cooldown(ctx.command, ctx)
                return await ctx.send("You must be in a VC to use this command!")
            else:
                vc = ctx.author.voice.channel
        elif not voice_channel:
            if not ctx.author.voice:
                return await ctx.send("You must be in a VC to use this command!")
            vc = ctx.author.voice.channel
        else:
            vc = voice_channel

        if ctx.author.id != self.client.owner_id:
            if vc in ctx.bot.guild_db.get(ctx.guild.id) or "Raid" in str(vc.name):
                commands.Command.reset_cooldown(ctx.command, ctx)
                return await ctx.send("You cannot use this command in a raiding VC!")


        soundname = soundname.strip().lower()
        if soundname not in ['ph', 'ahhaha', 'bully', 'fbi', 'roll', 'richard', 'sax', 'knock']:
            commands.Command.reset_cooldown(ctx.command, ctx)
            return await ctx.send("Please choose a valid sound option! Usage: `!sb <soundname>`\nOptions: `ph`, `ahhaha`, `bully`, `fbi`, `richard`, `roll`, `sax`, `knock`")

        file = 'files/'
        file += 'ph.mp3' if soundname == 'ph' else 'ahhaha.mp3' if soundname == 'ahhaha' else 'bully-me.mp3' if soundname == 'bully' else 'roll.mp3' if soundname == 'roll' \
            else 'fbi.mp3' if soundname == 'fbi' else 'richard.mp3' if soundname == 'richard' else 'sax.mp3' if soundname == 'sax' else 'knock.mp3'

        message = 'Where have you heard this before... ?' if soundname == 'ph' else 'Ah-Ha-Ha' if soundname == 'ahhaha' else 'Why you bully me?' if soundname == 'bully' else \
            'youtube.com/watch?v=dQw4w9WgXcQ' if soundname == 'roll' else 'FBI, OPEN UP' if soundname == 'fbi' else 'What the fuck, Richard?' if soundname == 'richard' else \
            '( ͡° ͜ʖ ͡°)' if soundname == 'sax' else "who's there?"

        voice = await connect_helper(self, ctx, vc)
        client = ctx.guild.voice_client
        if not client.source:
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(file, options=ffmpeg_options['options']),
                                                  volume=0.3)
            ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else disconnect_helper(self, voice=voice))
            await ctx.send(message)
        else:
            await ctx.send("Audio is already playing!")


    @commands.command(usage='joke', description='Tell a joke.')
    async def joke(self, ctx):
        async with aiohttp.ClientSession() as cs:
            async with cs.get('https://sv443.net/jokeapi/v2/joke/Dark?blacklistFlags=nsfw,religious,political,racist,sexist',
                              ssl=False) as r:
                data = await r.json()

        if data and not data['error']:
            if data['type'] == 'single':
                embed = discord.Embed(title=data['joke'])
            else:
                embed = discord.Embed(title=data['setup'], description=data['delivery'])
            await ctx.send(embed=embed)
        else:
            await ctx.send("Bot isn't funny I guess? (Servers couldn't be reached. Try again later.)")

    @commands.command(usage="oogabooga", description="The only command you ever need.")
    async def oogabooga(self, ctx):
        await ctx.message.delete()
        opts = ["BOOGA OOGA", "ooga boooga", "ooga chacka booga", "boogady oogady", "OOGA BOOGA", "boog.", "oog.", "booga", "ooga"]
        embed = discord.Embed(title=random.choice(opts), description="[Ooga-booga Translator](https://codepen.io/Darkm4tter/full/mNWpBZ)")
        embed.set_image(url="https://i.imgur.com/6z74JCz.png")
        await ctx.send(embed=embed)

    @commands.command(usage="whatthefuck", description="????")
    async def whatthefuck(self, ctx):
        await ctx.message.delete()
        embed = discord.Embed(title="w h a t ᵗʰᵉᶠᵘᶜᵏ")
        embed.set_image(url="https://i.imgur.com/qMK83uT.jpg")
        await ctx.send(embed=embed)

    @commands.command(usage="isitgone", description="Spooky...")
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

def setup(client):
    client.add_cog(Patreon(client))


