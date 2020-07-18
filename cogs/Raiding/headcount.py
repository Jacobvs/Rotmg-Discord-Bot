import asyncio

import discord

import embeds
import utils
from cogs.Raiding.afk_check import AfkCheck


class Headcount:

    def __init__(self, client, ctx, hcchannel, vcchannel, setup_msg, raidnum, inraiding, invet, inevents, raiderrole, rlrole):
        self.client = client
        self.ctx = ctx
        self.hcchannel = hcchannel
        self.vcchannel = vcchannel
        self.setup_msg = setup_msg
        self.raidnum = raidnum
        self.inraiding = inraiding
        self.invet = invet
        self.inevents = inevents
        self.raiderrole = raiderrole
        self.rlrole = rlrole
        self.guild_db = self.client.guild_db.get(self.ctx.guild.id)
        self.dungeonembed = embeds.dungeon_select(hc=True)
        self.dungeonembed.add_field(name="Other", value="`(61)` <:whitebag:682208350481547267> Realm Clearing\n`(62)` "
                                                        "<:fame:682209281722024044> Fame Train")


    async def start(self):
        await self.setup_msg.edit(embed=self.dungeonembed)

        def dungeon_check(m):
            return m.author == self.ctx.author and m.channel == self.ctx.channel and m.content.isdigit()

        while True:
            try:
                msg = await self.client.wait_for('message', timeout=60, check=dungeon_check)
            except asyncio.TimeoutError:
                embed = discord.Embed(title="Timed out!", description="You didn't choose a dungeon in time!", color=discord.Color.red())
                await self.setup_msg.clear_reactions()
                return await self.setup_msg.edit(embed=embed)
            if -1 < int(msg.content) < 56 or 60 < int(msg.content) < 62:
                break
            await self.ctx.send("Please choose a number between 0-55 or 61-62!", delete_after=7)

        self.keyed_run = False
        num = int(msg.content)
        if num == 0:
            self.dungeontitle = "Random Dungeons"
            self.emojis = utils.rand_dungon_keys()
            self.thumbnail = "https://static.drips.pw/rotmg/wiki/Environment/Portals/Rainbow%20Road.png"
            await msg.delete()
            await self.setup_msg.delete()
            embed = embeds.headcount_base(self.dungeontitle, self.ctx.author, False, self.emojis, [], thumbnail=self.thumbnail)
            embed.description = f"React to {self.emojis[0]} to participate in the run!\nIf you have keys, react to the appropriate emojis " \
                                f"below!"
            hcmsg = await self.hcchannel.send(f"@here Headcount for `{self.dungeontitle}` {self.emojis[0]} started by "
                                            f"{self.ctx.author.mention} for {self.vcchannel.name}", embed=embed)
            for emoji in self.emojis[:20]:
                await hcmsg.add_reaction(emoji)
            msg1 = await self.hcchannel.send("More Keys:")
            for emoji in self.emojis[20:40]:
                await msg1.add_reaction(emoji)
            msg2 = await self.hcchannel.send("Even More Keys:")
            for emoji in self.emojis[40:]:
                await msg2.add_reaction(emoji)
            return
        elif num == 61:
            self.dungeontitle = "Realm Clearing"
            self.emojis = ["<:defaultdungeon:682212333182910503>", "<:trickster:682214467483861023>", "<:Warrior_1:585616162407186433>",
                           "<:ninja_3:585616162151202817>"]
            self.rusher_emojis = ["<:planewalker:682212363889279091>"]
            self.hc_color = discord.Color.from_rgb(20, 125, 236)
            self.thumbnail = "https://www.realmeye.com/forum/uploads/default/original/1X/842ee5c4e569c7b7c1b0bf688e465a7435235fc8.png"
        elif num == 62:
            self.dungeontitle = "Fame Train"
            self.emojis = ["<:fame:682209281722024044>", "<:sorcerer:682214487490560010>", "<:necromancer:682214503106215966>",
                           "<:sseal:683815374403141651>", "<:puri:682205769973760001>"]
            self.rusher_emojis = []
            self.hc_color = discord.Color.from_rgb(233, 127, 33)
            self.thumbnail = "https://cdn.discordapp.com/attachments/679309966128971797/696452960825376788/fame2.png"
        else:
            self.dungeon_info = utils.dungeon_info(int(msg.content))
            self.keyed_run = True
            self.dungeontitle = self.dungeon_info[0]
            self.emojis = self.dungeon_info[1]
            self.rusher_emojis = self.dungeon_info[2]
            self.hc_color = self.dungeon_info[3]
            self.thumbnail = self.dungeon_info[4]
        await msg.delete()
        await self.setup_msg.delete()

        afkmsg = await self.hcchannel.send(
            f"@here Headcount for `{self.dungeontitle}` {self.emojis[0]} started by {self.ctx.author.mention} for {self.vcchannel.name}",
            embed=embeds.headcount_base(self.dungeontitle, self.ctx.author, self.keyed_run, self.emojis, self.rusher_emojis,
                                        self.thumbnail, self.hc_color))

        if 0 < num < 61:
            embed = discord.Embed(title="Headcount", description=f"{self.ctx.author.mention} - your headcount for"
                                                             f" `{self.dungeontitle}` has been started!\nTo convert this headcount into an "
                                                             "afk check, press the 🔀 button.", color=discord.Color.green())
        else:
            embed = discord.Embed(title="Headcount", description=f"{self.ctx.author.mention} - your headcount for"
                                                                 f" `{self.dungeontitle}` has been started!", color=discord.Color.green())
        hcmsg = await self.ctx.send(embed=embed)

        for e in self.emojis:
            await afkmsg.add_reaction(e)

        for e in self.rusher_emojis:
            await afkmsg.add_reaction(e)

        if 0 < num < 61:
            await hcmsg.add_reaction("🔀")
            while True:
                def check(react, usr):
                    return not usr.bot and react.message.id == hcmsg.id and usr == self.ctx.author and str(react.emoji) == '🔀'
                try:
                    reaction, user = await self.client.wait_for('reaction_add', timeout=3600, check=check)  # Wait max 1 hour
                except asyncio.TimeoutError:
                    embed.description = f"{self.ctx.author.mention} - your headcount for `{self.dungeontitle}` has been started!\n" \
                                        f"Conversion to an afk check timed out. Try starting a new headcount/afk."
                    await hcmsg.edit(embed=embed)
                    return await hcmsg.clear_reactions()

                if self.ctx.author.id in self.client.raid_db[self.ctx.guild.id]['leaders']:
                    await self.ctx.send("You cannot start another AFK while an AFK check is still up or a run log has not been "
                                               "completed.", delete_after=10)
                    await reaction.remove()
                    continue

                embed = discord.Embed(title="Location Selection", description="Please type the location you'd like to set for this run.")
                setup_msg = await self.ctx.send(embed=embed)

                def location_check(m):
                    return m.author == self.ctx.author and m.channel == self.ctx.channel

                try:
                    msg = await self.client.wait_for('message', timeout=60, check=location_check)  # Wait max 1 hour
                except asyncio.TimeoutError:
                    continue

                location = msg.content
                await msg.delete()
                afk = AfkCheck(self.client, self.ctx, location, self.raidnum, self.inraiding, self.invet, self.inevents, self.raiderrole,
                               self.rlrole, self.hcchannel, self.vcchannel, setup_msg)
                await afk.convert_from_headcount(afkmsg, self.dungeon_info, self.dungeontitle, self.emojis, self.raidnum, self.inraiding,
                                                 self.invet, self.inevents, self.raiderrole, self.rlrole, self.hcchannel, self.vcchannel)