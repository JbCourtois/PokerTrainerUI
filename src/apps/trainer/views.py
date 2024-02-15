from django.shortcuts import render
from django.views.generic import ListView

from .models import Spot, Hand


class SpotListView(ListView):
    model = Spot


def play_spot(request, spot_id):
    hand = Hand.objects\
        .filter(spot_id=spot_id)\
        .order_by('?')\
        .select_related('spot')\
        .first()
    context = {
        'spot': hand.spot,
        'hand': hand,
    }
    return render(request, 'play_spot.html', context)
