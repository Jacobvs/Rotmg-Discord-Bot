import asyncio
import random
from datetime import datetime

import discord
from discord.ext import commands
from discord.ext.commands import BucketType

import checks
import embeds
import sql
import utils
from checks import is_rl_or_higher_check, is_bot_owner


def is_lorlie():
    def predicate(ctx):
        return ctx.message.author.id == 482120766893064192
    return commands.check(predicate)

def is_caped():
    def predicate(ctx):
        return ctx.message.author.id == 163394008603820032
    return commands.check(predicate)

class Misc(commands.Cog):
    """Miscellaneous Commands"""


    def __init__(self, client):
        self.client = client
        self.laughs = ["files/ahhaha.mp3", "files/jokerlaugh.mp3"]
        self.numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']


    @commands.command(usage="stats [member]", description="Check your or someone else's run stats.")
    async def stats(self, ctx, what=None):
        # if member:
        #     converter = utils.MemberLookupConverter()
        #     mem = await converter.convert(ctx, member, is_logging=True)
        #     if isinstance(mem, int):
        #         uid = mem
        #         try:
        #             mem = await self.client.fetch_user(mem)
        #         except discord.NotFound:
        #             return await ctx.send("Found member in database with id of: {mem} - but the user account has since been deleted!")
        #     else:
        #         uid = mem.id
        # else:
        #     mem = None
        #     uid = ctx.author.id
        member = None
        server_id = None
        if what:
            if what.strip().lower() == 'wonderland' or what.strip().lower() == 'woland':
                server_id = 666063675416641539
                server_name = "Wonderland ✶"
            elif ctx.guild:
                converter = utils.MemberLookupConverter()
                member = await converter.convert(ctx, what)

        author = member if member and ctx.guild else ctx.author
        if not server_id:
            if not ctx.guild:
                servers = []
                for g in self.client.guilds:
                    if g.get_member(author.id):
                        servers.append(g)
                serverstr = ""
                for i, s in enumerate(servers[:10]):
                    serverstr += self.numbers[i] + " - " + s.name + "\n"
                embed = discord.Embed(description="What server would you like to check stats for?\n"+serverstr, color=discord.Color.gold())
                msg = await ctx.author.send(embed=embed)
                for e in self.numbers[:len(servers)]:
                    await msg.add_reaction(e)

                def check(react, usr):
                    return usr == ctx.author and react.message.id == msg.id and str(react.emoji) in self.numbers[:len(servers)]
                try:
                    reaction, user = await self.client.wait_for('reaction_add', timeout=1800, check=check)  # Wait 1/2 hr max
                except asyncio.TimeoutError:
                    embed = discord.Embed(title="Timed out!", description="You didn't choose a server in time!", color=discord.Color.red())
                    await msg.clear_reactions()
                    return await msg.edit(embed=embed)

                server = servers[self.numbers.index(str(reaction.emoji))]
                server_id = server.id
                server_name = server.name
                author = servers[self.numbers.index(str(reaction.emoji))].get_member(author.id)
                await msg.delete()
            else:
                try:
                    await ctx.message.delete()
                except discord.NotFound:
                    pass
                server = ctx.guild
                server_id = server.id
                server_name = server.name

        data = await sql.get_log(self.client.pool, server_id, author.id)


        embed = discord.Embed(title=f"Stats for {author.display_name} in {server_name}", color=discord.Color.green())
        embed.set_thumbnail(url=author.avatar_url)
        embed.add_field(name="__**Key Stats**__", value="Popped: "
                        f"**{data[sql.log_cols.pkey]}**\nEvent Keys: **{data[sql.log_cols.eventkeys]}**\nVials: "
                        f"**{data[sql.log_cols.vials]}**\nSword Runes: **{data[sql.log_cols.swordrunes]}**\nShield Runes: "
                        f"**{data[sql.log_cols.shieldrunes]}**\nHelm Runes: **{data[sql.log_cols.helmrunes]}**", inline=False)
        if server_id == 660344559074541579:
            embed.add_field(name="__**Run Stats**__", value=f"Oryx 3 Completes: **{data[sql.log_cols.ocompletes]}**\nOryx 3 Fails: **{data[sql.log_cols.oattempts]}**\nEvents "
                                                            f"Completed: **{data[sql.log_cols.eventsdone]}**", inline=False)
        else:
            embed.add_field(name="__**Run Stats**__", value=f"Completed: **{data[sql.log_cols.runsdone]}**\nEvents Completed: **{data[sql.log_cols.eventsdone]}**", inline=False)
        gdb = self.client.guild_db.get(server_id)
        if gdb:
            erl = gdb[sql.gld_cols.eventrlid]
            role = erl if erl else gdb[sql.gld_cols.rlroleid]
            if author.top_role >= role:
                embed.add_field(name="__**Leading Stats**__", value="Successful Runs: "
                            f"**{data[sql.log_cols.srunled]}**\nFailed Runs: **{data[sql.log_cols.frunled]}**\nAssisted: "
                            f"**{data[sql.log_cols.runsassisted]}**\nEvents: **{data[sql.log_cols.eventled]}**\nEvents Assisted: "
                            f"**{data[sql.log_cols.eventsassisted]}**\nWeekly Runs Led: **{data[sql.log_cols.weeklyruns]}**\n"
                            f"Weekly Runs Assisted: **{data[sql.log_cols.weeklyassists]}**", inline=False)
        else:
            embed.add_field(name="__**Leading Stats**__", value="Successful Runs: "
                            f"**{data[sql.log_cols.srunled]}**\nFailed Runs: **{data[sql.log_cols.frunled]}**\nAssisted: "
                            f"**{data[sql.log_cols.runsassisted]}**\nEvents: **{data[sql.log_cols.eventled]}**\nEvents Assisted: "
                            f"**{data[sql.log_cols.eventsassisted]}**\nWeekly Runs Led: **{data[sql.log_cols.weeklyruns]}**\n"
                            f"Weekly Runs Assisted: **{data[sql.log_cols.weeklyassists]}**", inline=False)
        embed.timestamp = datetime.utcnow()
        if ctx.guild:
            return await ctx.send(embed=embed)
        await ctx.author.send(embed=embed)


    @commands.command(usage='djoke', description="This command doesn't exist..... Shh...")
    @commands.guild_only()
    @commands.is_owner()
    async def djoke(self, ctx):
        joke = utils.darkjoke()
        embed = discord.Embed(title=joke[0], description=joke[1])
        await ctx.send(embed=embed)

    @commands.command(usage='roast <member>', description="This command doesn't exist either")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def roast(self, ctx, member: utils.MemberLookupConverter):
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        roast = utils.get_roast()
        embed = discord.Embed(title=roast)
        await ctx.send(content=member.mention, embed=embed)

    @commands.command(usage='bubblewrap', description="Relieve some stress if that's your thing...")
    async def bubblewrap(self, ctx):
        await ctx.send("||💥||||💥||||💥||||💥||||💥||\n||💥||||💥||||💥||||💥||||💥||\n||💥||||💥||||💥||||💥||||💥||\n||💥||||💥||||💥||||💥||||💥||\n"
                       "||💥||||💥||||💥||||💥||||💥||\n||💥||||💥||||💥||||💥||||💥||")


    @commands.command(usage='ghostping <member>', description='shhh')
    @commands.is_owner()
    @commands.guild_only()
    @commands.max_concurrency(1, per=BucketType.guild)
    async def ghostping(self, ctx, member: utils.MemberLookupConverter):
        for channel in ctx.guild.text_channels:
            permissions: discord.Permissions = channel.permissions_for(member)
            if permissions.send_messages:
                await channel.send(member.mention, delete_after=1)


    @commands.command(usage='poll <title> [option 1] [option 2] [option 3]...',
                      description="Creates a poll with up to 2-10 options\n"
                                  "For options/titles with more than one word, surround the text with quotes.")
    @commands.guild_only()
    @commands.check_any(is_rl_or_higher_check(), is_bot_owner())
    async def poll(self, ctx, title, *options):
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        if len(options) < 2:
            options = ["Yes", "No"]
        if len(options) > 10:
            await ctx.send("Please specify at most 10 options for the poll.", delete_after=4)
            return

        embed = embeds.poll(title, options)  # Get poll embed
        msg = await ctx.send(embed=embed)
        for i in range(len(options)):  # add reactions to poll
            await msg.add_reaction(self.numbers[i])
        # TODO: Implement counter, add check to only allow reactions to 1 option (remove all but last react from each person)
        # TODO: add option to ping @here or @everyone

    @commands.command(usage="ooga <text>", description="Translate text into booga.")
    @commands.guild_only()
    @commands.cooldown(1, 300, type=BucketType.member)
    async def ooga(self, ctx, *, text):
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        if len(text) > 52:
            return await ctx.send("Please send a message 50 characters or less.")

        if not all(ord(c) < 128 for c in text):
            return await ctx.send("Please only use alphanumeric characters!")

        str = ' '.join(["{0:b}".format(x) for x in bytes(text, "ascii")])
        obs = []
        for c in str.split(" "):
            cs = []
            for b in c:
                if b == '0':
                    cs.append("Ooga")
                else:
                    cs.append("Booga")
            obs.append(" ".join(cs))

        embed = discord.Embed(title=f"Oogified text | Decode with {ctx.prefix}booga <encoded_text>", description=" - ".join(obs), color=discord.Color.teal())
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")
        await ctx.send(embed=embed)

    @commands.command(usage='booga <encoded_text>', description='Decode booga text.')
    @commands.guild_only()
    async def booga(self, ctx, *, text):
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

        bs = ""
        for s in text.split(" - "):
            for c in s.split(" "):
                if c == "Ooga":
                    bs += "0"
                else:
                    bs += "1"
            bs += " "
        try:
            await ctx.author.send(f"Decoded text:\n{''.join([chr(int(binary, 2)) for binary in bs.split(' ') if binary])}")
            await ctx.send(embed=discord.Embed(description="The decoded text has been sent to your DM's!"))
        except discord.Forbidden:
            await ctx.send("Please enable DM's to use this command!")


    @commands.command(usage='isgay <member>', description="Preed's Custom Patreon Command")
    async def isgay(self, ctx, member: utils.MemberLookupConverter):
        if member.id == self.client.user.id:
            await ctx.send(f"Preed's Custom Patreon Command!\n__{member.display_name}__: Hmm, I don't think so...")
        b = bool(random.getrandbits(1))
        b2 = bool(random.getrandbits(1))
        b3 = bool(random.getrandbits(1))
        d = f"🌈__{member.display_name}__🌈: I've never been so sure of anything." if b and b2 and b3 else f"🌈__{member.display_name}__🌈: Yes." if b and b2 else \
            f"__{member.display_name}__: I'm pretty sure." if b else f"__{member.display_name}__: Hmm, I don't think so..."
        await ctx.send(f"Preed's Custom Patreon Command!\n{d}")

    @commands.command(usage='bean <member>', description="Lorlie's Custom Patreon Command")
    @commands.guild_only()
    @commands.check_any(is_lorlie(), checks.is_security_or_higher_check())
    @commands.cooldown(1, 1800, BucketType.member)
    async def bean(self, ctx, member: utils.MemberLookupConverter):
        if member.bot:
            commands.Command.reset_cooldown(ctx.command, ctx)
            return await ctx.send(f'Cannot bean `{member.display_name}` (is a bot).')
        if ctx.author.id != self.client.owner_id:
            if member.guild_permissions.manage_guild and ctx.author.id not in self.client.owner_ids:
                commands.Command.reset_cooldown(ctx.command, ctx)
                return await ctx.send(f'Cannot bean `{member.display_name}` due to roles.')
        if member.id in self.client.beaned_ids:
            commands.Command.reset_cooldown(ctx.command, ctx)
            return await ctx.send(f"{member.display_name}__ is already Beaned!")
        self.client.beaned_ids.add(member.id)
        await ctx.send(f"Lorlie's Custom Patreon Command!\n__{member.display_name}__ was Beaned!")
        await asyncio.sleep(240)
        if member.id in self.client.beaned_ids:
            self.client.beaned_ids.remove(member.id)
            await ctx.send(f"Lorlie's Custom Patreon Command!\n__{member.display_name}__ was automatically Un-Beaned!")

    @commands.command(usage='unbean <member>', description="Lorlie's Custom Patreon Command")
    @commands.guild_only()
    @commands.check_any(is_lorlie(), checks.is_security_or_higher_check())
    async def unbean(self, ctx, member: utils.MemberLookupConverter):
        if member.id not in self.client.beaned_ids:
            return await ctx.send(f"{member.display_name}__ is not currently Beaned!")

        self.client.beaned_ids.remove(member.id)
        await ctx.send(f"Lorlie's Custom Patreon Command!\n__{member.display_name}__ was Un-Beaned!")


    @commands.command(usage='exalted <member>', description="Make a member exalted!")
    @commands.guild_only()
    @commands.check_any(is_caped(), is_bot_owner())
    async def exalted(self, ctx, member: utils.MemberLookupConverter):
        b = bool(random.getrandbits(1))
        title = f"{member.display_name} was killed by O3!" if b else f"{member.display_name} slaughtered O3"
        embed = discord.Embed(title=title, color=discord.Color.gold())
        embed.set_image(url=utils.get_random_oryx())
        await ctx.send(f"{member.mention} was exalted by {ctx.author.display_name}", embed=embed)


def setup(client):
    client.add_cog(Misc(client))

