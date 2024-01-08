from datetime import datetime, timedelta
from itertools import accumulate
from functools import lru_cache

import math
import numpy as np
import scipy.stats as stats

from django.utils import timezone
from django.utils.formats import date_format

from .base.base import BaseHoldupCommand


WEEK = timedelta(days=7)
TIMEZONE = timezone.get_current_timezone()


def distance(dt, weekday, hour):
    """Compute how close the given daytime is to the input week period."""
    ref = get_ref_day(weekday) + timedelta(hours=hour)
    delta = (dt - ref) % WEEK
    return min(delta, WEEK - delta)


def bb100(number):
    return round(number * 100, 2)


@lru_cache(maxsize=10)
def get_ref_day(weekday):
    return datetime(2022, 8, weekday, tzinfo=timezone.utc)


@lru_cache(maxsize=10)
def get_day_name(weekday):
    return date_format(get_ref_day(weekday), 'l').title()


class Command(BaseHoldupCommand):
    help = 'Analyse hands'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('--per-day', action='store_true')
        parser.add_argument('--draw', action='store_true')

    def handle(self, *args, **options):
        qs = self.get_queryset(options)

        if options.get('draw'):
            self.draw(qs)
            return

        for limit in qs.values_list('limit', flat=True).order_by().distinct():
            print('-----')
            print('Limit:', limit)
            self.analyse(qs.filter(limit=limit))

        if options.get('per_day'):
            self.analyse_per_day(qs)

    def sample(self, qs):
        return [sum(sample) for sample in zip(*(
            (h.hero_all_in_adjusted for h in qs.filter(hero_position=pos).order_by('?'))
            for pos in range(-2, 4)
        ))]

    def draw(self, qs):
        import matplotlib.pyplot as plt

        # Draw winnings graph
        plt.figure()
        plt.xlabel('Hands')
        plt.ylabel('BB won')

        plot_data = [
            list(accumulate(
                qs.values_list(win_field, flat=True),
                initial=0
            ))
            for win_field in ['hero_net', 'hero_all_in_adjusted']
        ]
        plt.plot(plot_data[0], label='Net won')
        plt.plot(plot_data[1], '-r', label='All-in adjusted')

        plt.grid()
        plt.legend()

        # Winrate
        plt.figure()
        shift = len(qs) // 10
        winrate = [100 * acc / (shift + i) for (i, acc) in enumerate(plot_data[1][shift:])]
        plt.plot(range(shift, shift + len(winrate)), winrate, label="Winrate")

        plt.xlabel('Hands')
        plt.ylabel('BB / 100')
        plt.grid()
        plt.legend()

        # Compare to normal distribution
        NB_POSITIONS = 6
        NB_BATCHES = 50
        BOUND = 50 * NB_BATCHES

        plt.figure()
        data = np.array([h.hero_all_in_adjusted for h in qs])
        data_hist = self.sample(qs)
        print('Hist', len(data_hist))
        data_hist = [
            sum(data_hist[index:index + NB_BATCHES])
            for index in range(0, len(data_hist) - NB_BATCHES, NB_BATCHES)
        ]

        mean = np.mean(data) * NB_POSITIONS * NB_BATCHES
        std = np.std(data) * math.sqrt(NB_POSITIONS * NB_BATCHES)
        plt.hist([max(min(h, BOUND), -BOUND) for h in data_hist], density=True, bins=50)

        x = np.linspace(mean - 5 * std, mean + 5 * std, 100)
        normal_dist = stats.norm(loc=mean, scale=std)
        plt.plot(x, normal_dist.pdf(x))

        plt.xlabel('Value')
        plt.ylabel('Density')
        plt.title('Comparison of Data to Normal Distribution')
        plt.legend(['Normal Distribution', 'Winnings by session'])

        # Display the plot
        plt.show()

    @staticmethod
    def analyse(qs):
        ev = sum(float(h.hero_net) for h in qs) / len(qs)
        var = sum((float(h.hero_net) - ev)**2 for h in qs) / len(qs)

        adjust = sum(h.hero_all_in_adjusted for h in qs) / len(qs)
        var_a = sum((h.hero_all_in_adjusted - adjust)**2 for h in qs) / len(qs)

        total_rake = sum(h.rake for h in qs) / len(qs)
        total_holdup = sum(h.holdup for h in qs) / len(qs)

        print()
        print(len(qs), 'hands analysed.')
        print()
        print('bb/100:', ev * 100)
        print('Variance:', var)
        print('Std deviation:', var ** 0.5)
        print()
        print('All-in adjusted:', adjust * 100)
        print('Variance:', var_a)
        print('Std deviation:', var_a ** 0.5)
        print()
        print('Rake (all players):', total_rake * 100, 'bb/100')
        print('Holdups:', total_holdup * 100, 'bb/100')
        print('Ratio:', format(total_holdup / float(total_rake), '.2%') if total_rake > 0 else '-')

    @staticmethod
    def analyse_per_day(qs):
        for weekday in range(1, 8):
            for hour in [*range(3), *range(13, 24)]:
                total_hands = 0
                total_rake = 0
                total_holdup = 0
                total_net_won = 0

                for hand in qs:
                    dt = hand.played_at
                    seconds = distance(dt, weekday, hour).total_seconds()
                    if seconds >= 3600:
                        continue

                    coeff = 1 - seconds / 3600
                    total_hands += coeff
                    total_rake += float(hand.rake) * coeff
                    total_holdup += float(hand.holdup) * coeff
                    total_net_won += float(hand.hero_net) * coeff

                if total_hands > 100:
                    print()
                    print(get_day_name(weekday), f'{hour}h (UTC)')
                    print(
                        'Hands', total_hands,
                        'Net won', bb100(total_net_won / total_hands),
                        'Rake', bb100(total_rake / total_hands),
                        'Holdup', bb100(total_holdup / total_hands),
                    )
