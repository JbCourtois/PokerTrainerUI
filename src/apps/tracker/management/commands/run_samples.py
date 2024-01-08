from itertools import cycle
from random import random

from django.core.management.base import BaseCommand

from apps.tracker.models import HoldupHand

NB_SAMPLES = 1000
BANKROLL = 500


def choice(sample):
    """Faster implementation of random.choice."""
    index = int(random() * len(sample))
    return sample[index]


class Sample:
    NB_HANDS = 24000

    def __init__(self, qs):
        self.data = {pos: [] for pos in range(-2, 4)}
        for hand in qs:
            self.data[hand.hero_position].append(hand.hero_net)

        self.result = 0
        self.interrupted = False

    def run(self, limit=None):
        data = cycle(list(self.data.values()))
        if limit is not None:
            limit = -limit

        for _ in range(self.NB_HANDS):
            qs = next(data)
            self.result += choice(qs)
            if limit is not None and self.result <= limit:
                self.interrupted = True
                break

        return self


class Command(BaseCommand):
    help = 'Run sample simulations, return risk of ruin'

    def handle(self, *args, **options):
        qs = HoldupHand.objects.all()
        samples = [Sample(qs).run(limit=BANKROLL) for _ in range(NB_SAMPLES)]
        print(sum(1 for x in samples if not x.interrupted) / NB_SAMPLES)
