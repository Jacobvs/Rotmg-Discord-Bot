import asyncio
import functools
import io
import json
from datetime import datetime

import aiohttp
import cv2
import discord
from PIL import Image
from discord.ext import commands
from discord.ext.commands import BucketType

import checks
import embeds
import sql
import utils
from checks import is_rl_or_higher_check, is_bot_owner


def is_lorlie():
    def predicate(ctx):
        return ctx.message.author.id == 482120766893064192
    return commands.check(predicate)

def is_caped():
    def predicate(ctx):
        return ctx.message.author.id == 163394008603820032
    return commands.check(predicate)

def is_rl_and_not_beaned():
    def predicate(ctx):
        return (ctx.author.id, ctx.guild.id) not in ctx.bot.beaned_ids and checks.is_rl_or_higher_check()
    return commands.check(predicate)

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

class Misc(commands.Cog):
    """Miscellaneous Commands"""


    def __init__(self, client):
        self.client = client
        self.laughs = ["files/ahhaha.mp3", "files/jokerlaugh.mp3"]
        self.numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']


    @commands.command(usage="stats [member]", description="Check your or someone else's run stats.")
    async def stats(self, ctx, what=None):
        # if member:
        #     converter = utils.MemberLookupConverter()
        #     mem = await converter.convert(ctx, member, is_logging=True)
        #     if isinstance(mem, int):
        #         uid = mem
        #         try:
        #             mem = await self.client.fetch_user(mem)
        #         except discord.NotFound:
        #             return await ctx.send("Found member in database with id of: {mem} - but the user account has since been deleted!")
        #     else:
        #         uid = mem.id
        # else:
        #     mem = None
        #     uid = ctx.author.id
        member = None
        server_id = None
        if what:
            if what.strip().lower() == 'wonderland' or what.strip().lower() == 'woland':
                server_id = 666063675416641539
                server_name = "Wonderland ✶"
            elif ctx.guild:
                converter = utils.MemberLookupConverter()
                member = await converter.convert(ctx, what)

        author = member if member and ctx.guild else ctx.author
        if not server_id:
            if not ctx.guild:
                servers = []
                for g in self.client.guilds:
                    if g.get_member(author.id):
                        servers.append(g)
                serverstr = ""
                for i, s in enumerate(servers[:10]):
                    serverstr += self.numbers[i] + " - " + s.name + "\n"
                embed = discord.Embed(description="What server would you like to check stats for?\n"+serverstr, color=discord.Color.gold())
                msg = await ctx.author.send(embed=embed)
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

                server = servers[self.numbers.index(str(reaction.emoji))]
                server_id = server.id
                server_name = server.name
                author = servers[self.numbers.index(str(reaction.emoji))].get_member(author.id)
                await msg.delete()
            else:
                try:
                    await ctx.message.delete()
                except discord.NotFound:
                    pass
                server = ctx.guild
                server_id = server.id
                server_name = server.name

        data = await sql.get_log(self.client.pool, server_id, author.id)


        embed = discord.Embed(title=f"Stats for {author.display_name} in {server_name}", color=discord.Color.green())
        embed.set_thumbnail(url=author.avatar_url)
        embed.add_field(name="__**Key Stats**__", value="Popped: "
                        f"**{data[sql.log_cols.pkey]}**\nEvent Keys: **{data[sql.log_cols.eventkeys]}**\nVials: "
                        f"**{data[sql.log_cols.vials]}**\nSword Runes: **{data[sql.log_cols.swordrunes]}**\nShield Runes: "
                        f"**{data[sql.log_cols.shieldrunes]}**\nHelm Runes: **{data[sql.log_cols.helmrunes]}**", inline=False)
        if server_id == 660344559074541579:
            embed.add_field(name="__**Run Stats**__", value=f"Oryx 3 Completes: **{data[sql.log_cols.ocompletes]}**\nOryx 3 Fails: **{data[sql.log_cols.oattempts]}**\nEvents "
                                                            f"Completed: **{data[sql.log_cols.eventsdone]}**", inline=False)
        else:
            embed.add_field(name="__**Run Stats**__", value=f"Completed: **{data[sql.log_cols.runsdone]}**\nEvents Completed: **{data[sql.log_cols.eventsdone]}**", inline=False)
        gdb = self.client.guild_db.get(server_id)
        if gdb:
            erl = gdb[sql.gld_cols.eventrlid]
            role = erl if erl else gdb[sql.gld_cols.rlroleid]
            if author.top_role >= role:
                embed.add_field(name="__**Leading Stats**__", value="Successful Runs: "
                            f"**{data[sql.log_cols.srunled]}**\nFailed Runs: **{data[sql.log_cols.frunled]}**\nAssisted: "
                            f"**{data[sql.log_cols.runsassisted]}**\nEvents: **{data[sql.log_cols.eventled]}**\nEvents Assisted: "
                            f"**{data[sql.log_cols.eventsassisted]}**\nWeekly Runs Led: **{data[sql.log_cols.weeklyruns]}**\n"
                            f"Weekly Runs Assisted: **{data[sql.log_cols.weeklyassists]}**", inline=False)
        else:
            embed.add_field(name="__**Leading Stats**__", value="Successful Runs: "
                            f"**{data[sql.log_cols.srunled]}**\nFailed Runs: **{data[sql.log_cols.frunled]}**\nAssisted: "
                            f"**{data[sql.log_cols.runsassisted]}**\nEvents: **{data[sql.log_cols.eventled]}**\nEvents Assisted: "
                            f"**{data[sql.log_cols.eventsassisted]}**\nWeekly Runs Led: **{data[sql.log_cols.weeklyruns]}**\n"
                            f"Weekly Runs Assisted: **{data[sql.log_cols.weeklyassists]}**", inline=False)
        embed.timestamp = datetime.utcnow()
        if ctx.guild:
            return await ctx.send(embed=embed)
        await ctx.author.send(embed=embed)

    @commands.command(usage='realmeye [member]', description="Get realmeye info of your account or someone else's!", aliases=['chars', 'characters'])
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
                async with cs.get(f'https://darkmattr.uc.r.appspot.com/?player={ign}') as r:
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
        info = f"Characters: **{data['chars']}**\nExaltations: **{data['exaltations']}**\nSkins: **{data['skins']}**\nFame: **{data['fame']:,}**<:fame:682209281722024044>\nEXP: " \
               f"**{data['exp']:,}**\nStars: **{data['rank']}**⭐\n\nAccount Fame: **{data['account_fame']:,}**<:fame:682209281722024044>\n"
        info += f"Created: {data['created']}" if 'created' in data else f"First Seen: {data['player_first_seen']}" if 'player_first_seen' in data else ""
        info += f"\nLast Seen: {data['player_last_seen']}\nCharacters Hidden: {'✅' if data['characters_hidden'] else '❌'}"

        if not data['characters_hidden'] and data['characters']:
            base_embed.add_field(name="Info", value=info + "\n\nCharacter Data continues on the next page...", inline=False)
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
                ids = [c['equips']['data_weapon_id'] if 'data_weapon_id' in c['equips'] else -99,
                       c['equips']['data_ability_id'] if 'data_ability_id' in c['equips'] else -99,
                       c['equips']['data_armor_id'] if 'data_armor_id' in c['equips'] else -99,
                       c['equips']['data_ring_id'] if 'data_ring_id' in c['equips'] else -99]
                i_str = "-".join([str(id) for id in ids])
                if i_str in created_images:
                    i_url = created_images[i_str]
                else:
                    i_url = await make_equips_img(ids, item_images)
                    created_images[i_str] = i_url
                    with open('data/createdItemImages.json', 'w') as file:
                        json.dump(created_images, file)
                embed.set_image(url=i_url)
                if str(c['data_skin_id']) in skin_images[str(c['data_class_id'])]:
                    embed.set_thumbnail(url=skin_images[str(c['data_class_id'])][str(c['data_skin_id'])])
                desc = f"Class Quests: **{c['cqc']}/5** Quests\nEXP: **{c['exp']:,}**xp\nFame: **{c['fame']:,}** <:fame:682209281722024044>\nLevel: **{c['level']}**\nStats " \
                       f"Maxed: " \
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
                embed.add_field(name="Stats:", value="Stats other than HP/MP are currently broken on realmeye!", inline=False)
                # embed.add_field(name="More Stats:", value=stat_s_2)
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


    @commands.command(usage='djoke', description="This command doesn't exist..... Shh...")
    @commands.guild_only()
    @commands.check_any(commands.is_owner(), commands.has_permissions(administrator=True))
    async def djoke(self, ctx):
        joke = utils.darkjoke()
        embed = discord.Embed(title=joke[0], description=joke[1])
        await ctx.send(embed=embed)

    @commands.command(usage='roast <member>', description="This command doesn't exist either")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def roast(self, ctx, member: utils.MemberLookupConverter):
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        if member.id == 368449521224515585:
            embed = discord.Embed(title='patreon.com/preed', description="Support preed's quest to max his scale out!", url='https://www.patreon.com/preed')
        else:
            roast = utils.get_roast()
            embed = discord.Embed(title=roast)
        await ctx.send(content=member.mention, embed=embed)

    @commands.command(usage='bubblewrap', description="Relieve some stress if that's your thing...")
    async def bubblewrap(self, ctx):
        await ctx.send("||💥||||💥||||💥||||💥||||💥||\n||💥||||💥||||💥||||💥||||💥||\n||💥||||💥||||💥||||💥||||💥||\n||💥||||💥||||💥||||💥||||💥||\n"
                       "||💥||||💥||||💥||||💥||||💥||\n||💥||||💥||||💥||||💥||||💥||")


    @commands.command(usage='ghostping <member>', description='shhh')
    @commands.check_any(commands.is_owner(), commands.has_permissions(administrator=True))
    @commands.guild_only()
    @commands.max_concurrency(1, per=BucketType.guild)
    @commands.cooldown(1, 3600, type=BucketType.member)
    async def ghostping(self, ctx, member: utils.MemberLookupConverter):
        for channel in ctx.guild.text_channels:
            permissions: discord.Permissions = channel.permissions_for(member)
            if permissions.send_messages:
                await channel.send(member.mention, delete_after=1)


    @commands.command(usage='listrole <role>', description='Mentions everyone with a role')
    @commands.is_owner()
    @commands.guild_only()
    async def listrole(self, ctx, *, role: discord.Role):
        num = 0
        mlist = [role.members[i:i+80] for i in range(0, len(role.members), 80)]
        for members in mlist:
            str = ""
            for mem in members:
                str += mem.mention
            await ctx.send(str)
            num += 1
        await ctx.send(f"Done listing members! (in {num} messages)")

    @commands.command(usage='poll <title> [option 1] [option 2] [option 3]...',
                      description="Creates a poll with up to 2-10 options\n"
                                  "For options/titles with more than one word, surround the text with quotes.")
    @commands.guild_only()
    @commands.check_any(is_rl_or_higher_check(), is_bot_owner())
    async def poll(self, ctx, title, *options):
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        if len(options) < 2:
            options = ["Yes", "No"]
        if len(options) > 10:
            await ctx.send("Please specify at most 10 options for the poll.", delete_after=4)
            return

        embed = embeds.poll(title, options)  # Get poll embed
        msg = await ctx.send(embed=embed)
        for i in range(len(options)):  # add reactions to poll
            await msg.add_reaction(self.numbers[i])
        # TODO: Implement counter, add check to only allow reactions to 1 option (remove all but last react from each person)
        # TODO: add option to ping @here or @everyone

    @commands.command(usage="ooga <text>", description="Translate text into booga.")
    @commands.guild_only()
    @commands.cooldown(1, 300, type=BucketType.member)
    async def ooga(self, ctx, *, text):
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        if len(text) > 52:
            return await ctx.send("Please send a message 50 characters or less.")

        if not all(ord(c) < 128 for c in text):
            return await ctx.send("Please only use alphanumeric characters!")

        str = ' '.join(["{0:b}".format(x) for x in bytes(text, "ascii")])
        obs = []
        for c in str.split(" "):
            cs = []
            for b in c:
                if b == '0':
                    cs.append("Ooga")
                else:
                    cs.append("Booga")
            obs.append(" ".join(cs))

        embed = discord.Embed(title=f"Oogified text | Decode with {ctx.prefix}booga <encoded_text>", description=" - ".join(obs), color=discord.Color.teal())
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @commands.command(usage='booga <encoded_text>', description='Decode booga text.')
    @commands.guild_only()
    async def booga(self, ctx, *, text):
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        bs = ""
        for s in text.split(" - "):
            for c in s.split(" "):
                if c == "Ooga":
                    bs += "0"
                else:
                    bs += "1"
            bs += " "
        try:
            await ctx.author.send(f"Decoded text:\n{''.join([chr(int(binary, 2)) for binary in bs.split(' ') if binary])}")
            await ctx.send(embed=discord.Embed(description="The decoded text has been sent to your DM's!"))
        except discord.Forbidden:
            await ctx.send("Please enable DM's to use this command!")


    @commands.command(usage='isgay <member>', description="Preed's Custom Patreon Command")
    async def isgay(self, ctx, member: utils.MemberLookupConverter):
        if member.id == self.client.user.id:
            await ctx.send(f"Preed's Custom Patreon Command!\n__{member.display_name}__: Hmm, I don't think so...")

        isG = member.id % 10 > 3
        if isG:
            b = member.id % 10 % 2 == 1
            b2 = member.id % 10 % 4 == 1
            d = f"🌈__{member.display_name}__🌈: I've never been so sure of anything." if b and b2 else f"🌈__{member.display_name}__🌈: Yes." if b else \
                f"__{member.display_name}__: I'm pretty sure."
        else:
            d = f"__{member.display_name}__: Hmm, I don't think so..."
        await ctx.send(f"Preed's Custom Patreon Command!\n{d}")


    @commands.command(usage='unbean <member>', description="Lorlie's Custom Patreon Command")
    @commands.guild_only()
    @commands.check_any(is_lorlie(), is_rl_and_not_beaned())
    async def unbean(self, ctx, member: utils.MemberLookupConverter):
        if (member.id, ctx.guild.id) not in self.client.beaned_ids:
            return await ctx.send(f"{member.display_name}__ is not currently Beaned!")

        self.client.beaned_ids.remove((member.id, ctx.guild.id))
        await ctx.send(f"Lorlie's Custom Patreon Command!\n__{member.display_name}__ was Un-Beaned!")


def setup(client):
    client.add_cog(Misc(client))

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
            id = id if id and str(id) in definition else -99 if id else -1
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

