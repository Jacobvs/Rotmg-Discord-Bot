import asyncio

import discord

import sql


class VCSelect:
    def __init__(self, client, ctx, headcount=False, lock=False, unlock=False, clean=False, parse=False, log=False, manual_log=False, qafk=False, change_limit=False):
        self.client = client
        self.ctx = ctx
        self.headcount = headcount
        self.parse = parse
        title = "Headcount Setup" if headcount else "Lock Selection" if lock else "Unlock Selection" if unlock else "Cleaning Selection" if\
            clean else "Parsing Setup" if parse else "Key Pop Announcement" if log else "Manual Run Log Setup" if manual_log else "User Limit Selection" if change_limit \
            else "AFK-Check Setup"
        description = "Please choose what channel you'd like to start this headcount in." if headcount else\
            "Please choose which channel you'd like to lock." if lock else "Please choose which channel you'd like to unlock." if unlock\
            else "Please choose which channel you'd like to clean." if clean else "Please choose which channel you'd like to parse for." if\
            parse else "Please choose which channel to announce the key pop in." if log else\
            "Please choose the channel you did your run in." if manual_log else "Please choose which channel to change the user-limit for." if change_limit\
            else "Please choose what channel you'd like to start this afk check in."
        self.locationembed = discord.Embed(title=title,
                                           description=description,
                                           color=discord.Color.green())
        self.guild_db = self.client.guild_db.get(self.ctx.guild.id)
        self.inraiding = False
        self.invet = False
        self.inevents = False


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
            if one or two or three or four:
                self.inraiding = True

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
            if one or two or three or four:
                self.invet = True
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
            if one or two or three or four:
                self.inevents = True
            self.locationembed.add_field(name="Available Channels:", value=s)
            self.setup_msg = await self.ctx.send(embed=self.locationembed)
            for e in emojis:
                await self.setup_msg.add_reaction(e)
        else:
            return await self.ctx.send("You need to use this command in a proper bot-commands channel!", delete_after=5)


        def location_check(react, usr):
            return usr == self.ctx.author and react.message.id == self.setup_msg.id and react.emoji in ['1️⃣', '2️⃣', '3️⃣', '4️⃣']


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
                else:
                    self.raidnum = 3
                    self.hcchannel = self.guild_db.get(sql.gld_cols.raidhc4)
                    self.vcchannel = self.guild_db.get(sql.gld_cols.raidvc4)
            elif self.invet:
                self.raiderrole = self.guild_db.get(sql.gld_cols.vetroleid)
                self.rlrole = self.guild_db.get(sql.gld_cols.vetrlroleid)
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
                else:
                    self.raidnum = 3
                    self.hcchannel = self.guild_db.get(sql.gld_cols.vethc4)
                    self.vcchannel = self.guild_db.get(sql.gld_cols.vetvc4)
            elif self.inevents:
                self.raiderrole = self.guild_db.get(sql.gld_cols.eventraiderroleid) if self.guild_db.get(sql.gld_cols.eventraiderroleid) else\
                    self.guild_db.get(sql.gld_cols.raiderroleid)
                self.rlrole = self.guild_db.get(sql.gld_cols.eventrlid)
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
                else:
                    self.raidnum = 3
                    self.hcchannel = self.guild_db.get(sql.gld_cols.eventhc4)
                    self.vcchannel = self.guild_db.get(sql.gld_cols.eventvc4)

            await self.setup_msg.clear_reactions()

            return (self.raidnum, self.inraiding, self.invet, self.inevents, self.raiderrole, self.rlrole, self.hcchannel, self.vcchannel,
                    self.setup_msg)

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