from .settings import DATABASES

DATABASES['default'] = {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': 'pokertools',
}
