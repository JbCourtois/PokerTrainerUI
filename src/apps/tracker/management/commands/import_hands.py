import io
import glob

from django.core.management.base import BaseCommand

from apps.tracker.core.parser import StreamParser


class Command(BaseCommand):
    help = 'Import hands'

    def add_arguments(self, parser):
        parser.add_argument('-path', required=True)

    def handle(self, *args, **options):
        for filename in glob.glob(options['path'], recursive=True):
            print(filename)
            with io.open(filename, encoding='utf-8') as file:
                parser = StreamParser(file)
            print(parser.nb_hands, 'hands parsed.')
