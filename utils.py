import datetime
import re

import numpy as np
from enum import Enum

from discord.ext.commands import BadArgument, Converter


class Card:
    """Class that represents a normal playing card."""

    suit_names = ['Clubs', 'Diamonds', 'Hearts', 'Spades']
    rank_names = [None, 'A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']


    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
        self.suit_name = self.suit_names[suit]
        self.rank_name = self.rank_names[rank]
        self._card = (suit, rank)


    def __str__(self):
        return f'{self.rank_name} of {self.suit_name}'


    def __repr__(self):
        return f'{self.__class__.__name__}({self.suit}, {self.rank})'


    def __eq__(self, other):
        """Use the type tuple to make equality check."""

        return self._card == other._card


    def __lt__(self, other):
        """Use the type tuple to make the comparison.
        Sorts first by suit, then by rank.
        """
        return self._card < other._card


    @property
    def emoji(self):
        """Return a string of the card's rank and suit, in emoji form."""

        suit = Suits[self.suit_name.upper()].value
        if self.rank in (1, 11, 12, 13):
            rank = Alphabet[self.rank_name].value
        else:
            rank = Numbers[f'_{self.rank}'].value

        return rank + suit


class Deck:
    """Class that represents a full deck of cards, consisting of many
    Cards objects. Does not contain Jokers.
    """

    def __init__(self, cards=None):
        if cards is None:
            self.cards = [Card(suit, rank) for suit in range(4) for rank in range(1, 14)]
        else:
            self.cards = cards


    def __mul__(self, other):
        if isinstance(other, int):
            return self.__class__(cards=self.cards * other)
        else:
            raise ValueError('Invalid types for multiplication.')


    __rmul__ = __mul__


    def __len__(self):
        return len(self.cards)


    def __str__(self):
        return '\n'.join([str(card) for card in self.cards])


    def __iter__(self):
        return iter(self.cards)


    def __next__(self):
        return next(self.cards)


    def shuffle(self):
        """Shuffle the cards inplace."""

        np.random.shuffle(self.cards)


    def sort(self):
        """Sort the cards inplace."""

        self.cards.sort()


    def split(self, parts):
        """Split the deck in n parts."""

        cards_array = np.asarray(self.cards)
        split = np.array_split(cards_array, parts)
        decks = []
        for part in split:
            decks.append(self.__class__(cards=list(part)))

        return decks


    def add_card(self, card):
        """Add a card to the end of the deck."""

        self.cards.append(card)


    def remove_card(self, card):
        """Remove a given card form the deck."""

        self.cards.remove(card)


    def pop_card(self, *args):
        """Remove and return a card from the deck,
        the last one by default.
        """
        return self.cards.pop(*args)


    def give_cards(self, hand, amount):
        """Give the amount of cards from the deck to the player's hand."""

        for i in range(amount):
            hand.add_card(self.pop_card())


class Hand(Deck):
    """Class that represents the hand of a player.
    Inherits most from Deck class.
    """
    def __init__(self):
        self.cards = []


# Create an Enum with all the letters of the alphabet as emojis
Alphabet = Enum(
    'Alphabet',
    {
        chr(char): chr(emoji) for char, emoji in zip(
            range(ord('A'), ord('Z') + 1),
            range(0x1F1E6, 0x1F200)  # :regional_indicator_#:
            )
        }
    )


class Numbers(Enum):
    _0 = '\u0030\u20e3'  # :zero:
    _1 = '\u0031\u20e3'  # :one:
    _2 = '\u0032\u20e3'  # :two:
    _3 = '\u0033\u20e3'  # :three:
    _4 = '\u0034\u20e3'  # :four:
    _5 = '\u0035\u20e3'  # :five:
    _6 = '\u0036\u20e3'  # :six:
    _7 = '\u0037\u20e3'  # :seven:
    _8 = '\u0038\u20e3'  # :eight
    _9 = '\u0039\u20e3'  # :nine:
    _10 = '\U0001F51F'  # :keycap_ten:


class Controls(Enum):
    CANCEL = '\U0000274C'  # :x:


class Hangman(Enum):
    BLACK = '\U00002B1B'  # :black_large_square:
    DIZZY_FACE = '\U0001F635'  # :dizzy_face:
    SHIRT = '\U0001F455'  # :shirt:
    POINT_LEFT = '\U0001F448'  # :point_left:
    POINT_RIGHT = '\U0001F449'  # :point_right:
    JEANS = '\U0001F456'  # :jeans:
    SHOE = '\U0001F45E'  # :mans_shoe:
    BLANK = '\U000023F9'  # :stop_button:


class Connect4(Enum):
    BLACK = '\U000026AB'  # :black_circle:
    RED = '\U0001F534'  # :red_cirle:
    BLUE = '\U0001F535'  # :large_blue_circle:
    RED_WIN = '\U00002B55'  # :o:
    BLUE_WIN = '\U0001F518'  # :radio_button:


class Suits(Enum):
    SPADES = '\U00002660'  # :spades:
    CLUBS = '\U00002663'  # :clubs:
    HEARTS = '\U00002665'  # :hearts:
    DIAMONDS = '\U00002666'  # :diamonds:
    JOKER = '\U0001F0CF'  # :black_joker:


class HighLow(Enum):
    HIGH = '\U000023EB'  # :arrow_double_up:
    LOW = '\U000023EC'  # :arrow_double_down:


class TicTacToe(Enum):
    UL = '\U00002196'  # :arrow_upper_left:
    UM = '\U00002B06'  # :arrow_up:
    UR = '\U00002197'  # :arrow_upper_right:
    ML = '\U00002B05'  # :arrow_left:
    MM = '\U000023FA'  # :record_button:
    MR = '\U000027A1'  # :arrow_right:
    LL = '\U00002199'  # :arrow_lower_left:
    LM = '\U00002B07'  # :arrow_down:
    LR = '\U00002198'  # :arrow_lower_right:
    X = Alphabet.X.value  # :regional_indicator_x:
    O = '\U0001F17E'  # :o2:
    BLANK = '\U00002B1C'  # :white_large_square:


class RouletteGifs(Enum):
    _0 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004500/0_hw4ozi.gif"
    _1 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004506/1_d4hvgf.gif"
    _2 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004519/2_ffs0qi.gif"
    _3 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004524/3_ceclp8.gif"
    _4 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004478/4_rdaszs.gif"
    _5 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004482/5_sem3zb.gif"
    _6 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004503/6_xeiifa.gif"
    _7 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004536/7_v7avrx.gif"
    _8 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004480/8_uxpvdu.gif"
    _9 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004537/9_wptd9z.gif"
    _10 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004510/10_h85pj6.gif"
    _11 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004532/11_myjufk.gif"
    _12 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004538/12_ihb9cr.gif"
    _13 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004489/13_kfhkie.gif"
    _14 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004521/14_odqdlb.gif"
    _15 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004538/15_o9pfnj.gif"
    _16 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004500/16_rylldv.gif"
    _17 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004499/17_r9vre4.gif"
    _18 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004488/18_p67w69.gif"
    _19 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004510/19_hklqzo.gif"
    _20 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004512/20_chdzbq.gif"
    _21 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004518/21_p2uwou.gif"
    _22 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004479/22_q5cqyf.gif"
    _23 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004491/23_kpawtb.gif"
    _24 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004533/24_famfw9.gif"
    _25 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004531/25_sksh8g.gif"
    _26 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004521/26_mihjd4.gif"
    _27 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004489/27_bibte7.gif"
    _28 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004493/28_nipbll.gif"
    _29 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004515/29_gwskh5.gif"
    _30 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004528/30_fuhk2c.gif"
    _31 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004526/31_emmym4.gif"
    _32 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004535/32_salhf1.gif"
    _33 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004508/33_obghm6.gif"
    _34 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004481/34_pt4y0c.gif"
    _35 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004507/35_lzy82q.gif"
    _36 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004498/36_eskj7v.gif"


def build_duration(**kwargs):
    """Converts a dict with the keys defined in `Duration` to a timedelta
    object. Here we assume a month is 30 days, and a year is 365 days.
    """
    weeks = kwargs.get('weeks', 0)
    days = 365 * kwargs.get('years', 0) \
        + 30 * kwargs.get('months', 0) \
        + kwargs.get('days')
    hours = kwargs.get('hours', 0)
    minutes = kwargs.get('minutes', 0)
    seconds = kwargs.get('seconds', 0)

    return datetime.timedelta(
        days=days,
        seconds=seconds,
        minutes=minutes,
        hours=hours,
        weeks=weeks,
        )


class Duration(Converter):
    """Convert duration strings into UTC datetime.datetime objects.
    Inspired by the https://github.com/python-discord/bot repository.
    """

    duration_parser = re.compile(
        r"((?P<years>\d+?) ?(years|year|Y|y) ?)?"
        r"((?P<months>\d+?) ?(months|month|M) ?)?"  # switched m to M
        r"((?P<weeks>\d+?) ?(weeks|week|W|w) ?)?"
        r"((?P<days>\d+?) ?(days|day|D|d) ?)?"
        r"((?P<hours>\d+?) ?(hours|hour|H|h) ?)?"
        r"((?P<minutes>\d+?) ?(minutes|minute|min|m) ?)?"  # switched M to m
        r"((?P<seconds>\d+?) ?(seconds|second|S|s))?"
    )

    async def convert(self, ctx, duration: str) -> datetime:
        """
        Converts a `duration` string to a datetime object that's
        `duration` in the future.
        The converter supports the following symbols for each unit of time:
        - years: `Y`, `y`, `year`, `years`
        - months: `m`, `month`, `months`
        - weeks: `w`, `W`, `week`, `weeks`
        - days: `d`, `D`, `day`, `days`
        - hours: `H`, `h`, `hour`, `hours`
        - minutes: `m`, `minute`, `minutes`, `min`
        - seconds: `S`, `s`, `second`, `seconds`
        The units need to be provided in **descending** order of magnitude.
        """
        match = self.duration_parser.fullmatch(duration)
        if not match:
            raise BadArgument(f"`{duration}` is not a valid duration string.")

        duration_dict = {unit: int(amount) \
            for unit, amount in match.groupdict(default=0).items()}
        delta = build_duration(**duration_dict)
        now = datetime.datetime.utcnow()

        return now + delta
