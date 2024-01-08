from dateutil.parser import parse as date_parse
from dataclasses import dataclass
from fractions import Decimal
import re

import eval7
import logging
from django.db import transaction

from apps.utils.ranges.matchups_enum import Result
from apps.utils.ranges.matchups import MATCHUPS
from apps.utils.ranges._typing import Hole

from ..models import HoldupHand

logger = logging.getLogger(__name__)


NUMBER = r'([\d.]+)[€$]'
CARD = r'[AKQJT2-9][shdc]'
CARD_SET = fr'(?:\[(?:{CARD} )*{CARD}\])'

STREETS = {
    # Number of board cards before the street is revealed.
    # Used for adjusting all-in ev.
    'FLOP': 0,
    'TURN': 3,
    'RIVER': 4,
}

BLIND_POSITIONS = {
    'small': -1,
    'big': -2,
}


@dataclass
class Seat:
    seat_id: int = None
    position: int = None
    stack: Decimal = None
    hole: list = None
    invested: Decimal = 0
    invested_street: Decimal = 0
    collected: Decimal = 0

    showdown_cards: list = None


class Patterns:
    HEADER = re.compile(
        fr'^Winamax Poker - (?:Go Fast|HOLD-UP) .* HandId: #([\d-]+).* '
        fr'no limit \(.*/{NUMBER}.*- (.*)$'
    )
    BUTTON_SEAT = re.compile(r'^Table: .* Seat #(\d) is the button')
    PLAYER_SEAT = re.compile(rf'^Seat (\d): (.*) \({NUMBER}\)$')
    HOLDUP = re.compile(fr'^Hold-up to Pot: total {NUMBER}')
    BLIND = re.compile(fr'^(.*) posts (small|big) blind {NUMBER}(?: and is all-in)?$')
    HERO = re.compile(r'^Dealt to ([\w-]+) \[([\w ]+)\]$')
    RAKE = re.compile(fr'Rake {NUMBER}$')
    STREET = re.compile(fr'^\*\*\* (FLOP|TURN|RIVER|SHOW DOWN) \*\*\*(?: {CARD_SET}+)?$')
    BOARD = re.compile(fr'^Board: \[([\w ]+)\]$')
    SEAT_SHOW = re.compile(fr'^Seat (\d): (.*) showed \[({CARD} {CARD})\] and (?:won \S*|lost) with.*$')

    BET = re.compile(
        fr'^(.*) (bets|calls|raises \S* to) {NUMBER}'
        r'( and is all-in)?$'
    )
    COLLECT = re.compile(fr'^(.*) collected {NUMBER} from (?:pot|main pot|side pot \d+)$')
    CHECK = re.compile(fr'^(.*) checks$')
    FOLD = re.compile(fr'^(.*) folds$')


class StreamParser:
    def __init__(self, stream):
        self.stream = stream
        self.to_insert = []
        self.nb_hands = 0
        self.lines = []

        while (line := self.stream.readline()):
            if (match := Patterns.HEADER.match(line)) is not None:
                self.lines = [line.strip()]

                try:
                    self.parse_hand(match)
                except Exception as exc:
                    logger.error([exc, self.lines])
                    raise

                self.nb_hands += 1

        for batch in self.get_batches(self.to_insert):
            with transaction.atomic():
                HoldupHand.objects.filter(
                    winamax_id__in=[h.winamax_id for h in batch]).delete()
                HoldupHand.objects.bulk_create(batch, ignore_conflicts=True)

    def get_batches(self, iterable, size=500):
        if size <= 0:
            raise ValueError('size must be positive')

        index = 0
        while (batch := iterable[index:index + size]):
            yield batch
            index += size

    def _read_line(self):
        line = self.stream.readline().strip()
        self.lines.append(line)
        return line

    def parse_hand(self, header):
        hparse = HandParser(header)
        while (line := self._read_line().rstrip()):
            hparse.parse_line(line)

        hparse.end()
        hparse.hand.log = '\n'.join(self.lines).strip()

        # hparse.adjust_allin()

        self.to_insert.append(hparse.hand)


class HandParser:
    def __init__(self, header):
        hand_id = header.group(1)
        self.hand = HoldupHand(winamax_id=hand_id)

        self.patterns = None
        self.button_seat = None
        self.hero_hole = None
        self.hero_seat = None
        self.has_showdown = False
        self.hero_folded = False

        self.all_in_cards = None
        self.expects_action = False
        self.hero_in_showdown = False
        self.seats = {}
        self.seats_by_id = {}

        self.hand.holdup = 0
        self.hand.rake = 0
        self.hand.limit = Decimal(header.group(2))
        self.hand.played_at = date_parse(header.group(3))
        self.action = []

    def parse_line(self, line):
        if self.expects_action:
            self.expects_action = False
            if Patterns.STREET.match(line) is None:
                # Still action going, so not all-in
                self.all_in_cards = None

        if line == '*** SHOW DOWN ***':
            self.has_showdown = True

        elif (match := Patterns.SEAT_SHOW.match(line)) is not None:
            seat = self.seats_by_id[int(match.group(1))]
            seat.showdown_cards = [eval7.Card(c) for c in match.group(3).split(' ')]

        elif (match := Patterns.BLIND.match(line)) is not None:
            seat = self.seats[match.group(1)]
            seat.position = BLIND_POSITIONS[match.group(2)]
            seat.invested_street = Decimal(match.group(3))

        elif (match := Patterns.BUTTON_SEAT.match(line)) is not None:
            self.button_seat = int(match.group(1))

        elif (match := Patterns.PLAYER_SEAT.match(line)) is not None:
            seat_id = int(match.group(1))
            seat = self.seats[match.group(2)] = self.seats_by_id[seat_id] = Seat(seat_id=seat_id)
            seat.stack = Decimal(match.group(3))

        elif (match := Patterns.HERO.match(line)) is not None:
            hero_hole = sorted(match.group(2).split(' '))
            self.hand.hero_hole = ''.join(hero_hole)
            self.hero_hole = [eval7.Card(c) for c in hero_hole]
            self.hand.hero_hole_token = Hole(self.hero_hole).token
            self.hero_name = match.group(1)
            self.hero_seat = self.seats[self.hero_name]

            self.hand.hero_position = (
                self.hero_seat.position if self.hero_seat.position is not None
                else self.button_seat - self.hero_seat.seat_id
            )

        elif (match := Patterns.HOLDUP.match(line)) is not None:
            self.hand.holdup = Decimal(match.group(1)) / self.hand.limit

        elif (match := Patterns.RAKE.search(line)) is not None:
            self.hand.rake = Decimal(match.group(1)) / self.hand.limit

        elif (match := Patterns.BET.match(line)) is not None:
            player_name = match.group(1)
            seat = self.seats[player_name]
            action = match.group(2)
            bet_size = Decimal(match.group(3))

            if action == 'calls':
                seat.invested_street += bet_size
                self._act('c', player_name)
            else:
                seat.invested_street = bet_size
                formatted_size = bet_size / self.hand.limit
                if formatted_size == (int_size := int(formatted_size)):
                    formatted_size = int_size
                self._act(f'b{formatted_size}', player_name)

        elif (match := Patterns.COLLECT.match(line)) is not None:
            player_name = match.group(1)
            self.seats[player_name].collected = Decimal(match.group(2))

        elif (match := Patterns.STREET.match(line)) is not None:
            self._end_street()
            self.action.append('/')

            if self.all_in_cards is None and (street := match.group(1)) in STREETS:
                self.expects_action = True
                self.all_in_cards = STREETS[street]

        elif (match := Patterns.FOLD.match(line)) is not None:
            self._act('f', match.group(1))
            if match.group(1) == self.hero_name:
                self.hero_folded = True

        elif (match := Patterns.CHECK.match(line)) is not None:
            self._act('k', match.group(1))

        elif self.has_showdown and (match := Patterns.BOARD.match(line)) is not None:
            self.board = [eval7.Card(c) for c in match.group(1).split(' ')]
            if not self.hero_folded and self.hero_hole is not None:
                self.hand.hero_showdown = eval7.evaluate(self.hero_hole + self.board)
                self.hero_in_showdown = True

    def _act(self, action, player_name=None):
        if player_name == self.hero_name:
            action = action.upper()
        self.action.append(action)

    def _end_street(self):
        for seat in self.seats.values():
            seat.invested += seat.invested_street
            seat.invested_street = 0

    def end(self):
        self._end_street()
        self.hand.action = ''.join(self.action)
        self.hand.hero_net = (self.hero_seat.collected - self.hero_seat.invested) / self.hand.limit
        self.hand.hero_all_in_adjusted = self.hand.hero_net

        if self.has_showdown:
            self.hand.winning_hand = max(
                eval7.evaluate(seat.showdown_cards + self.board)
                for seat in self.seats.values()
                if seat.showdown_cards is not None
            )

        self._adjust_allin()

    def _adjust_allin(self):
        """Adjust all-in equity."""
        if (not self.hero_in_showdown) or (self.all_in_cards is None):
            return

        allin_seats = [
            seat for seat in self.seats.values()
            if seat is not self.hero_seat
            and seat.showdown_cards is not None
        ]

        if len(allin_seats) > 1:
            return

        vilain_seat = allin_seats[0]
        base_bet = min(self.hero_seat.invested, vilain_seat.invested)
        contested_pot = sum(
            min(base_bet, seat.invested)
            for seat in self.seats.values()
        )
        contested_pot = self.rake(contested_pot) + self.hand.holdup * self.hand.limit

        ref_board = self.board[:self.all_in_cards]
        hero_equity = self._get_equity(
            self.hero_seat.showdown_cards, vilain_seat.showdown_cards, ref_board)

        self.hand.hero_all_in_adjusted = (
            (float(contested_pot) * hero_equity - float(base_bet))
            / float(self.hand.limit)
        )

    @staticmethod
    def _get_equity(hero, vilain, board):
        if not board:
            return MATCHUPS[Hole(hero).token, Hole(vilain).token].score

        result = Result()
        result.match(hero, vilain, board)
        return result.equity

    @staticmethod
    def rake(pot):
        return round(pot * Decimal("0.9"), 2)
