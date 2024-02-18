from django.shortcuts import render
from django.views.generic import ListView
from django.http import Http404

from .models import Spot, Hand


class SpotListView(ListView):
    model = Spot


def play_spot(request, spot_id):
    qs = Hand.objects\
        .filter(spot_id=spot_id)\
        .order_by('?')\
        .select_related('spot')
    if (hero_is_oop := request.GET.get("hero_is_oop")):
        qs = qs.filter(hero_is_oop=hero_is_oop == '1')

    hand = qs.first()
    if hand is None:
        raise Http404("No hand found for this spot")

    context = {
        'spot': hand.spot,
        'hand': hand,
    }
    print(request.GET.get("hero_is_oop"))
    return render(request, 'trainer/play_spot.html', context)
