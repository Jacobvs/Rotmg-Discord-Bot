import asyncio

import discord
from discord.ext.commands import MemberConverter

import sql
import utils


class LogRun:

    def __init__(self, client, author, channel, guild, emojis, keyreacts, runtitle, members, rlrole, hcchannel, events=False, vialreacts=None, helmreacts=None,
                 shieldreacts=None, swordreacts=None, numruns=1, runleader=None):
        self.client = client
        self.author = author
        self.channel = channel
        self.guild = guild
        self.keyreacts = keyreacts[:5] if keyreacts else []
        self.emojis = emojis
        self.runtitle = runtitle
        self.members = members
        self.rlrole = rlrole
        self.hcchannel = hcchannel
        self.events = events
        self.vialreacts = vialreacts[:5] if vialreacts else []
        self.helmreacts = helmreacts[:5] if helmreacts else []
        self.shieldreacts = shieldreacts[:5] if shieldreacts else []
        self.swordreacts = swordreacts[:5] if swordreacts else []
        self.numruns = numruns
        self.leader = runleader if runleader else author
        self.converter = utils.MemberLookupConverter()
        self.confirmedLogs = []
        self.pkeymember = None
        self.numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', "🔟"]
        self.startembed = discord.Embed(title=f"Log this Run: {author.display_name}",
                                        description="Press the 📝 reaction when you **finish** the run to log it in the database.\n\nTo cancel "
                                                    "logging if you ***didn't do the run***, press the 🗑️",
                                        color=discord.Color.gold())
        self.runstatusembed = discord.Embed(title=f"Run Status: {author.display_name}",
                                            description="Was the run successful? If so, react to the ✅ emoji, "
                                            "otherwise react to the ❌ emoji.", color=discord.Color.gold())
        self.otheremebed = discord.Embed(title=f"Log Other member {author.display_name}",
                                         description="Please log who popped.\nType their __ROTMG IGN__, __Mention them__, or paste their __Discord ID__.",
                                         color=discord.Color.gold())


    async def start(self):
        print("LOGGING RUN! IN EVENTS? " + str(self.events))
        self.msg = await self.channel.send(content=self.author.mention, embed=self.startembed)
        await self.msg.add_reaction("📝")
        await self.msg.add_reaction("🗑️")

        def check(payload):
            # if str(payload.emoji) == "📝" and payload.channel_id == 687436051001638935:
            #     print("logrun check")
            #     print(f"Author: {self.author.display_name} | ID {self.author.id}")
            #     print(f"Reacted UserID: {payload.user_id}")
            #     print(payload.user_id == self.author.id and payload.message_id == self.msg.id and (str(payload.emoji) == "📝" or str(payload.emoji) == '🗑️'))
            return payload.user_id == self.author.id and payload.message_id == self.msg.id and (str(payload.emoji) == "📝" or str(payload.emoji) == '🗑️')

        try:
            payload = await self.client.wait_for('raw_reaction_add', check=check, timeout=10800)  # Wait
        except asyncio.TimeoutError:
            print("TIMED OUT IN LOGGING CHECK")
            print(f"Author of timeout: {self.author}")
            if self.author.id in self.client.raid_db[self.guild.id]['leaders']:
                self.client.raid_db[self.guild.id]['leaders'].remove(self.author.id)
            embed = discord.Embed(title="Timed out!", description="You didn't log this run in time!", color=discord.Color.red())
            try:
                await self.msg.clear_reactions()
                return await self.msg.edit(embed=embed)
            except discord.NotFound:
                print("NOT FOUND WHEN LOGGING AWAIT")
                return
        else:


            if str(payload.emoji) == '🗑️':
                if self.author.id in self.client.raid_db[self.guild.id]['leaders']:
                    self.client.raid_db[self.guild.id]['leaders'].remove(self.author.id)
                embed = discord.Embed(title="Cancelled!", description=f"{self.author.mention} cancelled this log.",
                                      color=discord.Color.red())
                await self.msg.clear_reactions()
                return await self.msg.edit(embed=embed)

            if self.runtitle != "Oryx 3":
                reacts = ""
                descript = ""
                if self.keyreacts:
                    for i, r in enumerate(self.keyreacts):
                        reacts += f"{self.numbers[i]} - {r.mention}\n"
                    descript = f"Users who confirmed key ({self.emojis[1]}) with the bot:\n{reacts}" + "\n"
                descript += "Click the 🔄 to enter who popped. If you don't know, hit the ❌."

                self.keyembed = discord.Embed(title=f"Key Pop: {self.author.display_name}", description=descript, color=discord.Color.gold())

                if self.keyreacts:
                    self.keyembed.add_field(name="Other", value="To log a different key popper, react to the 🔄 emoji.")

                if self.events:
                    await self.memberlog(self.keyembed, self.keyreacts, sql.log_cols.eventkeys, self.emojis[1])
                else:
                    await self.memberlog(self.keyembed, self.keyreacts, sql.log_cols.pkey, self.emojis[1])


            if self.runtitle == "Void" or self.runtitle == "Full-Skip Void":
                desc = ""
                descript = ""
                if self.vialreacts:
                    for i, r in enumerate(self.vialreacts):
                        desc += self.numbers[i] + f" - {r.mention}\n"
                    descript = f"Users who confirmed vial ({self.emojis[2]}) with the bot:\n" + desc + "\n"
                descript += "Click the 🔄 to enter who popped. If you don't know, hit the ❌."
                embed = discord.Embed(title="Vial Pop", description=descript, color=discord.Color.gold())
                await self.memberlog(embed, self.vialreacts, sql.log_cols.vials, self.emojis[2])
            elif self.runtitle == "Oryx 3":
                desc = ""
                descript = ""
                if any('sword' in str(emoji).lower() for emoji in self.emojis):
                    rune = next((x for x in self.emojis if 'sword' in str(x).lower()), "")
                    if self.swordreacts:
                        for i, r in enumerate(self.swordreacts):
                            desc += self.numbers[i] + f" - {r.mention}\n"
                        descript = f"Users who confirmed sword rune ({self.emojis[2]}) with the bot:\n" + desc + "\n"
                    descript += "Click the 🔄 to enter who popped. If you don't know, hit the ❌."
                    embed = discord.Embed(title="Sword Rune Pop", description=descript, color=discord.Color.gold())
                    await self.memberlog(embed, self.swordreacts, sql.log_cols.swordrunes, rune)
                desc = ""
                descript = ""
                if any('shield' in str(emoji).lower() for emoji in self.emojis):
                    rune = next((x for x in self.emojis if 'shield' in str(x).lower()), "")
                    if self.shieldreacts:
                        for i, r in enumerate(self.shieldreacts):
                            desc += self.numbers[i] + f" - {r.mention}\n"
                        descript = f"Users who confirmed shield rune ({self.emojis[3]}) with the bot:\n" + desc + "\n"
                    descript += "Click the 🔄 to enter who popped. If you don't know, hit the ❌."
                    embed = discord.Embed(title="Shield Rune Pop",
                                          description=descript,
                                          color=discord.Color.gold())
                    await self.memberlog(embed, self.shieldreacts, sql.log_cols.shieldrunes, rune)
                desc = ""
                descript = ""
                if any('helm' in str(emoji).lower() for emoji in self.emojis):
                    rune = next((x for x in self.emojis if 'helm' in str(x).lower()), "")
                    if self.helmreacts:
                        for i, r in enumerate(self.helmreacts):
                            desc += self.numbers[i] + f" - {r.mention}\n"
                        descript = f"Users who confirmed helm rune ({self.emojis[4]}) with the bot:\n" + desc + "\n"
                    descript += "Click the 🔄 to enter who popped. If you don't know, hit the ❌."
                    embed = discord.Embed(title="Helm Rune Pop",
                                          description=descript,
                                          color=discord.Color.gold())
                    await self.memberlog(embed, self.helmreacts, sql.log_cols.helmrunes, rune)

            num = 0
            if self.runtitle != 'Oryx 3' and self.numruns == 1:
                await self.msg.clear_reactions()
                embed = discord.Embed(title="Chain #", description="If you chained, please specify the number of runs chained. "
                                        "If the chain was longer than 5, react to the 🔄 emoji to specify how many you chained.\nIf you didn't chain, press the ❌",
                                      color=discord.Color.gold())
                await self.msg.edit(embed=embed)
                emojis = self.numbers[1:5]
                emojis.append("🔄")
                emojis.append("❌")
                asyncio.get_event_loop().create_task(self.add_emojis(self.msg, emojis))
                def check(react, usr):
                    return usr == self.author and react.message.id == self.msg.id and (str(react.emoji) in self.numbers or
                                                                                           str(react.emoji) == '🔄' or str(react.emoji) == "❌")

                try:
                    reaction, user = await self.client.wait_for('reaction_add', timeout=10800, check=check)  # Wait 1 hr max
                except asyncio.TimeoutError:
                    if self.author.id in self.client.raid_db[self.guild.id]['leaders']:
                        self.client.raid_db[self.guild.id]['leaders'].remove(self.author.id)
                    embed = discord.Embed(title="Timed out!", description="You didn't log this run in time!", color=discord.Color.red())
                    await self.msg.clear_reactions()
                    return await self.msg.edit(embed=embed)

                if str(reaction.emoji) == '❌':
                    num = self.numruns
                elif str(reaction.emoji) in self.numbers:
                    num = self.numbers.index(str(reaction.emoji)) + 1
                else:
                    embed = discord.Embed(title='Specify # of Chains', description='Please send the number of chains completed.',
                                          color=discord.Color.gold())
                    await self.msg.edit(embed=embed)

                    def number_check(m):
                        return m.author == self.author and m.channel == self.channel
                    while True:
                        try:
                            msg = await self.client.wait_for('message', timeout=10800, check=number_check)
                        except asyncio.TimeoutError:
                            if self.author.id in self.client.raid_db[self.guild.id]['leaders']:
                                self.client.raid_db[self.guild.id]['leaders'].remove(self.author.id)
                            embed = discord.Embed(title="Timed out!", description="You didn't choose a number of runs in time!",
                                                  color=discord.Color.red())
                            await self.msg.clear_reactions()
                            return await self.msg.edit(embed=embed)

                        try:
                            num = int(msg.content)
                            try:
                                await msg.delete()
                            except discord.NotFound:
                                pass
                            if not 0 < num < 16:
                                await self.channel.send("Please specify a number between 1-15.")
                            else:
                                break
                        except ValueError:
                            await self.channel.send("Please only send a number (how many dungeons you completed)", delete_after=7)
            else:
                num = self.numruns

            if num > 1 and self.runtitle != "Oryx 3":
                if self.pkeymember is not None:
                    embed = discord.Embed(title="Key", description=f"Were all the extra keys ({num}) popped by the same person? If so, "
                                                                   "react to the ✅, otherwise press the ❌.", color=discord.Color.gold())
                    await self.msg.clear_reactions()
                    await self.msg.edit(embed=embed)
                    await self.msg.add_reaction("✅")
                    await self.msg.add_reaction("❌")

                    def check(react, usr):
                        return usr == self.author and react.message.id == self.msg.id and (
                                    str(react.emoji) == "✅" or str(react.emoji) == "❌")

                    try:
                        reaction, user = await self.client.wait_for('reaction_add', timeout=108000, check=check)  # Wait 1 hr max
                    except asyncio.TimeoutError:
                        if self.author.id in self.client.raid_db[self.guild.id]['leaders']:
                            self.client.raid_db[self.guild.id]['leaders'].remove(self.author.id)
                        embed = discord.Embed(title="Timed out!", description="You didn't log this run in time!", color=discord.Color.red())
                        await self.msg.clear_reactions()
                        return await self.msg.edit(embed=embed)

                    if str(reaction.emoji) == '✅':
                        await sql.log_runs(self.client.pool, self.guild.id, self.pkeymember.id, sql.log_cols.eventkeys if self.events else sql.log_cols.pkey, num)
                        index = self.confirmedLogs.index((self.emojis[1], f"{self.pkeymember.mention}"))
                        del self.confirmedLogs[index]
                        self.confirmedLogs.insert(index, (self.emojis[1], f"{self.pkeymember.mention} x{num}"))
                    else:
                        for i in range(num-1):
                            embed = self.keyembed.copy()
                            embed.title = f"Chain - Key #{i+2}"
                            embed.description += f"\nPlease enter the member that popped key {i+2}/{num}."
                            if await self.memberlog(embed, self.keyreacts, sql.log_cols.eventkeys if self.events else sql.log_cols.pkey, self.emojis[1]) == '❌':
                                break

            if self.events:
                await sql.log_runs(self.client.pool, self.guild.id, self.author.id, sql.log_cols.eventled, number=num)
                self.confirmedLogs.append(("Run Successful", "✅"))
            else:
                self.numruns = num
                #else:
                await self.msg.clear_reactions()
                await self.msg.edit(embed=self.runstatusembed)
                await self.msg.add_reaction("✅")
                await self.msg.add_reaction("❌")

                def check(payload):
                    return payload.user_id == self.author.id and payload.message_id == self.msg.id and (str(payload.emoji) == "✅" or str(payload.emoji) == "❌")

                try:
                    payload = await self.client.wait_for('raw_reaction_add', timeout=10800, check=check)  # Wait 1 hr max
                except asyncio.TimeoutError:
                    if self.author.id in self.client.raid_db[self.guild.id]['leaders']:
                        self.client.raid_db[self.guild.id]['leaders'].remove(self.author.id)
                    embed = discord.Embed(title="Timed out!", description="You didn't log this run in time!", color=discord.Color.red())
                    await self.msg.clear_reactions()
                    return await self.msg.edit(embed=embed)

                col = sql.log_cols.srunled if str(payload.emoji) == "✅" else sql.log_cols.frunled
                await sql.log_runs(self.client.pool, self.guild.id, self.leader.id, col, self.numruns)
                self.confirmedLogs.append(("Run Successful", str(payload.emoji)))

            embed = discord.Embed(title="Logging...", description="Please wait while the run is logged in the database. "
                                  "This can take up to a minute at full run capacity.", color=discord.Color.orange())
            embed.set_thumbnail(url="https://i.imgur.com/nLRgnZf.gif")

            await self.msg.clear_reactions()
            await self.msg.edit(content=None, embed=embed)

            col1 = sql.log_cols.eventsassisted if self.events else sql.log_cols.runsassisted
            col2 = sql.log_cols.eventsdone if self.events else sql.log_cols.runsdone

            for m in self.members:
                m = self.guild.get_member(m)
                if m:
                    if m.top_role >= self.rlrole and self.guild.id != 713844220728967228 and m.id != self.leader.id: # disable for Malice
                        await sql.log_runs(self.client.pool, self.guild.id, m.id, col1, self.numruns)
                    await sql.log_runs(self.client.pool, self.guild.id, m.id, col2, self.numruns)

            desc = "Log Status:\n"
            for r in self.confirmedLogs:
                desc += r[0] + " - " + str(r[1]) + "\n"
            desc += "Run Leader - " + self.leader.mention + "\n"
            if len(self.members) != 1:
                desc += "# Raiders - " + str(len(self.members)) + "\n"
            else:
                desc += f"Manual run log for {self.numruns} runs.\n"
            # try:
            #     desc += str(self.confirmedLogs[-1][0]) + " - " + str(self.confirmedLogs[-1][1])
            # except IndexError:
            #     pass
            if self.author.id in self.client.raid_db[self.guild.id]['leaders']:
                self.client.raid_db[self.guild.id]['leaders'].remove(self.author.id)

            embed = discord.Embed(title="Run Logged!", description=desc, color=discord.Color.green())
            await self.msg.edit(embed=embed)

    async def memberlog(self, embed, reacts, column, emoji):
        await self.msg.clear_reactions()
        await self.msg.edit(embed=embed)
        emojis = []
        if reacts:
            if len(reacts) > 5:
                reacts = reacts[:5]
            emojis = self.numbers[:len(reacts)]

        emojis.append("🔄")
        emojis.append("❌")
        asyncio.get_event_loop().create_task(self.add_emojis(self.msg, emojis))

        def check(payload):
            return payload.user_id == self.author.id and payload.message_id == self.msg.id and str(payload.emoji) in emojis

        try:
            payload = await self.client.wait_for('raw_reaction_add', timeout=10800, check=check)  # Wait ~2 hr max
        except asyncio.TimeoutError:
            if self.author.id in self.client.raid_db[self.guild.id]['leaders']:
                self.client.raid_db[self.guild.id]['leaders'].remove(self.author.id)
            embed = discord.Embed(title="Timed out!", description="You didn't log this run in time!", color=discord.Color.red())
            await self.msg.clear_reactions()
            return await self.msg.edit(embed=embed)

        if str(payload.emoji) == '❌':
            return '❌'
        elif str(payload.emoji) in self.numbers:
            i = self.numbers.index(str(payload.emoji))
            member = reacts[i]
            if isinstance(member, str):
                member = self.client.get_user(int(member))
        else:
            await self.msg.clear_reactions()
            self.otheremebed.title = f"Log Other member {self.author.display_name} for {emoji}"
            await self.msg.edit(embed=self.otheremebed)
            def member_check(m):
                return m.author == self.author and m.channel == self.channel

            while True:
                try:
                    msg = await self.client.wait_for('message', timeout=10800, check=member_check)
                except asyncio.TimeoutError:
                    if self.author.id in self.client.raid_db[self.guild.id]['leaders']:
                        self.client.raid_db[self.guild.id]['leaders'].remove(self.author.id)
                    embed = discord.Embed(title="Timed out!", description="You didn't choose a member in time!", color=discord.Color.red())
                    await self.msg.clear_reactions()
                    return await self.msg.edit(embed=embed)

                try:
                    ctx = discord.ext.commands.Context(bot=self.client, prefix="!", guild=self.guild, message=msg)
                    member = await self.converter.convert(ctx, str(msg.content))
                    try:
                        await msg.delete()
                    except discord.NotFound:
                        pass
                    break
                except discord.ext.commands.BadArgument:
                    await self.channel.send(f"The member you specified (`{msg.content}`) was not found.", delete_after=7)

        if emoji == self.emojis[1]:
            self.pkeymember = member
        num = await sql.log_runs(self.client.pool, self.guild.id, member.id, column, 1)
        if emoji == self.emojis[1] and not self.events and str(emoji) != '<:WineCellarInc:708191799750950962>':
            await utils.check_pops(self.client, member, self.numruns, num, guild=self.guild, emoji=emoji, type='key', hcchannel=self.hcchannel)
        elif emoji == "<:helmrune:737673058722250782>":
            await utils.check_pops(self.client, member, self.numruns, num, guild=self.guild, emoji=emoji, type='helm', hcchannel=self.hcchannel)
        elif emoji == "<:shieldrune:737672554642276423>":
            await utils.check_pops(self.client, member, self.numruns, num, guild=self.guild, emoji=emoji, type='shield', hcchannel=self.hcchannel)
        elif emoji == "<:swordrune:737672554482761739>":
            await utils.check_pops(self.client, member, self.numruns, num, guild=self.guild, emoji=emoji, type='sword', hcchannel=self.hcchannel)
        elif emoji == "<:vial:682205784524062730>":
            await utils.check_pops(self.client, member, self.numruns, num, guild=self.guild, emoji=emoji, type='vial', hcchannel=self.hcchannel)

        # if (emoji, f"{member.mention}") in self.confirmedLogs:
        #     index = self.confirmedLogs.index((emoji, f"{member.mention}"))
        #     del self.confirmedLogs[index]
        #     self.confirmedLogs.append()
        # else:
        self.confirmedLogs.append((emoji, f"{member.mention}"))

    async def add_emojis(self, msg, emojis):
        for e in emojis:
            await msg.add_reaction(e)

