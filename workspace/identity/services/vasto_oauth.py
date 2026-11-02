from functools import lru_cache

from authlib.integrations.django_client import OAuth
from django.conf import settings


@lru_cache(maxsize=1)
def _oauth():
    oauth = OAuth()
    oauth.register(
        name='vasto', client_id=settings.VASTO_CLIENT_ID,
        client_secret=settings.VASTO_CLIENT_SECRET,
        server_metadata_url=settings.VASTO_DISCOVERY_URL,
        client_kwargs={'scope': 'openid profile email'},
        token_endpoint_auth_method='client_secret_basic',
    )
    return oauth


def client():
    if not settings.VASTO_CLIENT_ID or not settings.VASTO_CLIENT_SECRET:
        raise RuntimeError('Vasto OAuth client credentials are not configured.')
    return _oauth().create_client('vasto')


def validate_discovery_issuer():
    metadata = client().load_server_metadata()
    if metadata.get('issuer') != settings.VASTO_ISSUER:
        raise RuntimeError('Vasto discovery issuer does not match VASTO_ISSUER.')
    return metadata
