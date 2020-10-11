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
        self.raiderids = []
        self.nitroboosters = []
        self.patreons = []
        self.raiderids.append(ctx.author.id)
        self.keyreacts = []
        self.userswloc = []
        self.rushers = {}
        self.confirmedreactions = {}
        self.numrushers = 0
        self.numkeys = 0
        self.numvials = 0
        self.numhelms = 0
        self.numshields = 0
        self.numswords = 0
        self.firstpopperrole = self.guild_db[sql.gld_cols.firstpopperrole]
        self.secondpopperrole = self.guild_db[sql.gld_cols.secondpopperrole]
        self.thirdpopperrole = self.guild_db[sql.gld_cols.thirdpopperrole]
        self.firstrunerole = self.guild_db[sql.gld_cols.runepopper1role]
        self.secondrunerole = self.guild_db[sql.gld_cols.runepopper2role]
        self.firstruneearlyloc = True if self.guild_db[sql.gld_cols.runepopper1loc] == 1 else False
        self.secondruneearlyloc = True if self.guild_db[sql.gld_cols.runepopper2loc] == 1 else False
        self.firstpopperearlyloc = True if self.guild_db[sql.gld_cols.firstpopperearlyloc] == 1 else False
        self.secondpopperearlyloc = True if self.guild_db[sql.gld_cols.secondpopperearlyloc] == 1 else False
        self.thirdpopperearlyloc = True if self.guild_db[sql.gld_cols.thirdpopperearlyloc] == 1 else False
        self.maxrushers = self.guild_db[sql.gld_cols.maxrushersgetloc]
        self.locationembed = discord.Embed(title="AFK-Check Setup",
                                           description="Please choose what channel you'd like to start this afk check in.",
                                           color=discord.Color.green())
        self.dungeonembed = embeds.dungeon_select()
        self.iswoland = ctx.guild.id == 666063675416641539
        self.vetraiderrole = self.guild_db[sql.gld_cols.vetroleid]

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
                if int(msg.content) == -1:
                    embed = discord.Embed(title="Cancelled!", description="You chose to cancel this afk creation.", color=discord.Color.red())
                    await self.setup_msg.clear_reactions()
                    return await self.setup_msg.edit(embed=embed)
                if 0 < int(msg.content) < 56:
                    break
            await self.ctx.send("Please choose a number between 1-55!", delete_after=7)

        # Grab dungeon info from utils
        self.dungeon_info = utils.dungeon_info(int(msg.content))
        self.dungeontitle = self.dungeon_info[0]
        self.emojis = self.dungeon_info[1]
        try:
            await msg.delete()
        except discord.NotFound:
            pass

        await self.start_afk()

    async def start_afk(self, convert_from_hc=False):
        self.confirmreactions = self.dungeon_info[2]
        self.rusher_emojis = self.dungeon_info[3]
        self.afk_color = self.dungeon_info[4]
        self.afk_img = self.dungeon_info[5]

        # Setup Reaction
        if self.dungeontitle == "Void" or self.dungeontitle == "Full-Skip Void":
            self.vials = []
        elif self.dungeontitle == "Oryx 3":
            self.swordrunes = []
            self.shieldrunes = []
            self.helmrunes = []

        try:
            await self.setup_msg.delete()
        except discord.NotFound:
            pass
        if self.raiderrole:
            await self.vcchannel.set_permissions(self.raiderrole, connect=True, view_channel=True, speak=False)

        if not convert_from_hc:
            self.afkmsg = await self.hcchannel.send(f"@here `{self.dungeontitle}` {self.emojis[0]} started by {self.ctx.author.mention} "
                                                    f"in {self.vcchannel.name}", embed=embeds.
                                                    afk_check_base(self.dungeontitle, self.ctx.author, True, self.emojis, self.confirmreactions, self.rusher_emojis,
                                                                   self.afk_img, self.afk_color))
        else:
            try:
                await self.hcmsg.delete()
            except discord.Forbidden or discord.NotFound:
                pass
            self.afkmsg = await self.hcchannel.send(content=f"@here `{self.dungeontitle}` {self.emojis[0]} started by {self.ctx.author.mention} "
                                          f"in {self.vcchannel.name} (Converted from headcount)",
                                  embed=embeds.afk_check_base(self.dungeontitle, self.ctx.author, True, self.emojis, self.confirmreactions, self.rusher_emojis,
                                                              self.afk_img, self.afk_color))
            pingmsg = await self.hcchannel.send(f"@here `{self.dungeontitle}` {self.emojis[0]} re-ping (Headcount -> AFK)")
            try:
                await pingmsg.delete()
            except discord.NotFound:
                pass
        await self.afkmsg.pin()

        asyncio.get_event_loop().create_task(self.add_emojis())
        rush = True if self.rusher_emojis else False
        cmojis = True if self.confirmreactions else False
        cp = embeds.afk_check_control_panel(self.afkmsg.jump_url, self.location, self.dungeontitle, self.emojis[1], True, rushers=rush, reactions=cmojis,
                                            vc_name=self.vcchannel.name)
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
            emote = str(payload.emoji)
            if emote == self.emojis[0]:
                if payload.member.id not in self.raiderids:
                    self.raiderids.append(payload.member.id)
                if not payload.member.voice or not payload.member.voice.channel == self.vcchannel:
                    if len(self.vcchannel.members) >= self.vcchannel.user_limit:
                        return
                    try:
                        await payload.member.edit(voice_channel=self.vcchannel)
                    except discord.Forbidden:
                        pass
            else:
                if emote == '<:shard:682365548465487965>':
                    if self.ctx.guild.id == 660344559074541579:
                        await self.afkmsg.remove_reaction(payload.emoji, payload.member)
                    if payload.member.premium_since is not None or payload.member.top_role >= self.rlrole or \
                            (True if (self.firstpopperrole in payload.member.roles and self.firstpopperrole and self.firstpopperearlyloc)
                             or (self.secondpopperrole in payload.member.roles and self.secondpopperrole and self.secondpopperearlyloc)
                             or (self.thirdpopperrole in payload.member.roles and self.thirdpopperrole and self.thirdpopperearlyloc)
                             or (self.firstrunerole in payload.member.roles and self.firstrunerole and self.firstruneearlyloc)
                             or (self.secondrunerole in payload.member.roles and self.secondrunerole and self.secondruneearlyloc)
                             else False) and payload.member not in self.nitroboosters:
                        if len(self.nitroboosters) > 5:
                            return await payload.member.send("We already have 6 Nitro Boosters for this run. Wait for the RL to call location.")
                        if payload.member not in self.patreons:
                            await payload.member.send(f"Confirmed {payload.emoji}. The location for this run is:\n***{self.location}***\nPlease get to the location soon.")
                            if payload.member not in self.userswloc:
                                self.userswloc.append(payload.member)
                            if payload.member not in self.nitroboosters:
                                self.nitroboosters.append(payload.member)
                            cp = self.cpmsg.embeds[0]
                            cp.set_field_at(1, name="Nitro Boosters:", value=" | ".join([m.mention for m in self.nitroboosters]), inline=False)
                            await self.cpmsg.edit(embed=cp)
                elif emote == '<:patreon:736944176469508118>':
                    if self.ctx.guild.id == 660344559074541579:
                        await self.afkmsg.remove_reaction(payload.emoji, payload.member)
                    if payload.member not in self.patreons:
                        is_patreon = payload.member.id in self.client.patreon_ids
                        if is_patreon and payload.member not in self.nitroboosters:
                            if payload.member not in self.patreons:
                                self.patreons.append(payload.member)
                            if payload.member not in self.userswloc:
                                self.userswloc.append(payload.member)
                            await payload.member.send(f"Confirmed {payload.emoji}. The location for this run is:\n***{self.location}***\nPlease get to the location soon.")
                            cp = self.cpmsg.embeds[0]
                            cp.set_field_at(2, name="Patreons:", value=" | ".join([m.mention for m in self.patreons]), inline=False)
                            await self.cpmsg.edit(embed=cp)
                elif emote == "❌" and payload.member.top_role >= self.rlrole:
                    self.autoendtask.cancel()
                    return await self.post_afk(False, payload.member)
                elif emote == self.emojis[1]:
                    if payload.member not in self.keyreacts:
                        await self.dm_handler(emote, payload.member,
                                              f"Do you have a key you are willing to pop for this run? If so react to the {self.emojis[1]}"
                                              " emoji.", confirm_list=self.keyreacts, key=True)
                elif self.dungeontitle == "Void" or self.dungeontitle == "Full-Skip Void":
                    if emote == '<:vial:682205784524062730>':
                        if payload.member not in self.vials:
                            await self.dm_handler("<:vial:682205784524062730>", payload.member,
                                                  "Do you have a vial you are willing to pop for this run? If so react to the "
                                                  "<:vial:682205784524062730> emoji.", confirm_list=self.vials, vial=True)
                elif self.dungeontitle == "Oryx 3":
                    if emote == "<:swordrune:737672554482761739>":
                        if self.ctx.guild.id == 660344559074541579:
                            await self.afkmsg.remove_reaction(payload.emoji, payload.member)
                        if payload.member not in self.swordrunes:
                            await self.dm_handler("<:swordrune:737672554482761739>", payload.member,
                                                  "Do you have a Sword Rune you are willing to pop for this run? If so react to the "
                                                  "<:swordrune:737672554482761739> emoji.",
                                                  confirm_list=self.swordrunes, sword=True)
                    elif emote == "<:shieldrune:737672554642276423>":
                        if self.ctx.guild.id == 660344559074541579:
                            await self.afkmsg.remove_reaction(payload.emoji, payload.member)
                        if payload.member not in self.shieldrunes:
                            await self.dm_handler("<:shieldrune:737672554642276423>", payload.member,
                                                  "Do you have a Shield Rune you are willing to pop for this run? "
                                                  "If so react to the <:shieldrune:737672554642276423> emoji.",
                                                  confirm_list=self.shieldrunes, shield=True)
                    elif emote == "<:helmrune:737673058722250782>":
                        if self.ctx.guild.id == 660344559074541579:
                            await self.afkmsg.remove_reaction(payload.emoji, payload.member)
                        if payload.member not in self.helmrunes:
                            await self.dm_handler("<:helmrune:737673058722250782>", payload.member,
                                                  "Do you have a Helm Rune you are willing to pop for this run? If so react to the "
                                                  "<:helmrune:737673058722250782> emoji.", confirm_list=self.helmrunes, helm=True)
                if emote in self.confirmreactions:
                    if self.ctx.guild.id == 660344559074541579:
                        await self.afkmsg.remove_reaction(payload.emoji, payload.member)
                    await self.dm_handler(emote, payload.member, f"Please confirm your reaction by pressing: {payload.emoji}.", confirm_list=self.confirmedreactions,
                                          confirm_emoji=True)
                if emote in self.rusher_emojis:
                    if self.ctx.guild.id == 660344559074541579:
                        await self.afkmsg.remove_reaction(payload.emoji, payload.member)
                    if self.numrushers < self.maxrushers:
                        if self.guild_db[sql.gld_cols.rusherrole] and not self.guild_db[sql.gld_cols.rusherrole] in payload.member.roles:
                            return await payload.member.send("You don't have the required rusher role to get early location. Feel free to rush "
                                                             "regardless and ask an rl to give you the rusher role after – "
                                                             "or pm the RL to ask for location.")
                        if self.dungeontitle == "Oryx 3":
                            desc = f"Are you able to bring a trickster & know how to use it properly? If so - react to the: {payload.emoji}."
                        else:
                            desc = f"Are you willing & able to rush for this run? If so, react to the {payload.emoji} emoji."

                        await self.dm_handler(emote, payload.member, desc, confirm_list=self.rushers, rush=True)
                    else:
                        await payload.member.send("We already have enough rushers for this run! You can ask the rl for location if "
                                                  "extra rushers may be needed.")
        except discord.Forbidden:
            pass

    async def cp_handler(self, payload):
        if str(payload.emoji) == '📝':
            embed = discord.Embed(title="Location Selection", description="Please type the location you'd like to set for this run.")
            setup_msg = await self.ctx.send(embed=embed)

            def location_check(mem):
                return mem.author == payload.member and mem.channel == self.ctx.channel

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
                try:
                    await m.send(f"The location has changed to **{self.location}**.\nPlease get to the new location as soon as possible.")
                except discord.Forbidden:
                    await self.ctx.channel(f"{m.mention} has DM's from server members disabled so they weren't sent the new location. Please inform them in-game.")

            cp = self.cpmsg.embeds[0]
            cp.set_field_at(0, name="Location of run:", value=self.location, inline=False)
            await self.cpmsg.edit(embed=cp)

        elif str(payload.emoji) == "🛑":
            self.autoendtask.cancel()
            await self.abort_afk(payload.member)
        elif str(payload.emoji) == "🗺️":
            embed = self.afkmsg.embeds[0]
            embed.description += f"\n\nLocation has been revealed!\nThe location for this run is: ***{self.location}***."
            await self.afkmsg.edit(embed=embed)
            await self.cpmsg.remove_reaction("🗺️", payload.member)
            await self.cpmsg.remove_reaction("🗺️", self.client.user)
            await self.ctx.send(f"Location has been revealed by {payload.member.mention}!")
        elif str(payload.emoji) == "❌":
            self.autoendtask.cancel()
            await self.post_afk(False, payload.member)

    async def dm_handler(self, emoji, member, desc, confirm_list, key=False, vial=False, helm=False, shield=False,
                         sword=False, rush=False, confirm_emoji=False):
        msg = await member.send(desc)
        await msg.add_reaction(emoji)

        def check(react, user):
            return not user.bot and react.message.id == msg.id and str(react.emoji) == emoji

        try:
            reaction, usr = await self.client.wait_for('reaction_add', timeout=20, check=check)
        except asyncio.TimeoutError:
            return await member.send("Timed out! Please re-confirm your reaction on the AFK message.")

        if member.id not in self.raiderids:
            self.raiderids.append(member.id)

        if rush:
            if self.numrushers >= self.maxrushers:
                return await usr.send("We already have enough rushers for this run! You can ask the rl for location if extra rushers "
                                      "may be needed.")

            mstring = str(member.mention)
            if self.vetraiderrole and self.vetraiderrole in member.roles:
                mstring += "⭐"

            if emoji in self.rushers:
                self.rushers[emoji].append(mstring)
            else:
                self.rushers[emoji] = [mstring]
            self.numrushers += 1
            if member not in self.userswloc:
                self.userswloc.append(member)

            await member.send(f"Confirmed {emoji}. The location for this run is:\n***{self.location}***\nPlease get to the location soon.")
        elif confirm_emoji:
            mstring = str(member.mention)
            if self.vetraiderrole and self.vetraiderrole in member.roles:
                mstring += "⭐"

            if emoji in self.confirmedreactions:
                self.confirmedreactions[emoji].append(mstring)
            else:
                self.confirmedreactions[emoji] = [mstring]

            await member.send(f"Confirmed {emoji}. Thanks! Please wait for the run to start.")
        else:
            name = "keys" if key else "vial" if vial else "sword runes" if sword else "shield runes" if shield else "helm runes"
            if len(confirm_list) >= 2:
                return await member.send(f"There are already enough {name} for this run. Please wait for RL to call location.")
            else:
                await member.send(f"Confirmed {emoji}. The location for this run is:\n***{self.location}***\nPlease get to the location and "
                                  f"trade `{self.ctx.author.display_name}`.")
                if member not in self.userswloc:
                    self.userswloc.append(member)
            confirm_list.append(member)

        # TODO: add 🌟 emoji to name if key popper / rune popper role
        if key or vial or helm or shield or sword or confirm_emoji or rush:
            cp = self.cpmsg.embeds[0]
            add = 1 if self.confirmreactions else 0
            add += 1 if self.rusher_emojis else 0
            if key:
                if len(self.keyreacts) == 1:
                    cp.set_field_at(3 + add, name="Current Keys:", value=f"Main {self.emojis[1]}: {self.keyreacts[0].mention}"
                                                                         f"\nBackup {self.emojis[1]}: None", inline=False)
                else:
                    cp.set_field_at(3 + add, name="Current Keys:", value=f"Main {self.emojis[1]}: {self.keyreacts[0].mention}"
                                                                         f"\nBackup {self.emojis[1]}: {self.keyreacts[1].mention}", inline=False)
            elif vial:
                if len(self.vials) == 1:
                    cp.set_field_at(4 + add, name="Vials:", value=f"Main <:vial:682205784524062730>: {self.vials[0].mention}"
                                                                  f"\nBackup <:vial:682205784524062730>: None", inline=False)
                else:
                    cp.set_field_at(4 + add, name="Vials:", value=f"Main <:vial:682205784524062730>: {self.vials[0].mention}"
                                                                  f"\nBackup <:vial:682205784524062730>: {self.vials[1].mention}", inline=False)
            elif helm or shield or sword:
                r_str = "Helm Runes <:helmrune:737673058722250782> - " + " | ".join([m.mention for m in self.helmrunes])
                r_str += "\nShield Runes <:shieldrune:737672554642276423> - " + " | ".join([m.mention for m in self.shieldrunes])
                r_str += "\nSword Runes <:swordrune:737672554482761739> - " + " | ".join([m.mention for m in self.swordrunes])
                cp.set_field_at(4 + add, name="Runes:", value=r_str, inline=False)
            elif confirm_emoji:
                s = ""
                for k in self.confirmedreactions:
                    s += k + " - "
                    s += " | ".join(self.confirmedreactions[k])
                    s += "\n"
                cp.set_field_at(3, name="Confirmed Reactions", value=s, inline=False)
            else:
                s = ""
                for k in self.rushers:
                    s += k + " - "
                    s += " | ".join(self.rushers[k])
                    s += "\n"
                name = "Confirmed Tricksters" if self.dungeontitle == "Oryx 3" else "Confirmed Rushers"
                cp.set_field_at(2 + add, name=name, value=s, inline=False)

            await self.cpmsg.edit(embed=cp)

    async def wait_for_end(self):
        await asyncio.sleep(1200)  # Wait 20 minutes
        await self.post_afk(True)

    async def post_afk(self, automatic: bool, ended: discord.Member = None):
        await self.vcchannel.set_permissions(self.raiderrole, connect=False, view_channel=True, speak=False)
        seconds_left = 30
        for m in self.vcchannel.members:
            if m.id not in self.raiderids and not m.bot and m.top_role < self.rlrole:
                await m.edit(voice_channel=None)

        cpembd = self.cpmsg.embeds[0]
        cpembd.remove_field(len(cpembd.fields) - 1)
        if ended:
            cpembd.description = f"**AFK Check Ended by** {ended.mention} | Raid running in `{self.vcchannel.name}`"
        else:
            cpembd.description = f"**AFK Check Ended Automatically** | Raid running in `{self.vcchannel.name}`"
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
            self.log = LogRun(self.client, self.ctx.author, self.ctx.channel, self.ctx.guild, self.emojis, self.keyreacts, self.dungeontitle, self.raiderids, self.rlrole, \
                              self.hcchannel, events=self.inevents, vialreacts=self.vials)
        elif self.dungeontitle == "Oryx 3":
            self.log = LogRun(self.client, self.ctx.author, self.ctx.channel, self.ctx.guild, self.emojis, self.keyreacts, self.dungeontitle, self.raiderids, self.rlrole,
                              self.hcchannel, events=self.inevents, helmreacts=self.helmrunes, shieldreacts=self.shieldrunes, swordreacts=self.swordrunes)
        else:
            self.log = LogRun(self.client, self.ctx.author, self.ctx.channel, self.ctx.guild, self.emojis, self.keyreacts, self.dungeontitle, self.raiderids, self.rlrole,
                              self.hcchannel, events=self.inevents)

        await self.log.start()

    async def abort_afk(self, ended_by):
        del self.client.raid_db[self.ctx.guild.id]['afk'][self.afkmsg.id]
        del self.client.raid_db[self.ctx.guild.id]['cp'][self.cpmsg.id]

        if self.ctx.author.id in self.client.raid_db[self.ctx.guild.id]['leaders']:
            self.client.raid_db[self.ctx.guild.id]['leaders'].remove(self.ctx.author.id)

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
        for e in self.confirmreactions:
            await self.afkmsg.add_reaction(e)
        for e in self.rusher_emojis:
            await self.afkmsg.add_reaction(e)
        await self.afkmsg.add_reaction('<:shard:682365548465487965>')
        await self.afkmsg.add_reaction('<:patreon:736944176469508118>')
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
