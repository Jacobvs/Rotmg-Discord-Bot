import asyncio

import discord
from discord.ext.commands import MemberConverter

import sql


class LogRun:
    numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', "🔟"]

    def __init__(self, client, ctx, emojis, keyreacts, runtitle, members, rlrole, events=False, vialreacts=None, helmreacts=None,
                 shieldreacts=None, swordreacts=None, numruns=1, runleader=None):
        self.client = client
        self.ctx = ctx
        self.keyreacts = keyreacts
        self.emojis = emojis
        self.runtitle = runtitle
        self.members = members
        self.rlrole = rlrole
        self.events = events
        self.vialreacts = vialreacts
        self.helmreacts = helmreacts
        self.shieldreacts = shieldreacts
        self.swordreacts = swordreacts
        self.numruns = numruns
        self.leader = runleader if runleader else ctx.author
        self.converter = MemberConverter()
        self.confirmedLogs = []
        self.startembed = discord.Embed(title=f"Log this Run: {ctx.author.display_name}",
                                        description="Press the ✅ reaction when you finish the run to log it in the database.",
                                        color=discord.Color.gold())
        reacts = ""
        for i, r in enumerate(keyreacts[:10]):
            reacts += self.numbers[i] + " - <@" + r + ">\n"
        self.keyembed = discord.Embed(title=f"Key Pop: {ctx.author.display_name}",
                                      description=f"Users who confirmed key ({self.emojis[1]}) with the bot:\n"+reacts,
                                      color=discord.Color.gold())
        self.keyembed.add_field(name="Other", value="To log a different key popper, react to the 🔄 emoji.")
        self.runstatusembed = discord.Embed(title=f"Run Status: {ctx.author.display_name}",
                                            description="Was the run successful? If so, react to the ✅ emoji, "
                                            "otherwise react to the ❌ emoji.", color=discord.Color.gold())
        self.otheremebed = discord.Embed(title=f"Log Other member {ctx.author.display_name}",
                                         description="Please mention the member who popped by inputting a member in "
                                            "any of the following formats:\n1. Lookup by ID.\n2. Lookup by mention.\n3. Lookup by "
                                            "name#discrim\n4. Lookup by name\n5. Lookup by nickname", color=discord.Color.gold())


    async def start(self):
        self.msg = await self.ctx.send(content=self.ctx.author.mention, embed=self.startembed)
        await self.msg.add_reaction("✅")

        def check(react, usr):
            return usr == self.ctx.author and react.message.id == self.msg.id and str(react.emoji) == "✅"

        try:
            reaction, user = await self.client.wait_for('reaction_add', timeout=3600, check=check)  # Wait 1 hr max
        except asyncio.TimeoutError:
            embed = discord.Embed(title="Timed out!", description="You didn't log this run in time!", color=discord.Color.red())
            await self.msg.clear_reactions()
            return await self.msg.edit(embed=embed)

        if self.events:
            await self.memberlog(self.keyembed, self.keyreacts, sql.log_cols.eventkeys, self.emojis[1])
        else:
            await self.memberlog(self.keyembed, self.keyreacts, sql.log_cols.pkey, self.emojis[1])


        if self.runtitle == "Void" or self.runtitle == "Full-Skip Void":
            desc = ""
            for i, r in enumerate(self.vialreacts):
                desc += self.numbers[i] + " - <@" + r + ">\n"
            embed = discord.Embed(title="Vial Pop", description=f"Users who confirmed vial ({self.emojis[2]}) with the bot:\n"+desc,
                                      color=discord.Color.gold())
            await self.memberlog(embed, self.vialreacts, sql.log_cols.vials, self.emojis[2])
        elif self.runtitle == "Oryx 3":
            desc = ""
            for i, r in enumerate(self.swordreacts):
                desc += self.numbers[i] + " - <@" + r + ">\n"
            embed = discord.Embed(title="Sword Rune Pop", description=f"Users who confirmed sword rune ({self.emojis[2]}) with the bot:\n" +
                                                                      desc, color=discord.Color.gold())
            await self.memberlog(embed, self.swordreacts, sql.log_cols.swordrunes, self.emojis[2])
            desc = ""
            for i, r in enumerate(self.shieldreacts):
                desc += self.numbers[i] + " - <@" + r + ">\n"
            embed = discord.Embed(title="Shield Rune Pop",
                                  description=f"Users who confirmed shield rune ({self.emojis[3]}) with the bot:\n" + desc,
                                  color=discord.Color.gold())
            await self.memberlog(embed, self.shieldreacts, sql.log_cols.shieldrunes, self.emojis[3])
            desc = ""
            for i, r in enumerate(self.helmreacts):
                desc += self.numbers[i] + " - <@" + r + ">\n"
            embed = discord.Embed(title="Helm Rune Pop",
                                  description=f"Users who confirmed helm rune ({self.emojis[4]}) with the bot:\n" + desc,
                                  color=discord.Color.gold())
            await self.memberlog(embed, self.helmreacts, sql.log_cols.helmrunes, self.emojis[4])

        if self.events:
            await sql.log_runs(self.client.pool, self.ctx.guild.id, self.ctx.author.id, sql.log_cols.eventled)
        else:
            await self.msg.clear_reactions()
            await self.msg.edit(embed=self.runstatusembed)
            await self.msg.add_reaction("✅")
            await self.msg.add_reaction("❌")

            def check(react, usr):
                return usr == self.ctx.author and react.message.id == self.msg.id and (str(react.emoji) == "✅" or str(react.emoji) == "❌")

            try:
                reaction, user = await self.client.wait_for('reaction_add', timeout=3600, check=check)  # Wait 1 hr max
            except asyncio.TimeoutError:
                embed = discord.Embed(title="Timed out!", description="You didn't log this run in time!", color=discord.Color.red())
                await self.msg.clear_reactions()
                return await self.msg.edit(embed=embed)

            col = sql.log_cols.srunled if str(reaction.emoji) == "✅" else sql.log_cols.frunled
            await sql.log_runs(self.client.pool, self.ctx.guild.id, self.leader.id, col, self.numruns)
            self.confirmedLogs.append(("Run Successful", str(reaction.emoji)))

        for m in self.members:
            m = self.ctx.guild.get_member(m)
            if self.events:
                if m.top_role >= self.rlrole:
                    if not m.id == self.ctx.author.id:
                        await sql.log_runs(self.client.pool, self.ctx.guild.id, m.id, sql.log_cols.eventsassisted)

                await sql.log_runs(self.client.pool, self.ctx.guild.id, m.id, sql.log_cols.eventsdone)
            else:
                if m.top_role >= self.rlrole:
                    if not m.id == self.ctx.author.id:
                        await sql.log_runs(self.client.pool, self.ctx.guild.id, m.id, sql.log_cols.runsassisted)
                await sql.log_runs(self.client.pool, self.ctx.guild.id, m.id, sql.log_cols.runsdone)

        desc = "Log Status:\n"
        for r in self.confirmedLogs[:-1]:
            desc += r[0] + " - <@" + str(r[1]) + ">\n"
        desc += "Run Leader - " + self.leader.mention + "\n"
        if len(self.members) != 1:
            desc += "# Raiders - " + str(len(self.members)) + "\n"
        else:
            desc += f"Manual run log for {self.numruns} runs.\n"
        desc += self.confirmedLogs[-1][0] + " - " + self.confirmedLogs[-1][1]
        embed = discord.Embed(title="Run Logged!", description=desc, color=discord.Color.green())
        await self.msg.clear_reactions()
        await self.msg.edit(content=None, embed=embed)

    async def memberlog(self, embed, reacts, column, emoji):
        await self.msg.clear_reactions()
        await self.msg.edit(embed=embed)
        emojis = self.numbers[:len(reacts[:10])]
        emojis.append("🔄")
        emojis.append("❌")
        asyncio.get_event_loop().create_task(self.add_emojis(self.msg, emojis))

        def check(react, usr):
            return usr == self.ctx.author and react.message.id == self.msg.id and str(react.emoji) in emojis

        try:
            reaction, user = await self.client.wait_for('reaction_add', timeout=1800, check=check)  # Wait 1/2 hr max
        except asyncio.TimeoutError:
            embed = discord.Embed(title="Timed out!", description="You didn't log this run in time!", color=discord.Color.red())
            await self.msg.clear_reactions()
            return await self.msg.edit(embed=embed)

        if str(reaction.emoji) == '❌':
            return
        elif str(reaction.emoji) in self.numbers:
            i = self.numbers.index(str(reaction.emoji))
            memberid = reacts[i]
        else:
            await self.msg.clear_reactions()
            await self.msg.edit(embed=self.otheremebed)
            def member_check(m):
                return m.author == self.ctx.author and m.channel == self.ctx.channel

            while True:
                try:
                    msg = await self.client.wait_for('message', timeout=1800, check=member_check)
                except asyncio.TimeoutError:
                    embed = discord.Embed(title="Timed out!", description="You didn't choose a member in time!", color=discord.Color.red())
                    await self.msg.clear_reactions()
                    return await self.msg.edit(embed=embed)

                try:
                    member = await self.converter.convert(self.ctx, msg.content)
                    memberid = member.id
                    await msg.delete()
                    break
                except discord.ext.commands.BadArgument:
                    await self.ctx.send(f"The member you specified (`{msg}`) was not found.", delete_after=7)
                    await msg.delete()

        await sql.log_runs(self.client.pool, self.ctx.guild.id, memberid, column, self.numruns)
        self.confirmedLogs.append((emoji, memberid))

    async def add_emojis(self, msg, emojis):
        for e in emojis:
            await msg.add_reaction(e)

