import asyncio

import discord

import embeds
import utils


class Headcount:

    def __init__(self, client, ctx, hcchannel, vcchannel, setup_msg):
        self.client = client
        self.ctx = ctx
        self.hcchannel = hcchannel
        self.vcchannel = vcchannel
        self.setup_msg = setup_msg
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
            if -1 < int(msg.content) < 53 or 60 < int(msg.content) < 62:
                break
            await self.ctx.send("Please choose a number between 0-52 or 61-62!", delete_after=7)

        self.keyed_run = False
        if int(msg.content) == 0:
            self.dungeontitle = "Random Dungeons"
            self.emojis = utils.rand_dungon_keys()
            self.thumbnail = "https://static.drips.pw/rotmg/wiki/Environment/Portals/Rainbow%20Road.png"
            await msg.delete()
            await self.setup_msg.delete()
            embed = embeds.headcount_base(self.dungeontitle, self.ctx.author, False, self.emojis, thumbnail=self.thumbnail)
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
        elif int(msg.content) == 61:
            self.dungeontitle = "Realm Clearing"
            self.emojis = ["<:defaultdungeon:682212333182910503>", "<:trickster:682214467483861023>", "<:Warrior_1:585616162407186433>",
                           "<:ninja_3:585616162151202817>"]
            self.thumbnail = "https://www.realmeye.com/forum/uploads/default/original/1X/842ee5c4e569c7b7c1b0bf688e465a7435235fc8.png"
        elif int(msg.content) == 62:
            self.dungeontitle = "Fame Train"
            self.emojis = ["<:fame:682209281722024044>", "<:sorcerer:682214487490560010>", "<:necromancer:682214503106215966>",
                           "<:sseal:683815374403141651>", "<:puri:682205769973760001>"]
            self.thumbnail = "https://cdn.discordapp.com/attachments/679309966128971797/696452960825376788/fame2.png"
        else:
            dungeon_info = utils.dungeon_info(int(msg.content))
            self.keyed_run = True
            self.dungeontitle = dungeon_info[0]
            self.emojis = dungeon_info[1]
            self.thumbnail = dungeon_info[2]
        await msg.delete()
        await self.setup_msg.delete()

        afkmsg = await self.hcchannel.send(
            f"@here Headcount for `{self.dungeontitle}` {self.emojis[0]} started by {self.ctx.author.mention} for {self.vcchannel.name}",
            embed=embeds.headcount_base(self.dungeontitle, self.ctx.author, self.keyed_run, self.emojis, self.thumbnail))

        embed = discord.Embed(title="Headcount", description=f"{self.ctx.author.mention} - your headcount for"
                                                             f" `{self.dungeontitle}` has been started!", color=discord.Color.green())
        await self.ctx.send(embed=embed)

        for emoji in self.emojis:
            await afkmsg.add_reaction(emoji)
