import asyncio
import functools
import io
import re
from difflib import get_close_matches

import cv2
import discord
import numpy as np
from discord.ext import commands
from pytesseract import pytesseract

import sql
import utils


class ParseLog:

    def __init__(self, client, author, channel, guild, required_items, runtitle, all_members, members_left, rlrole, hcchannel):
        self.client = client
        self.author = author
        self.channel = channel
        self.guild = guild
        self.required_items = required_items
        self.run_title = runtitle
        self.all_members = all_members
        self.members_left = members_left
        self.rlrole = rlrole
        self.hcchannel = hcchannel

        self.confirmedLogs = []
        self.numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', "🔟"]
        self.converter = utils.MemberLookupConverter()

        self.startembed = discord.Embed(title=f"Log this Run: {author.display_name}", description="Press the 📝 reaction when you **finish** the run to log it in the "
                                        "database.\n\nTo cancel logging if you ***didn't do the run***, press the 🗑️",
                                        color=discord.Color.gold())
        self.runstatusembed = discord.Embed(title=f"Run Status: {author.display_name}", description="Was the run successful? If so, react to the ✅ emoji, otherwise react to the "
                                            "❌ emoji.", color=discord.Color.gold())
        self.otheremebed = discord.Embed(title=f"Log Other member {author.display_name}", description="Please log who popped.\nType their __ROTMG IGN__, __Mention them__, "
                                         "or paste their __Discord ID__.", color=discord.Color.gold())


    async def start(self):
        self.msg = await self.channel.send(content=self.author.mention, embed=self.startembed)
        await self.msg.add_reaction("📝")
        await self.msg.add_reaction("🗑️")

        def check(payload):
            return payload.user_id == self.author.id and payload.message_id == self.msg.id and (str(payload.emoji) == "📝" or str(payload.emoji) == '🗑️')

        try:
            payload = await self.client.wait_for('raw_reaction_add', check=check, timeout=7000)  # Wait
        except asyncio.TimeoutError:
            if self.author.id in self.client.raid_db[self.guild.id]['leaders']:
                self.client.raid_db[self.guild.id]['leaders'].remove(self.author.id)
            embed = discord.Embed(title="Timed out!", description="You didn't log this run in time!", color=discord.Color.red())
            try:
                await self.msg.clear_reactions()
                return await self.msg.edit(embed=embed)
            except discord.NotFound:
                print("NOT FOUND WHEN LOGGING AWAIT")
                return
        else:

            if str(payload.emoji) == '🗑️':
                if self.author.id in self.client.raid_db[self.guild.id]['leaders']:
                    self.client.raid_db[self.guild.id]['leaders'].remove(self.author.id)
                embed = discord.Embed(title="Cancelled!", description=f"{self.author.mention} cancelled this log.",
                                      color=discord.Color.red())
                await self.msg.clear_reactions()
                return await self.msg.edit(embed=embed)


        # Log rune pops
        if self.run_title == "Oryx 3" or self.run_title == 'Vet Oryx 3':
            desc = ""
            descript = ""
            if '<:swordrune:737672554482761739>' in self.required_items:
                swordreacts = self.required_items['<:swordrune:737672554482761739>']['confirmed']
                if swordreacts:
                    for i, r in enumerate(swordreacts):
                        desc += self.numbers[i] + f" - {r.mention}\n"
                    descript = f"Users who confirmed sword rune (<:swordrune:737672554482761739>) with the bot:\n" + desc + "\n"
                descript += "Click the 🔄 to enter who popped. If you don't know, hit the ❌."
                embed = discord.Embed(title="Sword Rune Pop", description=descript, color=discord.Color.gold())
                await self.memberlog(embed, swordreacts, sql.log_cols.swordrunes, '<:swordrune:737672554482761739>')
                desc = ""
                descript = ""
            if '<:shieldrune:737672554642276423>' in self.required_items:
                shieldreacts = self.required_items['<:shieldrune:737672554642276423>']['confirmed']
                if shieldreacts:
                    for i, r in enumerate(shieldreacts):
                        desc += self.numbers[i] + f" - {r.mention}\n"
                    descript = f"Users who confirmed shield rune (<:shieldrune:737672554642276423>) with the bot:\n" + desc + "\n"
                descript += "Click the 🔄 to enter who popped. If you don't know, hit the ❌."
                embed = discord.Embed(title="Shield Rune Pop", description=descript, color=discord.Color.gold())
                await self.memberlog(embed, shieldreacts, sql.log_cols.shieldrunes, '<:shieldrune:737672554642276423>')
                desc = ""
                descript = ""
            if '<:helmrune:737673058722250782>' in self.required_items:
                helmreacts = self.required_items['<:helmrune:737673058722250782>']['confirmed']
                if helmreacts:
                    for i, r in enumerate(helmreacts):
                        desc += self.numbers[i] + f" - {r.mention}\n"
                    descript = f"Users who confirmed helm rune (<:helmrune:737673058722250782>) with the bot:\n" + desc + "\n"
                descript += "Click the 🔄 to enter who popped. If you don't know, hit the ❌."
                embed = discord.Embed(title="Helm Rune Pop", description=descript, color=discord.Color.gold())
                await self.memberlog(embed, helmreacts, sql.log_cols.helmrunes, '<:helmrune:737673058722250782>')


        embed = discord.Embed(title=f"Member Completion: {self.author.display_name}", description="Please send a screenshot containing **only** the /who of members which "
                                    "completed the raid.\n\nIf you don't have a screenshot and a raider cannot take one either - send `SKIP`")
        await self.msg.clear_reactions()
        await self.msg.edit(embed=embed)

        def member_check(m):
            return m.author == self.author and m.channel == self.channel

        members = []
        while True:
            try:
                msg = await self.client.wait_for('message', timeout=7200, check=member_check)
            except asyncio.TimeoutError:
                if self.author.id in self.client.raid_db[self.guild.id]['leaders']:
                    self.client.raid_db[self.guild.id]['leaders'].remove(self.author.id)
                embed = discord.Embed(title="Timed out!", description="You didn't choose a member in time!", color=discord.Color.red())
                await self.msg.clear_reactions()
                return await self.msg.edit(embed=embed)

            if 'skip' in msg.content.strip().lower():
                print('skipped')
                members = self.members_left
                break
            else:
                if not msg.attachments:
                    await self.channel.send("Please attach an image containing only the result of the /who command!", delete_after=10)
                    continue
                if len(msg.attachments) > 1:
                    await self.channel.send("Please only attach 1 image.", delete_after=10)
                    continue
                attachment = msg.attachments[0]
                if not ".jpg" in attachment.filename and not ".png" in attachment.filename:
                    await self.channel.send("Please only attach an image of type 'png' or 'jpg'.", delete_after=10)
                    continue
                image = io.BytesIO()
                await attachment.save(image, seek_begin=True)
                pmsg = await self.channel.send("Parsing image. This may take a minute...")
                members = await self.client.loop.run_in_executor(None, functools.partial(parse_image, image, self.all_members))
                print('done parsing image')
                await pmsg.delete()
                if not members:
                    embed = discord.Embed(title="Error!", description="Could not find the /who command in the image you provided.\nPlease send a new message"
                                                                      "with an image that shows the results of `/who`. If you don't have a better image, say `SKIP`.",
                                          color=discord.Color.red())
                    await self.channel.send(embed=embed, delete_after=15)
                    await msg.delete()
                    continue
                converter = utils.MemberLookupConverter()
                _mems = []
                ctx = commands.Context(bot=self.client, prefix="!", guild=self.guild, message=msg)
                for n in members:
                    try:
                        m = await converter.convert(ctx, n)
                        _mems.append(m)
                    except discord.ext.commands.BadArgument:
                        pass
                members = _mems

                embed = discord.Embed(title=f"Member Completion: {self.author.display_name}",
                                      description="Please enter who took this screenshot.")
                await self.msg.edit(embed=embed)

                def member_check(m):
                    return m.author == self.author and m.channel == self.channel

                while True:
                    try:
                        msg = await self.client.wait_for('message', timeout=7200, check=member_check)
                    except asyncio.TimeoutError:
                        if self.author.id in self.client.raid_db[self.guild.id]['leaders']:
                            self.client.raid_db[self.guild.id]['leaders'].remove(self.author.id)
                        embed = discord.Embed(title="Timed out!", description="You didn't choose a member in time!", color=discord.Color.red())
                        await self.msg.clear_reactions()
                        return await self.msg.edit(embed=embed)

                    try:
                        ctx = commands.Context(bot=self.client, prefix="!", guild=self.guild, message=msg)
                        mem = await converter.convert(ctx, msg.content.strip())
                        members.append(mem)
                        break
                    except discord.ext.commands.BadArgument:
                        await self.channel.send(f"The member you specified (`{msg.content}`) was not found.", delete_after=7)
                        continue
                break

        await msg.delete()

        await self.msg.clear_reactions()
        await self.msg.edit(embed=self.runstatusembed)
        await self.msg.add_reaction("✅")
        await self.msg.add_reaction("❌")

        def check(payload):
            return payload.user_id == self.author.id and payload.message_id == self.msg.id and (str(payload.emoji) == "✅" or str(payload.emoji) == "❌")

        try:
            payload = await self.client.wait_for('raw_reaction_add', timeout=7200, check=check)  # Wait 1 hr max
        except asyncio.TimeoutError:
            if self.author.id in self.client.raid_db[self.guild.id]['leaders']:
                self.client.raid_db[self.guild.id]['leaders'].remove(self.author.id)
            embed = discord.Embed(title="Timed out!", description="You didn't log this run in time!", color=discord.Color.red())
            await self.msg.clear_reactions()
            return await self.msg.edit(embed=embed)

        col = sql.log_cols.srunled if str(payload.emoji) == "✅" else sql.log_cols.frunled
        await sql.log_runs(self.client.pool, self.guild.id, self.author.id, col, 1)
        self.confirmedLogs.append(("Run Successful", str(payload.emoji)))

        embed = discord.Embed(title="Logging...", description="Please wait while the run is logged in the database. "
                                                              "This can take up to a minute at full run capacity.", color=discord.Color.orange())
        embed.set_thumbnail(url="https://i.imgur.com/nLRgnZf.gif")
        await self.msg.clear_reactions()
        await self.msg.edit(content=None, embed=embed)

        print(members)
        members.append(self.author)
        for m in members:
            print(type(m))
            print(m)
            if m.top_role >= self.rlrole:
                print('logging rl')
                await sql.log_runs(self.client.pool, self.guild.id, m.id, sql.log_cols.runsassisted, 1)
            await sql.log_runs(self.client.pool, self.guild.id, m.id, sql.log_cols.ocompletes, 1)

        print('done logging 1')

        attempted = 0
        print(self.all_members)
        attempted_members = [m for m in self.all_members if m not in members]
        print(type(attempted_members))
        if attempted_members:
            for m in attempted_members:
                attempted += 1
                await sql.log_runs(self.client.pool, self.guild.id, m.id, sql.log_cols.oattempts, 1)

        print('done logging 2')
        desc = "Log Status:\n"
        for r in self.confirmedLogs:
            desc += r[0] + " - " + str(r[1]) + "\n"
        desc += "Run Leader - " + self.author.mention + "\n"
        desc += f"# Raiders Failed - {attempted}\n"
        desc += f"# Raiders Completed - {len(members)}\n"
        # try:
        #     desc += str(self.confirmedLogs[-1][0]) + " - " + str(self.confirmedLogs[-1][1])
        # except IndexError:
        #     pass
        if self.author.id in self.client.raid_db[self.guild.id]['leaders']:
            self.client.raid_db[self.guild.id]['leaders'].remove(self.author.id)

        embed = discord.Embed(title="Run Logged!", description=desc, color=discord.Color.green())
        await self.msg.edit(embed=embed)



    async def memberlog(self, embed, reacts, column, emoji):
        await self.msg.clear_reactions()
        await self.msg.edit(embed=embed)
        emojis = []
        if reacts:
            if len(reacts) > 5:
                reacts = reacts[:5]
            emojis = self.numbers[:len(reacts)]

        emojis.append("🔄")
        emojis.append("❌")
        asyncio.get_event_loop().create_task(self.add_emojis(self.msg, emojis))

        def check(payload):
            return payload.user_id == self.author.id and payload.message_id == self.msg.id and str(payload.emoji) in emojis

        try:
            payload = await self.client.wait_for('raw_reaction_add', timeout=7000, check=check)  # Wait ~2 hr max
        except asyncio.TimeoutError:
            if self.author.id in self.client.raid_db[self.guild.id]['leaders']:
                self.client.raid_db[self.guild.id]['leaders'].remove(self.author.id)
            embed = discord.Embed(title="Timed out!", description="You didn't log this run in time!", color=discord.Color.red())
            await self.msg.clear_reactions()
            return await self.msg.edit(embed=embed)

        if str(payload.emoji) == '❌':
            return
        elif str(payload.emoji) in self.numbers:
            i = self.numbers.index(str(payload.emoji))
            member = reacts[i]
            if isinstance(member, str):
                member = self.client.get_user(int(member))
        else:
            await self.msg.clear_reactions()
            self.otheremebed.title = f"Log Other member {self.author.display_name} for {emoji}"
            await self.msg.edit(embed=self.otheremebed)

            def member_check(m):
                return m.author == self.author and m.channel == self.channel

            while True:
                try:
                    msg = await self.client.wait_for('message', timeout=7200, check=member_check)
                except asyncio.TimeoutError:
                    if self.author.id in self.client.raid_db[self.guild.id]['leaders']:
                        self.client.raid_db[self.guild.id]['leaders'].remove(self.author.id)
                    embed = discord.Embed(title="Timed out!", description="You didn't choose a member in time!", color=discord.Color.red())
                    await self.msg.clear_reactions()
                    return await self.msg.edit(embed=embed)

                try:
                    ctx = commands.Context(bot=self.client, prefix="!", guild=self.guild, message=msg)
                    member = await self.converter.convert(ctx, str(msg.content))
                    try:
                        await msg.delete()
                    except discord.NotFound:
                        pass
                    break
                except discord.ext.commands.BadArgument:
                    await self.channel.send(f"The member you specified (`{msg.content}`) was not found.", delete_after=7)


        num = await sql.log_runs(self.client.pool, self.guild.id, member.id, column, 1)
        # if emoji == self.emojis[1] and not self.events and str(emoji) != '<:WineCellarInc:708191799750950962>':
        #     await utils.check_pops(self.client, member, self.numruns, num, guild=self.guild, emoji=emoji, type='key', hcchannel=self.hcchannel)
        if emoji == "<:helmrune:737673058722250782>":
            await utils.check_pops(self.client, member, 1, num, guild=self.guild, emoji=emoji, type='helm', hcchannel=self.hcchannel)
        elif emoji == "<:shieldrune:737672554642276423>":
            await utils.check_pops(self.client, member, 1, num, guild=self.guild, emoji=emoji, type='shield', hcchannel=self.hcchannel)
        elif emoji == "<:swordrune:737672554482761739>":
            await utils.check_pops(self.client, member, 1, num, guild=self.guild, emoji=emoji, type='sword', hcchannel=self.hcchannel)
        # elif emoji == "<:vial:682205784524062730>":
        #     await utils.check_pops(self.client, member, self.numruns, num, guild=self.guild, emoji=emoji, type='vial', hcchannel=self.hcchannel)

        self.confirmedLogs.append((emoji, f"{member.mention}"))


    async def add_emojis(self, msg, emojis):
        for e in emojis:
            await msg.add_reaction(e)


def parse_image(image, member_list):
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
        return []

    print("INFO - Split String: ")
    print(split_str)

    names = split_str[3].split(", ")
    cleaned_members = {}
    def clean_member(m):
        if " | " in m:
            names = m.split(" | ")
            for i, name in enumerate(names):
                    cleaned_members[clean_name(name)] = m
        else:
            cleaned_members[clean_name(m)] = m

    def clean_name(n):
        return "".join(c for c in n if c.isalpha()).lower()

    for m in member_list:
        if not m.bot:
            clean_member(m.display_name)

    print('done cleaning member names')

    completed = []
    for name in names:
        if " " in name:
            names = name.split(" ")
            name = names[0]
        if name.strip().lower() not in cleaned_members:
            matches = get_close_matches(name.strip().lower(), cleaned_members.keys(), n=1, cutoff=0.65)
            if len(matches) != 0:
                if matches[0] in cleaned_members:
                    completed.append(cleaned_members[matches[0]])
        else:
            completed.append(cleaned_members[name.strip().lower()])

    return completed
