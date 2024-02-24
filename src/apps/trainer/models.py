from random import random, getrandbits, shuffle

from django.db import models
from django.utils.functional import cached_property

from .core.tree import Game


class Spot(models.Model):
    name = models.TextField()
    gamefile = models.FileField()
    board = models.CharField(max_length=10)
    pot = models.PositiveIntegerField()
    stack = models.PositiveIntegerField()
    hero_is_oop = models.BooleanField(null=True)

    @cached_property
    def game(self):
        return Game.from_file(self.gamefile.name)

    @classmethod
    def from_file(cls, filename):
        """Return a spot without name. Need to set name before saving."""
        self = cls(gamefile=filename)

        self.board = ''.join(self.game.board)
        self.pot = self.game.pot
        self.stack = self.game.stack
        self.hero_is_oop = (
            None if len(self.game.human_ids) > 1
            else not self.game.human_ids[0]
        )

        return self

    def generate_hand(self):
        hero_id = (
            getrandbits(1) if self.hero_is_oop is None
            else 1 - self.hero_is_oop
        )

        hole_index = int(random() * len(self.game.ranges[hero_id]))
        opp_index = int(random() * len(self.game.ranges[1 - hero_id]))

        hero_hole = self.game.ranges[hero_id][hole_index]
        dead_cards = hero_hole + self.game.ranges[1 - hero_id][opp_index]

        def get_tree(node, dead):
            if node is None:
                return None

            if node[0] > 1:  # Chance node
                draws = list(node[1])
                shuffle(draws)
                for next_street in draws:
                    if next_street not in dead_cards:
                        break
                else:
                    raise ValueError('Cannot find a non-dead card')

                return [2, next_street, get_tree(node[1][next_street], dead + next_street)]

            # Decision node for either player
            is_hero = node[0] == hero_id
            actions = node.get_actions(hole_index if is_hero else opp_index)

            if not is_hero:
                rng = random()
                for action, (freq, _) in actions.items():
                    rng -= freq
                    if rng <= 0:
                        break
                return [node[0], action, get_tree(node[1][action], dead)]

            # Keep only valid lines for hero
            children = {
                action: get_tree(subtree, dead)
                for (action, subtree) in node[1].items()
                if actions[action][0] > 0
            }
            return [node[0], actions, children]

        return Hand(
            spot=self,
            hero_hole=hero_hole,
            hero_is_oop=not hero_id,
            tree=get_tree(self.game.tree, dead_cards),
        )


class Hand(models.Model):
    spot = models.ForeignKey(Spot, on_delete=models.CASCADE)
    hero_hole = models.CharField(max_length=5)
    hero_is_oop = models.BooleanField()
    tree = models.JSONField()

    class Meta:
        indexes = [
            models.Index(fields=['spot']),
        ]
