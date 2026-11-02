import logging

from authlib.integrations.base_client import OAuthError
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.http import JsonResponse, HttpResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST
from joserfc.errors import JoseError

from identity.models import VastoIdentity
from identity.services.oidc import validate_identity
from identity.services.transactions import consume_transaction, create_transaction
from identity.services.vasto_oauth import client

logger = logging.getLogger(__name__)


@require_GET
def vasto_start(request):
    if not request.session.session_key:
        request.session.create()
    oauth_client = client()
    item, challenge = create_transaction(request.session.session_key)
    authorization = oauth_client.create_authorization_url(
        redirect_uri=settings.VASTO_REDIRECT_URI,
        state=item.state,
        nonce=item.nonce,
        code_challenge=challenge,
        code_challenge_method='S256',
    )
    return redirect(authorization['url'])


def _error_response(message, status=400):
    return JsonResponse({'authenticated': False, 'error': message}, status=status)


@require_GET
def vasto_callback(request):
    state = request.GET.get('state', '')
    if not state or not request.session.session_key:
        return _error_response('Invalid or expired authorization transaction.')
    item = consume_transaction(state, request.session.session_key)
    if item is None:
        return _error_response('Invalid or expired authorization transaction.')
    if request.GET.get('error'):
        return _error_response('Vasto authorization was not completed.', 403)
    response_issuer = request.GET.get('iss')
    if response_issuer and response_issuer != settings.VASTO_ISSUER:
        return _error_response('Authorization response issuer mismatch.')
    code = request.GET.get('code')
    if not code:
        return _error_response('Authorization response did not contain a code.')

    try:
        oauth_client = client()
        metadata = oauth_client.load_server_metadata()
        if metadata.get('issuer') != settings.VASTO_ISSUER:
            return _error_response('Vasto discovery issuer mismatch.', 502)
        token = oauth_client.fetch_access_token(
            code=code, redirect_uri=settings.VASTO_REDIRECT_URI,
            code_verifier=item.code_verifier,
        )
        claims = validate_identity(token, item.nonce)
        user = _get_or_create_user(claims)
    except (OAuthError, JoseError, ValueError) as exc:
        logger.info('Vasto authorization rejected: %s', type(exc).__name__)
        return _error_response('Vasto authorization could not be validated.', 401)
    except Exception:
        logger.exception('Vasto callback failed.')
        return _error_response('Vasto authorization could not be completed.', 502)

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    if settings.WORKSPACES_FRONTEND_URL:
        return redirect(settings.WORKSPACES_FRONTEND_URL)
    return HttpResponse('<!doctype html><title>Vasto Workspaces</title><h1>Signed in</h1><p>Vasto identity verified. You can close this page.</p>')


def _get_or_create_user(claims):
    User = get_user_model()
    try:
        with transaction.atomic():
            mapping = VastoIdentity.objects.select_related('user').filter(
                issuer=claims['issuer'], subject=claims['subject'],
            ).first()
            if mapping:
                mapping.username = claims['username']
                mapping.email = claims['email']
                mapping.email_verified = claims['email_verified']
                mapping.save(update_fields=('username', 'email', 'email_verified', 'updated_at'))
                return mapping.user

            username = _unique_username(User, claims['username'] or claims['subject'])
            user = User.objects.create_user(username=username, email=claims['email'])
            user.set_unusable_password()
            user.save(update_fields=('password',))
            VastoIdentity.objects.create(user=user, **claims)
            return user
    except IntegrityError:
        # A concurrent callback may have inserted the unique issuer/subject mapping.
        mapping = VastoIdentity.objects.select_related('user').get(
            issuer=claims['issuer'], subject=claims['subject'],
        )
        return mapping.user


def _unique_username(User, preferred):
    base = ''.join(ch for ch in preferred if ch.isalnum() or ch in '._-')[:120] or 'vasto-user'
    candidate = base
    suffix = 1
    while User.objects.filter(username=candidate).exists():
        candidate = f'{base[:130-len(str(suffix))]}-{suffix}'
        suffix += 1
    return candidate


@require_GET
def me(request):
    if not request.user.is_authenticated:
        return JsonResponse({'authenticated': False}, status=401)
    try:
        identity = request.user.vasto_identity
    except VastoIdentity.DoesNotExist:
        return JsonResponse({'authenticated': False}, status=401)
    return JsonResponse({
        'authenticated': True,
        'identity': {
            'username': identity.username,
            'email': identity.email,
            'email_verified': identity.email_verified,
        },
    })


@csrf_protect
@require_POST
def logout_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'authenticated': False}, status=401)
    logout(request)
    return JsonResponse({'authenticated': False, 'logged_out': True})
