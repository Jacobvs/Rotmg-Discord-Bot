import asyncio
from datetime import datetime

import discord

import embeds
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
        self.raiderids = []
        self.nitroboosters = []
        self.raiderids.append(ctx.author.id)
        self.keyreacts = []
        self.potentialkeys = []
        self.userswloc = []
        self.locationembed = discord.Embed(title="AFK-Check Setup",
                                           description="Please choose what channel you'd like to start this afk check in.",
                                           color=discord.Color.green())
        self.dungeonembed = embeds.dungeon_select()


    async def start(self):
        await self.setup_msg.edit(embed=self.dungeonembed)

        def dungeon_check(m):
            return m.author == self.ctx.author and m.channel == self.ctx.channel and m.content.isdigit()

        while True:
            try:
                msg = await self.client.wait_for('message', timeout=60, check=dungeon_check)
            except asyncio.TimeoutError:
                embed = discord.Embed(title="Timed out!", description="You didn't choose a dungeon in time!", color=discord.Color.red())
                await self.setup_msg.clear_reactions()
                return await self.setup_msg.edit(embed=embed)

            if msg.content.isdigit():
                if 0 < int(msg.content) < 51:
                    break
            await self.ctx.send("Please choose a number between 1-50!", delete_after=7)

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
        # if " <-- Join!" not in self.vcchannel.name:
        #     name = self.vcchannel.name + " <-- Join!"
        #     await self.vcchannel.edit(name=name)
        await self.vcchannel.set_permissions(self.raiderrole, connect=True, view_channel=True, speak=False)

        self.afkmsg = await self.hcchannel.send(f"@here `{self.dungeontitle}` {self.emojis[0]} started by {self.ctx.author.mention} "
                                                f"in {self.vcchannel.name}", embed=embeds.
                                                afk_check_base(self.dungeontitle, self.ctx.author, True, self.emojis, dungeon_info[2]))
        await self.afkmsg.pin()
        try:
            pinmsg = await self.hcchannel.fetch_message(self.hcchannel.last_message_id)
            if pinmsg.type == discord.MessageType.pins_add:
                    await pinmsg.delete()
        except discord.NotFound:
            pass

        # for emoji in self.emojis:
        #     await self.afkmsg.add_reaction(emoji)

        asyncio.get_event_loop().create_task(self.add_emojis())

        cp = embeds.afk_check_control_panel(self.afkmsg.jump_url, self.location, self.dungeontitle, self.emojis[1], True)
        self.cpmsg = await self.ctx.send(embed=cp)

        starttime = datetime.utcnow()
        timeleft = 300  # 300 seconds = 5 mins
        lasttime = starttime
        while True:
            def check(react, usr):
                return not usr.bot and react.message.id == self.afkmsg.id or (not react.message.guild and str(react.emoji) in ['👍',
                "<:sword:715832479507808317>️", "<:shield:715832479310938113>", "<:helm:715832479205949591>", "<:vial:714012990873272321>"])
            try:
                reaction, user = await self.client.wait_for('reaction_add', timeout=timeleft, check=check)  # Wait max 1.5 hours
            except asyncio.TimeoutError:
                return await self.end_afk(True)

            timeleft = 300 - (datetime.utcnow() - starttime).seconds
            embed = self.afkmsg.embeds[0]
            uid = str(user.id)
            try:
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
                    if str(reaction.emoji) == '<:vial:714012990873272321>':
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
                                self.potentialvials.append(uid)
                                msg = await user.send("Do you have a vial you are willing to pop for this run? If so react to the "
                                                      "<:vial:714012990873272321> emoji.")
                                await msg.add_reaction("<:vial:714012990873272321>")
                elif self.dungeontitle == "Oryx 3":
                    if str(reaction.emoji) in ["<:sword:715832479507808317>️", "<:shield:715832479310938113>", "<:helm:715832479205949591>"]:
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
                                                      "<:sword:715832479507808317>️ emoji.")
                                await msg.add_reaction("<:sword:715832479507808317>")
                    elif str(reaction.emoji) == "<:ShieldRune:708191783674314814>":
                        if uid not in self.shieldrunes and uid not in self.potentialshield:
                            if len(self.shieldrunes) == 2:
                                await user.send("There are already enough Shield Runes for this run. Wait until the next run to use yours.")
                            else:
                                self.potentialshield.append(uid)
                                msg = await user.send("Do you have a Shield Rune you are willing to pop for this run? If so react to the "
                                                      "<:shield:715832479310938113> emoji.")
                                await msg.add_reaction("<:shield:715832479310938113>")
                    elif str(reaction.emoji) == "<:HelmRune:708191783825178674>":
                        if uid not in self.helmrunes and uid not in self.potentialhelm:
                            if len(self.helmrunes) == 2:
                                await user.send("There are already enough Helm Runes for this run. Wait until the next run to use yours.")
                            else:
                                self.potentialhelm.append(uid)
                                msg = await user.send("Do you have a Helm Rune you are willing to pop for this run? If so react to the "
                                                      "<:helm:715832479205949591> emoji.")
                                await msg.add_reaction("<:helm:715832479205949591>")
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
            except discord.Forbidden:
                pass

            if (datetime.utcnow() - lasttime).seconds > 10:
                footer = f"Time remaining: {int(timeleft/60)} minutes and {timeleft%60} seconds | Raiders accounted for: " \
                         f"{len(self.raiderids)}"
                embed.set_footer(text=footer)
                await self.afkmsg.edit(embed=embed)
                lasttime = datetime.utcnow()


    async def end_afk(self, automatic: bool, ended: discord.Member = None):
        await self.afkmsg.clear_reactions()
        await self.afkmsg.unpin()
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

        # vc_name = self.vcchannel.name
        # if " <-- Join!" in vc_name:
        #     vc_name = vc_name.split(" <")[0]
        #     await self.vcchannel.edit(name=vc_name)
        await self.vcchannel.set_permissions(self.raiderrole, connect=False, view_channel=True, speak=False)

        if self.dungeontitle == "Void" or self.dungeontitle == "Full-Skip Void":
            log = LogRun(self.client, self.ctx, self.emojis, self.keyreacts, self.dungeontitle, self.raiderids, self.rlrole, self.inevents,
                         vialreacts=self.vials)
        elif self.dungeontitle == "Oryx 3":
            log = LogRun(self.client, self.ctx, self.emojis, self.keyreacts, self.dungeontitle, self.raiderids, self.rlrole, self.inevents,
                         helmreacts=self.helmrunes, shieldreacts=self.shieldrunes, swordreacts=self.swordrunes)
        else:
            log = LogRun(self.client, self.ctx, self.emojis, self.keyreacts, self.dungeontitle, self.raiderids, self.rlrole, self.inevents)

        await log.start()

    async def add_emojis(self):
        for e in self.emojis:
            await self.afkmsg.add_reaction(e)
        await self.afkmsg.add_reaction('<:shard:682365548465487965>')
        await self.afkmsg.add_reaction('❌')
