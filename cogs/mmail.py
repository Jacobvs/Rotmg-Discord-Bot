import asyncio
import datetime
import textwrap

import discord
from discord.ext import commands

import sql
import utils


class Mmail(commands.Cog):
    """Modmail Related Commands & Configuration"""

    def __init__(self, client):
        self.client = client


    @commands.command(usage='modmail', description='Send a modmail.', aliases=['mail', 'mod'])
    async def modmail(self, ctx):
        mail_message = ModmailMessage(self.client, ctx)
        await mail_message.start()

    @commands.command(usage='modmailsetup', description='Setup the modmail for this server.')
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def modmailsetup(self, ctx):
        if self.client.guild_db[ctx.guild.id][sql.gld_cols.modmailcategory]:
            return await ctx.send("This server already has a modmail category setup! If you want to change the name of the category, just rename it normally!")

        embed = discord.Embed(title="Name", description="Please type the name of the modmail category.", color=discord.Color.gold())
        msg = await ctx.send(embed=embed)

        def check(m):
            return m.author.id == ctx.author.id and msg.channel.id == m.channel.id

        try:
            namemsg = await self.client.wait_for('message', timeout=1800, check=check)
        except asyncio.TimeoutError:
            embed = discord.Embed(title="Timed out!", description="You didn't choose a name in time!", color=discord.Color.red())
            await msg.delete()
            return await ctx.send(embed=embed)

        name = str(namemsg.content)


        category = await ctx.guild.create_category(name=name)
        await sql.update_guild(self.client.pool, ctx.guild.id, 'modmailcategory', category.id)
        self.client.guild_db[ctx.guild.id][sql.gld_cols.modmailcategory] = category

        embed = discord.Embed(title="Configure", description="Please configure the appropriate permissions for the category. When you are done, react to the ✅ emoji to continue.",
                              color=discord.Color.gold())
        try:
            await msg.edit(embed=embed)
        except discord.NotFound:
            msg = await ctx.send(embed=embed)

        await msg.add_reaction("✅")

        def check(react, usr):
            return usr.id == ctx.author.id and react.message.id == msg.id and str(react.emoji) in ["✅", "❌"]

        try:
            reaction, user = await self.client.wait_for('reaction_add', timeout=1800, check=check)  # Wait 1/2 hr max
        except asyncio.TimeoutError:
            embed = discord.Embed(title="Timed out!", description="You didn't configure the category in time! Please configure the category as soon as you get a chance, "
                                                                  "then sync the log channel's permissions to the category.",
                                  color=discord.Color.red())
            await msg.edit(embed=embed)

        logchannel = await category.create_text_channel(name="0-modmail-log")
        await sql.update_guild(self.client.pool, ctx.guild.id, 'modmaillogchannel', logchannel.id)
        self.client.guild_db[ctx.guild.id][sql.gld_cols.modmaillogchannel] = logchannel

        embed = discord.Embed(title="Success!", description="The modmail category was successfully setup! You should be able to receive modmail now!", color=discord.Color.green())
        try:
            await msg.edit(embed=embed)
            await msg.clear_reactions()
        except discord.NotFound:
            await ctx.send(embed=embed)


    @commands.command(usage="reply <response>", description="Reply to a modmail. Must be used in the modmail channel you wish to respond to.", aliases=['respond'])
    @commands.guild_only()
    async def reply(self, ctx, *, response=None):
        await ctx.message.delete()

        modmail_category = self.client.guild_db[ctx.guild.id][sql.gld_cols.modmailcategory]
        if not modmail_category:
            return await ctx.send("This server does not have modmail setup yet! Contact an upper level staff if you believe this to be a mistake!")

        if not ctx.channel.category or ctx.channel.category != modmail_category:
            return await ctx.send(f"Please use this command in the appropriate modmail category ({modmail_category.text_channels[0].mention}), in a modmail thread channel.")

        if not ctx.channel.topic or "Modmail Channel" not in ctx.channel.topic:
            return await ctx.send("Please use this command in a channel for modmail threads below!")


        msgembed = discord.Embed(title="Response", description="Please type out your response to the modmail.", color=discord.Color.gold())
        member = ctx.guild.get_member(int(ctx.channel.topic.split(" - ")[0].split("Channel ")[1]))
        msg = None

        while True:
            if not response:
                if not msg:
                    msg = await ctx.send(embed=msgembed)

                def member_check(m):
                    return m.author.id == ctx.author.id and m.channel == ctx.channel
                try:
                    mailmsg = await self.client.wait_for('message', timeout=1800, check=member_check)
                except asyncio.TimeoutError:
                    embed = discord.Embed(title="Timed out!", description="You didn't write your response in time!", color=discord.Color.red())
                    return await msg.edit(embed=embed)

                response = str(mailmsg.content)
                await mailmsg.delete()

            if msg:
                await msg.delete()

            mailembed = discord.Embed(title=f"Modmail Response from {ctx.author.name} -> {member.name}", description="If this looks correct, please press the ✅ to send the "
                                      "message, otherwise press the 🔄 emoji to change your message.", color=discord.Color.gold())
            if len(response) <= 1024:
                mailembed.add_field(name="Response:", value=response, inline=False)
            else:
                lines = textwrap.wrap(response, width=1024)  # Wrap message before max len of field of 1024
                for i, l in enumerate(lines):
                    mailembed.add_field(name=f"Response (pt. {i+1})", value=l)
            mailembed.set_footer(text="Modmail response written at ")
            mailembed.timestamp = datetime.datetime.utcnow()

            msg = await ctx.send(embed=mailembed)
            await msg.add_reaction("✅")
            await msg.add_reaction("🔄")

            def check(react, usr):
                return usr.id == ctx.author.id and react.message.id == msg.id and str(react.emoji) in ["✅", "🔄"]

            try:
                reaction, user = await self.client.wait_for('reaction_add', timeout=1800, check=check)  # Wait 1/2 hr max
            except asyncio.TimeoutError:
                embed = discord.Embed(title="Timed out!", description="You didn't choose an option in time!",
                                      color=discord.Color.red())
                await msg.delete()
                return await ctx.author.send(embed=embed)

            await msg.clear_reactions()
            if str(reaction.emoji) == '✅':
                break
            else:
                response = None
                await msg.edit(embed=msgembed)


        embed = discord.Embed(title="Anonymous?", description="Would you like to send this message anonymously?", color=discord.Color.gold())
        await msg.edit(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        def check(react, usr):
            return usr.id == ctx.author.id and react.message.id == msg.id and str(react.emoji) in ["✅", "❌"]

        try:
            reaction, user = await self.client.wait_for('reaction_add', timeout=1800, check=check)  # Wait 1/2 hr max
        except asyncio.TimeoutError:
            embed = discord.Embed(title="Timed out!", description="You didn't choose an option in time!",
                                  color=discord.Color.red())
            await msg.delete()
            return await ctx.author.send(embed=embed)

        await msg.clear_reactions()
        if str(reaction.emoji) == '✅':
            anonymous = True
        else:
            anonymous = False

        if anonymous:
            mailembed.title += " (Sent Anonymously)"

        mailembed.description = "To close this thread, use the `close` command."

        await msg.delete()
        await ctx.send(embed=mailembed)

        if anonymous:
            mailembed.title = f"Anonmous Response from Staff in {ctx.guild.name}"

        mailembed.set_thumbnail(url="https://www.bootgum.com/wp-content/uploads/2018/07/Email_Open_550px-1.gif")
        mailembed.description = "To respond again to this message, use the `!modmail` command."
        await member.send(content=member.mention, embed=mailembed)


    @commands.command(usage='close <reason>', description="Close a modmail thread")
    @commands.guild_only()
    async def close(self, ctx, *, reason):
        await ctx.message.delete()

        modmail_category = self.client.guild_db[ctx.guild.id][sql.gld_cols.modmailcategory]
        if not modmail_category:
            return await ctx.send("This server does not have modmail setup yet! Contact an upper level staff if you believe this to be a mistake!")
        modmail_log_channel = self.client.guild_db[ctx.guild.id][sql.gld_cols.modmaillogchannel]

        if not ctx.channel.category or ctx.channel.category != modmail_category:
            return await ctx.send(f"Please use this command in the appropriate modmail category ({modmail_log_channel.mention}), in a modmail thread channel.")

        if not ctx.channel.topic or "Modmail Channel" not in ctx.channel.topic:
            return await ctx.send("Please use this command in a channel for modmail threads below!")

        member = ctx.guild.get_member(int(ctx.channel.topic.split(" - ")[0].split("Channel ")[1]))

        embed = discord.Embed(title="Ticket closed", description=f"Closed by {ctx.author.mention} for reason:\n\n{reason}.", color=discord.Color.red())
        embed.set_author(name=member.name, icon_url=member.avatar_url)
        embed.set_footer(text="Closed at ")
        embed.timestamp = datetime.datetime.utcnow()
        await modmail_log_channel.send(embed=embed)

        embed = discord.Embed(title=f"Modmail Thread Closed by: {ctx.author.name}", description=f"Closed for reason:\n\n{reason}.", color=discord.Color.red())
        await member.send(embed=embed)

        await ctx.channel.delete()



def setup(client):
    client.add_cog(Mmail(client))


class ModmailMessage:
    def __init__(self, client, ctx):
        self.client = client
        self.ctx = ctx
        self.numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

    async def start(self):
        if not self.ctx.guild:
            servers = []
            for g in self.client.guilds:
                if g.get_member(self.ctx.author.id):
                    servers.append(g)
            serverstr = ""
            for i, s in enumerate(servers[:10]):
                serverstr += self.numbers[i] + " - " + s.name + "\n"
            embed = discord.Embed(description="What server would you like to send modmail to?\n" + serverstr,
                                  color=discord.Color.gold())
            msg = await self.ctx.author.send(embed=embed)
            for e in self.numbers[:len(servers)]:
                await msg.add_reaction(e)

            def check(react, usr):
                return usr.id == self.ctx.author.id and react.message.id == msg.id and str(react.emoji) in self.numbers[:len(servers)]

            try:
                reaction, user = await self.client.wait_for('reaction_add', timeout=1800, check=check)  # Wait 1/2 hr max
            except asyncio.TimeoutError:
                embed = discord.Embed(title="Timed out!", description="You didn't choose a server in time!",
                                      color=discord.Color.red())
                await msg.delete()
                return await self.ctx.author.send(embed=embed)

            server = servers[self.numbers.index(str(reaction.emoji))]
            await msg.delete()

        else:
            try:
                await self.ctx.message.delete()
            except discord.NotFound:
                pass
            server = self.ctx.guild

        modmail_category = self.client.guild_db[server.id][sql.gld_cols.modmailcategory]
        if not modmail_category:
            return await self.ctx.author.send("This server does not have modmail setup yet! Contact an upper level staff if you believe this to be a mistake!")
        modmail_log_channel = self.client.guild_db[server.id][sql.gld_cols.modmaillogchannel]

        embed = discord.Embed(title="Is the modmail about a specific member?", description="If this message is "
                            "regarding someone in the server, please react to the ✅ emoji, otherwise react to the ❌.",
                            color=discord.Color.gold())
        try:
            msg = await self.ctx.author.send(embed=embed)
            dmchannel = msg.channel
        except discord.Forbidden:
            return await self.ctx.send(f"{self.ctx.author.mention} - You have DM's from server members disabled! Please enable DM's then try again.")

        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        def check(react, usr):
            return usr.id == self.ctx.author.id and react.message.id == msg.id and str(react.emoji) in ["✅", "❌"]

        try:
            reaction, user = await self.client.wait_for('reaction_add', timeout=1800, check=check)  # Wait 1/2 hr max
        except asyncio.TimeoutError:
            embed = discord.Embed(title="Timed out!", description="You didn't choose an option in time!",
                                  color=discord.Color.red())
            await msg.delete()
            return await self.ctx.author.send(embed=embed)

        await msg.delete()

        if str(reaction.emoji) == '✅':
            embed = discord.Embed(title="Please choose a member.", description="To select a member, use one of these formats:\n1. ROTMG IGN\n2.Discord ID\n3. Discord tag & "
                                                                               "descriminator (ex: Darkmatter#7321).", colour=discord.Color.gold())
            msg = await self.ctx.author.send(embed=embed)

            converter = utils.MemberLookupConverter()

            def member_check(m):
                return m.author.id == self.ctx.author.id and m.channel == dmchannel

            while True:
                try:
                    membermsg = await self.client.wait_for('message', timeout=1800, check=member_check)
                except asyncio.TimeoutError:
                    embed = discord.Embed(title="Timed out!", description="You didn't choose a member in time!", color=discord.Color.red())
                    await msg.delete()
                    return await self.ctx.author.send(embed=embed)

                try:
                    aboutmember = await converter.convert(self.ctx, str(membermsg.content), server)
                    try:
                        await msg.delete()
                    except discord.NotFound:
                        pass
                    break
                except discord.ext.commands.BadArgument:
                    await self.ctx.author.send(f"The member you specified (`{msg.content}`) was not found.", delete_after=7)
        else:
            aboutmember = None

        embed = discord.Embed(title="Describe your issue", description="Send a message with your modmail to this channel. Please be as descriptive as possible & include "
                                                                       "**links** (not attachments) to images/videos of proof if you have them.", color=discord.Color.gold())
        msg = await self.ctx.author.send(embed=embed)

        while True:
            def member_check(m):
                return m.author.id == self.ctx.author.id and m.channel == dmchannel
            try:
                mailmsg = await self.client.wait_for('message', timeout=1800, check=member_check)
            except asyncio.TimeoutError:
                embed = discord.Embed(title="Timed out!", description="You didn't write your modmail in time!", color=discord.Color.red())
                await msg.delete()
                return await self.ctx.author.send(embed=embed)

            content = str(mailmsg.content)
            mailembed = discord.Embed(title=f"Modmail from {self.ctx.author.name} -> {server.name}", description="If this looks correct, please press the ✅ to send the message, "
                                    "otherwise press the 🔄 emoji to change your message.", color=discord.Color.gold())
            if len(content) <= 1024:
                mailembed.add_field(name="Content:", value=content, inline=False)
            else:
                lines = textwrap.wrap(content, width=1024)  # Wrap message before max len of field of 1024
                for i, l in enumerate(lines):
                    mailembed.add_field(name=f"Content (pt. {i+1})", value=l)
            if aboutmember:
                mailembed.add_field(name="Regarding:", value=f"This modmail is regarding {aboutmember.nick}")
            mailembed.set_footer(text="Modmail written at ")
            mailembed.timestamp = datetime.datetime.utcnow()

            msg = await self.ctx.author.send(embed=mailembed)
            await msg.add_reaction("✅")
            await msg.add_reaction("🔄")

            def check(react, usr):
                return usr.id == self.ctx.author.id and react.message.id == msg.id and str(react.emoji) in ["✅", "🔄"]

            try:
                reaction, user = await self.client.wait_for('reaction_add', timeout=1800, check=check)  # Wait 1/2 hr max
            except asyncio.TimeoutError:
                embed = discord.Embed(title="Timed out!", description="You didn't choose an option in time!",
                                      color=discord.Color.red())
                await msg.delete()
                return await self.ctx.author.send(embed=embed)

            if str(reaction.emoji) == '✅':
                break
            else:
                await msg.delete()
                await self.ctx.author.send(embed=embed)


            #TODO: Add option to send anonymously


        user_ids = [int(c.topic.split(" - ")[0].split("Channel ")[1]) for c in modmail_category.text_channels if c.topic and " - " in c.topic]
        if self.ctx.author.id in user_ids:
            index = user_ids.index(self.ctx.author.id)+1
            modmail_channel = modmail_category.text_channels[index]
        else:
            modmail_channel = await modmail_category.create_text_channel(name=str(self.ctx.author), topic=f"Modmail Channel"
                                                                         f" {self.ctx.author.id} - DO NOT CHANGE THIS!")

        # Sort channels alphabetically by name
        by_name = sorted(modmail_category.text_channels, key=lambda c: c.name)
        min_position = min(by_name, key=lambda c: c.position).position
        for new_pos, ch in enumerate(by_name, start=min_position):
            if new_pos != ch.position:
                await ch.edit(position=new_pos)

        if aboutmember:
            over = modmail_channel.overwrites.update({aboutmember: discord.PermissionOverwrite(read_messages=False)})
            await modmail_channel.edit(overwrites=over)
            mailembed.set_field_at(len(mailembed.fields)-1, name="Regarding:", value=f"This modmail is regarding {aboutmember.mention}")

        mailembed.description = f"To reply to this message, use the `reply` command, or to close this thread use `close <reason>`.\nFrom: {self.ctx.author.mention}"
        mailembed.set_thumbnail(url="https://www.bootgum.com/wp-content/uploads/2018/07/Email_Open_550px-1.gif")
        await modmail_channel.send(embed=mailembed)

        embed = discord.Embed(title="New Ticket", description=f"Ticket opened in {modmail_channel.mention}.", color=discord.Color.green())
        embed.set_author(name=self.ctx.author, icon_url=self.ctx.author.avatar_url)
        embed.set_footer(text="Opened at ")
        embed.timestamp = datetime.datetime.utcnow()
        await modmail_log_channel.send(embed=embed)

        embed = discord.Embed(title="Success!", description="Your message was sent successfully! Please be patient, staff will respond as soon as possible.",
                              color=discord.Color.green())
        await self.ctx.author.send(embed=embed)


