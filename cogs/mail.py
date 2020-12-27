import asyncio
import datetime
import textwrap

import discord
from discord.ext import commands

import sql
import utils


class Mail(commands.Cog):
    """Modmail Related Commands & Configuration"""

    def __init__(self, client):
        self.client = client


    @commands.command(usage='modmail', description='Send a modmail.', aliases=['mmail', 'mod'])
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
        storagechannel = await category.create_text_channel(name="1-mail-storage")
        await sql.update_guild(self.client.pool, ctx.guild.id, 'modmaillogchannel', logchannel.id)
        await sql.update_guild(self.client.pool, ctx.guild.id, 'modmailstoragechannel', storagechannel.id)
        self.client.guild_db[ctx.guild.id][sql.gld_cols.modmaillogchannel] = logchannel

        embed = discord.Embed(title="Success!", description="The modmail category was successfully setup! You should be able to receive modmail now!", color=discord.Color.green())
        try:
            await msg.edit(embed=embed)
            await msg.clear_reactions()
        except discord.NotFound:
            await ctx.send(embed=embed)


    @commands.command(usage="reply", description="Reply to a modmail. Must be used in the modmail channel you wish to respond to.", aliases=['respond'])
    @commands.guild_only()
    async def reply(self, ctx):
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
            images = []
            txt_file = None
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
            if mailmsg.attachments:
                images = [i for i in mailmsg.attachments if i.height]
                if not images:
                    txt_files = [a for a in mailmsg.attachments if a.filename.split('.')[1].lower() == 'txt']
                    if len(txt_files) < 1:
                        await ctx.send("Please only send images or .txt files for proof.", delete_after=7)
                        continue
                    elif len(txt_files) > 1:
                        await ctx.send("Please only attach 1 .txt file for proof.", delete_after=7)
                        continue
                    txt_file = await txt_files[0].to_file()
                    bytes = await txt_files[0].read()
                    text = str(bytes, encoding='utf-8')
                    if len(text) > 1:
                        response += f"\n**--File ({txt_files[0].filename})--**\n"
                        response += text
                else:
                    images = [await utils.image_upload(await i.read(), ctx, is_rc=False) for i in images]
            if not response and not images:
                await ctx.send('Please type something out or attach an image.')
                continue
            if not response:
                response = "No response provided, look at image(s) below."


            try:
                await mailmsg.delete()
            except discord.NotFound:
                pass

            if msg:
                await msg.delete()

            mailembed = discord.Embed(title=f"Modmail Response from {ctx.author.name} -> {member.name}", description="If this looks correct, please press the ✅ to send the "
                                      "message, otherwise press the 🔄 emoji to change your message.", color=discord.Color.gold())
            if len(response) > 4096:
                response = response[:4055]
                response += "\n**Message Continues in File Below.**"
            if len(response) <= 1024:
                mailembed.add_field(name="Response:", value=response, inline=False)
            else:
                lines = textwrap.wrap(response, width=1024)  # Wrap message before max len of field of 1024
                for i, l in enumerate(lines):
                    mailembed.add_field(name=f"Response (pt. {i+1})", value=l, inline=False)
            if images:
                mailembed.add_field(name="Proof Images:", value=f"{len(images)} Images will be attached to this response.", inline=False)
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

        mailembed.description = f"To close this thread, use the `{ctx.prefix}close` command."

        await msg.delete()
        modmail_storage = self.client.guild_db[ctx.guild.id][sql.gld_cols.modmailstoragechannel]
        await modmail_storage.send(embed=mailembed)
        await ctx.send(embed=mailembed)

        if anonymous:
            mailembed.title = f"Anonmous Response from Staff in {ctx.guild.name}"

        mailembed.set_thumbnail(url="https://www.bootgum.com/wp-content/uploads/2018/07/Email_Open_550px-1.gif")
        mailembed.color = discord.Color.teal()
        mailembed.description = "To respond again to this message, use the `!modmail` command."
        await member.send(content=member.mention, embed=mailembed)

        for i, img in enumerate(images, start=1):
            embed = discord.Embed(title=f"Proof #{i}")
            embed.set_image(url=img["secure_url"])
            await ctx.send(embed=embed)
            await member.send(embed=embed)

        if txt_file:
            await member.send(file=txt_file)


    @commands.command(usage='close <reason>', description="Close a modmail thread")
    @commands.guild_only()
    async def close(self, ctx, *, reason=None):
        await ctx.message.delete()

        modmail_category = self.client.guild_db[ctx.guild.id][sql.gld_cols.modmailcategory]
        if not modmail_category:
            return await ctx.send("This server does not have modmail setup yet! Contact an upper level staff if you believe this to be a mistake!")
        modmail_log_channel = self.client.guild_db[ctx.guild.id][sql.gld_cols.modmaillogchannel]

        if not ctx.channel.category or ctx.channel.category != modmail_category:
            return await ctx.send(f"Please use this command in the appropriate modmail category ({modmail_log_channel.mention}), in a modmail thread channel.")

        if not ctx.channel.topic or "Modmail Channel" not in ctx.channel.topic:
            return await ctx.send("Please use this command in a channel for modmail threads below!")

        if not reason:
            reason = "No reason specified."

        member = ctx.guild.get_member(int(ctx.channel.topic.split(" - ")[0].split("Channel ")[1]))

        embed = discord.Embed(title="Ticket closed", description=f"Closed by {ctx.author.mention} for reason:\n\n{reason}.", color=discord.Color.red())
        if member:
            embed.set_author(name=member.display_name, icon_url=member.avatar_url)
        embed.set_footer(text="Closed at ")
        embed.timestamp = datetime.datetime.utcnow()
        await modmail_log_channel.send(embed=embed)

        embed = discord.Embed(title=f"Modmail Thread Closed.", description=f"Please use {ctx.prefix}modmail if you'd like to start a new ticket.\n\nClosed for reason:\n{reason}",
                              color=discord.Color.red())
        if member:
            await member.send(embed=embed)

        await ctx.channel.delete()



def setup(client):
    client.add_cog(Mail(client))


class ModmailMessage:
    def __init__(self, client, ctx):
        self.client = client
        self.ctx = ctx
        self.numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

    async def start(self):
        if not self.ctx.guild:
            servers = []
            for g in self.client.guilds:
                if self.client.guild_db[g.id][sql.gld_cols.modmailcategory]:
                    if g.get_member(self.ctx.author.id):
                        servers.append(g)
            if len(servers) > 1:
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
                server = servers[0]
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
        modmail_storage = self.client.guild_db[server.id][sql.gld_cols.modmailstoragechannel]

        blacklisted = await sql.get_blacklist(self.client.pool, self.ctx.author.id, server.id, 'modmail')
        if blacklisted:
            embed = discord.Embed(title="Modmail attempt (Blacklisted!)", description=f"{self.ctx.author.mention} was prevented from sending modmail due to blacklist.",
                                  color=discord.Color.orange())
            embed.set_author(name=self.ctx.author.display_name, icon_url=self.ctx.author.avatar_url)
            embed.set_footer(text="Attempted at ")
            embed.timestamp = datetime.datetime.utcnow()
            await modmail_log_channel.send(embed=embed)
            return await self.ctx.author.send("You have been blacklisted from sending modmail in this server! Contact a security+ if you believe this to be a mistake!")


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
            embed = discord.Embed(title="Please choose a member.", description="To select a member, please type their ROTMG IGN.", colour=discord.Color.gold())
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
                                                                       "an attached image/video showing proof if you have it.\nIf the message is over 2k characters, "
                                                                       "send it as a .txt file (as discord will suggest).", color=discord.Color.gold())
        msg = await self.ctx.author.send(embed=embed)

        while True:
            images = []
            txt_file = None
            def member_check(m):
                return m.author.id == self.ctx.author.id and m.channel == dmchannel
            try:
                mailmsg = await self.client.wait_for('message', timeout=1800, check=member_check)
            except asyncio.TimeoutError:
                embed = discord.Embed(title="Timed out!", description="You didn't write your modmail in time!", color=discord.Color.red())
                await msg.delete()
                return await self.ctx.author.send(embed=embed)

            content = str(mailmsg.content)
            if not content:
                content = "No mail content provided."
            if mailmsg.attachments:
                images = [i for i in mailmsg.attachments if i.height]
                if not images:
                    txt_files = [a for a in mailmsg.attachments if a.filename.split('.')[1].lower() == 'txt']
                    if len(txt_files) < 1:
                        await self.ctx.author.send("Please only send images or .txt files for proof.", delete_after=7)
                        continue
                    elif len(txt_files) > 1:
                        await self.ctx.author.send("Please only attach 1 .txt file for proof.", delete_after=7)
                        continue
                    txt_file = await txt_files[0].to_file()
                    bytes = await txt_files[0].read()
                    text = str(bytes, encoding='utf-8')
                    if len(text) > 1:
                        content += f"\n**--File ({txt_files[0].filename})--**\n"
                        content += text
                else:
                    images = [await utils.image_upload(await i.read(), self.ctx.author, is_rc=False) for i in images]
            mailembed = discord.Embed(title=f"Modmail from {self.ctx.author.name} -> {server.name}", description="If this looks correct, please press the ✅ to send the message, "
                                    "otherwise press the 🔄 emoji to change your message.", color=discord.Color.gold())

            if len(content) > 4096:
                content = content[:4055]
                content += "\n**Message Continues in File Below.**"
            if len(content) <= 1024:
                mailembed.add_field(name="Content:", value=content, inline=False)
            else:
                lines = textwrap.wrap(content, width=1024)  # Wrap message before max len of field of 1024
                for i, l in enumerate(lines):
                    mailembed.add_field(name=f"Content (pt. {i+1})", value=l, inline=False)
            if images:
                mailembed.add_field(name="Proof Images:", value=f"{len(images)} Image will be attached to this response.", inline=False)
            if aboutmember:
                mailembed.add_field(name="Regarding:", value=f"This modmail is regarding {aboutmember.nick}", inline=False)
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


        # Find channel
        modmail_channel = None
        for c in modmail_category.text_channels:
            if c.topic and ' - DO NOT CHANGE THIS!' in c.topic:
                try:
                    id = int(c.topic.split(" - ")[0].split("Channel ")[1])
                    if id == self.ctx.author.id:
                        modmail_channel = c
                        created = False
                        break
                except ValueError:
                    pass
        if not modmail_channel:
            modmail_channel = await modmail_category.create_text_channel(name=str(self.ctx.author), topic=f"Modmail Channel"
                                                                         f" {self.ctx.author.id} - DO NOT CHANGE THIS!")
            created = True

        # Sort channels alphabetically by name
        by_name = sorted(modmail_category.text_channels, key=lambda c: c.name)
        min_position = min(by_name, key=lambda c: c.position).position
        for new_pos, ch in enumerate(by_name, start=min_position):
            if new_pos != ch.position:
                try:
                    await ch.edit(position=new_pos)
                except discord.Forbidden:
                    break

        if aboutmember:
            over = modmail_channel.overwrites
            over[aboutmember] = discord.PermissionOverwrite(read_messages=False)
            await modmail_channel.edit(overwrites=over)
            mailembed.set_field_at(len(mailembed.fields)-1, name="Regarding:", value=f"This modmail is regarding {aboutmember.mention}")

        mailembed.description = f"To reply to this message, use the `{self.ctx.prefix}reply` command, or to close this thread use `{self.ctx.prefix}close <reason>`.\nFrom:" \
                                f" {self.ctx.author.mention}"
        mailembed.set_thumbnail(url="https://www.bootgum.com/wp-content/uploads/2018/07/Email_Open_550px-1.gif")
        mailembed.color = discord.Color.green()
        await modmail_channel.send(embed=mailembed)
        await modmail_storage.send(embed=mailembed)
        for i, img in enumerate(images, start=1):
            embed = discord.Embed(title=f"Proof #{i}")
            embed.set_image(url=img["secure_url"])
            await modmail_channel.send(embed=embed)
            await modmail_storage.send(embed=embed)
        if txt_file:
            await modmail_channel.send(file=txt_file)
            await modmail_storage.send(embed=txt_file)

        title = "New Ticket" if created else "Response"
        desc = "opened in" if created else "responded to"
        color = discord.Color.green() if created else discord.Color.teal()


        embed = discord.Embed(title=title, description=f"Ticket {desc} `{modmail_channel.name}` by {self.ctx.author.mention}.", color=discord.Color.green())
        embed.set_author(name=self.ctx.author.display_name, icon_url=self.ctx.author.avatar_url)
        embed.set_footer(text="Opened at ")
        embed.timestamp = datetime.datetime.utcnow()
        await modmail_log_channel.send(embed=embed)


        embed = discord.Embed(title="Success!", description="Your message was sent successfully! Please be patient, staff will respond as soon as possible.",
                              color=discord.Color.green())
        await self.ctx.author.send(embed=embed)


