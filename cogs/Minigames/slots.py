import asyncio
import random

import discord

import sql


class Slots:
    emojis = ['🍋', '🍉', '🍌', '🍒', '💎', '<:slot7:711843601369530458>']

    def __init__(self, client, ctx, bet, user, balance):
        self.client = client
        self.ctx = ctx
        self.bet = bet
        self.user = user
        self.winner = False
        self.winnerE = 0
        self.balance = balance
        self.gameembed = discord.Embed(color=discord.Color.blue(), description="Slots").set_author(name=user.display_name,
                                        icon_url=user.avatar_url).add_field(name="Board", value="Setting up...", inline=False)\
                                        .add_field(name="Bet", value=f"**{bet:,}** credits.", inline=False)

    async def play(self):
        self.gamemsg = await self.ctx.send(embed=self.gameembed)
        self.ticket = random.randint(1, 1001)
        self.board = self.rand_board()
        if self.ticket > 729:
            self.winner = True
            self.winnerE = 0 if self.ticket < 830 else 1 if self.ticket < 900 else 2 if self.ticket < 950 else 3 if self.ticket < 980 \
            else 4 if self.ticket < 995 else 5
            self.winnerE = self.emojis[self.winnerE]
            self.mult = 2 if self.ticket < 830 else 5 if self.ticket < 900 else 10 if self.ticket < 950 else 20 if self.ticket < 980 else \
                40 if self.ticket < 995 else 100
            self.winA = int(self.bet*self.mult)
        else:
            self.lossE = [self.rand_emoji(), self.rand_emoji(), self.rand_emoji()]
            if self.lossE.count(self.lossE[0]) == len(self.lossE):
                choices = self.emojis
                choices.remove(self.lossE[0])
                self.lossE[2] = random.choice(choices)

        await self.update_embed()
        for b in self.generate_boards():
            self.board = b
            await self.update_embed()
            await asyncio.sleep(0.7)

        if self.winner is True:
            await sql.change_balance(self.client.pool, self.ctx.guild.id, self.user.id, self.balance+self.winA)
            self.gameembed.color = discord.Color.gold() if self.mult >= 50 else discord.Color.green()
            self.gameembed.description = "Slots - **JACKPOT!**" if self.mult >= 50 else "Slots - **You Won!**"
            self.gameembed.set_field_at(1, name="Bet", value=f"**+{self.winA:,}** credits", inline=False)
            self.gameembed.add_field(name="Balance", value=f"**{self.balance+self.winA}** credits.", inline=False)
        else:
            await sql.change_balance(self.client.pool, self.ctx.guild.id, self.user.id, self.balance - self.bet)
            self.gameembed.color = discord.Color.red()
            self.gameembed.description = "Slots - **You lost!**"
            self.gameembed.set_field_at(1, name="Bet", value=f"**-{self.bet:,}** credits", inline=False)
            self.gameembed.add_field(name="Balance", value=f"**{self.balance-self.bet}** credits.", inline=False)
        self.gameembed.set_footer(text=f"Your Ticket was {self.ticket}")
        await self.gamemsg.edit(embed=self.gameembed)


    def generate_boards(self):
        boards = []
        i = 1
        while i < 16:
            if i < 4:
                self.update_reels(0)
            elif i == 4:
                if self.winner:
                    self.update_reels(0, self.winnerE)
                else:
                    self.update_reels(0, self.lossE[0])
            elif i == 5:
                self.update_reels(0)
            elif i < 9:
                self.update_reels(1)
            elif i == 9:
                if self.winner:
                    self.update_reels(1, self.winnerE)
                else:
                    self.update_reels(1, self.lossE[1])
            elif i == 10:
                self.update_reels(1)
            elif i < 14:
                self.update_reels(2)
            elif i == 14:
                if self.winner:
                    self.update_reels(2, self.winnerE)
                else:
                    self.update_reels(2, self.lossE[2])
            else:
                self.update_reels(2)
            boards.append(self.board)
            i += 1
        return boards


    async def update_embed(self):
        s = f"     ––––––––––––––-\n | {self.board[0][2]} | {self.board[1][2]} | {self.board[2][2]} |\n" \
            f" | {self.board[0][1]} | {self.board[1][1]} | {self.board[2][1]} | ⇐\n " \
            f"| {self.board[0][0]} | {self.board[1][0]} | {self.board[2][0]} |\n ––––––––––––––-"
        self.gameembed.set_field_at(0, name="Board", value=s)
        await self.gamemsg.edit(embed=self.gameembed)

    def update_reels(self, reel_num, emoji=None):
        if not emoji:
            if reel_num == 0:
                self.board = [self.bump_down(self.board[0]), self.bump_down(self.board[1]), self.bump_down(self.board[2])]
            elif reel_num == 1:
                self.board = [self.board[0], self.bump_down(self.board[1]), self.bump_down(self.board[2])]
            else:
                self.board = [self.board[0], self.board[1], self.bump_down(self.board[2])]
        else:
            self.board = [self.bump_down(self.board[0], emoji), self.bump_down(self.board[1]), self.bump_down(self.board[2])] if \
                reel_num == 0 else [self.board[0], self.bump_down(self.board[1], emoji), self.bump_down(self.board[2])] if reel_num == 1 \
                else [self.board[0], self.board[1], self.bump_down(self.board[0], emoji)]

    def bump_down(self, reel, emoji=None):
        newR = reel[1:]
        newR.append(emoji) if emoji else newR.append(self.rand_emoji())
        return newR

    def rand_emoji(self):
        return random.choice(self.emojis)

    def rand_reel(self):
        return [random.choice(self.emojis), random.choice(self.emojis), random.choice(self.emojis)]

    def rand_board(self):
        return [self.rand_reel(), self.rand_reel(), self.rand_reel()]