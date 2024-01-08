import re

from django.db import models


class HoldupHand(models.Model):
    winamax_id = models.CharField(unique=True, max_length=200)
    limit = models.DecimalField(decimal_places=2, max_digits=40)
    played_at = models.DateTimeField()
    holdup = models.PositiveSmallIntegerField()
    hero_position = models.SmallIntegerField(null=True)
    hero_hole = models.CharField(max_length=5, null=True)
    hero_hole_token = models.CharField(max_length=5, null=True)
    hero_net = models.DecimalField(decimal_places=2, max_digits=40, null=True)
    hero_showdown = models.IntegerField(null=True)
    hero_all_in_adjusted = models.FloatField(null=True)
    winning_hand = models.IntegerField(null=True)
    rake = models.DecimalField(decimal_places=2, max_digits=40)
    action = models.TextField(null=True)
    log = models.TextField()

    class Meta:
        indexes = [
            models.Index(fields=['winamax_id']),
            models.Index(fields=['limit']),
            models.Index(fields=['played_at']),
            models.Index(fields=['holdup']),
        ]

    def hash_id(self):
        return sum(int(nnn) for nnn in re.findall(r'\d+', self.winamax_id))
