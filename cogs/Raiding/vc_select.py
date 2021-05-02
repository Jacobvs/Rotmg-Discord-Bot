import asyncio

import discord

import sql


class VCSelect:

    letters = ['🇦', '🇧', '🇨', '🇩', '🇪', '🇫', '🇬', '🇭', '🇮', '🇯', '🇰', '🇱', '🇲', '🇳', '🇴', '🇵', '🇶', '🇷', '🇸', '🇹', '🇺', '🇻', '🇼', '🇽', '🇾', '🇿']

    def __init__(self, client, ctx, headcount=False, lock=False, unlock=False, clean=False, parse=False, log=False, manual_log=False, qafk=False, change_limit=False):
        self.client = client
        self.ctx = ctx
        self.headcount = headcount
        self.parse = parse
        self.non_creation = lock or unlock or clean or parse or log or manual_log or change_limit
        title = "Headcount Setup" if headcount else "Lock Selection" if lock else "Unlock Selection" if unlock else "Cleaning Selection" if\
            clean else "Parsing Setup" if parse else "Key Pop Announcement" if log else "Manual Run Log Setup" if manual_log else "User Limit Selection" if change_limit \
            else "AFK-Check Setup"
        description = "Please choose what channel you'd like to start this headcount in." if headcount else\
            "Please choose which channel you'd like to lock." if lock else "Please choose which channel you'd like to unlock." if unlock\
            else "Please choose which channel you'd like to clean." if clean else "Please choose which channel you'd like to parse for." if\
            parse else "Please choose which channel to announce the key pop in." if log else\
            "Please choose the channel you did your run in." if manual_log else "Please choose which channel to change the user-limit for." if change_limit\
            else "Please choose what channel you'd like to start this afk check in."
        if not self.non_creation:
            description += "\nPress 🆕 to create a temporary channel!"
        self.locationembed = discord.Embed(title=title,
                                           description=description,
                                           color=discord.Color.green())
        self.guild_db = self.client.guild_db.get(self.ctx.guild.id)
        self.inraiding = False
        self.invet = False
        self.inevents = False
        self.hcchannel = None
        self.vcchannel = None
        self.raidnum = None


    async def start(self):
        if not self.parse:
            try:
                await self.ctx.message.delete()
            except discord.NotFound:
                pass

        if self.ctx.channel == self.guild_db.get(sql.gld_cols.raidcommandschannel):
            s = ""
            emojis = []
            one = self.guild_db.get(sql.gld_cols.raidvc1)
            if one:
                s += "1️⃣ - " + one.name + "\n"
                emojis.append("1️⃣")
            two = self.guild_db.get(sql.gld_cols.raidvc2)
            if two:
                s += "2️⃣ - " + two.name + "\n"
                emojis.append("2️⃣")
            three = self.guild_db.get(sql.gld_cols.raidvc3)
            if three:
                s += "3️⃣ - " + three.name + "\n"
                emojis.append("3️⃣")
            four = self.guild_db.get(sql.gld_cols.raidvc4)
            if four:
                s += "4️⃣ - " + four.name + "\n"
                emojis.append("4️⃣")
            five = self.guild_db.get(sql.gld_cols.raidvc5)
            if five:
                s += "5️⃣ - " + five.name + "\n"
                emojis.append("5️⃣")
            six = self.guild_db.get(sql.gld_cols.raidvc6)
            if six:
                s += "6️⃣ - " + six.name + "\n"
                emojis.append("6️⃣")

            self.inraiding = True
            if one:
                self.add_temp_channel_selectors(one, emojis)
            if not self.non_creation:
                emojis.append("🆕")

            self.locationembed.add_field(name="Available Channels:", value=s)
            self.setup_msg = await self.ctx.send(embed=self.locationembed)
            for e in emojis:
                await self.setup_msg.add_reaction(e)
        elif self.ctx.channel == self.guild_db.get(sql.gld_cols.vetcommandschannel):
            s = ""
            emojis = []
            one = self.guild_db.get(sql.gld_cols.vetvc1)
            if one:
                s += "1️⃣ - " + one.name + "\n"
                emojis.append("1️⃣")
            two = self.guild_db.get(sql.gld_cols.vetvc2)
            if two:
                s += "2️⃣ - " + two.name + "\n"
                emojis.append("2️⃣")
            three = self.guild_db.get(sql.gld_cols.vetvc3)
            if three:
                s += "3️⃣ - " + three.name + "\n"
                emojis.append("3️⃣")
            four = self.guild_db.get(sql.gld_cols.vetvc4)
            if four:
                s += "4️⃣ - " + four.name + "\n"
                emojis.append("4️⃣")

            self.invet = True
            if one:
                s += self.add_temp_channel_selectors(one, emojis)
            if not self.non_creation:
                emojis.append("🆕")

            self.locationembed.add_field(name="Available Channels:", value=s)
            self.setup_msg = await self.ctx.send(embed=self.locationembed)
            for e in emojis:
                await self.setup_msg.add_reaction(e)
        elif self.ctx.channel == self.guild_db.get(sql.gld_cols.eventcommandschannel):
            s = ""
            emojis = []
            one = self.guild_db.get(sql.gld_cols.eventvc1)
            if one:
                s += "1️⃣ - " + one.name + "\n"
                emojis.append("1️⃣")
            two = self.guild_db.get(sql.gld_cols.eventvc2)
            if two:
                s += "2️⃣ - " + two.name + "\n"
                emojis.append("2️⃣")
            three = self.guild_db.get(sql.gld_cols.eventvc3)
            if three:
                s += "3️⃣ - " + three.name + "\n"
                emojis.append("3️⃣")
            four = self.guild_db.get(sql.gld_cols.eventvc4)
            if four:
                s += "4️⃣ - " + four.name + "\n"
                emojis.append("4️⃣")

            self.inevents = True
            if one:
                self.add_temp_channel_selectors(one, emojis)
            if not self.non_creation:
                emojis.append("🆕")

            self.locationembed.add_field(name="Available Channels:", value=s)
            self.setup_msg = await self.ctx.send(embed=self.locationembed)
            for e in emojis:
                await self.setup_msg.add_reaction(e)
        else:
            return await self.ctx.send("You need to use this command in a proper bot-commands channel!", delete_after=5)


        def location_check(react, usr):
            return usr == self.ctx.author and react.message.id == self.setup_msg.id and \
                   (react.emoji in ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣'] or react.emoji in self.letters or react.emoji == '🆕')

        try:
            reaction, user = await self.client.wait_for('reaction_add', timeout=60, check=location_check)
        except asyncio.TimeoutError:
            try:
                if self.ctx.author.id in self.client.raid_db[self.ctx.guild.id]['leaders']:
                    self.client.raid_db[self.ctx.guild.id]['leaders'].remove(self.ctx.author.id)
                embed = discord.Embed(title="Timed out!", description="You didn't choose a channel in time!", color=discord.Color.red())
                await self.setup_msg.clear_reactions()
                return await self.setup_msg.edit(embed=embed)

            except discord.NotFound:
                await self.ctx.send("Timed out while selecting channel.")
        else:
            if self.inraiding:
                self.raiderrole = self.guild_db.get(sql.gld_cols.raiderroleid)
                self.rlrole = self.guild_db.get(sql.gld_cols.rlroleid)
            elif self.invet:
                self.raiderrole = self.guild_db.get(sql.gld_cols.vetroleid)
                self.rlrole = self.guild_db.get(sql.gld_cols.vetrlroleid)
            elif self.inevents:
                self.raiderrole = self.guild_db.get(sql.gld_cols.eventraiderroleid) if self.guild_db.get(sql.gld_cols.eventraiderroleid) else\
                    self.guild_db.get(sql.gld_cols.raiderroleid)
                self.rlrole = self.guild_db.get(sql.gld_cols.eventrlid)

            if self.inraiding:
                if reaction.emoji == "1️⃣":
                    self.raidnum = 0
                    self.hcchannel = self.guild_db.get(sql.gld_cols.raidhc1)
                    self.vcchannel = self.guild_db.get(sql.gld_cols.raidvc1)
                elif reaction.emoji == "2️⃣":
                    self.raidnum = 1
                    self.hcchannel = self.guild_db.get(sql.gld_cols.raidhc2)
                    self.vcchannel = self.guild_db.get(sql.gld_cols.raidvc2)
                elif reaction.emoji == "3️⃣":
                    self.raidnum = 2
                    self.hcchannel = self.guild_db.get(sql.gld_cols.raidhc3)
                    self.vcchannel = self.guild_db.get(sql.gld_cols.raidvc3)
                elif reaction.emoji == "4️⃣":
                    self.raidnum = 3
                    self.hcchannel = self.guild_db.get(sql.gld_cols.raidhc4)
                    self.vcchannel = self.guild_db.get(sql.gld_cols.raidvc4)
                elif reaction.emoji == "5️⃣":
                    self.raidnum = 4
                    self.hcchannel = self.guild_db.get(sql.gld_cols.raidhc5)
                    self.vcchannel = self.guild_db.get(sql.gld_cols.raidvc5)
                elif reaction.emoji in self.letters:
                    self.hcchannel = self.guild_db.get(sql.gld_cols.raidhc1)
                    self.raidnum = (self.letters.index(reaction.emoji)+65) * -1
                    raid_string = "Raiding - " + chr(self.raidnum*-1)
                    self.vcchannel = next(c for c in self.hcchannel.category.voice_channels if c.name == raid_string)
                elif reaction.emoji == '🆕' and not self.non_creation:
                    self.hcchannel = self.guild_db.get(sql.gld_cols.raidhc1)
                    num, vc = await self.create_temp_vc(self.guild_db.get(sql.gld_cols.raidvc1))
                    self.raidnum = num
                    self.vcchannel = vc
                else:
                    self.raidnum = 5
                    self.hcchannel = self.guild_db.get(sql.gld_cols.raidhc6)
                    self.vcchannel = self.guild_db.get(sql.gld_cols.raidvc6)

            elif self.invet:
                if reaction.emoji == "1️⃣":
                    self.raidnum = 0
                    self.hcchannel = self.guild_db.get(sql.gld_cols.vethc1)
                    self.vcchannel = self.guild_db.get(sql.gld_cols.vetvc1)
                elif reaction.emoji == "2️⃣":
                    self.raidnum = 1
                    self.hcchannel = self.guild_db.get(sql.gld_cols.vethc2)
                    self.vcchannel = self.guild_db.get(sql.gld_cols.vetvc2)
                elif reaction.emoji == "3️⃣":
                    self.raidnum = 2
                    self.hcchannel = self.guild_db.get(sql.gld_cols.vethc3)
                    self.vcchannel = self.guild_db.get(sql.gld_cols.vetvc3)
                elif reaction.emoji in self.letters:
                    self.hcchannel = self.guild_db.get(sql.gld_cols.vethc1)
                    self.raidnum = (self.letters.index(reaction.emoji)+65) * -1
                    raid_string = "Raiding - " + chr(self.raidnum*-1)
                    self.vcchannel = next(c for c in self.hcchannel.category.voice_channels if c.name == raid_string)
                elif reaction.emoji == '🆕' and not self.non_creation:
                    self.hcchannel = self.guild_db.get(sql.gld_cols.vethc1)
                    num, vc = await self.create_temp_vc(self.guild_db.get(sql.gld_cols.vetvc1))
                    self.raidnum = num
                    self.vcchannel = vc
                else:
                    self.raidnum = 3
                    self.hcchannel = self.guild_db.get(sql.gld_cols.vethc4)
                    self.vcchannel = self.guild_db.get(sql.gld_cols.vetvc4)
            elif self.inevents:
                if reaction.emoji == "1️⃣":
                    self.raidnum = 0
                    self.hcchannel = self.guild_db.get(sql.gld_cols.eventhc1)
                    self.vcchannel = self.guild_db.get(sql.gld_cols.eventvc1)
                elif reaction.emoji == "2️⃣":
                    self.raidnum = 1
                    self.hcchannel = self.guild_db.get(sql.gld_cols.eventhc2)
                    self.vcchannel = self.guild_db.get(sql.gld_cols.eventvc2)
                elif reaction.emoji == "3️⃣":
                    self.raidnum = 2
                    self.hcchannel = self.guild_db.get(sql.gld_cols.eventhc3)
                    self.vcchannel = self.guild_db.get(sql.gld_cols.eventvc3)
                elif reaction.emoji in self.letters:
                    self.hcchannel = self.guild_db.get(sql.gld_cols.eventhc1)
                    self.raidnum = (self.letters.index(reaction.emoji)+65) * -1
                    raid_string = "Raiding - " + chr(self.raidnum*-1)
                    self.vcchannel = next(c for c in self.hcchannel.category.voice_channels if c.name == raid_string)
                elif reaction.emoji == '🆕' and not self.non_creation:
                    self.hcchannel = self.guild_db.get(sql.gld_cols.eventhc1)
                    num, vc = await self.create_temp_vc(self.guild_db.get(sql.gld_cols.eventvc1))
                    self.raidnum = num
                    self.vcchannel = vc
                else:
                    self.raidnum = 3
                    self.hcchannel = self.guild_db.get(sql.gld_cols.eventhc4)
                    self.vcchannel = self.guild_db.get(sql.gld_cols.eventvc4)

            await self.setup_msg.clear_reactions()

            return (self.raidnum, self.inraiding, self.invet, self.inevents, self.raiderrole, self.rlrole, self.hcchannel, self.vcchannel,
                    self.setup_msg)

    def add_temp_channel_selectors(self, hcchannel, emoji_list):
        # if non creation action, look through cat vc's for letter raid channels --- append emojis for each in list....
        s = ""
        for c in hcchannel.category.voice_channels:
            if "Raiding -" in c.name:
                if len(emoji_list) < 19:
                    emoji_list.append(self.letters[ord(c.name.split(" - ")[1]) - 65]) # get decimal rep. of letter, subtract 65 (uppercase), use index to retrieve letter emoji
                    s += f'{self.letters[ord(c.name.split(" - ")[1]) - 65]} - {c.name}'
                else:
                    break
        return s

    async def create_temp_vc(self, clone_vc: discord.VoiceChannel):
        largest_lett = 64
        for c in self.hcchannel.category.voice_channels:
            if "Raiding -" in c.name:
                if ord(c.name.split(" - ")[1]) > largest_lett:
                    largest_lett = ord(c.name.split(" - ")[1])

        largest_lett += 1
        raidnum = largest_lett * -1
        vcchannel = await self.hcchannel.category.create_voice_channel(name=f'Raiding - {chr(largest_lett)}', overwrites=clone_vc.overwrites, user_limit=clone_vc.user_limit)
        return raidnum, vcchannel

    async def q_start(self):
        await self.ctx.message.delete()
        if self.ctx.channel == self.guild_db.get(sql.gld_cols.raidcommandschannel):
            raiderrole = self.guild_db.get(sql.gld_cols.raiderroleid)
            rlrole = self.guild_db.get(sql.gld_cols.rlroleid)
            hcchannel = self.guild_db.get(sql.gld_cols.raidhc1)
        elif self.ctx.channel == self.guild_db.get(sql.gld_cols.vetcommandschannel):
            raiderrole = self.guild_db.get(sql.gld_cols.vetroleid)
            rlrole = self.guild_db.get(sql.gld_cols.vetrlroleid)
            hcchannel = self.guild_db.get(sql.gld_cols.vethc1)
        elif self.ctx.channel == self.guild_db.get(sql.gld_cols.eventcommandschannel):
            raiderrole = self.guild_db.get(sql.gld_cols.raiderroleid)
            rlrole = self.guild_db.get(sql.gld_cols.eventrlid)
            hcchannel = self.guild_db.get(sql.gld_cols.eventhc1)
        else:
            return await self.ctx.send("You need to use this command in a proper bot-commands channel!", delete_after=5)

        return (raiderrole, rlrole, hcchannel)