from django.urls import path, include

urlpatterns = [
    path('trainer/', include('apps.trainer.urls')),
]
