from django.urls import path
from . import views

urlpatterns = [
    path('spots', views.SpotListView.as_view(), name='spot-list'),
    path('spots/play/<int:spot_id>', views.play_spot, name='play-spot'),
]
