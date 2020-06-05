import asyncio

import discord

import sql


class VCSelect:
    def __init__(self, client, ctx, headcount=False, lock=False, unlock=False, clean=False, parse=False):
        self.client = client
        self.ctx = ctx
        self.headcount = headcount
        title = "Headcount Setup" if headcount else "Lock Selection" if lock else "Unlock Selection" if unlock else "Cleaning Selection" if\
            clean else "Parsing Setup" if parse else "AFK-Check Setup"
        description = "Please choose what channel you'd like to start this headcount in." if headcount else\
            "Please choose which channel you'd like to lock." if lock else "Please choose which channel you'd like to unlock." if unlock\
            else "Please choose which channel you'd like to clean." if clean else "Please choose which channel you'd like to parse for." if\
                parse else "Please choose what channel you'd like to start this afk check in."
        self.locationembed = discord.Embed(title=title,
                                           description=description,
                                           color=discord.Color.green())
        self.guild_db = self.client.guild_db.get(self.ctx.guild.id)
        self.inraiding = False
        self.invet = False
        self.inevents = False


    async def start(self):
        await self.ctx.message.delete()

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
            if one or two or three:
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
                self.invet = True
            two = self.guild_db.get(sql.gld_cols.vetvc2)
            if two:
                s += "2️⃣ - " + two.name + "\n"
                emojis.append("2️⃣")
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
                self.inevents = True
            two = self.guild_db.get(sql.gld_cols.eventvc2)
            if two:
                s += "2️⃣ - " + two.name + "\n"
                emojis.append("2️⃣")
                self.inevents = True
            self.locationembed.add_field(name="Available Channels:", value=s)
            self.setup_msg = await self.ctx.send(embed=self.locationembed)
            for e in emojis:
                await self.setup_msg.add_reaction(e)
        else:
            return await self.ctx.send("You need to use this command in a proper bot-commands channel!", delete_after=5)


        def location_check(react, usr):
            return usr == self.ctx.author and react.message.id == self.setup_msg.id and react.emoji in ['1️⃣', '2️⃣', '3️⃣']


        try:
            reaction, user = await self.client.wait_for('reaction_add', timeout=60, check=location_check)
        except asyncio.TimeoutError:
            embed = discord.Embed(title="Timed out!", description="You didn't choose a channel in time!", color=discord.Color.red())
            await self.setup_msg.clear_reactions()
            return await self.setup_msg.edit(embed=embed)

        if self.inraiding:
            self.raiderrole = self.guild_db.get(sql.gld_cols.raiderroleid)
            self.rlrole = self.guild_db.get(sql.gld_cols.rlroleid)
            if reaction.emoji == "1️⃣":
                self.raidnum = 0
                self.hcchannel = self.guild_db.get(sql.gld_cols.raidhc1)
                self.vcchannel = self.guild_db.get(sql.gld_cols.raidvc1)
                self.client.raid_db[self.ctx.guild.id]["raiding"][0] = self
            elif reaction.emoji == "2️⃣":
                self.raidnum = 1
                self.hcchannel = self.guild_db.get(sql.gld_cols.raidhc2)
                self.vcchannel = self.guild_db.get(sql.gld_cols.raidvc2)
                self.client.raid_db[self.ctx.guild.id]["raiding"][1] = self
            else:
                self.raidnum = 2
                self.hcchannel = self.guild_db.get(sql.gld_cols.raidhc3)
                self.vcchannel = self.guild_db.get(sql.gld_cols.raidvc3)
                self.client.raid_db[self.ctx.guild.id]["raiding"][2] = self
        elif self.invet:
            self.raiderrole = self.guild_db.get(sql.gld_cols.vetroleid)
            self.rlrole = self.guild_db.get(sql.gld_cols.vetrlroleid)
            if reaction.emoji == "1️⃣":
                self.raidnum = 0
                self.hcchannel = self.guild_db.get(sql.gld_cols.vethc1)
                self.vcchannel = self.guild_db.get(sql.gld_cols.vetvc1)
                self.client.raid_db[self.ctx.guild.id]["vet"][0] = self
            elif reaction.emoji == "2️⃣":
                self.raidnum = 1
                self.hcchannel = self.guild_db.get(sql.gld_cols.vethc2)
                self.vcchannel = self.guild_db.get(sql.gld_cols.vetvc2)
                self.client.raid_db[self.ctx.guild.id]["vet"][1] = self
        elif self.inevents:
            self.raiderrole = self.guild_db.get(sql.gld_cols.raiderroleid)
            self.rlrole = self.guild_db.get(sql.gld_cols.eventrlid)
            if reaction.emoji == "1️⃣":
                self.raidnum = 0
                self.hcchannel = self.guild_db.get(sql.gld_cols.eventhc1)
                self.vcchannel = self.guild_db.get(sql.gld_cols.eventvc1)
                self.client.raid_db[self.ctx.guild.id]["events"][0] = self
            elif reaction.emoji == "2️⃣":
                self.raidnum = 1
                self.hcchannel = self.guild_db.get(sql.gld_cols.eventhc2)
                self.vcchannel = self.guild_db.get(sql.gld_cols.eventvc2)
                self.client.raid_db[self.ctx.guild.id]["events"][1] = self

        await self.setup_msg.clear_reactions()

        return (self.raidnum, self.inraiding, self.invet, self.inevents, self.raiderrole, self.rlrole, self.hcchannel, self.vcchannel,
                self.setup_msg)
