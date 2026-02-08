from django.http import HttpResponseForbidden
from django.conf import settings
from django.core.cache import cache
from .utils import get_client_ip
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class BlockBlockedIPMiddleware:
    """Middleware to mark requests from blocked IPs and prevent login POSTs.

    - Sets `request.blocked_ip_until` to expiry timestamp (float) when IP is blocked.
    - Allows GET to the login page so the template can display a message.
    - Blocks POST attempts to the login path with 403.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.login_path = getattr(settings, 'LOGIN_URL', '/accounts/login/')

    def __call__(self, request):
        ip = get_client_ip(request)
        if ip:
            blocked_key = f'blocked_ip:{ip}'
            expiry_ts = cache.get(blocked_key)
            if expiry_ts:
                try:
                    expiry = float(expiry_ts)
                except Exception:
                    expiry = expiry_ts
                # remaining seconds until unblock
                try:
                    remaining = int(max(0, expiry - timezone.now().timestamp()))
                except Exception:
                    remaining = None
                request.blocked_ip_until = expiry
                request.blocked_remaining = remaining

                # If this is a login POST, block it
                if request.path == self.login_path or request.path.startswith(self.login_path):
                    if request.method == 'POST':
                        logger.info('Blocking login POST from blocked IP %s', ip)
                        return HttpResponseForbidden('Too many failed login attempts. Try again later.')
                    # allow GET so template can show a message

        return self.get_response(request)
