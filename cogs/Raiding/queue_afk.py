import asyncio
from datetime import datetime

import discord

import embeds
import sql
import utils
from cogs.Raiding.parselogging import ParseLog
from cogs.Raiding.realm_select import RealmSelect

ffmpeg_options = {'options': '-vn', 'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'}


# TODO: add an offset number to morder that denotes people who were in queue but reacted to get moved in early

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
        self.raid_msg = None
        self.in_normal = True if self.hcchannel.id == 660347564767313952 else False

        self.raiderids = set()
        self.confirmed_raiders = {}
        self.raiderids.add(ctx.author.id)
        self.nitroboosters = []
        self.patreons = []
        self.last_edited = datetime.utcnow()
        self.awaiting_confirmations = set()
        self.priority_order = []
        self.normal_order = []

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

        d = await sql.get_all_missed(self.client.pool)
        n_priority = 0
        n_regular = 0
        self.missed_runs = {}
        for r in d:
            if r[1]:
                n_priority += 1
            else:
                n_regular += 1
            self.missed_runs.update({r[0]: r[1]})

        # Grab dungeon info from utils
        dungeon_info = utils.q_dungeon_info(1) if self.in_normal else utils.q_dungeon_info(2)
        self.dungeontitle = dungeon_info[0]
        self.dungeon_emoji = dungeon_info[1][0]
        self.dungeon_image = dungeon_info[1][1]
        self.max_members = dungeon_info[2][0]
        self.max_nitro = dungeon_info[2][1]
        self.max_patreons = self.max_nitro
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
        try:
            await self.raid_msg.pin()
        except discord.HTTPException or discord.Forbidden:
            pass

        self.client.raid_db[self.ctx.guild.id]['afk'][self.raid_msg.id] = self

        emojis = [e for e in self.required_items]
        if self.in_normal:
            emojis.insert(0, self.dungeon_emoji)
            emojis.append("<:nitro:736138528710459473>")
            emojis.append('<:patreon:736944176469508118>')
        asyncio.get_event_loop().create_task(self.add_emojis(self.raid_msg, emojis))

        # class_embed = discord.Embed(description="Please react below to indicate what class you are bringing to the run! (Only used to check percentages)")
        # self.class_message = await self.hcchannel.send(embed=class_embed)
        # asyncio.get_event_loop().create_task(self.add_emojis(self.class_message, self.class_emojis))

        # Create Raid VC
        overwrites = self.category.overwrites
        overwrites[self.raiderrole] = discord.PermissionOverwrite(connect=False, view_channel=True, speak=False)
        self.raid_vc: discord.VoiceChannel = await self.category.create_voice_channel(name=
                                             f"{''.join([c for c in self.ctx.author.display_name if c.isalpha()])}'s {self.dungeontitle} Raid", overwrites=overwrites,
                                             user_limit=self.max_members)
        await self.raid_vc.edit(position=self.queuechannel.position+1)

        # Setup Control Panel
        self.cp_embed = discord.Embed(description=f"QAFK [**Control Panel**]({self.raid_msg.jump_url}) for **{self.dungeontitle}** | Started by {self.ctx.author.mention}",
                                      color=discord.Color.teal())
        self.cp_embed.add_field(name="Meetup Location:", value=self.meetup, inline=True)
        self.cp_embed.add_field(name="Run Location:", value=f"{self.location} *[Hidden]*", inline=True)
        self.cp_embed.add_field(name="Inc & Runes:", value="N/A", inline=False)
        self.cp_embed.add_field(name="Item/Class Reactions:", value="N/A", inline=False)
        self.cp_embed.add_field(name="DPS Reactions:", value="N/A", inline=False)
        self.cp_embed.add_field(name="Nitro Boosters / Patreons:", value="N/A", inline=False)
        self.cp_embed.add_field(name="Info:", value="N/A", inline=False)
        # self.cp_embed.add_field(name="Class Reactions (1):", value="N/A", inline=False)
        # self.cp_embed.add_field(name="Class Reactions (2):", value="N/A", inline=False)
        self.cp_embed.set_footer(text="QAFK Started at ")
        self.cp_embed.timestamp = datetime.utcnow()
        await self.update_cp_embed()

        # Send Control Panel
        self.cp_msg = await self.ctx.send(embed=self.cp_embed)
        await self.cp_msg.add_reaction("📥")
        await self.cp_msg.add_reaction("🛑")
        self.client.raid_db[self.ctx.guild.id]['cp'][self.cp_msg.id] = self

        # Delete automated message about pinned afk msg
        try:
            pinmsg = await self.hcchannel.fetch_message(self.hcchannel.last_message_id)
            if pinmsg.type == discord.MessageType.pins_add:
                await pinmsg.delete()
        except discord.NotFound:
            pass

        self.update_task = asyncio.get_event_loop().create_task(self.update_embeds())

        self.autoend_task = asyncio.get_event_loop().create_task(self.autoend())


    async def autoend(self):
        await asyncio.sleep(1800)  # wait 30 mins max
        self.update_task.cancel()
        await self.cp_msg.clear_reactions()
        await self.abort_afk(self.client.user)

    async def dequeue(self):
        print('in dequeue')

        qmembers = [m.id for m in self.queuechannel.members]

        await self.raid_msg.unpin()

        for id in self.confirmed_raiders:
            self.client.morder[self.ctx.guild.id].pop(id, None)

        # await self.class_message.delete()
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
            self.cp_embed.set_field_at(6, name="Info:", value=info_str)
            await self.cp_msg.edit(embed=self.cp_embed)
            await asyncio.sleep(1.5)

        await self.end_afk(qmembers)


    async def move_members(self):
        print('moving priority')
        all = len(self.raid_vc.members)
        for id in self.priority_order:
            if len(self.raid_vc.members) >= self.max_members:
                print(f'ended moving at len vc: {len(self.raid_vc.members)}')
                print(f'ended moving at normal moved: {all}')
                break
            if id in self.confirmed_raiders:
                member = self.confirmed_raiders[id]
                res = await self.movem(member)
                all += 1 if res else 0

        print('moving confirmed')
        for id in self.normal_order:
            if len(self.raid_vc.members) >= self.max_members:
                print(f'ended moving at len vc: {len(self.raid_vc.members)}')
                print(f'ended moving at normal moved: {all}')
                break
            if id in self.confirmed_raiders:
                member = self.confirmed_raiders[id]
                res = await self.movem(member)
                all += 1 if res else 0

        print('done moving')
        print(f'Num regular moved: {all}')

    async def movem(self, member):
        if member and member.voice:
            try:
                await member.move_to(self.raid_vc)
                if member.id not in self.raiderids:
                    self.raiderids.add(member.id)
                self.client.active_raiders[member.id] = self.raid_vc.id
                self.confirmed_raiders.pop(member.id, None)
                return True
            except discord.Forbidden or discord.HTTPException:
                print(f"MEMBER FAILED TO BE MOVED: {member.display_name}")
                return False
        return False

    async def end_afk(self, qmembers):
        print("in end afk")

        for m in self.raid_vc.members:
            if m.id not in self.raiderids:
                self.raiderids.add(m.id)

        # Update sql db with member res
        missed_runs = []
        for id in self.raiderids:
            missed_runs.append((id, False))
        for id in self.confirmed_raiders:
            if id in qmembers:
                missed_runs.append((id, True))
        print(f"N: reset to normal - {len(self.raiderids)}")
        print(f"N: given priority - {len(self.confirmed_raiders)}")
        print(f"N: total changed - {len(missed_runs)}")
        await sql.mass_update_missed(self.client.pool, missed_runs)

        mentions = '<#738615552594935910> and <#706563122944802856>' if self.in_normal else 'vet section of <#738615552594935910> and <#736240706955378788>'
        embed = discord.Embed(description=f"Read {mentions}.\n"
                                          f"This raid is running with **{len(self.raid_vc.members)}** members.\nIf you get disconnected, "
                                          f"rejoin {self.queuechannel.name} to be moved in. **Use !leaverun if you don't want to be moved in.**\n\n__If you "
                                          f"weren't moved in for this afk, you have been given 💎 priority queuing to ensure you make it to the next raid!__\n\n"
                                          f"Please send us any positive/negative feedback you have!\nThis can be on anything - staff behavior/callouts/AFK-check system/the server "
                                          f"itself:\n[Leave Feedback](https://discordapp.com/channels/660344559074541579/660344735692750858/750191143903559731)",
                              color=self.dungeon_color)
        embed.set_thumbnail(url=self.dungeon_boss_image)
        embed.set_author(name=f"{self.dungeontitle} Raid is currently running!", icon_url=self.dungeon_image)

        # classes = ""
        # for c in self.class_emojis[:3]:
        #     num = next((r.count for r in self.class_message.reactions if str(r.emoji) == c), 0)
        #     bar = utils.textProgressBar(num, int(self.max_members/4), prefix="", percent_suffix=" Full", suffix="", decimals=0, length=10, fullisred=True)
        #     classes += f"{c} - {bar}\n"
        # embed.add_field(name="Class Reactions (1):", value=classes, inline=False)
        # classes = ""
        # for c in self.class_emojis[3:]:
        #     num = next((r.count for r in self.class_message.reactions if str(r.emoji) == c), 0)
        #     bar = utils.textProgressBar(num, int(self.max_members/4), prefix="", percent_suffix=" Full", suffix="", decimals=0, length=10, fullisred=True)
        #     classes += f"{c} - {bar}\n"
        # embed.add_field(name="Class Reactions (2):", value=classes, inline=False)
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
        # DM runes first
        runems = []
        failed = []
        for e in self.required_items:
            if e in ["<:swordrune:737672554482761739>", "<:shieldrune:737672554642276423>", "<:helmrune:737673058722250782>", "<:WineCellarInc:708191799750950962>"]:
                for m in self.required_items[e]['confirmed']:
                    try:
                        await m.send(f"The location is: {self.location}.\nYou have 30 seconds before location is called for everyone.")
                        runems.append(m)
                    except discord.Forbidden or discord.HTTPException:
                        failed.append(m)
        self.cp_embed.description += "\nLocation has been sent to Runes & Inc... (Waiting 10 seconds)"
        await self.cp_msg.edit(embed=self.cp_embed)

        await asyncio.sleep(10)

        if self.in_normal:
            for i in self.required_items:
                for m in self.required_items[i]['confirmed']:
                    if m not in runems:
                        try:
                            await m.send(f"The location is: {self.location}.\nYou have 20 seconds before location is called for everyone.")
                        except discord.Forbidden or discord.HTTPException:
                            failed.append(m)

        for m in self.patreons:
            try:
                await m.send(f"The location is: {self.location}.\nYou have 20 seconds before location is called for everyone.")
            except discord.Forbidden or discord.HTTPException:
                failed.append(m)

        for m in self.nitroboosters:
            try:
                await m.send(f"The location is: {self.location}.\nYou have 20 seconds before location is called for everyone.")
            except discord.Forbidden or discord.HTTPException:
                failed.append(m)

        if failed:
            await self.ctx.send(f'These members have dms disabled!\n{", ".join([m.mention for m in failed])}')


        print('print done sending dms')

        self.cp_embed.description += "\nLocation has been sent to all members with required items... (Waiting 20 seconds)" if self.in_normal else "\nLocation has been sent to " \
                                                                                                                                                  "patreons & nitros."
        await self.cp_msg.edit(embed=self.cp_embed)
        await asyncio.sleep(20)

        try:
            await self.ctx.author.send(f"CALL NOW: `{self.location}`\n{self.ctx.author.mention}")
        except discord.Forbidden or discord.HTTPException:
            pass
        self.cp_embed.description = f"QAFK [**Control Panel**]({self.raid_msg.jump_url}) for **{self.dungeontitle}** | Started by {self.ctx.author.mention}\n\n" \
                                    "__**CALL LOCATION NOW!**__"
        await self.cp_msg.edit(embed=self.cp_embed)
        await asyncio.sleep(5)

        self.cp_embed.description = f"QAFK [**Control Panel**]({self.raid_msg.jump_url}) for **{self.dungeontitle}** | Started by {self.ctx.author.mention}\n\n" \
                                    "Press the 🔓 emoji to unlock the raid vc.\nPress the 📤 button when you are done with the run\n 📝 to change location (early locations will be " \
                                    "sent a DM)."
        await self.cp_msg.edit(embed=self.cp_embed)
        await self.cp_msg.add_reaction('🔓')
        await self.cp_msg.add_reaction('📤')
        await self.cp_msg.add_reaction('📝')

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
                                    "\nPress the 📤 button when you are done with the run, 📝 to change location."
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

        embed: discord.Embed = self.raid_msg.embeds[0]
        embed.set_author(name=f"{self.dungeontitle} Raid is finished!", icon_url=self.dungeon_image)
        embed.set_footer(text="Raid Finished at")
        embed.timestamp = datetime.utcnow()
        await self.raid_msg.edit(embed=embed)

        voice = discord.utils.get(self.client.voice_clients, guild=self.ctx.guild)

        if voice and voice.is_connected():
            await voice.move_to(self.raid_vc)
        else:
            voice = await self.raid_vc.connect()

        client = self.ctx.guild.voice_client
        if not client.source:
            # TODO: make mp3 file thanking raiders for joining & telling them to send modmail for +/- remarks
            source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio("files/movebacktoqueue.mp3", options=ffmpeg_options['options']), volume=0.5)
            self.ctx.voice_client.play(source, after=lambda e: print('Player error: %s' % e) if e else disconnect_helper(self, voice))

        await asyncio.sleep(5)

        await self.raid_vc.delete()

        log = ParseLog(self.client, self.ctx.author, self.ctx.channel, self.ctx.guild, self.required_items, self.dungeontitle, all_members, members_left,
                       self.rlrole, self.hcchannel)
        await log.start()



    async def abort_afk(self, ended_by):
        del self.client.raid_db[self.ctx.guild.id]['afk'][self.raid_msg.id]
        del self.client.raid_db[self.ctx.guild.id]['cp'][self.cp_msg.id]

        for id in self.confirmed_raiders:
            self.client.morder[self.ctx.guild.id].pop(id, None)

        for r in self.raiderids:
            self.client.active_raiders.pop(r, None)

        # await self.class_message.delete()

        await self.raid_msg.clear_reactions()
        await self.raid_msg.unpin()

        self.cp_embed.remove_field(len(self.cp_embed.fields) - 1)
        self.cp_embed.description = f"**AFK Check Aborted by** {ended_by.mention}"
        self.cp_embed.set_footer(text="AFK Check Aborted at ")
        self.cp_embed.timestamp = datetime.utcnow()
        await self.cp_msg.edit(embed=self.cp_embed)
        await self.cp_msg.clear_reactions()

        await asyncio.sleep(0.2)  # Sleep to wait for embed update task to fully cancel
        embed = embeds.aborted_afk(self.dungeontitle, ended_by, self.dungeon_boss_image)
        await self.raid_msg.edit(content="", embed=embed)

        await self.raid_vc.delete(reason="Afk Check Aborted!")



    async def update_embeds(self):
        while True:
            if (datetime.utcnow() - self.last_edited).seconds > 2:
                await self.update_start_embed(update_msg=True)
                await self.update_cp_embed(update_msg=True)
                self.last_edited = datetime.utcnow()
            await asyncio.sleep(2)


    # Handlers
    # Reaction Handler
    async def reaction_handler(self, payload):
        emote = str(payload.emoji)
        if emote == self.dungeon_emoji:
            # If member is in the priority order or has a role giving them priority queuing
            status = self.missed_runs.get(payload.member.id, None)
            if status is not None and status or\
                    (self.firstpopperrole in payload.member.roles and self.firstpopperrole and self.firstpopperearlyloc) or \
                    (self.secondpopperrole in payload.member.roles and self.secondpopperrole and self.secondpopperearlyloc) or \
                    (self.thirdpopperrole in payload.member.roles and self.thirdpopperrole and self.thirdpopperearlyloc) or \
                    (self.firstrunerole in payload.member.roles and self.firstrunerole and self.firstruneearlyloc) or \
                    (self.secondrunerole in payload.member.roles and self.secondrunerole and self.secondruneearlyloc):
                if payload.member not in self.confirmed_raiders:
                    self.priority_order.append(payload.member.id)
                    self.confirmed_raiders[payload.member.id] = payload.member
                    self.client.morder[self.ctx.guild.id][payload.member.id] = (True, len(self.priority_order))
                    self.client.morder[self.ctx.guild.id]['npriority'] = len(self.priority_order)
            else:
                if payload.member not in self.confirmed_raiders:
                    self.normal_order.append(payload.member.id)
                    self.confirmed_raiders[payload.member.id] = payload.member
                    self.client.morder[self.ctx.guild.id][payload.member.id] = (False, len(self.normal_order))
                    self.client.morder[self.ctx.guild.id]['nnormal'] = len(self.normal_order)
                else:
                    print(f"{payload.member} re-reacted to afk")
        else:
            await self.raid_msg.remove_reaction(payload.emoji, payload.member)

            if emote in self.required_items and payload.member not in self.required_items[emote]['confirmed']:
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
        if str(payload.emoji) == '📝' and self.in_run:
            rs = RealmSelect(self.client, self.ctx)
            self.location = await rs.start()

            failed = []
            for e in self.required_items:
                for m in self.required_items[e]['confirmed']:
                    try:
                        await m.send(f"The location has changed to **{self.location}**.\nPlease get to the new location as soon as possible.")
                    except discord.Forbidden or discord.HTTPException:
                        failed.append(m)
            for m in self.nitroboosters:
                try:
                    await m.send(f"The location has changed to **{self.location}**.\nPlease get to the new location as soon as possible.")
                except discord.Forbidden or discord.HTTPException:
                    failed.append(m)
            for m in self.patreons:
                try:
                    await m.send(f"The location has changed to **{self.location}**.\nPlease get to the new location as soon as possible.")
                except discord.Forbidden or discord.HTTPException:
                    failed.append(m)
            await self.ctx.send('Early location members have been sent the new location.')
            if failed:
                await self.ctx.send(f'These members have dms disabled!\n{", ".join([m.mention for m in failed])}')

            self.cp_embed.set_field_at(1, name='Run Location:', value=self.location, inline=False)
            await self.cp_msg.edit(embed=self.cp_embed)

        # elif str(payload.emoji) == '<:pepeGun:736540068969447445>':
        #     embed = discord.Embed(title='O3 Run Preparse', description="Please send a screenshot of members in the realm before the run started. If you clicked this button by "
        #                                                                "mistake, send `SKIP` to exit out of preparsing.")
        #     msg = await self.ctx.send(embed=embed)
        #
        #     def member_check(m):
        #         return m.author == payload.member and m.channel == self.ctx.channel
        #
        #     while True:
        #         try:
        #             msg = await self.client.wait_for('message', timeout=7200, check=member_check)
        #         except asyncio.TimeoutError:
        #             embed = discord.Embed(title="Timed out!", description="You didn't upload an image time!", color=discord.Color.red())
        #             return await msg.edit(embed=embed)
        #
        #         if 'skip' in msg.content.strip().lower():
        #             print('skipped')
        #             try:
        #                 await msg.delete()
        #             except discord.Forbidden or discord.HTTPException:
        #                 pass
        #             break
        #         else:
        #             if not msg.attachments:
        #                 await self.ctx.send("Please attach an image containing only the result of the /who command!", delete_after=10)
        #                 continue
        #             if len(msg.attachments) > 1:
        #                 await self.ctx.send("Please only attach 1 image.", delete_after=10)
        #                 continue
        #             attachment = msg.attachments[0]
        #             if not ".jpg" in attachment.filename and not ".png" in attachment.filename:
        #                 await self.ctx.send("Please only attach an image of type 'png' or 'jpg'.", delete_after=10)
        #                 continue
        #             image = io.BytesIO()
        #             await attachment.save(image, seek_begin=True)
        #             pmsg = await self.ctx.send("Parsing image. This may take a minute...")
        #
        #             await preparse(self, image, msg)

        if not self.in_run:
            if str(payload.emoji) == '📥':
                self.autoend_task.cancel()
                self.update_task.cancel()
                await self.cp_msg.clear_reactions()
                rs = RealmSelect(self.client, self.ctx, payload.member)
                loc = await rs.start()

                self.location = "No location selected." if loc is None else loc

                await self.update_cp_embed(update_msg=True)
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
            if 'rune' in str(emoji) or 'Inc' in str(emoji):
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
            link = 'https://discordapp.com/channels/660344559074541579/706563122944802856/749698837232222328' if self.in_normal else \
                'https://discordapp.com/channels/660344559074541579/736240706955378788/762415033371328533'
            if 'rune' in emoji:
                await member.send(f"Confirmed {emoji}. Thanks for bringing a rune! You do not have to meet requirements.")
            elif 'dps' in emoji:
                await member.send(f"Confirmed {emoji}. This means you're bringing Wizard/Sorcerer/Ninja. Please make sure you are meeting the requirements. They can be found here:\
                n{link}")
            else:
                await member.send(f"Confirmed {emoji}. Please make sure you are meeting the requirements. They can be found here:\n{link}")

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
                await member.send(f'Confirmed {emoji}. Please wait for the run to start.')
                self.nitroboosters.append(member)
                if len(self.nitroboosters) >= self.max_nitro:
                    await self.raid_msg.clear_reaction(emoji)
            else:
                await self.raid_msg.clear_reaction(emoji)
                await member.send('There are already enough nitro boosters in this run! Please wait for the next run to redeem your nitro reaction. You can still be moved in '
                                  'normally by reacting to the portal on the afk check.')
        elif is_patreon:
            if len(self.patreons) < self.max_patreons:
                await member.send(f'Confirmed {emoji}. Please wait for the run to start.')
                self.patreons.append(member)
                if len(self.patreons) >= self.max_patreons:
                    await self.raid_msg.clear_reaction(emoji)
            else:
                await self.raid_msg.clear_reaction(emoji)
                await member.send('There are already enough patreons in this run! Please wait for the next run to redeem your patreon reaction. You can still be moved in '
                                  'normally by reacting to the portal on the afk check.')
        else:
            self.required_items[emoji]['confirmed'].append(member)
            if len(self.required_items[emoji]['confirmed']) >= self.required_items[emoji]['max']:
                await self.raid_msg.clear_reaction(emoji)
            if 'rune' in str(emoji) or 'Inc' in str(emoji):
                await member.send(f"The Meetup Location for this run is:\n ***{self.meetup}**\nPlease get to the location and trade `{self.ctx.author.display_name}` if you are "
                                  f"bringing an item. If you are bringing a class, don't trade the RL.")

        await self.update_start_embed(update_msg=True)
        await self.update_cp_embed(update_msg=True)
        self.last_edited = datetime.utcnow()
        self.client.morder[self.ctx.guild.id]['nvc'] = len(self.raid_vc.members)
        reason = f"{member.display_name} skipped the queue for {self.ctx.author.display_name}'s {self.dungeontitle} Raid by bringing {emoji}."
        print(reason)
        if member.id in self.awaiting_confirmations:
            self.awaiting_confirmations.remove(member.id)
        await member.move_to(self.raid_vc, reason=reason)
        if member.id in self.confirmed_raiders:
            del self.confirmed_raiders[member.id]
        if member.id not in self.raiderids:
            self.raiderids.add(member.id)
        self.client.active_raiders[member.id] = self.raid_vc.id


    # Utility Methods
    # Update starting embed
    async def update_start_embed(self, update_msg=False):
        if self.raid_msg:
            self.raid_msg = await self.hcchannel.fetch_message(self.raid_msg.id)
            nqueue = next((r.count for r in self.raid_msg.reactions if str(r.emoji) == self.dungeon_emoji), 1)-1
        else:
            nqueue = 0
        nvc = len(self.raid_vc.members) if self.raid_vc else 0
        if not self.in_normal:
            nqueue = nvc
        capacity_bar = utils.textProgressBar(nqueue, self.max_members, prefix="", percent_suffix=" Full", suffix="", decimals=0, length=18)
        link = 'https://discordapp.com/channels/660344559074541579/706563122944802856/749698837232222328' if self.in_normal else \
               'https://discordapp.com/channels/660344559074541579/736240706955378788/762415033371328533'
        mentions = '<#738615552594935910> and <#706563122944802856>' if self.in_normal else 'vet section of <#738615552594935910> and <#736240706955378788>'
        desc = f"Read {mentions}.\n" \
               f"**{nqueue}** Members are in the queue & have been confirmed to join the raid!\n{capacity_bar}\n\n" \
               f"Make sure you meet the [requirements]({link}) when reacting to this message.\n**RUNES DO NOT HAVE TO MEET REQS!**\n\n" \
               f"If you have a required item or class for this run, **first join __{self.queuechannel.name}__, then** react to the emojis below & " \
               f"confirm with the bot to skip the queue!\n"
        desc += "React to either <:wizard:711307534685962281> (2/4 DPS Gear) OR <:wizardPlus:757981015380852906> (4/4 DPS Gear). **Don't react with both.**"\
            if self.in_normal else "\nIf you are bringing a <:wizard:711307534685962281>, <:sorcerer:711307536573399070>, or <:ninja:711307535071576145> " \
                                   "- React to <:dps:751494941980753991> if you meet the requirements for those classes."
        if self.in_normal:
            desc += f"\n\nIf you are one of my lovely patreons, react to: <:patreon:736944176469508118>  ⇒  `!patreon`"
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
        if self.in_normal:
            items_str += f"\n\n<:nitro:736138528710459473> Reserved Slots - **{len(self.nitroboosters)}/{self.max_nitro}**"
            items_str += f"\n\n<:patreon:736944176469508118> Reserved Slots - **{len(self.patreons)}/{self.max_patreons}**"
        self.raid_start_embed.set_field_at(0, name="Items Needed:", value=items_str, inline=False)

        self.raid_start_embed.set_footer(text=f"{nvc}/{self.max_members} Slots Filled | Queue Started at ")

        if update_msg:
            await self.raid_msg.edit(embed=self.raid_start_embed)


    # Update Control Panel Embed
    async def update_cp_embed(self, update_msg=False):
        item_str = ""
        rune_str = ""
        dps_str = ""
        # Todo: ADD ⭐ to names who are vet raider
        for i in self.required_items:
            if 'rune' in i or 'Inc' in i:
                rune_str += f"{i} - {' | '.join(m.mention for m in self.required_items[i]['confirmed'])} |⇒ ({len(self.required_items[i]['confirmed'])}/" \
                            f"{self.required_items[i]['max']})\n"
            elif i != '<:dps:751494941980753991>' and i != "<:wizard:711307534685962281>" and i != '<:wizardPlus:757981015380852906>':
                item_str += f"{i} - {' | '.join(m.mention for m in self.required_items[i]['confirmed'])} |⇒ ({len(self.required_items[i]['confirmed'])}/" \
                            f"{self.required_items[i]['max']})\n"
            else:
                dps_str += f"{i} - {' | '.join(m.mention for m in self.required_items[i]['confirmed'])} |⇒ ({len(self.required_items[i]['confirmed'])}/" \
                            f"{self.required_items[i]['max']})\n"
        self.cp_embed.set_field_at(2, name="Inc & Runes:", value=rune_str, inline=False)
        self.cp_embed.set_field_at(3, name="Item/Class Reactions:", value=item_str, inline=False)
        self.cp_embed.set_field_at(4, name='DPS Reactions:', value=dps_str, inline=False)

        nitro_str = f"<:nitro:736138528710459473> - " \
                    f"{' | '.join([m.mention for m in self.nitroboosters])} |⇒ ({len(self.nitroboosters)}/{self.max_nitro})"
        nitro_str += f"\n<:patreon:736944176469508118> - " \
                     f"{' | '.join([m.mention for m in self.patreons])} |⇒ ({len(self.patreons)}/{self.max_patreons})"
        self.cp_embed.set_field_at(5, name="Nitro Boosters / Patreons:", value=nitro_str, inline=False)

        if self.raid_msg:
            self.raid_msg = await self.hcchannel.fetch_message(self.raid_msg.id)
            nqueue = next((r.count for r in self.raid_msg.reactions if str(r.emoji) == self.dungeon_emoji), 1) - 1
        else:
            nqueue = 0
        nvc = len(self.raid_vc.members)
        q_capacity_bar = utils.textProgressBar(nqueue, self.max_members, prefix="", percent_suffix=" Full", suffix="", decimals=0, length=15)
        n_capacity_bar = utils.textProgressBar(nvc, self.max_members, prefix="", percent_suffix=" Full", suffix="", decimals=0, length=15)
        info_str = f"**{nqueue}** Members are currently in the queue to join the raid!\n{q_capacity_bar}\n\n**{nvc}** Slots Filled in VC\n{n_capacity_bar}\n\n" \
                   "Start the AFK once you have confirmed enough reactions.\nReact to the 📥 emoji to start, 🛑 to abort."
        self.cp_embed.set_field_at(6, name="Info:", value=info_str, inline=False)

        # self.class_message = await self.hcchannel.fetch_message(self.class_message.id)
        # classes = ""
        # for c in self.class_emojis[:3]:
        #     num = next((r.count for r in self.class_message.reactions if str(r.emoji) == c), 1)-1
        #     bar = utils.textProgressBar(num, int(self.max_members/4), prefix="", percent_suffix=" ", suffix="", decimals=0, length=10, fullisred=False)
        #     classes += f"{c} - {bar}\n"
        # self.cp_embed.set_field_at(5, name="Class Reactions (1):", value=classes, inline=False)
        # classes = ""
        # for c in self.class_emojis[3:]:
        #     num = next((r.count for r in self.class_message.reactions if str(r.emoji) == c), 1)-1
        #     bar = utils.textProgressBar(num, int(self.max_members/4), prefix="", percent_suffix=" ", suffix="", decimals=0, length=10, fullisred=False)
        #     classes += f"{c} - {bar}\n"
        # self.cp_embed.set_field_at(6, name="Class Reactions (2):", value=classes, inline=False)

        self.cp_embed.set_field_at(1, name="Run Location:", value=f"{self.location}", inline=True)
        if update_msg:
            await self.cp_msg.edit(embed=self.cp_embed)



    async def add_emojis(self, msg, emojis):
        for e in emojis:
            await msg.add_reaction(e)


defaultnames = ["darq", "deyst", "drac", "drol", "eango", "eashy", "eati", "eendi", "ehoni", "gharr", "iatho", "iawa", "idrae", "iri", "issz", "itani", "laen", "lauk", "lorz",
                "oalei", "odaru", "oeti", "orothi", "oshyu", "queq", "radph", "rayr", "ril", "rilr", "risrr", "saylt", "scheev", "sek", "serl", "seus", "tal", "tiar", "uoro",
                "urake", "utanu", "vorck", "vorv", "yangu", "yimi", "zhiar"]


# async def preparse(self, image, msg):
#     names = await self.client.loop.run_in_executor(None, functools.partial(parse_image, image))
#     memlist = []
#     namelist = []
#     conveter = utils.MemberLookupConverter()
#     ctx = commands.Context(bot=self.client, prefix="!", guild=self.ctx.guild, message=msg)
#     for name in names:
#         if " " in name:
#             names = name.split(" ")
#             name = names[0]
#
#         try:
#             mem = await conveter.convert(ctx, name)
#             memlist.append(mem)
#         except discord.ext.commands.BadArgument:
#             namelist.append(name)
#
#     earlylocs = []
#     for e in self.required_items:
#         for m in self.required_items[e]['confirmed']:
#             if m not in earlylocs:
#                 earlylocs.append(m)
#     for m in self.nitroboosters:
#         if m not in earlylocs:
#             earlylocs.append(m)
#     for m in self.patreons:
#         if m not in earlylocs:
#             earlylocs.append(m)
#
#     mcrashers = []
#     for m in memlist:
#         if m not in earlylocs:
#             mcrashers.append(m)
#
#     return mcrashers, namelist
#
# def parse_image(image):
#     file_bytes = np.asarray(bytearray(image.read()), dtype=np.uint8)
#     img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
#     width = img.shape[:2][1]
#     factor = 700 / width
#     img = cv2.resize(img, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
#     hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
#
#     # define range of yellow color in HSV
#     lower = np.array([27, 130, 180])
#     upper = np.array([31, 255, 255])
#     # Threshold the HSV image to get only yellow colors
#     mask = cv2.inRange(hsv, lower, upper)
#     # cv2.imwrite("mask.jpg", mask)
#     # invert the mask to get yellow letters on white background
#     res = cv2.bitwise_not(mask)
#     # cv2.imwrite("res.jpg", res)
#     kernel = np.ones((2, 2), np.uint8)
#     res = cv2.erode(res, kernel, iterations=1)
#     blur = cv2.GaussianBlur(res, (3, 3), 0)
#
#     str = pytesseract.image_to_string(blur, lang='eng')
#     str = str.replace("\n", " ")
#     str = str.replace("}", ")")
#     str = str.replace("{", "(")
#     str = str.replace(";", ":")
#     split_str = re.split(r'(.*)(Players online \([0-9]+\): )', str)
#     if len(split_str) < 4:
#         print("ERROR - Parsed String: " + str)
#         print("INFO - Split String: ")
#         print(split_str)
#         return []
#
#     print("INFO - Split String: ")
#     print(split_str)
#
#     names = split_str[3].split(", ")
#     print('done cleaning member names')
#
#     return names



def disconnect_helper(self, voice):
    coroutine = voice.disconnect()
    task = asyncio.run_coroutine_threadsafe(coroutine, self.client.loop)
    try:
        task.result()
    except:
        pass
