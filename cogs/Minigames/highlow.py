import asyncio

import discord
import numpy as np

import utils


class HighLow:
    def __init__(self, ctx, bot):
        self.ctx = ctx
        self.bot = bot
        # Higher or Lower
        self.moves = [
            utils.HighLow.HIGH.value,
            utils.HighLow.LOW.value,
            utils.Controls.CANCEL.value,
            ]
        self.deck = utils.Deck()
        self.deck.shuffle()
        # use half a deck since it can be a long game otherwise
        self.deck = self.deck.split(2)[0]
        self.dealer_score = 0
        self.player_score = 0

        self.embed = discord.Embed(
            title=None,
            type='rich',
            color=np.random.randint(0xFFFFFF),  # Random color
            ).set_author(
            name=self.ctx.author.display_name,
            icon_url=self.ctx.author.avatar_url_as(static_format='png'),
            ).add_field(
            name='Higher or Lower?',
            value=None,  # will be filled later
            inline=False,
            ).add_field(
            name='Previous Card',
            value=None,  # will be filled later
            inline=True,
            ).add_field(
            name='Next Card',
            value=None,  # will be filled later
            inline=True,
            )

    async def play(self):
        self.prev_card = self.deck.pop_card()

        self.update_embed('Please wait, setting things up...', hide_next=True)
        self.message_game = await self.ctx.send(embed=self.embed)

        def check(reaction, user):
            valid = user == self.ctx.author \
                    and reaction.message.id == self.message_game.id \
                    and reaction.emoji in self.moves

            return valid

        for move in self.moves:
            await self.message_game.add_reaction(move)

        dstr = {
            utils.HighLow.HIGH.value: 'higher',
            utils.HighLow.LOW.value: 'lower',
            }

        while len(self.deck) > 0:
            self.next_card = self.deck.pop_card()

            self.update_embed('Higher or Lower?', hide_next=True)
            await self.message_game.edit(embed=self.embed)

            # guess = input('Higher or Lower? ').upper()
            try:
                reaction, user = await self.bot.wait_for(
                    'reaction_add',
                    timeout=5 * 60,
                    check=check,
                    )
            except asyncio.TimeoutError as e:
                break

            move = reaction.emoji
            await reaction.remove(user)
            prev_lower_than_next = self.prev_card.rank < self.next_card.rank

            if self.prev_card.rank == self.next_card.rank:
                hint_message = 'Actually, that was mean.'

            elif (move == utils.HighLow.HIGH.value \
                    and prev_lower_than_next) or \
                    (move == utils.HighLow.LOW.value \
                    and not prev_lower_than_next):
                hint_message = (
                    f'Yep! {self.next_card} is {dstr[move]} '
                    f'than {self.prev_card}.'
                    )
                self.player_score += 1

            elif move == utils.Controls.CANCEL.value:
                # cancel the game
                break

            else:
                hint_message = 'Nope!'
                self.dealer_score += 1

            self.update_embed(hint_message, hide_next=False)
            await self.message_game.edit(embed=self.embed)

            await asyncio.sleep(2)
            self.prev_card = self.next_card

        # print('No more cards!')
        # print(f'Dealer: {self.dealer_score}\nPlayer: {self.player_score}')
        self.update_embed('No more cards!', hide_next=True)
        await self.message_game.edit(embed=self.embed)

        await self.message_game.clear_reactions()

    def update_embed(self, hint_message, hide_next):
        score_str = (
            f'You got **{self.player_score}** guesses right, '
            f'and {self.dealer_score} wrong.\n'
            f'({len(self.deck)} cards left in the deck)'
            )

        self.embed.set_field_at(
            index=0,
            name=self.embed.fields[0].name,
            value=score_str,
            inline=self.embed.fields[0].inline,
            ).set_field_at(
            index=1,  # previous card
            name=self.embed.fields[1].name,
            value=self.prev_card.emoji,
            inline=self.embed.fields[1].inline,
            ).set_field_at(
            index=2,  # next card
            name=self.embed.fields[2].name,
            value=self.next_card.emoji if not hide_next else utils.Suits.JOKER.value,
            inline=self.embed.fields[2].inline,
            ).set_footer(
            text=hint_message,
            )


if __name__ == '__main__':
    game = HighLow()
    game.play()