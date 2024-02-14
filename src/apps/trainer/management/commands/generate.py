from glob import glob

from django.core.management.base import BaseCommand

from ...models import Spot, Hand


class Command(BaseCommand):
    help = 'Test'  # TODO

    def handle(self, *args, **options):
        filenames = glob('local/fixtures/*.txt')
        for filename in filenames:
            print("Generating for", filename)
            spot = Spot.from_file(filename)
            spot.save()

            hands = [spot.generate_hand() for _ in range(100)]
            print('Hands generated. Saving...')
            Hand.objects.bulk_create(hands)
            print('Saved.')
