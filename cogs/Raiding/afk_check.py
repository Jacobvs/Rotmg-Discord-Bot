import asyncio
from datetime import datetime

import discord

import embeds
import sql
import utils
from cogs.Raiding.logrun import LogRun


class AfkCheck:

    def __init__(self, client, ctx, location, raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg):
        self.client = client
        self.ctx = ctx
        self.location = location
        self.raidnum = raidnum
        self.inraiding = inraiding
        self.invet = invet
        self.inevents = inevents
        self.raiderrole = raiderrole
        self.rlrole = rlrole
        self.hcchannel = hcchannel
        self.vcchannel = vcchannel
        self.setup_msg = setup_msg
        self.guild_db = self.client.guild_db.get(self.ctx.guild.id)
        self.firstpopperrole = self.guild_db[sql.gld_cols.firstpopperrole]
        self.secondpopperrole = self.guild_db[sql.gld_cols.secondpopperrole]
        self.thirdpopperrole = self.guild_db[sql.gld_cols.thirdpopperrole]
        self.raiderids = []
        self.nitroboosters = []
        self.raiderids.append(ctx.author.id)
        self.keyreacts = []
        self.potentialkeys = []
        self.userswloc = []
        self.rushers = {}
        self.numrushers = 0
        self.firstpopperearlyloc = True if self.guild_db[sql.gld_cols.firstpopperearlyloc] == 1 else False
        self.secondpopperearlyloc = True if self.guild_db[sql.gld_cols.secondpopperearlyloc] == 1 else False
        self.thirdpopperearlyloc = True if self.guild_db[sql.gld_cols.thirdpopperearlyloc] == 1 else False
        self.maxrushers = self.guild_db[sql.gld_cols.maxrushersgetloc]
        self.locationembed = discord.Embed(title="AFK-Check Setup",
                                           description="Please choose what channel you'd like to start this afk check in.",
                                           color=discord.Color.green())
        self.dungeonembed = embeds.dungeon_select()


    async def start(self):
        # Edit to dungeon selection embed
        await self.setup_msg.edit(embed=self.dungeonembed)

        def dungeon_check(m):
            return m.author == self.ctx.author and m.channel == self.ctx.channel and m.content.isdigit()

        # Wait for author to select a dungeon
        while True:
            try:
                msg = await self.client.wait_for('message', timeout=60, check=dungeon_check)
            except asyncio.TimeoutError:
                embed = discord.Embed(title="Timed out!", description="You didn't choose a dungeon in time!", color=discord.Color.red())
                await self.setup_msg.clear_reactions()
                return await self.setup_msg.edit(embed=embed)

            if msg.content.isdigit():
                if 0 < int(msg.content) < 56:
                    break
            await self.ctx.send("Please choose a number between 1-55!", delete_after=7)

        # Grab dungeon info from utils
        self.dungeon_info = utils.dungeon_info(int(msg.content))
        self.dungeontitle = self.dungeon_info[0]
        self.emojis = self.dungeon_info[1]
        await msg.delete()

        await self.start_afk()


    async def start_afk(self, convert_from_hc=False):
        self.rusher_emojis = self.dungeon_info[2]
        self.afk_color = self.dungeon_info[3]
        self.afk_img = self.dungeon_info[4]

        # Setup Reaction
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
        await self.vcchannel.set_permissions(self.raiderrole, connect=True, view_channel=True, speak=False)

        if not convert_from_hc:
            self.afkmsg = await self.hcchannel.send(f"@here `{self.dungeontitle}` {self.emojis[0]} started by {self.ctx.author.mention} "
                                                f"in {self.vcchannel.name}", embed=embeds.
                                                afk_check_base(self.dungeontitle, self.ctx.author, True, self.emojis, self.rusher_emojis,
                                                               self.afk_img, self.afk_color))
        else:
            await self.hcmsg.clear_reactions()
            await self.hcmsg.edit(content=f"@here `{self.dungeontitle}` {self.emojis[0]} started by {self.ctx.author.mention} "
                                    f"in {self.vcchannel.name} (Converted from headcount)",
                                  embed=embeds.afk_check_base(self.dungeontitle, self.ctx.author, True, self.emojis, self.rusher_emojis,
                                                              self.afk_img, self.afk_color))
            pingmsg = await self.hcchannel.send(f"@here `{self.dungeontitle}` {self.emojis[0]} re-ping (Headcount -> AFK)")
            await pingmsg.delete()
            self.afkmsg = self.hcmsg
        await self.afkmsg.pin()

        asyncio.get_event_loop().create_task(self.add_emojis())
        rush = True if self.rusher_emojis else False
        cp = embeds.afk_check_control_panel(self.afkmsg.jump_url, self.location, self.dungeontitle, self.emojis[1], True, rushers=rush)
        self.cpmsg = await self.ctx.send(embed=cp)

        await self.cpmsg.add_reaction("📝")
        await self.cpmsg.add_reaction("🗺️")
        await self.cpmsg.add_reaction("🛑")
        await self.cpmsg.add_reaction("❌")

        try:
            pinmsg = await self.hcchannel.fetch_message(self.hcchannel.last_message_id)
            if pinmsg.type == discord.MessageType.pins_add:
                await pinmsg.delete()
        except discord.NotFound:
            pass

        self.autoendtask = self.client.loop.create_task(self.wait_for_end())

        self.client.raid_db[self.ctx.guild.id]['afk'][self.afkmsg.id] = self
        self.client.raid_db[self.ctx.guild.id]['cp'][self.cpmsg.id] = self


    async def reaction_handler(self, payload):
        try:
            if str(payload.emoji) == self.emojis[0]:
                if payload.member.id not in self.raiderids:
                    self.raiderids.append(payload.member.id)
                if not payload.member.voice or not payload.member.voice.channel == self.vcchannel:
                    try:
                        await payload.member.edit(voice_channel=self.vcchannel)
                    except discord.Forbidden:
                        pass

            elif str(payload.emoji) == '<:shard:682365548465487965>':
                if payload.member.premium_since is not None or payload.member.top_role >= self.rlrole or \
                   (True if (self.firstpopperrole in payload.member.roles and self.firstpopperrole and self.firstpopperearlyloc)
                    or (self.secondpopperrole in payload.member.roles and self.secondpopperrole and self.secondpopperearlyloc)
                    or (self.thirdpopperrole in payload.member.roles and self.thirdpopperrole and self.thirdpopperearlyloc)
                           else False) and payload.member.display_name not in self.nitroboosters:
                    await payload.member.send(f"The location for this run is: {self.location}")
                    if payload.member not in self.userswloc:
                        self.userswloc.append(payload.member)
                    if payload.member.display_name not in self.nitroboosters:
                        self.nitroboosters.append(payload.member.display_name)
                    cp = self.cpmsg.embeds[0]
                    cp.set_field_at(1, name="Nitro Boosters", value=str(self.nitroboosters), inline=True)
                    await self.cpmsg.edit(embed=cp)
            elif str(payload.emoji) == "❌" and payload.member.top_role >= self.rlrole:
                self.autoendtask.cancel()
                return await self.post_afk(False, payload.member)
            elif str(payload.emoji) == self.emojis[1]:
                if payload.member not in self.keyreacts and payload.member not in self.potentialkeys:
                    if len(self.keyreacts) == 2:
                        await payload.member.send("There are already enough keys for this run. Wait until the next run to use yours.")
                    else:
                        await self.dm_handler(self.emojis[1], payload.member,
                                              f"Do you have a key you are willing to pop for this run? If so react to the {self.emojis[1]}"
                                              " emoji.", self.potentialkeys, self.keyreacts, key=True)
            elif self.dungeontitle == "Void" or self.dungeontitle == "Full-Skip Void":
                if str(payload.emoji) == '<:vial:682205784524062730>':
                    if payload.member not in self.vials and payload.member not in self.potentialvials:
                        if len(self.vials) == 2:
                            await payload.member.send("There are already enough vials for this run. Wait until the next run to use yours.")
                        else:
                            await self.dm_handler("<:vial:682205784524062730>", payload.member,
                                                  "Do you have a vial you are willing to pop for this run? If so react to the "
                                                  "<:vial:682205784524062730> emoji.", self.potentialvials, self.vials, vial=True)
            elif self.dungeontitle == "Oryx 3":
                if str(payload.emoji) == "<:SwordRune:708191783405879378>":
                    if payload.member not in self.swordrunes and payload.member not in self.potentialsword:
                        if len(self.swordrunes) == 2:
                            await payload.member.send("There are already enough Sword Runes for this run. "
                                                      "Wait until the next run to use yours.")
                        else:
                            await self.dm_handler("<:SwordRune:708191783405879378>", payload.member,
                                                  "Do you have a Sword Rune you are willing to pop for this run? If so react to the "
                                                  "<:SwordRune:708191783405879378> emoji.",
                                                  self.potentialsword, self.swordrunes, sword=True)
                elif str(payload.emoji) == "<:ShieldRune:708191783674314814>":
                    if payload.member not in self.shieldrunes and payload.member not in self.potentialshield:
                        if len(self.shieldrunes) == 2:
                            await payload.member.send("There are already enough Shield Runes for this run. "
                                                      "Wait until the next run to use yours.")
                        else:
                            await self.dm_handler("<:ShieldRune:708191783674314814>", payload.member,
                                                  "Do you have a Shield Rune you are willing to pop for this run? "
                                                  "If so react to the <:ShieldRune:708191783674314814> emoji.",
                                                  self.potentialshield, self.shieldrunes, shield=True)
                elif str(payload.emoji) == "<:HelmRune:708191783825178674>":
                    if payload.member not in self.helmrunes and payload.member not in self.potentialhelm:
                        if len(self.helmrunes) == 2:
                            await payload.member.send("There are already enough Helm Runes for this run. "
                                                      "Wait until the next run to use yours.")
                        else:
                            await self.dm_handler("<:HelmRune:708191783825178674>", payload.member,
                                                  "Do you have a Helm Rune you are willing to pop for this run? If so react to the "
                                                  "<:HelmRune:708191783825178674> emoji.", self.potentialhelm, self.helmrunes, helm=True)

            if str(payload.emoji) in self.rusher_emojis:
                if self.numrushers < self.maxrushers:
                    if self.guild_db[sql.gld_cols.rusherrole] and not self.guild_db[sql.gld_cols.rusherrole] in payload.member.roles:
                        return await payload.member.send("You don't have the required rusher role to get early location. Feel free to rush "
                                                  "regardless and ask an rl to give you the rusher role after – "
                                                  "or pm the RL to ask for location.")
                    await self.dm_handler(str(payload.emoji), payload.member, "Are you willing & able to rush for this run? If so, "
                                          f"react to the {payload.emoji} emoji.", confirm_list=self.rushers, rush=True)
                else:
                    await payload.member.send("We already have enough rushers for this run! You can ask the rl for location if "
                                              "extra rushers may be needed.")
        except discord.Forbidden:
            pass


    async def cp_handler(self, payload):
        if str(payload.emoji) == '📝':
            embed = discord.Embed(title="Location Selection", description="Please type the location you'd like to set for this run.")
            setup_msg = await self.ctx.send(embed=embed)
            def location_check(m):
                return m.author == payload.member and m.channel == self.ctx.channel
            try:
                msg = await self.client.wait_for('message', timeout=60, check=location_check)  # Wait max 1 hour
            except asyncio.TimeoutError:
                try:
                    await setup_msg.delete()
                    return
                except discord.NotFound:
                    return

            self.location = msg.content

            try:
                await setup_msg.delete()
                await msg.delete()
            except discord.NotFound:
                pass

            for m in self.userswloc:
                await m.send(f"The location has changed to {self.location}.\nPlease get to the new location as soon as possible.")

            cp = self.cpmsg.embeds[0]
            cp.set_field_at(0, name="Location of run:", value=self.location, inline=False)
            await self.cpmsg.edit(embed=cp)

        elif str(payload.emoji) == "🛑":
            await self.abort_afk(payload.member)
        elif str(payload.emoji) == "🗺️":
            embed = self.afkmsg.embeds[0]
            embed.description += f"\n\nLocation has been revealed!\nThe location for this run is: ***{self.location}***."
            await self.afkmsg.edit(embed=embed)
            await self.cpmsg.remove_reaction("🗺️", payload.member)
            await self.cpmsg.remove_reaction("🗺️", self.client.user)
        elif str(payload.emoji) == "❌":
            self.autoendtask.cancel()
            await self.post_afk(False, payload.member)


    async def dm_handler(self, emoji, member, desc, pot_list=None, confirm_list=None, key=False, vial=False, helm=False, shield=False,
                         sword=False, rush=False):
        if pot_list != None:
            pot_list.append(member)
        msg = await member.send(desc)
        await msg.add_reaction(emoji)

        def check(reaction, user):
            return not user.bot and reaction.message.id == msg.id and str(reaction.emoji) == emoji

        try:
            reaction, usr = await self.client.wait_for('reaction_add', timeout=120, check=check)
        except asyncio.TimeoutError:
            pot_list.remove(member)
            await msg.clear_reactions()
            return await member.send("Timed out! Please re-confirm key on the AFK message.")

        if pot_list != None:
            pot_list.remove(member)

        if rush:
            if self.numrushers >= self.maxrushers:
                return await usr.send("We already have enough rushers for this run! You can ask the rl for location if extra rushers "
                                      "may be needed.")
            if emoji in self.rushers:
                self.rushers[emoji].append(member.mention)
            else:
                self.rushers[emoji] = [member.mention]
            self.numrushers += 1
        elif confirm_list != None:
            confirm_list.append(member)

        if not rush:
            await member.send(f"Confirmed {emoji}. The location for this run is:\n***{self.location}***\nPlease get to the location and "
                              f"trade `{self.ctx.author.display_name}`.")
        else:
            await member.send(f"Confirmed {emoji}. The location for this run is:\n***{self.location}***\nPlease get to the location soon.")
        if member not in self.userswloc:
            self.userswloc.append(member)

        if key or vial or helm or shield or sword or rush:
            cp = self.cpmsg.embeds[0]
            add = 1 if self.rusher_emojis else 0
            if key:
                if len(self.keyreacts) == 1:
                    cp.set_field_at(2+add, name="Current Keys:", value=f"Main {self.emojis[1]}: {self.keyreacts[0].mention}"
                                                                   f"\nBackup {self.emojis[1]}: None", inline=False)
                else:
                    cp.set_field_at(2+add, name="Current Keys:", value=f"Main {self.emojis[1]}: {self.keyreacts[0].mention}"
                                                                   f"\nBackup {self.emojis[1]}: {self.keyreacts[1].mention}", inline=False)
            elif vial:
                if len(self.vials) == 1:
                    cp.set_field_at(3+add, name="Vials:", value=f"Main <:vial:682205784524062730>: {self.vials[0].mention}"
                                                            f"\nBackup <:vial:682205784524062730>: None", inline=False)
                else:
                    cp.set_field_at(3+add, name="Vials:", value=f"Main <:vial:682205784524062730>: {self.vials[0].mention}"
                                                            f"\nBackup <:vial:682205784524062730>: {self.vials[1].mention}", inline=False)
            elif helm:
                if len(self.helmrunes) == 1:
                    cp.set_field_at(5+add, name="Helm Rune:", value=f"Main <:HelmRune:708191783825178674>: {self.helmrunes[0].mention}"
                                                                f"\nBackup <:HelmRune:708191783825178674>: None", inline=True)
                else:
                    cp.set_field_at(5+add, name="Helm Rune:", value=f"Main <:HelmRune:708191783825178674>: {self.helmrunes[0].mention}"
                                                                f"\nBackup <:HelmRune:708191783825178674>: {self.helmrunes[1].mention}",
                                    inline=True)
            elif shield:
                if len(self.shieldrunes) == 1:
                    cp.set_field_at(4+add, name="Shield Rune:", value=f"Main <:ShieldRune:708191783674314814>: {self.shieldrunes[0].mention}"
                                                                  f"\nBackup <:ShieldRune:708191783674314814>: None", inline=True)
                else:
                    cp.set_field_at(4+add, name="Shield Rune:", value=f"Main <:ShieldRune:708191783674314814>: {self.shieldrunes[0].mention}"
                                                                  f"\nBackup <:ShieldRune:708191783674314814>: {self.shieldrunes[1].mention}",
                                    inline=True)
            elif sword:
                if len(self.swordrunes) == 1:
                    cp.set_field_at(3+add, name="Sword Rune:", value=f"Main <:SwordRune:708191783405879378>: {self.swordrunes[0].mention}"
                                                                 f"\nBackup <:SwordRune:708191783405879378>: None", inline=True)
                else:
                    cp.set_field_at(3+add, name="Sword Rune:", value=f"Main <:SwordRune:708191783405879378>: {self.swordrunes[0].mention}"
                                                                 f"\nBackup <:SwordRune:708191783405879378>: {self.swordrunes[1].mention}",
                                    inline=True)
            else:
                s = ""
                for k in self.rushers:
                    s += k + " - "
                    s += ", ".join(self.rushers[k])
                    s += "\n"
                cp.set_field_at(2, name="Confirmed Rushers", value=s, inline=False)

            await self.cpmsg.edit(embed=cp)


    async def wait_for_end(self):
        await asyncio.sleep(480) # Wait 8 minutes
        await self.post_afk(True)


    async def post_afk(self, automatic: bool, ended: discord.Member = None):
        await self.vcchannel.set_permissions(self.raiderrole, connect=False, view_channel=True, speak=False)
        seconds_left = 30
        for m in self.vcchannel.members:
            if m.id not in self.raiderids and not m.bot:
                await m.edit(voice_channel=None)

        cpembd = self.cpmsg.embeds[0]
        cpembd.remove_field(len(cpembd.fields)-1)
        if ended:
            cpembd.description = f"**AFK Check Ended by** {ended.mention}"
        else:
            cpembd.description = "**AFK Check Ended Automatically**"
        cpembd.set_footer(text="AFK Check Ended at ")
        cpembd.timestamp = datetime.utcnow()
        await self.cpmsg.edit(embed=cpembd)
        await self.cpmsg.clear_reactions()

        if not automatic:
            await self.afkmsg.remove_reaction("❌", ended)
        await self.afkmsg.remove_reaction("❌", self.client.user)

        while seconds_left > 0:
            embed = embeds.post_afk(seconds_left, len(self.raiderids), self.emojis, self.afk_color)
            await self.afkmsg.edit(content="Last chance to join the run!", embed=embed)
            seconds_left -= 5
            await asyncio.sleep(5)
        await self.end_afk(automatic, ended)

    async def end_afk(self, automatic: bool, ended: discord.Member = None):
        await self.afkmsg.clear_reactions()
        await self.afkmsg.unpin()
        embed = self.afkmsg.embeds[0]
        if automatic:
            embed.set_author(name=f"{self.dungeontitle} raid has been ended automatically.", icon_url=self.ctx.author.avatar_url)
        else:
            embed.set_author(name=f"{self.dungeontitle} raid has been ended by {ended.display_name}", icon_url=ended.avatar_url)
        embed.set_thumbnail(url=self.afk_img)
        embed.title = None
        embed.description = f"Raid running in {self.vcchannel.name}. Thanks for running with us!\n" \
                            f"This raid ran with {len(self.raiderids)} members.\nPlease wait for the next AFK-Check to begin."
        embed.set_footer(text="Raid ended at")
        embed.timestamp = datetime.utcnow()
        await self.afkmsg.edit(content="", embed=embed)
        try:
            del self.client.raid_db[self.ctx.guild.id]['afk'][self.afkmsg.id]
            del self.client.raid_db[self.ctx.guild.id]['cp'][self.cpmsg.id]
        except KeyError:
            pass

        if self.dungeontitle == "Void" or self.dungeontitle == "Full-Skip Void":
            log = LogRun(self.client, self.ctx, self.emojis, self.keyreacts, self.dungeontitle, self.raiderids, self.rlrole, self.hcchannel,
                         events=self.inevents, vialreacts=self.vials)
        elif self.dungeontitle == "Oryx 3":
            log = LogRun(self.client, self.ctx, self.emojis, self.keyreacts, self.dungeontitle, self.raiderids, self.rlrole, self.hcchannel,
                         events=self.inevents, helmreacts=self.helmrunes, shieldreacts=self.shieldrunes, swordreacts=self.swordrunes)
        else:
            log = LogRun(self.client, self.ctx, self.emojis, self.keyreacts, self.dungeontitle, self.raiderids, self.rlrole, self.hcchannel,
                         events=self.inevents)

        await log.start()


    async def abort_afk(self, ended_by):
        del self.client.raid_db[self.ctx.guild.id]['afk'][self.afkmsg.id]
        del self.client.raid_db[self.ctx.guild.id]['cp'][self.cpmsg.id]

        await self.afkmsg.clear_reactions()
        await self.afkmsg.unpin()
        embed = embeds.aborted_afk(self.dungeontitle, ended_by, self.afk_img)
        await self.afkmsg.edit(content="", embed=embed)

        cpembd = self.cpmsg.embeds[0]
        cpembd.remove_field(len(cpembd.fields) - 1)
        cpembd.description = f"**AFK Check Aborted by** {ended_by.mention}"
        cpembd.set_footer(text="AFK Check Aborted at ")
        cpembd.timestamp = datetime.utcnow()
        await self.cpmsg.edit(embed=cpembd)
        await self.cpmsg.clear_reactions()


        await self.vcchannel.set_permissions(self.raiderrole, connect=False, view_channel=True, speak=False)

    async def add_emojis(self):
        for e in self.emojis:
            await self.afkmsg.add_reaction(e)
        for e in self.rusher_emojis:
            await self.afkmsg.add_reaction(e)
        await self.afkmsg.add_reaction('<:shard:682365548465487965>')
        await self.afkmsg.add_reaction('❌')


    async def convert_from_headcount(self, hcmsg, dungeoninfo, dungeontitle, emojis, raidnum, inraiding, invet, inevents, raiderrole,
                                     rlrole, hcchannel, vcchannel):
        self.hcmsg = hcmsg
        self.dungeon_info = dungeoninfo
        self.dungeontitle = dungeontitle
        self.emojis = emojis
        self.raidnum = raidnum
        self.inraiding = inraiding
        self.invet = invet
        self.inevents = inevents
        self.raiderrole = raiderrole
        self.rlrole = rlrole
        self.hcchannel = hcchannel
        self.vcchannel = vcchannel
        await self.start_afk(True)
