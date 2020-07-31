import asyncio
from datetime import datetime

import discord

import embeds
import sql
import utils
from cogs.Raiding.parselogging import ParseLog

ffmpeg_options = {'options': '-vn', 'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'}


class QAfk:

    def __init__(self, client, ctx, location, hcchannel, raiderrole, rlrole, is_US):
        self.client = client
        self.ctx = ctx
        self.guild_db = self.client.guild_db.get(self.ctx.guild.id)
        self.queuechannel = self.client.queue_links[hcchannel.category.id][0]
        self.category = self.client.queue_links[hcchannel.category.id][1]
        self.hcchannel = hcchannel
        self.raiderrole = raiderrole
        self.rlrole = rlrole
        self.location = location
        self.meetup = utils.get_server(is_US)
        self.raid_vc = None
        self.in_run = False
        self.max_patreons = 6

        self.raiderids = set()
        self.confirmed_raiders = {}
        self.confirmed_priority = {}
        self.raiderids.add(ctx.author.id)
        self.nitroboosters = []
        self.patreons = []
        self.last_edited = datetime.utcnow()
        self.awaiting_confirmations = set()

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


    async def start(self):
        # dungeonembed = embeds.dungeon_select()
        # # Edit to dungeon selection embed
        # setup_msg = await self.ctx.send(embed=dungeonembed)
        #
        # def dungeon_check(m):
        #     return m.author == self.ctx.author and m.channel == self.ctx.channel and m.content.isdigit()
        #
        # # Wait for author to select a dungeon
        # while True:
        #     try:
        #         msg = await self.client.wait_for('message', timeout=60, check=dungeon_check)
        #     except asyncio.TimeoutError:
        #         embed = discord.Embed(title="Timed out!", description="You didn't choose a dungeon in time!", color=discord.Color.red())
        #         return await setup_msg.edit(embed=embed)
        #
        #     if msg.content.isdigit():
        #         if 0 < int(msg.content) < 2:
        #             break
        #     await self.ctx.send("`1` (Oryx 3) Is the only dungeon configured for this command yet!", delete_after=7)
        #
        # await setup_msg.delete()

        # Grab dungeon info from utils
        dungeon_info = utils.q_dungeon_info(1)
        self.dungeontitle = dungeon_info[0]
        self.dungeon_emoji = dungeon_info[1][0]
        self.dungeon_image = dungeon_info[1][1]
        self.max_members = dungeon_info[2][0]
        self.max_nitro = dungeon_info[2][1]
        r_emojis = dungeon_info[3]
        self.class_emojis = dungeon_info[4]
        self.dungeon_color = dungeon_info[5]
        self.dungeon_boss_image = dungeon_info[6]
        self.required_items = {}
        for i in r_emojis:
            self.required_items[i[0]] = {'max': i[1], 'confirmed': []}

        # await msg.delete()

        # Setup Start AFK embed
        self.raid_start_embed = discord.Embed(colour=self.dungeon_color)
        self.raid_start_embed.set_author(name=f"{self.dungeontitle} AFK Started by {self.ctx.author.display_name}", icon_url=self.ctx.author.avatar_url)
        self.raid_start_embed.add_field(name="Items Needed:", value="All required items have been confirmed already! Please wait for the run to start!")
        # self.raid_start_embed.set_thumbnail(url=self.dungeon_image)
        self.raid_start_embed.timestamp = datetime.utcnow()
        await self.update_start_embed()

        # Send Start AFK Message
        self.raid_msg = await self.hcchannel.send(f"@here - `{self.dungeontitle}` {self.dungeon_emoji} raid is starting soon!", embed=self.raid_start_embed)
        await self.raid_msg.pin()
        emojis = [e for e in self.required_items]
        emojis.insert(0, self.dungeon_emoji)
        emojis.append("<:nitro:736138528710459473>")
        emojis.append('<:patreon:736944176469508118>')
        asyncio.get_event_loop().create_task(self.add_emojis(self.raid_msg, emojis))

        class_embed = discord.Embed(description="Please react below to indicate what class you are bringing to the run!")
        self.class_message = await self.hcchannel.send(embed=class_embed)
        asyncio.get_event_loop().create_task(self.add_emojis(self.class_message, self.class_emojis))

        # Create Raid VC
        overwrites = self.category.overwrites
        overwrites[self.raiderrole] = discord.PermissionOverwrite(connect=False, view_channel=True, speak=False)
        self.raid_vc: discord.VoiceChannel = await self.category.create_voice_channel(name=f"{self.ctx.author.display_name}'s {self.dungeontitle} Raid", overwrites=overwrites,
                                                                user_limit=self.max_members)
        await self.raid_vc.edit(position=self.queuechannel.position+1)
        self.client.qraid_vcs[self.raid_vc.id] = self.raid_vc

        # Setup Control Panel
        self.cp_embed = discord.Embed(description=f"QAFK [**Control Panel**]({self.raid_msg.jump_url}) for **{self.dungeontitle}** | Started by {self.ctx.author.mention}",
                                      color=discord.Color.teal())
        self.cp_embed.add_field(name="Meetup Location:", value=self.meetup, inline=True)
        self.cp_embed.add_field(name="Run Location:", value="*Hidden*", inline=True)
        self.cp_embed.add_field(name="Required Reactions:", value="N/A", inline=False)
        self.cp_embed.add_field(name="Nitro Boosters / Patreons:", value="N/A", inline=False)
        self.cp_embed.add_field(name="Info:", value="N/A", inline=False)
        self.cp_embed.add_field(name="Class Reactions (1):", value="N/A", inline=False)
        self.cp_embed.add_field(name="Class Reactions (2):", value="N/A", inline=False)
        self.cp_embed.set_footer(text="QAFK Started at ")
        self.cp_embed.timestamp = datetime.utcnow()
        await self.update_cp_embed()

        # Send Control Panel
        self.cp_msg = await self.ctx.send(embed=self.cp_embed)
        await self.cp_msg.add_reaction("📥")
        await self.cp_msg.add_reaction("🛑")

        # Delete automated message about pinned afk msg
        try:
            pinmsg = await self.hcchannel.fetch_message(self.hcchannel.last_message_id)
            if pinmsg.type == discord.MessageType.pins_add:
                await pinmsg.delete()
        except discord.NotFound:
            pass

        self.client.raid_db[self.ctx.guild.id]['afk'][self.raid_msg.id] = self
        self.client.raid_db[self.ctx.guild.id]['cp'][self.cp_msg.id] = self

        self.update_task = asyncio.get_event_loop().create_task(self.update_embeds())

        self.autoend_task = asyncio.get_event_loop().create_task(self.autoend())


    async def autoend(self):
        await asyncio.sleep(900)  # wait 15 mins max
        await self.dequeue()

    async def dequeue(self):
        print('in dequeue')
        await self.class_message.delete()
        task = asyncio.get_event_loop().create_task(self.move_members())
        await self.raid_msg.clear_reactions()
        while not task.done():
            num = len(self.raid_vc.members)
            capacity_bar = utils.textProgressBar(num, self.max_members, prefix="", percent_suffix=" Moved", suffix="", decimals=0, length=13)
            embed = discord.Embed(title="Moving Members...", description=capacity_bar, color=discord.Color.orange())
            await self.raid_msg.edit(embed=embed)
            nvc = len(self.raid_vc.members)
            n_capacity_bar = utils.textProgressBar(nvc, self.max_members, prefix="", percent_suffix=" Full", suffix="", decimals=0, length=13)
            info_str = f"Moving Members...\n\n**{nvc}** Slots Filled in VC\n{n_capacity_bar}"
            self.cp_embed.set_field_at(4, name="Info:", value=info_str)
            await self.cp_msg.edit(embed=self.cp_embed)
            await asyncio.sleep(1.5)

        await self.end_afk()


    async def move_members(self):
        print('moving priority')
        for id in self.confirmed_priority:
            if len(self.raid_vc.members) >= self.max_members:
                break
            if id in self.client.queues[self.queuechannel.id]:
                member = self.confirmed_priority[id]
                if member.voice:
                    await member.move_to(self.raid_vc)
                    if member.id not in self.raiderids:
                        self.raiderids.add(member.id)
                    self.client.active_raiders[member.id] = self.raid_vc.id

        print('moving confirmed')
        for id in self.confirmed_raiders:
            if len(self.raid_vc.members) >= self.max_members:
                break
            if id in self.client.queues[self.queuechannel.id]:
                member = self.confirmed_raiders[id]
                if member.voice:
                    await member.move_to(self.raid_vc)
                    if member.id not in self.raiderids:
                        self.raiderids.add(member.id)
                    self.client.active_raiders[member.id] = self.raid_vc.id
        print('done moving')


    async def end_afk(self):
        print("in end afk")


        embed = discord.Embed(description=f"This raid is running with **{len(self.raiderids)}** members.\nIf you get disconnected, rejoin {self.queuechannel.name} to be moved "
                                          f"in.\n\n__If you "
                                          f"weren't moved in for this afk, **stay in {self.queuechannel.name}** to keep your position for the "
                                          f"next raid.__\n\nStaying in the {self.queuechannel.name} VC will ensure you make it to a subsequent run!", color=self.dungeon_color)
        embed.set_thumbnail(url=self.dungeon_boss_image)
        embed.set_author(name=f"{self.dungeontitle} Raid is currently runnning!", icon_url=self.dungeon_image)

        classes = ""
        for c in self.class_emojis[:3]:
            num = next((r.count for r in self.class_message.reactions if str(r.emoji) == c), 0)
            bar = utils.textProgressBar(num, self.max_members, prefix="", percent_suffix=" Full", suffix="", decimals=0, length=10, fullisred=False)
            classes += f"{c} - {bar}\n"
        embed.add_field(name="Class Reactions (1):", value=classes, inline=False)
        classes = ""
        for c in self.class_emojis[3:]:
            num = next((r.count for r in self.class_message.reactions if str(r.emoji) == c), 0)
            bar = utils.textProgressBar(num, self.max_members, prefix="", percent_suffix=" Full", suffix="", decimals=0, length=10, fullisred=True)
            classes += f"{c} - {bar}\n"
        embed.add_field(name="Class Reactions (2):", value=classes, inline=False)
        embed.set_footer(text="Raid Started ")
        embed.timestamp = datetime.utcnow()

        await self.raid_msg.edit(content="", embed=embed)

        del self.client.raid_db[self.ctx.guild.id]['afk'][self.raid_msg.id]

        # Update cp with class info
        self.cp_embed.description += "\n\nPlease go to location ASAP & wait for bot to tell you when to call!"
        self.cp_embed.set_field_at(1, name="Run Location:", value=self.location)
        await self.cp_msg.edit(embed=self.cp_embed)

        print("before update cp")


        print('dming members')
        # DM MEMBERS
        for i in self.required_items:
            for m in self.required_items[i]['confirmed']:
                await m.send(f"The location is: {self.location}.\nYou have 15 seconds before location is called for everyone.")

        for m in self.patreons:
            await m.send(f"The location is: {self.location}.\nYou have 15 seconds before location is called for everyone.")

        for m in self.nitroboosters:
            await m.send(f"The location is: {self.location}.\nYou have 15 seconds before location is called for everyone.")


        print('print done sending dms')

        self.cp_embed.description += "\nLocation has been sent to all members with required items."
        await self.cp_msg.edit(embed=self.cp_embed)
        await asyncio.sleep(15)


        await self.ctx.author.send(f"CALL NOW: `{self.location}`\n{self.ctx.author.mention}")
        self.cp_embed.description = f"QAFK [**Control Panel**]({self.raid_msg.jump_url}) for **{self.dungeontitle}** | Started by {self.ctx.author.mention}\n\n" \
                                    "__**CALL LOCATION NOW!**__"
        await self.cp_msg.edit(embed=self.cp_embed)
        await asyncio.sleep(5)

        self.cp_embed.description = f"QAFK [**Control Panel**]({self.raid_msg.jump_url}) for **{self.dungeontitle}** | Started by {self.ctx.author.mention}\n\n" \
                                    "Press the 🔓 emoji to unlock the raid vc.\nPress the 📤 button when you are done with the run."
        await self.cp_msg.edit(embed=self.cp_embed)
        await self.cp_msg.add_reaction('🔓')
        await self.cp_msg.add_reaction('<:gray:736515579103543336>')
        await self.cp_msg.add_reaction('📤')

        self.in_run = True



    async def unlock_vc(self, member: discord.Member):
        voice = discord.utils.get(self.client.voice_clients, guild=self.ctx.guild)

        if voice and voice.is_connected():
            await voice.move_to(self.raid_vc)
        else:
            voice = await self.raid_vc.connect()

        client = self.ctx.guild.voice_client
        if not client.source:
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio("files/thevchasbeenunlocked.mp3", options=ffmpeg_options['options']), volume=0.5)
            self.ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else disconnect_helper(self, voice))

        for r in self.raiderids:
            self.client.active_raiders.pop(r, None)

        await self.hcchannel.send(f"{member.mention} has unlocked the raid vc!")
        await self.cp_msg.clear_reaction('🔓')

        self.cp_embed.description = f"QAFK [**Control Panel**]({self.raid_msg.jump_url}) for **{self.dungeontitle}** | Started by {self.ctx.author.mention}\n\n" \
                                    "\nPress the 📤 button when you are done with the run."
        await self.cp_msg.edit(embed=self.cp_embed)



    async def after_raid(self):
        print("in after raid")
        del self.client.raid_db[self.ctx.guild.id]['cp'][self.cp_msg.id]

        members_left = self.raid_vc.members
        for r in self.raiderids:
            self.client.active_raiders.pop(r, None)

        print('past deletion')

        all_members = []
        for r in self.raiderids:
            m = self.ctx.guild.get_member(r)
            if m:
                all_members.append(m)

        await self.cp_msg.clear_reactions()
        self.cp_embed.description = f"QAFK [**Control Panel**]({self.raid_msg.jump_url}) for **{self.dungeontitle}** | Started by {self.ctx.author.mention}\n\n" \
                                    "\nThe run has completed. Thank you for leading."
        await self.cp_msg.edit(embed=self.cp_embed)

        voice = discord.utils.get(self.client.voice_clients, guild=self.ctx.guild)

        if voice and voice.is_connected():
            await voice.move_to(self.raid_vc)
        else:
            voice = await self.raid_vc.connect()

        client = self.ctx.guild.voice_client
        if not client.source:
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio("files/movebacktoqueue.mp3", options=ffmpeg_options['options']), volume=0.5)
            self.ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else disconnect_helper(self, voice))

        await asyncio.sleep(5)

        del self.client.qraid_vcs[self.raid_vc.id]
        await self.raid_vc.delete()

        log = ParseLog(self.client, self.ctx.author, self.ctx.channel, self.ctx.guild, self.required_items, self.dungeontitle, all_members, members_left,
                       self.rlrole, self.hcchannel)
        await log.start()



    async def abort_afk(self, ended_by):
        del self.client.raid_db[self.ctx.guild.id]['afk'][self.raid_msg.id]
        del self.client.raid_db[self.ctx.guild.id]['cp'][self.cp_msg.id]

        for r in self.raiderids:
            self.client.active_raiders.pop(r, None)

        await self.class_message.delete()

        await self.raid_msg.clear_reactions()
        await self.raid_msg.unpin()
        embed = embeds.aborted_afk(self.dungeontitle, ended_by, self.dungeon_boss_image)
        await self.raid_msg.edit(content="", embed=embed)

        self.cp_embed.remove_field(len(self.cp_embed.fields) - 1)
        self.cp_embed.description = f"**AFK Check Aborted by** {ended_by.mention}"
        self.cp_embed.set_footer(text="AFK Check Aborted at ")
        self.cp_embed.timestamp = datetime.utcnow()
        await self.cp_msg.edit(embed=self.cp_embed)
        await self.cp_msg.clear_reactions()

        await self.raid_vc.delete(reason="Afk Check Aborted!")



    async def update_embeds(self):
        while True:
            if (datetime.utcnow() - self.last_edited).seconds > 1:
                await self.update_start_embed(update_msg=True)
                await self.update_cp_embed(update_msg=True)
                self.last_edited = datetime.utcnow()
            await asyncio.sleep(1)




    # Handlers
    # Reaction Handler
    async def reaction_handler(self, payload):
        emote = str(payload.emoji)
        if emote == self.dungeon_emoji:
            if (self.firstpopperrole in payload.member.roles and self.firstpopperrole and self.firstpopperearlyloc) or \
               (self.secondpopperrole in payload.member.roles and self.secondpopperrole and self.secondpopperearlyloc) or \
               (self.thirdpopperrole in payload.member.roles and self.thirdpopperrole and self.thirdpopperearlyloc) or \
               (self.firstrunerole in payload.member.roles and self.firstrunerole and self.firstruneearlyloc) or \
               (self.secondrunerole in payload.member.roles and self.secondrunerole and self.secondruneearlyloc):
                if payload.member not in self.confirmed_priority:
                    self.confirmed_priority[payload.member.id] = payload.member
            else:
                if payload.member not in self.confirmed_raiders:
                    if payload.member.id not in self.client.queues[self.queuechannel.id]:
                        if payload.member.voice and payload.member.voice.channel == self.queuechannel:
                            self.client.queues[self.queuechannel.id].append(payload.member.id)
                    self.confirmed_raiders[payload.member.id] = payload.member
        elif emote in self.required_items and payload.member not in self.required_items[emote]['confirmed']:
            if payload.user_id not in self.awaiting_confirmations:
                self.awaiting_confirmations.add(payload.member.id)
                await self.dm_handler(payload.member, emote)
        elif emote == "<:nitro:736138528710459473>":
            if payload.member.premium_since is not None and payload.member not in self.nitroboosters and payload.member not in self.patreons:
                await self.dm_handler(payload.member, 'Nitro', is_nitro=True)
        elif emote == "<:patreon:736944176469508118>":
            is_patreon = payload.member.id in self.client.patreon_ids
            if is_patreon and payload.member not in self.nitroboosters and payload.member not in self.patreons:
                await self.dm_handler(payload.member, 'Patreon', is_patreon=True)


    # Control panel handler
    async def cp_handler(self, payload):
        if not self.in_run:
            if str(payload.emoji) == '📥':
                self.autoend_task.cancel()
                self.update_task.cancel()
                await self.cp_msg.clear_reactions()
                await self.dequeue()
            elif str(payload.emoji) == '🛑':
                self.autoend_task.cancel()
                self.update_task.cancel()
                await self.cp_msg.clear_reactions()
                await self.abort_afk(payload.member)
        else:
            if str(payload.emoji) == '🔓':
                await self.unlock_vc(payload.member)
            elif str(payload.emoji) == '📤':
                await self.after_raid()


    # DM Confirmation Handler
    async def dm_handler(self, member, emoji, is_nitro=False, is_patreon=False):
        if is_nitro:
            max = self.max_nitro
            if len(self.nitroboosters) >= max:
                return
        elif is_patreon:
            max = self.max_patreons
            if len(self.patreons) >= max:
                return
        else:
            max = self.required_items[emoji]['max']
            if len(self.required_items[emoji]['confirmed']) >= max:
                if member.id in self.awaiting_confirmations:
                    self.awaiting_confirmations.remove(member.id)
                return
            msg = await member.send(f"Please react to the {emoji} to confirm you are bringing it to this run.\nIgnore this message if the reaction was a mistake.\n\n**Confirming "
                            f"this & not bringing to the run it is a suspendable offense.**")
            await msg.add_reaction(emoji)

            def check(react, usr):
                return not usr.bot and react.message.id == msg.id and str(react.emoji) == emoji

            try:
                await self.client.wait_for('reaction_add', timeout=15, check=check)
            except asyncio.TimeoutError:
                if member.id in self.awaiting_confirmations:
                    self.awaiting_confirmations.remove(member.id)
                return await member.send("Timed out! Please re-confirm key on the AFK message.")

            if len(self.required_items[emoji]['confirmed']) >= max:
                if member.id in self.awaiting_confirmations:
                    self.awaiting_confirmations.remove(member.id)
                return await member.send(f"We already have enough confirmed {emoji}'s for this run.")
            await member.send(f"Confirmed {emoji}.")

        if not member.voice:
            await member.send(f"Please join the __**{self.queuechannel.name}**__ VC within 30 seconds to confirm your spot in the raid.")
            def vc_check(mem, before, after):
                return mem == member and after is not None and after.channel == self.queuechannel
            try:
                m, b, a = await self.client.wait_for('voice_state_update', timeout=30, check=vc_check)
            except asyncio.TimeoutError:
                if member.id in self.awaiting_confirmations:
                    self.awaiting_confirmations.remove(member.id)
                return await member.send(f"You didn't join the `{self.queuechannel.name}` VC in time! Re-react to the afk message to confirm your spot in the raid.")
            else:
                if not is_nitro:
                    if len(self.required_items[emoji]['confirmed']) >= max:
                        if member.id in self.awaiting_confirmations:
                            self.awaiting_confirmations.remove(member.id)
                        return await member.send(f"We already have enough confirmed {emoji}'s for this run. Please ensure you're in the __{self.queuechannel.name}__ VC before "
                                                 f"reacting to ensure you secure a spot in the raid.")

        if is_nitro:
            if len(self.nitroboosters) < self.max_nitro:
                self.nitroboosters.append(member)
                if len(self.nitroboosters) >= self.max_nitro:
                    await self.raid_msg.clear_reaction(emoji)
        elif is_patreon:
            if len(self.patreons) < self.max_patreons:
                self.patreons.append(member)
                if len(self.patreons) >= self.max_patreons:
                    await self.raid_msg.clear_reaction(emoji)
        else:
            self.required_items[emoji]['confirmed'].append(member)
            if len(self.required_items[emoji]['confirmed']) >= self.required_items[emoji]['max']:
                await self.raid_msg.clear_reaction(emoji)
            await member.send(f"The Meetup Location for this run is:\n ***{self.meetup}**\nPlease get to the location and trade `{self.ctx.author.display_name}` if you are "
                              f"bringing an item. If you are bringing a class, don't trade the RL.")

        await self.update_start_embed(update_msg=True)
        await self.update_cp_embed(update_msg=True)
        self.last_edited = datetime.utcnow()
        reason = f"{member.display_name} skipped the queue for {self.ctx.author.display_name}'s {self.dungeontitle} Raid by bringing {emoji}."
        print(reason)
        if member.id in self.awaiting_confirmations:
            self.awaiting_confirmations.remove(member.id)
        await member.move_to(self.raid_vc, reason=reason)
        if member.id in self.confirmed_priority:
            del self.confirmed_priority[member.id]
        elif member.id in self.confirmed_raiders:
            del self.confirmed_raiders[member.id]
        if member.id not in self.raiderids:
            self.raiderids.add(member.id)
        self.client.active_raiders[member.id] = self.raid_vc.id


    # Utility Methods
    # Update starting embed
    async def update_start_embed(self, update_msg=False):
        nqueue = len(self.confirmed_raiders)+len(self.confirmed_priority)
        nvc = len(self.raid_vc.members) if self.raid_vc else 0
        capacity_bar = utils.textProgressBar(nqueue, self.max_members, prefix="", percent_suffix=" Full", suffix="", decimals=0, length=18)
        desc = f"**Join __{self.queuechannel.name}__ to to join the raiding queue!**\nUse `!position` to check your position in the queue.\n\n" \
               f"**{nqueue}** Members are in the queue & have been confirmed to join the raid!\n\n{capacity_bar}\n\nOnce you join the queue, react to {self.dungeon_emoji} to " \
               f"confirm you'd " \
               f"like to join this raid.\n\nIf you have a required item for this run, **first join __{self.queuechannel.name}__, then** react to the emojis below & confirm with " \
               f"the bot to skip the queue!\n\nIf you are one of my lovely patreons, react to: <:patreon:736944176469508118>  ⇒  `!patreon`"
        self.raid_start_embed.description = desc

        items = []
        items_str = ""
        for i in self.required_items:
            confirm = len(self.required_items[i]['confirmed'])
            max = self.required_items[i]['max']
            if confirm < max:
                items.append(f"{i} - **{confirm}**/{max}")
        items_str += " | ".join(items)
        items_str = items_str if items_str else "All required items have been confirmed already! Please wait for the run to start!"
        items_str += f"\n\n<:nitro:736138528710459473> Reserved Slots - **{len(self.nitroboosters)}/{self.max_nitro}**"
        items_str += f"\n\n<:patreon:736944176469508118> Reserved Slots - **{len(self.patreons)}/{self.max_patreons}**"
        self.raid_start_embed.set_field_at(0, name="Items Needed:", value=items_str, inline=False)

        self.raid_start_embed.set_footer(text=f"{nvc}/{self.max_members} Slots Filled | Queue Started at ")

        if update_msg:
            await self.raid_msg.edit(embed=self.raid_start_embed)


    # Update Control Panel Embed
    async def update_cp_embed(self, update_msg=False):
        item_str = ""
        for i in self.required_items:
            item_str += f"{i} - {' | '.join(m.mention for m in self.required_items[i]['confirmed'])} |⇒ ({len(self.required_items[i]['confirmed'])}/" \
                        f"{self.required_items[i]['max']})\n"
        self.cp_embed.set_field_at(2, name="Required Reactions:", value=item_str, inline=False)

        nitro_str = f"<:nitro:736138528710459473> - " \
                    f"{' | '.join([m.mention for m in self.nitroboosters])} |⇒ ({len(self.nitroboosters)}/{self.max_nitro})"
        nitro_str += f"\n<:patreon:736944176469508118> - " \
                     f"{' | '.join([m.mention for m in self.patreons])} |⇒ ({len(self.patreons)}/{self.max_patreons})"
        self.cp_embed.set_field_at(3, name="Nitro Boosters / Patreons:", value=nitro_str, inline=False)

        nqueue = len(self.confirmed_raiders)+len(self.confirmed_priority)
        nvc = len(self.raid_vc.members)
        q_capacity_bar = utils.textProgressBar(nqueue, self.max_members, prefix="", percent_suffix=" Full", suffix="", decimals=0, length=15)
        n_capacity_bar = utils.textProgressBar(nvc, self.max_members, prefix="", percent_suffix=" Full", suffix="", decimals=0, length=15)
        info_str = f"**{nqueue}** Members are currently in the queue to join the raid!\n{q_capacity_bar}\n\n**{nvc}** Slots Filled in VC\n{n_capacity_bar}\n\n" \
                   "Start the AFK once you have confirmed enough reactions.\nReact to the 📥 emoji to start, 🛑 to abort."
        self.cp_embed.set_field_at(4, name="Info:", value=info_str, inline=False)

        self.class_message = await self.hcchannel.fetch_message(self.class_message.id)
        classes = ""
        for c in self.class_emojis[:3]:
            num = next((r.count for r in self.class_message.reactions if str(r.emoji) == c), 1)-1
            bar = utils.textProgressBar(num, self.max_members, prefix="", percent_suffix=" ", suffix="", decimals=0, length=10, fullisred=False)
            classes += f"{c} - {bar}\n"
        self.cp_embed.set_field_at(5, name="Class Reactions (1):", value=classes, inline=False)
        classes = ""
        for c in self.class_emojis[3:]:
            num = next((r.count for r in self.class_message.reactions if str(r.emoji) == c), 1)-1
            bar = utils.textProgressBar(num, self.max_members, prefix="", percent_suffix=" ", suffix="", decimals=0, length=10, fullisred=False)
            classes += f"{c} - {bar}\n"
        self.cp_embed.set_field_at(6, name="Class Reactions (2):", value=classes, inline=False)

        if update_msg:
            await self.cp_msg.edit(embed=self.cp_embed)



    async def add_emojis(self, msg, emojis):
        for e in emojis:
            await msg.add_reaction(e)



def disconnect_helper(self, voice):
    coroutine = voice.disconnect()
    task = asyncio.run_coroutine_threadsafe(coroutine, self.client.loop)
    try:
        task.result()
    except:
        pass
