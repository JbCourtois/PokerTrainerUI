import os
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.utils import timezone

from .base.base import BaseHoldupCommand


def encode_number(number):
    chars = []
    while number > 0:
        unit = number % 62
        chars.append(encode_unit(unit))
        number //= 62

    chars.reverse()
    return ''.join(chars)


def encode_unit(number):
    if number < 0:
        raise ValueError('Number must be positive')

    if number < 10:
        return chr(48 + number)

    number -= 10
    if number < 26:
        return chr(97 + number)

    number -= 26
    if number < 26:
        return chr(65 + number)

    raise ValueError('Number too high')


class BatchList(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hash = 0


class Command(BaseHoldupCommand):
    help = 'Export hands'

    def handle(self, *args, **options):
        qs = iter(self.get_queryset(options))
        hand = next(qs, None)

        while hand is not None:
            hands = defaultdict(BatchList)
            ref_date = hand.played_at.date()
            hands[hand.holdup].append(hand.log.strip())

            for hand in qs:
                if hand.played_at.date() == ref_date:
                    logs = hands[hand.holdup]
                    logs.append(hand.log.strip())
                    logs.hash += hand.hash_id()
                else:
                    break
            else:
                # No more hands to export
                hand = None

            # Write in files
            ref_month = str(ref_date)[:7]
            ref_day = ref_date.day
            for holdup, logs in hands.items():
                path = f'local/Holdups/{holdup}/{ref_month}'
                key = encode_number(logs.hash)
                filename = f'{path}/{ref_day}-{len(logs)}-{key}.txt'
                os.makedirs(path, exist_ok=True)

                with open(filename, 'w', encoding='utf-8') as file:
                    for log in logs:
                        print(log, file=file, end='\n\n\n')
