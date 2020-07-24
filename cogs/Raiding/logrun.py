import asyncio

import discord
from discord.ext.commands import MemberConverter

import sql
import utils


class LogRun:

    def __init__(self, client, ctx, emojis, keyreacts, runtitle, members, rlrole, hcchannel, events=False, vialreacts=None, helmreacts=None,
                 shieldreacts=None, swordreacts=None, numruns=1, runleader=None):
        self.client = client
        self.ctx = ctx
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
        self.leader = runleader if runleader else ctx.author
        self.converter = utils.MemberLookupConverter()
        self.confirmedLogs = []
        self.pkeymember = None
        self.numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', "🔟"]
        self.startembed = discord.Embed(title=f"Log this Run: {ctx.author.display_name}",
                                        description="Press the ✅ reaction when you **finish** the run to log it in the database.\n\nTo cancel "
                                                    "logging if you ***didn't do the run***, press the 🗑️",
                                        color=discord.Color.gold())
        self.runstatusembed = discord.Embed(title=f"Run Status: {ctx.author.display_name}",
                                            description="Was the run successful? If so, react to the ✅ emoji, "
                                            "otherwise react to the ❌ emoji.", color=discord.Color.gold())
        self.otheremebed = discord.Embed(title=f"Log Other member {ctx.author.display_name}",
                                         description="Please mention the member who popped by inputting a member in "
                                            "any of the following formats:\n1. Lookup by ID.\n2. Lookup by mention.\n3. Lookup by "
                                            "name#discrim\n4. Lookup by name\n5. Lookup by nickname", color=discord.Color.gold())


    async def start(self):
        print("logrun author")
        print(self.ctx.author)
        self.msg = await self.ctx.send(content=self.ctx.author.mention, embed=self.startembed)
        await self.msg.add_reaction("✅")
        await self.msg.add_reaction("🗑️")

        def check(react, usr):
            if (str(react.emoji) == "✅" and react.message.channel.id == 687436051001638935):
                print("logrun check")
                print(usr)
                print(react.message.id)
                print(self.msg.id)
                print(str(react.emoji))
                print(usr.id == self.ctx.author.id and react.message.id == self.msg.id and (str(react.emoji) == "✅" or str(react.emoji) == '🗑️'))
            return not usr.bot and usr.id == self.ctx.author.id and react.message.id == self.msg.id and (str(react.emoji) == "✅" or str(react.emoji) == '🗑️')

        try:
            reaction, user = await self.client.wait_for('reaction_add', timeout=9000, check=check)  # Wait 2 hr max
        except asyncio.TimeoutError:
            embed = discord.Embed(title="Timed out!", description="You didn't log this run in time!", color=discord.Color.red())
            try:
                await self.msg.clear_reactions()
                return await self.msg.edit(embed=embed)
            except discord.NotFound:
                print("NOT FOUND WHEN LOGGING AWAIT")
                return
        else:
            print("MADE IT THROUGH CHECK!!")
            print(self.ctx.author)
            print(user)
            print(reaction)
            print(self.msg)
            print(self.keyreacts)
            print(self.helmreacts)
            print(self.swordreacts)
            print(self.shieldreacts)
            print(self.events)
            print(self.emojis)

            if str(reaction.emoji) == '🗑️':
                embed = discord.Embed(title="Cancelled!", description=f"{self.ctx.author.mention} cancelled this log.",
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

                keyembed = discord.Embed(title=f"Key Pop: {self.ctx.author.display_name}", description=descript, color=discord.Color.gold())

                if self.keyreacts:
                    keyembed.add_field(name="Other", value="To log a different key popper, react to the 🔄 emoji.")

                if self.events:
                    await self.memberlog(keyembed, self.keyreacts, sql.log_cols.eventkeys, self.emojis[1])
                else:
                    print("starting memberlog - key")
                    print(self.keyreacts)
                    print(keyembed.to_dict())
                    print(self.emojis[1])
                    await self.memberlog(keyembed, self.keyreacts, sql.log_cols.pkey, self.emojis[1])


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
                print("Starting o3 logging")
                desc = ""
                descript = ""
                if self.swordreacts:
                    for i, r in enumerate(self.swordreacts):
                        desc += self.numbers[i] + f" - {r.mention}\n"
                    descript = f"Users who confirmed sword rune ({self.emojis[2]}) with the bot:\n" + desc + "\n"
                descript += "Click the 🔄 to enter who popped. If you don't know, hit the ❌."
                embed = discord.Embed(title="Sword Rune Pop", description=descript, color=discord.Color.gold())
                await self.memberlog(embed, self.swordreacts, sql.log_cols.swordrunes, self.emojis[2])
                desc = ""
                descript = ""
                if self.shieldreacts:
                    for i, r in enumerate(self.shieldreacts):
                        desc += self.numbers[i] + f" - {r.mention}\n"
                    descript = f"Users who confirmed shield rune ({self.emojis[3]}) with the bot:\n" + desc + "\n"
                descript += "Click the 🔄 to enter who popped. If you don't know, hit the ❌."
                embed = discord.Embed(title="Shield Rune Pop",
                                      description=descript,
                                      color=discord.Color.gold())
                await self.memberlog(embed, self.shieldreacts, sql.log_cols.shieldrunes, self.emojis[3])
                desc = ""
                descript = ""
                if self.helmreacts:
                    for i, r in enumerate(self.helmreacts):
                        desc += self.numbers[i] + f" - {r.mention}\n"
                    descript = f"Users who confirmed helm rune ({self.emojis[4]}) with the bot:\n" + desc + "\n"
                descript += "Click the 🔄 to enter who popped. If you don't know, hit the ❌."
                embed = discord.Embed(title="Helm Rune Pop",
                                      description=descript,
                                      color=discord.Color.gold())
                await self.memberlog(embed, self.helmreacts, sql.log_cols.helmrunes, self.emojis[4])

            if self.events:
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
                    return usr == self.ctx.author and react.message.id == self.msg.id and (str(react.emoji) in self.numbers or
                                                                                           str(react.emoji) == '🔄' or str(react.emoji) == "❌")

                try:
                    reaction, user = await self.client.wait_for('reaction_add', timeout=7200, check=check)  # Wait 1 hr max
                except asyncio.TimeoutError:
                    embed = discord.Embed(title="Timed out!", description="You didn't log this run in time!", color=discord.Color.red())
                    await self.msg.clear_reactions()
                    return await self.msg.edit(embed=embed)

                if str(reaction.emoji) == '❌':
                    num = 0
                elif str(reaction.emoji) in self.numbers:
                    num = self.numbers.index(str(reaction.emoji))
                else:
                    embed = discord.Embed(title='Specify # of Chains', description='Please send the number of chains completed.',
                                          color=discord.Color.gold())
                    await self.msg.edit(embed=embed)

                    def number_check(m):
                        return m.author == self.ctx.author and m.channel == self.ctx.channel
                    while True:
                        try:
                            msg = await self.client.wait_for('message', timeout=7200, check=number_check)
                        except asyncio.TimeoutError:
                            embed = discord.Embed(title="Timed out!", description="You didn't choose a member in time!",
                                                  color=discord.Color.red())
                            await self.msg.clear_reactions()
                            return await self.msg.edit(embed=embed)

                        try:
                            num = int(msg.content)-1
                            try:
                                await msg.delete()
                            except discord.NotFound:
                                pass
                            if not 1 < num < 11:
                                await self.ctx.send("Please specify a number between 2-10.")
                            else:
                                break
                        except ValueError:
                            await self.ctx.send("Please only send a number (how many chains you completed)", delete_after=7)

                if num != 0 and num != 1:
                    if self.pkeymember:
                        embed = discord.Embed(title="Key", description=f"Were all the extra keys ({num}) popped by the same person? If so, "
                                                                       "react to the ✅, otherwise press the ❌.", color=discord.Color.gold())
                        await self.msg.clear_reactions()
                        await self.msg.edit(embed=embed)
                        await self.msg.add_reaction("✅")
                        await self.msg.add_reaction("❌")

                        def check(react, usr):
                            return usr == self.ctx.author and react.message.id == self.msg.id and (
                                        str(react.emoji) == "✅" or str(react.emoji) == "❌")

                        try:
                            reaction, user = await self.client.wait_for('reaction_add', timeout=7200, check=check)  # Wait 1 hr max
                        except asyncio.TimeoutError:
                            embed = discord.Embed(title="Timed out!", description="You didn't log this run in time!", color=discord.Color.red())
                            await self.msg.clear_reactions()
                            return await self.msg.edit(embed=embed)

                        if str(reaction.emoji) == '✅':
                            await sql.log_runs(self.client.pool, self.ctx.guild.id, self.pkeymember.id, sql.log_cols.eventkeys, num)
                            index = self.confirmedLogs.index((self.emojis[1], f"{self.pkeymember.mention}"))
                            del self.confirmedLogs[index]
                            self.confirmedLogs.insert(index, (self.emojis[1], f"{self.pkeymember.mention} x{num+1}"))
                        else:
                            for i in range(num):
                                embed = self.keyembed.copy()
                                embed.title = f"Chain - Key #{i+2}"
                                embed.description += f"\nPlease enter the member that popped key {i+2}/{num+1}."
                                await self.memberlog(embed, self.keyreacts, sql.log_cols.eventkeys, self.emojis[1])
                    else:
                        for i in range(num+1):
                            embed = self.keyembed.copy()
                            embed.title = f"Chain - Key #{i+1}"
                            embed.description += f"\nPlease enter the member that popped key {i+1}/{num+1}."
                            await self.memberlog(embed, self.keyreacts, sql.log_cols.eventkeys, self.emojis[1])

                await sql.log_runs(self.client.pool, self.ctx.guild.id, self.ctx.author.id, sql.log_cols.eventled, number=num+1)
                self.numruns = num + 1
            else:
                await self.msg.clear_reactions()
                await self.msg.edit(embed=self.runstatusembed)
                await self.msg.add_reaction("✅")
                await self.msg.add_reaction("❌")

                def check(react, usr):
                    return usr == self.ctx.author and react.message.id == self.msg.id and (str(react.emoji) == "✅" or str(react.emoji) == "❌")

                try:
                    reaction, user = await self.client.wait_for('reaction_add', timeout=7200, check=check)  # Wait 1 hr max
                except asyncio.TimeoutError:
                    embed = discord.Embed(title="Timed out!", description="You didn't log this run in time!", color=discord.Color.red())
                    await self.msg.clear_reactions()
                    return await self.msg.edit(embed=embed)

                col = sql.log_cols.srunled if str(reaction.emoji) == "✅" else sql.log_cols.frunled
                await sql.log_runs(self.client.pool, self.ctx.guild.id, self.leader.id, col, self.numruns)
                self.confirmedLogs.append(("Run Successful", str(reaction.emoji)))

            embed = discord.Embed(title="Logging...", description="Please wait while the run is logged in the database. "
                                  "This can take up to a minute at full run capacity.", color=discord.Color.orange())
            embed.set_thumbnail(url="https://i.imgur.com/nLRgnZf.gif")

            await self.msg.clear_reactions()
            await self.msg.edit(content=None, embed=embed)

            for m in self.members:
                m = self.ctx.guild.get_member(m)
                if m:
                    if self.events:
                        if m.top_role >= self.rlrole:
                            if not m.id == self.ctx.author.id:
                                await sql.log_runs(self.client.pool, self.ctx.guild.id, m.id, sql.log_cols.eventsassisted, self.numruns)

                        await sql.log_runs(self.client.pool, self.ctx.guild.id, m.id, sql.log_cols.eventsdone, self.numruns)
                    else:
                        if m.top_role >= self.rlrole:
                            if not m.id == self.ctx.author.id:
                                await sql.log_runs(self.client.pool, self.ctx.guild.id, m.id, sql.log_cols.runsassisted, self.numruns)
                        await sql.log_runs(self.client.pool, self.ctx.guild.id, m.id, sql.log_cols.runsdone, self.numruns)

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
            embed = discord.Embed(title="Run Logged!", description=desc, color=discord.Color.green())
            await self.msg.edit(embed=embed)

    async def memberlog(self, embed, reacts, column, emoji):
        print("in memberlog")
        await self.msg.clear_reactions()
        await self.msg.edit(embed=embed)
        print("edited msg")
        emojis = []
        if reacts:
            if len(reacts) > 5:
                reacts = reacts[:5]
            emojis = self.numbers[:len(reacts)]

        emojis.append("🔄")
        emojis.append("❌")
        asyncio.get_event_loop().create_task(self.add_emojis(self.msg, emojis))

        def check(react, usr):
            return usr.id == self.ctx.author.id and react.message.id == self.msg.id and str(react.emoji) in emojis

        try:
            reaction, user = await self.client.wait_for('reaction_add', timeout=9000, check=check)  # Wait 2.5 hr max
        except asyncio.TimeoutError:
            embed = discord.Embed(title="Timed out!", description="You didn't log this run in time!", color=discord.Color.red())
            await self.msg.clear_reactions()
            return await self.msg.edit(embed=embed)

        if str(reaction.emoji) == '❌':
            return
        elif str(reaction.emoji) in self.numbers:
            i = self.numbers.index(str(reaction.emoji))
            member = reacts[i]
            if isinstance(member, str):
                member = self.client.get_user(int(member))
        else:
            await self.msg.clear_reactions()
            await self.msg.edit(embed=self.otheremebed)
            def member_check(m):
                return m.author == self.ctx.author and m.channel == self.ctx.channel

            while True:
                try:
                    msg = await self.client.wait_for('message', timeout=7200, check=member_check)
                except asyncio.TimeoutError:
                    embed = discord.Embed(title="Timed out!", description="You didn't choose a member in time!", color=discord.Color.red())
                    await self.msg.clear_reactions()
                    return await self.msg.edit(embed=embed)

                try:
                    member = await self.converter.convert(self.ctx, str(msg.content))
                    try:
                        await msg.delete()
                    except discord.NotFound:
                        pass
                    break
                except discord.ext.commands.BadArgument:
                    await self.ctx.send(f"The member you specified (`{msg.content}`) was not found.", delete_after=7)

        if emoji == self.emojis[1]:
            self.pkeymember = member
        num = await sql.log_runs(self.client.pool, self.ctx.guild.id, member.id, column, self.numruns)
        if emoji == self.emojis[1] and not self.events and str(emoji) != '<:WineCellarInc:708191799750950962>':
            await utils.check_pops(self.client, self.ctx, member, self.numruns, num, emoji=emoji, hcchannel=self.hcchannel)
        # if (emoji, f"{member.mention}") in self.confirmedLogs:
        #     index = self.confirmedLogs.index((emoji, f"{member.mention}"))
        #     del self.confirmedLogs[index]
        #     self.confirmedLogs.append()
        # else:
        self.confirmedLogs.append((emoji, f"{member.mention}"))

    async def add_emojis(self, msg, emojis):
        for e in emojis:
            await msg.add_reaction(e)

