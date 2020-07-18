import asyncio
import bisect
import io
import json
from datetime import datetime
from difflib import get_close_matches

import discord
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

import embeds
import utils


class RealmClear:

    numbers = ['1️⃣','2️⃣','3️⃣','4️⃣','5️⃣','6️⃣','7️⃣','8️⃣','9️⃣', "🔟", "<:11:710641817539969076>", "<:12:710641817867124816>", "<:13:710641817887965224>"]
    emojis = ["<:defaultdungeon:682212333182910503>", "<:trickster:682214467483861023>", "<:Warrior_1:585616162407186433>",
              "<:ninja_3:585616162151202817>"]

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
        self.markers = []
        self.markers.append(ctx.author.id)
        self.guild_db = self.client.guild_db.get(self.ctx.guild.id)
        self.raiderids = []
        self.raiderids.append(ctx.author.id)
        self.markednums = []
        self.events = {}
        self.nitroboosters = []
        with open("data/world_data_clean.json") as file:
            self.world_data = json.load(file)
        self.raiderids.append(ctx.author.id)
        self.worldembed = discord.Embed(title="Realm Clearing AFK",
                                        description="Please choose what world you'd like to start an afk check for.",
                                        color=discord.Color.green())
        self.locationembed = discord.Embed(title="Realm Clearing AFK",
                                        description="Please choose what channel you'd like to start this afk check in.",
                                        color=discord.Color.green())
        matplotlib.use('agg')


    async def start(self):
        self.client.mapmarkers[self.ctx.author.id] = self
        await self.setup_msg.edit(embed=self.worldembed)
        for r in self.numbers:
            await self.setup_msg.add_reaction(r)

        def world_check(reaction, user):
            return user == self.ctx.author and reaction.message.id == self.setup_msg.id and str(reaction.emoji) in self.numbers

        try:
            reaction, user = await self.client.wait_for('reaction_add', timeout=60, check=world_check)
        except asyncio.TimeoutError:
            mapembed = discord.Embed(title="Timed out!", description="You didn't choose a world in time!", color=discord.Color.red())
            await self.setup_msg.clear_reactions()
            return await self.setup_msg.edit(embed=mapembed)

        self.world_num = self.numbers.index(str(reaction.emoji))+1
        self.world_data = self.world_data[f"world_{self.world_num}.png"]

        await self.setup_msg.delete()
        await self.vcchannel.set_permissions(self.raiderrole, connect=True, view_channel=True, speak=False)
        embed = embeds.afk_check_base("Realm Clearing", self.ctx.author, False, self.emojis, ["<:planewalker:682212363889279091>"])
        embed.color = discord.Color.gold()
        self.afkmsg = await self.hcchannel.send(f"@here `Realm Clearing` {self.emojis[0]} started by {self.ctx.author.mention} "
                                                f"in {self.vcchannel.name}", embed=embed)

        for emoji in self.emojis:
            await self.afkmsg.add_reaction(emoji)
        await self.afkmsg.add_reaction('<:shard:682365548465487965>')
        await self.afkmsg.add_reaction('❌')

        img_data = await utils.image_upload(open(f"world-maps/world_{self.world_num}.jpg", 'rb'), self.ctx)
        if not img_data:
            return await self.ctx.send("There was an issue communicating with the image server, try again and if the issue "
                                  "persists – contact the developer.", delete_after=10)

        cp = embeds.afk_check_control_panel(self.afkmsg.jump_url, self.location, "Realm Clearing", self.emojis[1], False)
        cp.add_field(name="Markers", value="".join("<@"+str(m)+">" for m in self.markers)+".", inline=True)
        cp.add_field(name="Events Spawned:", value="No events currently spawned", inline=False)
        cp.set_image(url=img_data["secure_url"])
        self.cpmsg = await self.ctx.send("React with :pencil: to toggle map marking for this session",
                                         embed=cp)
        await self.cpmsg.add_reaction("📝")
        mapembed = discord.Embed(title="Current Map:", description="`Spawns left: All -- 0% Cleared`‏‏‎")
        mapembed.set_image(url=img_data["secure_url"])
        mapembed.add_field(name="Events Spawned:", value="No events currently spawned", inline=False)
        self.mapmsg = await self.hcchannel.send(embed=mapembed)

        while True:
            def check(react, usr):
                return not usr.bot and react.message.id == self.afkmsg.id or react.message.id == self.cpmsg.id

            try:
                reaction, user = await self.client.wait_for('reaction_add', timeout=5400, check=check)  # Wait max 1.5 hours
            except asyncio.TimeoutError:
                return await self.end_afk(True)

            if str(reaction.emoji) == self.emojis[0]:
                if user.id not in self.raiderids:
                    self.raiderids.append(user.id)
                    embed = self.afkmsg.embeds[0]
                    embed.set_footer(text=f"Raiders accounted for: {len(self.raiderids)}")
                    await self.afkmsg.edit(embed=embed)
            if str(reaction.emoji) == '<:shard:682365548465487965>':
                if user.premium_since is not None or user.top_role >= self.rlrole:
                    await user.send(f"The location for this realm clearing is: {self.location}")
                    if user.display_name not in self.nitroboosters:
                        self.nitroboosters.append(user.mention)
                    cp = self.cpmsg.embeds[0]
                    cp.set_field_at(1, name="Nitro Boosters", value=str(self.nitroboosters), inline=True)
                    await self.cpmsg.edit(embed=cp)
            elif reaction.emoji == "❌" and user.top_role >= self.rlrole:
                return await self.end_afk(False, user)
            elif reaction.message.id == self.cpmsg.id:
                if user.id in self.markers:
                    if user.id in self.client.mapmarkers:
                        del self.client.mapmarkers[user.id]
                    self.markers.remove(user.id)
                else:
                    self.client.mapmarkers[user.id] = self
                    self.markers.append(user.id)
                cp = self.cpmsg.embeds[0]
                cp.set_field_at(3, name="Markers", value="".join("<@"+str(m)+">" for m in self.markers)+".", inline=True)
                await self.cpmsg.edit(embed=cp)

    async def end_afk(self, automatic: bool, ended:discord.Member=None):
        try:
            await self.mapmsg.delete()
        except discord.NotFound:
            pass
        await self.afkmsg.clear_reactions()
        embed = discord.Embed()
        if automatic:
            embed.title = "Realm Clearing has been ended automatically."
        else:
            embed.title = f"Realm Clearing has been ended by {ended.display_name}"
        embed.description = "Thanks for running with us!\n"\
                            f"This realm clearing ran with {len(self.raiderids)} members\n{len(self.markednums)} spawns were cleared & " \
                            f"{len(self.events)} events spawned."
        embed.set_footer(text="Clearing ended at")
        embed.set_thumbnail(url="https://www.realmeye.com/forum/uploads/default/original/1X/842ee5c4e569c7b7c1b0bf688e465a7435235fc8.png")
        embed.timestamp = datetime.utcnow()
        await self.afkmsg.edit(content="", embed=embed)
        if self.inraiding:
            if self.raidnum == 0:
                self.client.raid_db[self.ctx.guild.id]["raiding"][0] = None
            elif self.raidnum == 1:
                self.client.raid_db[self.ctx.guild.id]["raiding"][1] = None
            else:
                self.client.raid_db[self.ctx.guild.id]["raiding"][2] = None
        elif self.invet:
            if self.raidnum == 0:
                self.client.raid_db[self.ctx.guild.id]["vet"][0] = None
            else:
                self.client.raid_db[self.ctx.guild.id]["vet"][1] = None
        elif self.inevents:
            if self.raidnum == 0:
                self.client.raid_db[self.ctx.guild.id]["events"][0] = None
            else:
                self.client.raid_db[self.ctx.guild.id]["events"][1] = None

        await self.vcchannel.set_permissions(self.raiderrole, connect=False, view_channel=True, speak=False)

        for m in self.markers:
            if m in self.client.mapmarkers:
                del self.client.mapmarkers[m]

    async def markmap(self, context, remove: bool, numbers):
        if not self.mapmsg:
            return await self.ctx.send("There's no running realm clearing at the moment.")
        badnumbers = []
        limit = self.world_data["range"]
        for num in numbers:
            if "-" in num:
                lower = int(num.split("-")[0])
                upper = int(num.split("-")[1]) + 1
            else:
                if num.isdigit():
                    lower = int(num)
                    upper = int(num) + 1
                else:
                    lower = 1
                    upper = 1
            for n in range(lower, upper):
                ismarked = n in self.markednums
                if n - 1 < 0 or n - 1 > limit or (ismarked and not remove) or (not ismarked and remove):
                    badnumbers.append(n)
                else:
                    if not remove:
                        bisect.insort_right(self.markednums, n)
                    else:
                        self.markednums.remove(n)

        if len(badnumbers) >= 1:
            await self.ctx.send(f"Some of the numbers provided were out of range or already cleared. Bad numbers: `{badnumbers}`",
                           delete_after=5)
        if len(numbers) == len(badnumbers):
            return
        file = await asyncio.get_event_loop().run_in_executor(None, self.mark_nums)
        spawns_left = (limit + 1) - len(self.markednums)
        percent = len(self.markednums) / (limit + 1)
        embed = self.cpmsg.embeds[0]
        embed.set_field_at(1, name="Cleared Numbers:", value=f"`{self.markednums}`", inline=False)
        await self.cpmsg.edit(embed=embed)

        img_data = await utils.image_upload(file.read(), context)
        if not img_data:
            return await self.ctx.send(
                "There was an issue communicating with the image server, try again and if the issue persists – contact the developer.",
                delete_after=10)
        embed = self.mapmsg.embeds[0]
        embed.set_image(url=img_data["secure_url"])
        embed.description = f"`Spawns left: {spawns_left} -- {percent:.0%} Cleared`"
        await self.mapmsg.edit(embed=embed)
        embed = self.cpmsg.embeds[0]
        embed.set_image(url=img_data["secure_url"])
        await self.cpmsg.edit(embed=embed)

    def mark_nums(self):
        img = plt.imread(f"world-maps/world_{self.world_num}.jpg")
        fig, ax = plt.subplots(1)
        ax.set_aspect('equal')
        ax.axis("off")
        ax.imshow(img)
        for n in self.markednums:
            point = self.world_data[str(n - 1)]
            circ = Circle((point["x"] / 2, point["y"] / 2), 14, color='#0000FFAA')
            ax.add_patch(circ)
        file = io.BytesIO()
        plt.savefig(file, transparent=True, bbox_inches='tight', pad_inches=0, format='jpg', dpi=300)
        plt.close()
        file.seek(0)
        return file

    async def eventspawn(self, context, remove: bool, event):
        fixed_event = self.event_type(event)
        if fixed_event is None:
            return await context.send("The specified event type is not an option.")
        if fixed_event[1] is True:
            await context.send(f"A correction was made, `{event}` was changed to `{fixed_event[2]}`", delete_after=6)
        embed = self.mapmsg.embeds[0]
        events = ""
        if not remove:
            if fixed_event[0] in self.events:
                self.events[fixed_event[0]] += 1
            else:
                self.events[fixed_event[0]] = 1
        else:
            if fixed_event[0] in self.events:
                del self.events[fixed_event[0]]
        for key, value in self.events.items():
            events += f"{key} x{value}\n"
        if not events:
            events = "No events currently spawned"
        embed.set_field_at(0, name="Events Spawned:", value=events)
        await self.mapmsg.edit(embed=embed)
        embed = self.cpmsg.embeds[0]
        embed.set_field_at(4, name="Events Spawned:", value=events, inline=False)
        await self.cpmsg.edit(embed=embed)

    def event_type(self, run_type):
        event_types = {'ava': 'Avatar of the Forgotten King', 'avatar': 'Avatar of the Forgotten King', 'cube': 'Cube God',
                       'cubegod': 'Cube God', 'gship': 'Ghost Ship', 'sphinx': 'Grand Sphinx', 'hermit': 'Hermit God', 'herm': 'Hermit God',
                       'lotll': 'Lord of the Lost Lands', 'lord': 'Lord of the Lost Lands', 'pent': 'Pentaract', 'penta': 'Pentaract',
                       'drag': 'Rock Dragon', 'rock': 'Rock Dragon', 'skull': 'Skull Shrine', 'shrine': 'Skull Shrine',
                       'skullshrine': 'Skull Shrine', 'miner': 'Dwarf Miner', 'dwarf': 'Dwarf Miner', 'sentry': 'Lost Sentry',
                       'nest': 'Killer Bee Nest', 'statues': 'Jade and Garnet Statues'}
        result = event_types.get(run_type, None)
        if result is None:
            matches = get_close_matches(run_type, event_types.keys(), n=1, cutoff=0.8)
            if len(matches) == 0:
                return None
            return event_types.get(matches[0]), True, matches[0]
        return result, False