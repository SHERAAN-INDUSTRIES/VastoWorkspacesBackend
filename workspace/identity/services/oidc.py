from django.conf import settings

from identity.services.vasto_oauth import client


def validate_identity(token, nonce):
    oauth_client = client()
    metadata = oauth_client.load_server_metadata()
    if metadata.get('issuer') != settings.VASTO_ISSUER:
        raise ValueError('Vasto issuer mismatch.')
    # Authlib verifies the signature against discovered JWKS and validates
    # issuer, audience, expiry, and nonce using the discovered metadata.
    id_claims = oauth_client.parse_id_token(
        token, nonce=nonce,
        claims_options={'iss': {'values': [settings.VASTO_ISSUER]}},
    )
    if not id_claims or not id_claims.get('sub'):
        raise ValueError('ID token has no subject.')
    userinfo = oauth_client.userinfo(token=token)
    if userinfo.get('sub') != id_claims.get('sub'):
        raise ValueError('UserInfo subject does not match ID token subject.')
    # Only claims from this allowlist are retained locally.
    return {
        'issuer': id_claims.get('iss'), 'subject': id_claims.get('sub'),
        'username': userinfo.get('preferred_username') or userinfo.get('name') or '',
        'email': userinfo.get('email') or '',
        'email_verified': userinfo.get('email_verified') is True,
    }
