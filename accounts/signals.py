import logging
from django.contrib.auth.signals import user_login_failed
from django.core.cache import cache
from django.dispatch import receiver
from django.utils import timezone
from .utils import get_client_ip

logger = logging.getLogger(__name__)

# Configuration
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 10 * 60  # 10 minutes
BLOCK_SECONDS = 10 * 60   # block IP for 10 minutes


@receiver(user_login_failed)
def handle_login_failed(sender, credentials, request, **kwargs):
    ip = get_client_ip(request) if request is not None else None
    if not ip:
        return

    key = f'failed_login:{ip}'
    blocked_key = f'blocked_ip:{ip}'

    # If already blocked, nothing to do
    if cache.get(blocked_key):
        logger.debug('Login attempt from already-blocked IP %s', ip)
        return

    # Increment attempts (initialize with WINDOW_SECONDS)
    attempts = (cache.get(key) or 0) + 1
    cache.set(key, attempts, timeout=WINDOW_SECONDS)

    logger.debug('Failed login attempt %s for IP %s', attempts, ip)

    if attempts >= MAX_ATTEMPTS:
        # Store expiry timestamp as value so middleware/template can show remaining time
        expiry_ts = timezone.now().timestamp() + BLOCK_SECONDS
        cache.set(blocked_key, expiry_ts, timeout=BLOCK_SECONDS)
        cache.delete(key)
        logger.warning('IP %s blocked for %s seconds after %s failed attempts', ip, BLOCK_SECONDS, attempts)
