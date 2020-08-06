import asyncio
import functools
import io
import json
import random

import aiohttp
import cv2
import discord
import youtube_dl
from PIL import Image
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

# HP, MP, ATT, DEF, SPD, DEX, VIT, WIS
max_stats = {
"Rogue" : (720, 252, 50, 25, 75, 75, 40, 50),
"Archer" : (700, 252, 75, 25, 50, 50, 40, 50),
"Wizard" : (670, 385, 75, 25, 50, 75, 40, 60),
"Priest" : (670, 385, 50, 25, 55, 55, 40, 75),
"Warrior" : (770, 252, 75, 25, 50, 50, 75, 50),
"Knight" : (770, 252, 50, 40, 50, 50, 75, 50),
"Paladin" : (770, 252, 50, 30, 55, 45, 40, 75),
"Assassin" : (720, 252, 60, 25, 75, 75, 40, 60),
"Necromancer" : (670, 385, 75, 25, 50, 60, 30, 75),
"Huntress" : (700, 252, 75, 25, 50, 50, 40, 50),
"Mystic" : (670, 385, 60, 25, 60, 55, 40, 75),
"Trickster" : (720, 252, 65, 25, 75, 75, 40, 60),
"Sorcerer" : (670, 385, 70, 25, 60, 60, 75, 60),
"Ninja" : (720, 252, 70, 25, 60, 70, 60, 70),
"Samurai" : (720, 252, 75, 30, 55, 50, 60, 60),
"Bard" : (670, 385, 55, 25, 55, 70, 45, 75)
}


async def connect_helper(self, ctx):
    if ctx.message.guild is None:
        await ctx.message.author.send("This command can only be used in a server when connected to a VC.")
        return None

    channel = ctx.message.author.voice.channel
    voice = discord.utils.get(self.client.voice_clients, guild=ctx.guild)

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


class Patreon(commands.Cog):
    """Patreon Only Commands!"""

    def __init__(self, client):
        self.client = client

    async def cog_check(self, ctx):
        is_rl = False
        if ctx.guild:
            is_rl = ctx.author.top_role >= self.client.guild_db[ctx.guild.id][sql.gld_cols.rlroleid]
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


    @commands.command(usage='realmeye [member]', description="Get realmeye info of your account or someone else's!")
    @commands.guild_only()
    @commands.cooldown(1, 30, type=BucketType.member)
    async def realmeye(self, ctx, member: utils.MemberLookupConverter = None):
        if not member:
            member = ctx.author
        udata = await sql.get_user(self.client.pool, member.id)
        if not udata:
            return await ctx.send("The specified user was not found in the database!")
        ign = udata[sql.usr_cols.ign]

        embed = discord.Embed(title="Fetching...", description="Please wait while your player-data is being retrieved.\nThis can take up to a minute if realmeye's servers are "
                                                               "being slow! (They usually are)", color=discord.Color.orange())
        embed.set_thumbnail(url="https://i.imgur.com/nLRgnZf.gif")
        msg = await ctx.send(embed=embed)

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(10)) as cs:
                async with cs.get(f'https://nightfirec.at/realmeye-api/?player={ign}') as r:
                    if r.status == 403:
                        print("ERROR: API ACCESS FORBIDDEN")
                        await ctx.send(f"<@{self.client.owner_id}> ERROR: API ACCESS REVOKED!.")
                    data = await r.json()  # returns dict
                if not data:
                    try:
                        await msg.delete()
                    except discord.NotFound:
                        pass
                    return await ctx.send("There was an issue retrieving realmeye data. Please try the command later.")
            if 'error' in data:
                try:
                    await msg.delete()
                except discord.NotFound:
                    pass
                embed = discord.Embed(title='Error!', description=f"There were no players found on realmeye with the name `{ign}`.",
                                      color=discord.Color.red())
                return await ctx.send(embed=embed)
        except asyncio.TimeoutError:
            try:
                await msg.delete()
            except discord.NotFound:
                pass
            return await ctx.send("There was an issue retrieving realmeye data. Please try the command later.")

        d = f"{member.mention}\n"
        d += f"**{data['desc1']}**\n" if data['desc1'] else ""
        d += f"{data['desc2']}\n" if data['desc2'] else ""
        d += f"{data['desc3']}\n" if data['desc3'] else ""
        d += f"\n\nGuild: [{data['guild']}](https://www.realmeye.com/guild/{data['guild'].replace(' ', '%20')}) ({data['guild_rank']})" if data['guild'] else ""
        base_embed = discord.Embed(title=f"Realmeye Info for {ign}", description=d,
                                   url=f'https://www.realmeye.com/player/{ign}', color=discord.Color.blue())
        info = f"Characters: **{data['chars']}**\nSkins: **{data['skins']}**\nFame: **{data['fame']:,}**<:fame:682209281722024044>\nEXP: **{data['exp']:,}**\nStars: **" \
               f"{data['rank']}**⭐\n\nAccount Fame: **{data['account_fame']:,}**<:fame:682209281722024044>\n"
        info += f"Created: {data['created']}" if 'created' in data else f"First Seen: {data['player_first_seen']}" if 'player_first_seen' in data else ""
        info += f"\nLast Seen: {data['player_last_seen']}\nCharacters Hidden: {'✅' if data['characters_hidden'] else '❌'}"


        if not data['characters_hidden'] and data['characters']:
            base_embed.add_field(name="Info", value=info+"\n\nCharacter Data continues on the next page...", inline=False)
            base_embed.set_footer(text='© Darkmattr | Use the reactions to flip pages', icon_url=member.avatar_url)
            with open('data/itemImages.json') as file:
                item_images = json.load(file)
            with open('data/skinImages.json') as file:
                skin_images = json.load(file)
            with open('data/createdItemImages.json') as file:
                created_images: dict = json.load(file)

            embeds = []
            embeds.append(base_embed)
            for c in data['characters']:
                embed = discord.Embed(title=f"Characters of {ign}: {c['class']}", color=discord.Color.teal())
                ids = [c['equips']['data_weapon_id'], c['equips']['data_ability_id'], c['equips']['data_armor_id'], c['equips']['data_ring_id']]
                i_str = "-".join([str(id) for id in ids])
                if i_str in created_images:
                    i_url = created_images[i_str]
                else:
                    i_url = await make_equips_img(ids, item_images)
                    created_images[i_str] = i_url
                    with open('data/createdItemImages.json', 'w') as file:
                        json.dump(created_images, file)
                embed.set_image(url=i_url)
                embed.set_thumbnail(url=skin_images[str(c['data_class_id'])][str(c['data_skin_id'])])
                desc = f"Class Quests: **{c['cqc']}/5** Quests\nEXP: **{c['exp']:,}**xp\nLevel: **{c['level']}**\nStats Maxed: " \
                       f"**{c['stats_maxed']}/8**\nPlace: **{c['place']:,}**\nBackpack: "
                desc += "✅" if c['backpack'] else "❌"
                desc += "\nPet: "
                desc += f"✅\nPet Name: {c['pet']}" if c['pet'] else "❌"
                embed.description = desc
                stat_d = c['stats']
                hp_bar = utils.textProgressBar(stat_d['hp'], max_stats[c['class']][0], decimals=0, prefix='', percent_suffix="  Maxed", suffix="", length=12, fullisred=False)
                mp_bar = utils.textProgressBar(stat_d['mp'], max_stats[c['class']][1], decimals=0, prefix='', percent_suffix=" Maxed", suffix="", length=12, fullisred=False)
                att_bar = utils.textProgressBar(stat_d['attack'], max_stats[c['class']][2], decimals=0, prefix='', percent_suffix=" Maxed", suffix="", length=6, fullisred=False)
                def_bar = utils.textProgressBar(stat_d['defense'], max_stats[c['class']][3], decimals=0, prefix='', percent_suffix=" Maxed", suffix="", length=6, fullisred=False)
                spd_bar = utils.textProgressBar(stat_d['speed'], max_stats[c['class']][4], decimals=0, prefix='', percent_suffix=" Maxed", suffix="", length=6, fullisred=False)
                dex_bar = utils.textProgressBar(stat_d['dexterity'], max_stats[c['class']][5], decimals=0, prefix='', percent_suffix=" Maxed", suffix="", length=6, fullisred=False)
                vit_bar = utils.textProgressBar(stat_d['vitality'], max_stats[c['class']][6], decimals=0, prefix='', percent_suffix=" Maxed", suffix="", length=6, fullisred=False)
                wis_bar = utils.textProgressBar(stat_d['wisdom'], max_stats[c['class']][7], decimals=0, prefix='', percent_suffix=" Maxed", suffix="", length=6, fullisred=False)

                hp_s = f"HP: **{stat_d['hp']}/{max_stats[c['class']][0]}**\n{hp_bar}\n" \
                         f"MP: **{stat_d['mp']}/{max_stats[c['class']][1]}**\n{mp_bar}\n"
                stat_s_1 = f"ATT: **{stat_d['attack']}/{max_stats[c['class']][2]}** | {att_bar}\n" \
                         f"DEF: **{stat_d['defense']}/{max_stats[c['class']][3]}** | {def_bar}\n" \
                         f"SPD: **{stat_d['speed']}/{max_stats[c['class']][4]}** | {spd_bar}\n"
                stat_s_2 = f"DEX: **{stat_d['dexterity']}/{max_stats[c['class']][5]}** | {dex_bar}\n" \
                         f"VIT: **{stat_d['vitality']}/{max_stats[c['class']][6]}** | {vit_bar}\n" \
                         f"WIS: **{stat_d['wisdom']}/{max_stats[c['class']][7]}** | {wis_bar}"
                embed.add_field(name="Health & Mana", value=hp_s, inline=False)
                embed.add_field(name="Stats:", value=stat_s_1, inline=False)
                embed.add_field(name="More Stats:", value=stat_s_2)
                embed.set_footer(text='© Darkmattr | Use the reactions to flip pages')
                embeds.append(embed)

            paginator = utils.EmbedPaginator(self.client, ctx, embeds)
            try:
                await msg.delete()
            except discord.NotFound:
                pass
            return await paginator.paginate()

        base_embed.add_field(name="Info", value=info, inline=False)
        await msg.edit(embed=base_embed)

    @commands.command(usage='soundboard <soundname>', description='Play a sound effect! (Must be in VC)', aliases=['sb'])
    @commands.guild_only()
    @commands.cooldown(1, 600, type=BucketType.member)
    async def soundboard(self, ctx, soundname=""):
        if not ctx.author.voice:
            commands.Command.reset_cooldown(ctx.command, ctx)
            return await ctx.send("You must be in a VC to use this command!")

        if ctx.author.id != self.client.owner_id:
            if ctx.author.voice.channel in ctx.bot.guild_db.get(ctx.guild.id) or "Raid" in str(ctx.author.voice.channel.name):
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

        voice = await connect_helper(self, ctx)
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


def get_split_image(img, x, y):
    img = img[y:y + 46, x:x + 46].copy()
    return img


top = 7
left = (6, 103, 202, 299)
## Scale x2,
async def make_equips_img(equip_ids, definition):
    images = []
    async with aiohttp.ClientSession() as cs:
        for id in equip_ids:
            id = id if id else -1
            url = definition[str(id)]
            async with cs.request('GET', url=url) as resp:
                if resp.status == 200:
                    b = await resp.read()
                    b = io.BytesIO(b)
                    images.append(b)

    io_buf = await asyncio.get_event_loop().run_in_executor(None, functools.partial(make_images, images))
    payload = {'file': io_buf.read(), 'upload_preset': 'realmeye-pics'}
    async with aiohttp.ClientSession() as cs:
        async with cs.request('POST', "https://api.cloudinary.com/v1_1/darkmattr/image/upload", data=payload) as resp:
            if resp.status == 200:
                img_data = await resp.json()
                return img_data["secure_url"]

def make_images(bytes_arr):
    images = []
    for b in bytes_arr:
        img = Image.open(b)
        img = img.convert('RGBA')
        img = img.resize((92, 92), Image.ANTIALIAS)
        images.append(img)

    background_img = Image.open('files/equips.jpg')
    for i, img in enumerate(images):
        background_img.paste(img, (left[i], top), img)

    io_buf = io.BytesIO()
    background_img.save(io_buf, format='JPEG')
    io_buf.seek(0)

    return io_buf

def transparentOverlay(backgroundImage, overlayImage, pos=(0, 0), scale=1):
    overlayImage = cv2.resize(overlayImage, (0, 0), fx=scale, fy=scale)
    h, w, _ = overlayImage.shape  # Size of foreground
    rows, cols, _ = backgroundImage.shape  # Size of background Image
    y, x = pos[0], pos[1]  # Position of foreground/overlayImage image

    # loop over all pixels and apply the blending equation
    for i in range(h):
        for j in range(w):
            if x + i >= rows or y + j >= cols:
                continue
            alpha = float(overlayImage[i][j][3] / 255.0)  # read the alpha channel
            backgroundImage[x + i][y + j] = alpha * overlayImage[i][j][:3] + (1 - alpha) * backgroundImage[x + i][y + j]
    return backgroundImage