from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.tracker.models import HoldupHand


class BaseHoldupCommand(BaseCommand):
    """Mixin to filter a Holdup queryset."""

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('--limit')
        parser.add_argument('--holdup', type=int)

        parser.add_argument('--last-days', '--last_days', type=float)
        parser.add_argument('--min-date', '--min_date')
        parser.add_argument('--all', action='store_true')

    def get_queryset(self, options):
        filters = {}
        if (last_days := options.get('last_days')):
            filters['played_at__gte'] = timezone.now() - timedelta(days=last_days)
        elif (min_date := options.get('min_date')):
            filters['played_at__gte'] = min_date
        elif not options.get('all'):
            raise CommandError(
                'Either argument --last-days, --min-date, or --all '
                'must be provided')

        if (limit := options.get('limit')) is not None:
            filters['limit'] = limit
        if (holdup := options.get('holdup')) is not None:
            filters['holdup'] = holdup

        qs = HoldupHand.objects.filter(**filters).order_by('played_at')
        return qs
