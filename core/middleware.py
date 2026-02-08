from django.utils import timezone


class LastSeenMiddleware:
    """Middleware to update authenticated patient's `last_seen` timestamp."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            user = getattr(request, 'user', None)
            if user and user.is_authenticated:
                if hasattr(user, 'patient'):
                    try:
                        user.patient.last_seen = timezone.now()
                        user.patient.save(update_fields=['last_seen'])
                    except Exception:
                        pass
                if hasattr(user, 'clinic'):
                    try:
                        user.clinic.last_seen = timezone.now()
                        user.clinic.save(update_fields=['last_seen'])
                    except Exception:
                        pass
        except Exception:
            # don't let presence update break requests
            pass
        return response
