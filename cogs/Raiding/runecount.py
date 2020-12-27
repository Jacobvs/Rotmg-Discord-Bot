import asyncio
import datetime

import discord
import discord.ext.commands

from cogs.Raiding.queue_afk import QAfk


class RuneCount:

    def __init__(self, client, ctx, hcchannel, raiderrole, rlrole):
        self.client: discord.ext.commands.Bot = client
        self.ctx: discord.ext.commands.Context = ctx
        self.hcchannel: discord.TextChannel = hcchannel
        self.in_normal = True if self.hcchannel.id == 660347564767313952 else False
        self.raiderrole = raiderrole
        self.rlrole = rlrole
        self.runes = {"<:swordrune:737672554482761739>": [],
                      "<:shieldrune:737672554642276423>": [],
                      "<:helmrune:737673058722250782>": []}
        self.reacted_ids = []

    async def start(self):
        mentions = '<#738615552594935910> and <#706563122944802856>' if self.in_normal else 'vet section of <#738615552594935910> and <#736240706955378788>'
        self.rcembed = discord.Embed(description=f"Please read {mentions}.\nReact with a Rune if you would like to use it in an upcoming raid. "
                                          f"You will get a dm when the run starts if you react, so pay attention!\n**Runes do not have to meet requirements!**",
                              color=discord.Color.teal())
        self.rcembed.add_field(name="Confirmed Runes:", value="No Confirmed Runes! Please react below.")
        self.rcembed.set_author(name=f"Rune Check for Oryx 3 | Started by {self.ctx.author.display_name}", icon_url=self.ctx.author.avatar_url)
        self.rcembed.set_thumbnail(url='https://i.imgur.com/vojEZGO.gif')
        self.rcembed.set_footer(text="Rune Count started at")
        self.rcembed.timestamp = datetime.datetime.utcnow()

        self.rcmsg = await self.hcchannel.send(content="@here Rune Count for Oryx 3!", embed=self.rcembed)

        self.client.raid_db[self.ctx.guild.id]['afk'][self.rcmsg.id] = self
        for r in self.runes.keys():
            await self.rcmsg.add_reaction(r)

        self.cpembed = discord.Embed(title="Rune Count Control Panel", url=self.rcmsg.jump_url, description="Press 🔀 to convert this check into a QAFK.\nPress 🛑 to abort this "
                                                                                                            "Rune Count.",
                                     color=discord.Color.orange())
        self.cpembed.add_field(name="Confirmed <:shieldrune:737672554642276423> Runes:", value="No Confirmed Shield Runes.")
        self.cpembed.add_field(name="Confirmed <:swordrune:737672554482761739> Runes:", value="No Confirmed Sword Runes.")
        self.cpembed.add_field(name="Confirmed <:helmrune:737673058722250782> Runes:", value="No Confirmed Helm Runes.")
        self.cpmsg = await self.ctx.send(embed=self.cpembed)

        self.client.raid_db[self.ctx.guild.id]['cp'][self.cpmsg.id] = self
        await self.cpmsg.add_reaction("🔀")
        await self.cpmsg.add_reaction("🛑")

        self.autoend_task = asyncio.get_event_loop().create_task(self.autoend())

    async def autoend(self):
        await asyncio.sleep(7200)  # wait 2 hrs max
        await self.cpmsg.clear_reactions()
        await self.abort_rc(self.client.user)

    async def abort_rc(self, ended_by: discord.User, conversion=False):
        if conversion:
            pass
        elif ended_by.bot:
            pass # if ended by bot, we know the run timed out (2 HRS!!!)
        else:
            pass
        # do I send a dm saying the run was aborted??
        # cleanup cp handlers and such

    async def cp_handler(self, payload):
        if str(payload.emoji) == '🔀':
            if self.ctx.author.id in self.client.raid_db[self.ctx.guild.id]['leaders']:
                return await self.ctx.send("You cannot start another AFK while an AFK check is still up or a run log has not been completed.")
            await self.abort_rc(payload.member, conversion=True)

            qafk = QAfk(self.client, self.ctx, "Location has not been set yet.", self.hcchannel, self.raiderrole, self.rlrole, True)
            await qafk.start()

        elif str(payload.emoji) == '🛑':
            await self.abort_rc(payload.member)

    async def reaction_handler(self, payload):
        emote = str(payload.emoji)
        await self.rem
        if emote in self.runes.keys():
            if payload.member.id not in self.reacted_ids:
                await self.dm_handler(emote, payload.member)

    async def dm_handler(self, emote, member):
        msg = await member.send(f"Please react with {emote} to confirm you have this rune and are willing to bring it to a run! (Ignore this message if the reaction was a "
                                f"mistake).")

        await msg.add_reaction(emote)

        def check(react, user):
            return not user.bot and react.message.id == msg.id and str(react.emoji) == emote

        try:
            reaction, usr = await self.client.wait_for('reaction_add', timeout=20, check=check)
        except asyncio.TimeoutError:
            return await member.send("Timed out! Please re-confirm your reaction on the Rune Count.")

        self.reacted_ids.append(member.id)
        self.runes[emote].append(member)

        await member.send("Confirmed! Please wait for a run to start (I'll send a DM when one does!)")
        # ping leader if shield rune
        if 'shield' in emote:
            await self.ctx.send(f"{self.ctx.author.mention} SHIELD RUNE Reacted!")
        elif all([len(l) > 0 for l in self.runes.values()]):
            await self.ctx.send(f"{self.ctx.author.mention} ALL RUNES Confirmed!")
            await self.ctx.author.send(f'{self.ctx.author.mention} All runes were confirmed!')
            for l in self.runes.values():
                for m in l:
                    try:
                        await m.send(f"{m.mention} - All runes have been confirmed, an afk check will start soon!")
                    except discord.Forbidden:
                        pass

        await self.update_embeds()

    async def update_embeds(self):
        pass