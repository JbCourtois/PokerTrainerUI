import io
import os

from itertools import count
from fractions import Decimal
import random

from dateutil.parser import parse as date_parse

from django.test import TestCase

from apps.tracker.models import HoldupHand
from apps.tracker.core.parser import StreamParser

from apps.tracker.management.commands.run_samples import Sample
from apps.tracker.management.commands.export_hands import encode_number

base_path = os.path.dirname(__file__)


class TestEncode(TestCase):
    def test_encode(self):
        self.assertEqual(encode_number(0), '')
        self.assertEqual(encode_number(61), 'Z')
        self.assertEqual(encode_number(62), '10')
        self.assertEqual(encode_number(46549516981919989), '3rcelJG7Pv')


class TestSample(TestCase):
    @classmethod
    def setUpTestData(cls):
        counter = count()
        HoldupHand.objects.bulk_create([
            HoldupHand(
                played_at='2022-01-01 20:00Z', winamax_id=str(next(counter)),
                limit=1, rake=0, holdup=0,
                hero_position=pos, hero_net=net,
            )
            for pos in range(-2, 4)
            for net in range(-15, 20)
        ])

    def test_run_sample(self):
        random.seed(42)
        sample = Sample(HoldupHand.objects.all())

        sample.run(limit=100)
        self.assertFalse(sample.interrupted)
        self.assertEqual(sample.result, 47873)

        sample.result = 0
        sample.run(limit=20)
        self.assertTrue(sample.interrupted)


class TestStreamParser(TestCase):
    @classmethod
    def setUpTestData(cls):
        with io.open(os.path.join(base_path, 'fixtures/Floride.txt'), encoding='utf-8') as file:
            StreamParser(file)

    def test_log(self):
        hand = HoldupHand.objects.get(winamax_id='17338644-4049380-1658761263')
        log_path = os.path.join(base_path, 'fixtures/17338644-4049380-1658761263.txt')
        with io.open(log_path, encoding='utf-8') as file:
            data = file.read().strip()

        self.assertEqual(hand.log.strip(), data)

    def test_walk(self):
        hand = HoldupHand.objects.get(winamax_id='17338644-4049380-1658761263')
        self.assertEqual(hand.hash_id(), 1680149287)
        self.assertEqual(hand.played_at, date_parse('2022/07/25 15:01:03 UTC'))
        self.assertEqual(hand.limit, Decimal("0.1"))
        self.assertEqual(hand.hero_position, -2)
        self.assertEqual(hand.hero_hole, 'TcTd')
        self.assertEqual(hand.hero_hole_token, 'TT')
        self.assertEqual(hand.action, 'fffff')
        self.assertEqual(hand.hero_net, Decimal("0.5"))
        self.assertEqual(hand.hero_all_in_adjusted, 0.5)
        self.assertEqual(hand.rake, 0)
        self.assertEqual(hand.holdup, 0)
        self.assertIsNone(hand.hero_showdown)

    def test_holdup_steal(self):
        hand = HoldupHand.objects.get(winamax_id='17338644-4050527-1658761944')
        self.assertEqual(hand.limit, Decimal("0.1"))
        self.assertEqual(hand.hero_position, 3)
        self.assertEqual(hand.hero_hole, '8dQd')
        self.assertEqual(hand.hero_hole_token, 'Q8s')
        self.assertEqual(hand.action, 'B20fffff')
        self.assertEqual(hand.hero_net, Decimal("6.5"))
        self.assertEqual(hand.hero_all_in_adjusted, 6.5)
        self.assertEqual(hand.rake, 0)
        self.assertEqual(hand.holdup, 5)
        self.assertIsNone(hand.hero_showdown)

    def test_allin_pre(self):
        hand = HoldupHand.objects.get(winamax_id='17338644-4076413-1658776057')
        self.assertEqual(hand.limit, Decimal("0.1"))
        self.assertEqual(hand.hero_position, 0)
        self.assertEqual(hand.hero_hole, 'AhQc')
        self.assertEqual(hand.hero_hole_token, 'AQo')
        self.assertEqual(hand.action, 'fffB2.5fb7.5B23.5c///')
        self.assertEqual(hand.hero_net, Decimal("19.2"))
        self.assertAlmostEqual(hand.hero_all_in_adjusted, -10.53098207639142)
        self.assertEqual(hand.rake, Decimal("4.8"))
        self.assertEqual(hand.holdup, 0)
        self.assertEqual(hand.hero_showdown, 34380288)
        self.assertEqual(hand.winning_hand, 34380288)

    def test_allin_pre_side_pot(self):
        hand = HoldupHand.objects.get(winamax_id='17464639-305951-1659182914')
        self.assertEqual(hand.limit, Decimal("0.1"))
        self.assertEqual(hand.hero_position, -1)
        self.assertEqual(hand.hero_hole, '8sAs')
        self.assertEqual(hand.hero_hole_token, 'A8s')
        self.assertEqual(hand.action, 'ffccB43.2b85.4ff///')
        self.assertEqual(hand.hero_net, Decimal("61.4"))
        self.assertAlmostEqual(hand.hero_all_in_adjusted, 23.244264175637035)
        self.assertEqual(hand.rake, Decimal("8.8"))
        self.assertEqual(hand.holdup, 25)
        self.assertEqual(hand.hero_showdown, 51037696)
        self.assertEqual(hand.winning_hand, 51037696)

    def test_allin_flop(self):
        hand = HoldupHand.objects.get(winamax_id='17464639-848682-1659654330')
        self.assertEqual(hand.limit, Decimal("0.1"))
        self.assertEqual(hand.hero_position, 0)
        self.assertEqual(hand.hero_hole, 'QdQh')
        self.assertEqual(hand.hero_hole_token, 'QQ')
        self.assertEqual(hand.action, 'fcfB5ffc/kB6.4c//')
        self.assertEqual(hand.hero_net, Decimal("15.5"))
        self.assertAlmostEqual(hand.hero_all_in_adjusted, 8.476111111111111)
        self.assertEqual(hand.rake, Decimal("2.4"))
        self.assertEqual(hand.holdup, 5)
        self.assertEqual(hand.hero_showdown, 17467200)
        self.assertEqual(hand.winning_hand, 17467200)

    def test_split(self):
        hand = HoldupHand.objects.get(winamax_id='17194928-480529-1651407831')
        self.assertEqual(hand.limit, Decimal("0.02"))
        self.assertEqual(hand.hero_hole, 'AhQd')
        self.assertEqual(hand.hero_hole_token, 'AQo')
        self.assertEqual(hand.action, 'fffB2.5fc/kB4c/kB20c/')
        self.assertEqual(hand.hero_net, Decimal("-2.5"))
        self.assertAlmostEqual(hand.hero_all_in_adjusted, 14.954545454545455)
        self.assertEqual(hand.rake, Decimal("5.5"))
        self.assertEqual(hand.holdup, 0)
        self.assertEqual(hand.hero_showdown, 101486592)
        self.assertEqual(hand.winning_hand, 101486592)

    def test_conflict(self):
        old_count = HoldupHand.objects.count()
        with io.open(os.path.join(base_path, 'fixtures/Floride-conflict.txt'), encoding='utf-8') as file:
            StreamParser(file)
        self.assertEqual(HoldupHand.objects.count(), old_count)

        hand = HoldupHand.objects.get(winamax_id='17194928-480529-1651407831')
        self.assertEqual(hand.limit, Decimal("0.02"))
        self.assertEqual(hand.hero_hole, 'AhQd')
        self.assertEqual(hand.hero_hole_token, 'AQo')
        self.assertEqual(hand.action, 'fffB2.5fc/kB4c/kB20c/')
        self.assertEqual(hand.hero_net, Decimal("47.5"))
        self.assertEqual(hand.rake, Decimal("5.5"))
        self.assertEqual(hand.holdup, 0)
        self.assertEqual(hand.hero_showdown, 101486592)
        self.assertEqual(hand.winning_hand, 101486592)

    def test_side_pot(self):
        hand = HoldupHand.objects.get(winamax_id='17259194-2364102-1654473541')
        self.assertEqual(hand.limit, Decimal("0.02"))
        self.assertEqual(hand.action, 'ffB4ccf/kB3.5fc/kK/b16.5C')
        self.assertEqual(hand.hero_net, 3)
        self.assertEqual(hand.hero_all_in_adjusted, 3)
        self.assertEqual(hand.rake, Decimal("4.5"))
        self.assertEqual(hand.holdup, 5)
        self.assertEqual(hand.hero_showdown, 67305472)
        self.assertEqual(hand.winning_hand, 67305472)

    def test_split_side_pot(self):
        hand = HoldupHand.objects.get(winamax_id='17497931-4318029-1663442411')
        self.assertEqual(hand.limit, Decimal("0.1"))
        self.assertEqual(hand.action, 'ffB48.2fb95.4f///')
        self.assertEqual(hand.hero_net, Decimal("0.7"))
        self.assertAlmostEqual(hand.hero_all_in_adjusted, 0.65)
        self.assertEqual(hand.rake, Decimal("9.7"))
        self.assertEqual(hand.holdup, 10)
        self.assertEqual(hand.hero_showdown, 17418320)
        self.assertEqual(hand.winning_hand, 17418320)

    def test_complex(self):
        hand = HoldupHand.objects.get(winamax_id='17464639-246880-1659123145')
        self.assertEqual(hand.limit, Decimal("0.1"))
        self.assertEqual(hand.hero_position, -1)
        self.assertEqual(hand.action, 'fffcB4.5fc/B2.5c/B5.5b21.5C/')
        self.assertEqual(hand.hero_net, Decimal("20.1"))
        self.assertAlmostEqual(hand.hero_all_in_adjusted, 18.09545454545455)
        self.assertEqual(hand.rake, Decimal("4.9"))
        self.assertEqual(hand.holdup, 0)
        self.assertEqual(hand.hero_showdown, 101036032)
        self.assertEqual(hand.winning_hand, 101036032)

    def test_external(self):
        hand = HoldupHand.objects.get(winamax_id='17497931-484441-1660161499')
        self.assertEqual(hand.limit, Decimal("0.1"))
        self.assertEqual(hand.hero_position, -2)
        self.assertEqual(hand.hero_hole, '4sJd')
        self.assertEqual(hand.hero_hole_token, 'J4o')
        self.assertEqual(hand.action, 'ffcb9.5cFf/b9.1c/b70.6c/')
        self.assertEqual(hand.hero_net, -1)
        self.assertEqual(hand.hero_all_in_adjusted, -1)
        self.assertEqual(hand.rake, 18)
        self.assertEqual(hand.holdup, 5)
        self.assertIsNone(hand.hero_showdown)  # Folded before showdown
        self.assertEqual(hand.winning_hand, 101384192)

    def test_bb_allin(self):
        hand = HoldupHand.objects.get(winamax_id='17497931-28056-1659798272')
        self.assertEqual(hand.limit, Decimal("0.1"))
        self.assertEqual(hand.hero_position, -2)
        self.assertEqual(hand.action, 'ffb2.5fc/kb3.9c/kk/b7f')
        self.assertEqual(hand.hero_net, Decimal("1.7"))
        self.assertEqual(hand.rake, Decimal("1.4"))
        self.assertEqual(hand.holdup, 0)
        self.assertEqual(hand.hero_showdown, 34293504)
        self.assertEqual(hand.winning_hand, 34293504)

    def test_alt_name(self):
        hand = HoldupHand.objects.get(winamax_id='17744560-312114-1666537229')
        self.assertEqual(hand.limit, Decimal("0.1"))
        self.assertEqual(hand.hero_position, 0)
        self.assertEqual(hand.hero_hole, '2h6s')
        self.assertEqual(hand.action, 'fffB2.2fc/kB1.2b3F')
        self.assertEqual(hand.hero_net, Decimal("-3.4"))
        self.assertEqual(hand.rake, Decimal("0.7"))
        self.assertEqual(hand.holdup, 0)
        self.assertIsNone(hand.hero_showdown)  # Folded before showdown

        with io.open(os.path.join(base_path, 'fixtures/Floride-single-log.txt'), encoding='utf-8') as file:
            expected_log = file.read().rstrip()
        self.assertEqual(hand.log, expected_log)

    def test_allin_hero_covers(self):
        hand = HoldupHand.objects.get(winamax_id='17744560-913853-1667142813')
        self.assertEqual(hand.limit, Decimal("0.1"))
        self.assertEqual(hand.hero_position, -2)
        self.assertEqual(hand.action, 'b3ccffB23.8fcf///')
        self.assertEqual(hand.hero_net, Decimal("31.1"))
        self.assertAlmostEqual(hand.hero_all_in_adjusted, 3.415738005634513)
        self.assertEqual(hand.rake, Decimal("4.5"))
        self.assertEqual(hand.holdup, 10)
        self.assertEqual(hand.hero_showdown, 67698688)
        self.assertEqual(hand.winning_hand, 67698688)

    def test_format_2023_04(self):
        hand = HoldupHand.objects.get(winamax_id='18352826-2009726-1682763846')
        self.assertEqual(hand.limit, Decimal("0.1"))
        self.assertEqual(hand.hero_position, 0)
        self.assertEqual(hand.hero_hole, '4hQh')
        self.assertEqual(hand.hero_hole_token, 'Q4s')
        self.assertEqual(hand.action, 'b3cfCcc/kkb13fFff')
        self.assertEqual(hand.hero_net, -3)
        self.assertEqual(hand.hero_all_in_adjusted, -3)
        self.assertEqual(hand.rake, Decimal("1.5"))
        self.assertEqual(hand.holdup, 5)
        self.assertIsNone(hand.hero_showdown)  # Folded before showdown
        self.assertIsNone(hand.winning_hand)  # Folded before showdown
