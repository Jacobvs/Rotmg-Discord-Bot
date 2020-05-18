import asyncio
from datetime import datetime

import discord

import embeds
import sql
import utils


class AfkCheck:

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
        self.raidnum = 0
        self.nitroboosters = []
        self.raiderids.append(ctx.author.id)
        self.keyreacts = []
        self.potentialkeys = []
        self.userswloc = []
        self.locationembed = discord.Embed(title="AFK-Check Setup",
                                           description="Please choose what channel you'd like to start this afk check in.",
                                           color=discord.Color.green())
        self.dungeonembed = embeds.dungeon_select()

        #notes:
        # step 1: send embed of choosing vc number
        # step 2: choose run type (timeout 1m)
        # step 3: type location (timeout 1m)
        # step 4: send out afk & control panel
        # step 5: start countdown
        # step 6: await ending
        # on end: move ppl out

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
        await self.setup_msg.edit(embed=self.dungeonembed)

        def dungeon_check(m):
            return m.author == self.ctx.author and m.channel == self.ctx.channel and m.content.isdigit()

        try:
            msg = await self.client.wait_for('message', timeout=60, check=dungeon_check)
        except asyncio.TimeoutError:
            mapembed = discord.Embed(title="Timed out!", description="You didn't choose a dungeon in time!", color=discord.Color.red())
            await self.setup_msg.clear_reactions()
            return await self.setup_msg.edit(embed=mapembed)

        dungeon_info = utils.dungeon_info(int(msg.content))
        self.dungeontitle = dungeon_info[0]
        self.emojis = dungeon_info[1]
        await msg.delete()

        if self.dungeontitle == "Void" or self.dungeontitle == "Full-Skip Void":
            self.vials = []
            self.potentialvials = []
        elif self.dungeontitle == "Oryx 3":
            self.swordrunes = []
            self.potentialsword = []
            self.shieldrunes = []
            self.potentialshield = []
            self.helmrunes = []
            self.potentialhelm = []

        await self.setup_msg.delete()
        if " <-- Join!" not in self.vcchannel.name:
            await self.vcchannel.edit(name=self.vcchannel.name + " <-- Join!")
        await self.vcchannel.set_permissions(self.raiderrole, connect=True, view_channel=True, speak=False)

        self.afkmsg = await self.hcchannel.send(f"@here `{self.dungeontitle}` {self.emojis[0]} started by {self.ctx.author.mention} "
                                                f"in {self.vcchannel.name}", embed=embeds.
                                                afk_check_base(self.dungeontitle, self.ctx.author, True, self.emojis, dungeon_info[2]))
        # for emoji in self.emojis:
        #     await self.afkmsg.add_reaction(emoji)

        asyncio.get_event_loop().create_task(self.add_emojis())

        cp = embeds.afk_check_control_panel(self.afkmsg.jump_url, self.location, self.dungeontitle, self.emojis[1], True)
        self.cpmsg = await self.ctx.send(embed=cp)

        starttime = datetime.utcnow()
        timeleft = 300 # 300 seconds = 5 mins

        while True:
            def check(react, usr):
                return not usr.bot and react.message.id == self.afkmsg.id or (not react.message.guild and str(react.emoji) == '👍')
            try:
                reaction, user = await self.client.wait_for('reaction_add', timeout=timeleft, check=check)  # Wait max 1.5 hours
            except asyncio.TimeoutError:
                return await self.end_afk(True)


            timeleft = 300 - (datetime.utcnow() - starttime).seconds
            embed = self.afkmsg.embeds[0]
            uid = str(user.id)
            if str(reaction.emoji) == self.emojis[0]:
                if user.id not in self.raiderids:
                    self.raiderids.append(user.id)
            elif str(reaction.emoji) == '<:shard:682365548465487965>':
                if user.premium_since is not None or user.top_role >= self.rlrole:
                    await user.send(f"The location for this run is: {self.location}")
                    if user.display_name not in self.nitroboosters:
                        self.nitroboosters.append(user.display_name)
                    cp = self.cpmsg.embeds[0]
                    cp.set_field_at(1, name="Nitro Boosters", value=str(self.nitroboosters), inline=True)
                    await self.cpmsg.edit(embed=cp)
            elif reaction.emoji == "❌" and user.top_role >= self.rlrole:
                return await self.end_afk(False, user)
            elif str(reaction.emoji) == self.emojis[1]:
                if uid not in self.keyreacts and uid not in self.potentialkeys and reaction.message.guild:
                    if len(self.keyreacts) == 2:
                        await user.send("There are already enough keys for this run. Wait until the next run to use yours.")
                    else:
                        self.potentialkeys.append(uid)
                        msg = await user.send("Do you have a key you are willing to pop for this run? If so react to the "
                                              "👍 emoji.")
                        await msg.add_reaction('👍')

            elif self.dungeontitle == "Void" or self.dungeontitle == "Full-Skip Void":
                if str(reaction.emoji) == '👍':
                    if uid in self.potentialvials:
                        self.potentialvials.remove(uid)
                        self.vials.append(uid)
                        cp = self.cpmsg.embeds[0]
                        if len(self.vials) == 1:
                            cp.set_field_at(3, name="Vials:", value=f"Main <:vial:682205784524062730>: <@{self.vials[0]}>"
                                                                    f"\nBackup <:vial:682205784524062730>: None", inline=False)
                        else:
                            cp.set_field_at(3, name="Vials:", value=f"Main <:vial:682205784524062730>: <@{self.vials[0]}>"
                                                                    f"\nBackup <:vial:682205784524062730>: <@{self.vials[1]}>",
                                            inline=False)
                        await self.cpmsg.edit(embed=cp)
                        if user not in self.userswloc:
                            self.userswloc.append(user)
                        await user.send(f"The location for this run has been set to: {self.location}")
                elif str(reaction.emoji) == '<:vial:682205784524062730>':
                    if uid not in self.vials and uid not in self.potentialvials:
                        if len(self.vials) == 2:
                            await user.send("There are already enough vials for this run. Wait until the next run to use yours.")
                        else:
                            self.vials.append(uid)
                            msg = await user.send("Do you have a vial you are willing to pop for this run? If so react to the "
                                                  "👍 emoji.")
                            await msg.add_reaction("👍")
            elif self.dungeontitle == "Oryx 3":
                if str(reaction.emoji) == '👍':
                    if uid in self.potentialsword:
                        self.potentialsword.remove(uid)
                        self.swordrunes.append(uid)
                        cp = self.cpmsg.embeds[0]
                        if len(self.swordrunes) == 1:
                            cp.set_field_at(3, name="Sword Rune:", value=f"Main <:SwordRune:708191783405879378>: <@{self.swordrunes[0]}>"
                                                                         f"\nBackup <:SwordRune:708191783405879378>: None", inline=True)
                        else:
                            cp.set_field_at(3, name="Sword Rune:", value=f"Main <:SwordRune:708191783405879378>: <@{self.swordrunes[0]}>"
                                                                    f"\nBackup <:SwordRune:708191783405879378>: <@{self.swordrunes[1]}>",
                                            inline=True)
                        await self.cpmsg.edit(embed=cp)
                        if user not in self.userswloc:
                            self.userswloc.append(user)
                        await user.send(f"The location for this run has been set to: {self.location}")
                    elif uid in self.potentialshield:
                        self.potentialshield.remove(uid)
                        self.shieldrunes.append(uid)
                        cp = self.cpmsg.embeds[0]
                        if len(self.shieldrunes) == 1:
                            cp.set_field_at(4, name="Shield Rune:", value=f"Main <:ShieldRune:708191783674314814>: <@{self.shieldrunes[0]}>"
                                                                         f"\nBackup <:ShieldRune:708191783674314814>: None", inline=True)
                        else:
                            cp.set_field_at(4, name="Shield Rune:", value=f"Main <:ShieldRune:708191783674314814>: <@{self.shieldrunes[0]}>"
                                                                    f"\nBackup <:ShieldRune:708191783674314814>: <@{self.shieldrunes[1]}>",
                                            inline=True)
                        await self.cpmsg.edit(embed=cp)
                        if user not in self.userswloc:
                            self.userswloc.append(user)
                        await user.send(f"The location for this run has been set to: {self.location}")
                    elif uid in self.potentialhelm:
                        self.potentialhelm.remove(uid)
                        self.helmrunes.append(uid)
                        cp = self.cpmsg.embeds[0]
                        if len(self.helmrunes) == 1:
                            cp.set_field_at(5, name="Helm Rune:", value=f"Main <:HelmRune:708191783825178674>: <@{self.helmrunes[0]}>"
                                                                         f"\nBackup <:HelmRune:708191783825178674>: None", inline=True)
                        else:
                            cp.set_field_at(5, name="Helm Rune:", value=f"Main <:HelmRune:708191783825178674>: <@{self.helmrunes[0]}>"
                                                                    f"\nBackup <:HelmRune:708191783825178674>: <@{self.helmrunes[1]}>",
                                            inline=True)
                        await self.cpmsg.edit(embed=cp)
                        if user not in self.userswloc:
                            self.userswloc.append(user)
                        await user.send(f"The location for this run has been set to: {self.location}")
                if str(reaction.emoji) == "<:SwordRune:708191783405879378>":
                    if uid not in self.swordrunes and uid not in self.potentialsword:
                        if len(self.swordrunes) == 2:
                            await user.send("There are already enough Sword Runes for this run. Wait until the next run to use yours.")
                        else:
                            self.potentialsword.append(uid)
                            msg = await user.send("Do you have a Sword Rune you are willing to pop for this run? If so react to the "
                                                  "👍 emoji.")
                            await msg.add_reaction("👍")
                elif str(reaction.emoji) == "<:ShieldRune:708191783674314814>":
                    if uid not in self.shieldrunes and uid not in self.potentialshield:
                        if len(self.shieldrunes) == 2:
                            await user.send("There are already enough Shield Runes for this run. Wait until the next run to use yours.")
                        else:
                            self.potentialshield.append(uid)
                            msg = await user.send("Do you have a Shield Rune you are willing to pop for this run? If so react to the "
                                                  "👍 emoji.")
                            await msg.add_reaction("👍")
                elif str(reaction.emoji) == "<:HelmRune:708191783825178674>":
                    if uid not in self.helmrunes and uid not in self.potentialhelm:
                        if len(self.helmrunes) == 2:
                            await user.send("There are already enough Helm Runes for this run. Wait until the next run to use yours.")
                        else:
                            self.potentialhelm.append(uid)
                            msg = await user.send("Do you have a Helm Rune you are willing to pop for this run? If so react to the "
                                                  "👍 emoji.")
                            await msg.add_reaction("👍")
            if str(reaction.emoji) == '👍':
                if uid in self.potentialkeys:
                    self.potentialkeys.remove(uid)
                    self.keyreacts.append(uid)
                    cp = self.cpmsg.embeds[0]
                    if len(self.keyreacts) == 1:
                        cp.set_field_at(2, name="Current Keys:", value=f"Main {self.emojis[1]}: <@{self.keyreacts[0]}>"
                                                                       f"\nBackup {self.emojis[1]}: None", inline=False)
                    else:
                        cp.set_field_at(2, name="Current Keys:", value=f"Main {self.emojis[1]}: <@{self.keyreacts[0]}>"
                                                                       f"\nBackup {self.emojis[1]}: <@{self.keyreacts[1]}>", inline=False)
                    await self.cpmsg.edit(embed=cp)
                    if user not in self.userswloc:
                        self.userswloc.append(user)
                    await user.send(f"The location for this run has been set to: {self.location}")

            footer = f"Time remaining: {int(timeleft/60)} minutes and {timeleft%60} seconds | Raiders accounted for: {len(self.raiderids)}"
            embed.set_footer(text=footer)
            await self.afkmsg.edit(embed=embed)


    async def end_afk(self, automatic: bool, ended: discord.Member = None):
        await self.afkmsg.clear_reactions()
        embed = self.afkmsg.embeds[0]
        if automatic:
            embed.set_author(name=f"{self.dungeontitle} raid has been ended automatically.", icon_url=self.ctx.author.avatar_url)
        else:
            embed.set_author(name=f"{self.dungeontitle} raid has been ended by {ended.display_name}", icon_url=ended.avatar_url)
        embed.description = "Thanks for running with us!\n" \
                            f"This raid ran with {len(self.raiderids)} members.\nPlease wait for the next AFK-Check to begin."
        embed.set_footer(text="Raid ended at")
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


    async def add_emojis(self):
        for e in self.emojis:
            await self.afkmsg.add_reaction(e)
        await self.afkmsg.add_reaction('<:shard:682365548465487965>')
        await self.afkmsg.add_reaction('❌')
