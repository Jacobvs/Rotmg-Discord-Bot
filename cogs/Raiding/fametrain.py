import asyncio
from datetime import datetime

import discord

import embeds
import sql


class FameTrain:

    numbers = ['1️⃣','3️⃣',"🔟","<:12:710641817867124816>"]
    emojis = ["<:fame:682209281722024044>", "<:sorcerer:682214487490560010>", "<:necromancer:682214503106215966>",
              "<:sseal:683815374403141651>", "<:puri:682205769973760001>"]

    def __init__(self, client, ctx, location):
        self.client = client
        self.ctx = ctx
        self.location = location
        self.setting_up = True
        self.world_chosen = False
        self.channel_chosen = False
        self.inraiding = False
        self.invet = False
        self.inevents = False
        self.guild_db = self.client.guild_db.get(self.ctx.guild.id)
        self.raiderids = []
        self.raiderids.append(ctx.author.id)
        self.raidnum = 0
        self.nitroboosters = []
        self.raiderids.append(ctx.author.id)
        self.worldembed = discord.Embed(title="Fame Train AFK",
                                        description="Please choose what world you'd like to start an afk check for.",
                                        color=discord.Color.green())
        self.locationembed = discord.Embed(title="Fame Train AFK",
                                        description="Please choose what channel you'd like to start this afk check in.",
                                        color=discord.Color.green())


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
            mapembed = discord.Embed(title="Timed out!", description="You didn't choose a channel in time!", color=discord.Color.red())
            await self.setup_msg.clear_reactions()
            return await self.setup_msg.edit(embed=mapembed)

        if self.inraiding:
            self.raiderrole = self.guild_db.get(sql.gld_cols.verifiedroleid)
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
            self.raiderrole = self.guild_db.get(sql.gld_cols.verifiedroleid)
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
        await self.setup_msg.edit(embed=self.worldembed)
        for r in self.numbers:
            await self.setup_msg.add_reaction(r)


        def world_check(reaction, user):
            return user == self.ctx.author and reaction.message.id == self.setup_msg.id and str(reaction.emoji) in self.numbers


        try:
            reaction, user = await self.client.wait_for('reaction_add', timeout=60, check=world_check)
        except asyncio.TimeoutError:
            mapembed = discord.Embed(title="Timed out!", description="You didn't choose a world in time!", color=discord.Color.red())
            await self.setup_msg.clear_reactions()
            return await self.setup_msg.edit(embed=mapembed)

        index = self.numbers.index(str(reaction.emoji))
        self.world_num = 1 if index == 0 else 3 if index == 1 else 10 if index == 2 else 12

        await self.setup_msg.delete()
        if " <-- Join!" not in self.vcchannel.name:
            await self.vcchannel.edit(name=self.vcchannel.name + " <-- Join!")
        await self.vcchannel.set_permissions(self.raiderrole, connect=True, view_channel=True, speak=False)

        self.afkmsg = await self.hcchannel.send(f"@here `Fame Train` {self.emojis[0]} started by {self.ctx.author.mention} "
                                                f"in {self.vcchannel.name}",
                                                embed=embeds.fame_train_afk(self.ctx.author, self.vcchannel, self.world_num))
        for emoji in self.emojis:
            await self.afkmsg.add_reaction(emoji)
        await self.afkmsg.add_reaction('<:shard:682365548465487965>')
        await self.afkmsg.add_reaction('❌')

        cp = embeds.afk_check_control_panel(self.afkmsg.jump_url, self.location, "Fame Train", self.emojis[1], False)
        self.cpmsg = await self.ctx.send(embed=cp)

        while True:
            def check(react, usr):
                return not usr.bot and react.message.id == self.afkmsg.id
            try:
                reaction, user = await self.client.wait_for('reaction_add', timeout=14400, check=check)  # Wait max 1.5 hours
            except asyncio.TimeoutError:
                return await self.end_afk(True)

            if str(reaction.emoji) == self.emojis[0]:
                if user.id not in self.raiderids:
                    self.raiderids.append(user.id)
                    embed = self.afkmsg.embeds[0]
                    embed.set_footer(text=f"Raiders accounted for: {len(self.raiderids)}")
                    await self.afkmsg.edit(embed=embed)
            elif str(reaction.emoji) == '<:shard:682365548465487965>':
                if user.premium_since is not None or user.top_role >= self.rlrole:
                    await user.send(f"The location for this fame train is: {self.location}")
                    if user.display_name not in self.nitroboosters:
                        self.nitroboosters.append(user.mention)
                    cp = self.cpmsg.embeds[0]
                    cp.set_field_at(1, name="Nitro Boosters", value=str(self.nitroboosters), inline=True)
                    await self.cpmsg.edit(embed=cp)
            elif reaction.emoji == "❌" and user.top_role >= self.rlrole:
                return await self.end_afk(False, user)

    async def end_afk(self, automatic: bool, ended: discord.Member = None):
        await self.afkmsg.clear_reactions()
        embed = self.afkmsg.embeds[0]
        if automatic:
            embed.set_author(name="Fame Train has been ended automatically.", icon_url=self.ctx.author.avatar_url)
        else:
            embed.set_author(name=f"Fame Train has been ended by {ended.display_name}", icon_url=ended.avatar_url)
        embed.description = "Thanks for running with us!\n" \
                            f"This fame train ran with {len(self.raiderids)} members.\nPlease wait for the next AFK-Check to begin."
        embed.set_footer(text="Train ended at")
        embed.timestamp = datetime.utcnow()
        await self.afkmsg.edit(content="", embed=embed)
        if self.inraiding:
            if self.raidnum == 0:
                self.client.raid_db[self.ctx.guild.id]["raiding"][0] = None
            elif self.raidnum == 1:
                self.client.raid_db[self.ctx.guild.id]["raiding"][1] = None
            else:
                self.client.raid_db[self.ctx.guild.id]["raiding"][2] = None
        elif self.invet:
            if self.raidnum == 0:
                self.client.raid_db[self.ctx.guild.id]["vet"][0] = None
            else:
                self.client.raid_db[self.ctx.guild.id]["vet"][1] = None
        elif self.inevents:
            if self.raidnum == 0:
                self.client.raid_db[self.ctx.guild.id]["events"][0] = None
            else:
                self.client.raid_db[self.ctx.guild.id]["events"][1] = None

        vc_name = self.vcchannel.name
        if " <-- Join!" in vc_name:
            vc_name = vc_name.split(" <")[0]
            await self.vcchannel.edit(name=vc_name)
        await self.vcchannel.set_permissions(self.raiderrole, connect=False, view_channel=True, speak=False)