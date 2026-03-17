import logging
from io import BytesIO
from urllib.parse import urlparse

import requests
from allauth.socialaccount.signals import social_account_added, social_account_updated
from django.contrib.auth.signals import user_logged_in
from django.core.files.base import ContentFile
from django.db import transaction
from django.dispatch import receiver
from PIL import Image

from patients.models import Patient

logger = logging.getLogger(__name__)


def _safe_full_name(user, extra_data):
    full_name = (extra_data.get("name") or "").strip()
    if full_name:
        return full_name

    joined = f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip()
    if joined:
        return joined

    return user.username


def _normalized_avatar_url(extra_data):
    picture_url = (extra_data.get("picture") or "").strip()
    if not picture_url:
        return ""

    # Google avatar URLs usually include query params; force a deterministic size.
    if "googleusercontent.com" in picture_url:
        if "=" in picture_url:
            return picture_url.rsplit("=", 1)[0] + "=s256-c"
        if "?" in picture_url:
            return picture_url.split("?", 1)[0] + "?sz=256"
    return picture_url


def _download_and_attach_avatar(patient, picture_url):
    if not picture_url or patient.profile_picture:
        return

    try:
        response = requests.get(picture_url, timeout=8)
        response.raise_for_status()
    except requests.RequestException:
        logger.warning("Could not fetch Google profile image for user_id=%s", patient.user_id)
        return

    content_type = (response.headers.get("Content-Type", "") or "").lower()
    extension = "jpg"
    content_bytes = response.content

    if "webp" in content_type:
        try:
            image = Image.open(BytesIO(response.content)).convert("RGB")
            converted = BytesIO()
            image.save(converted, format="PNG")
            content_bytes = converted.getvalue()
            extension = "png"
        except Exception:
            logger.warning("Could not convert WEBP avatar for user_id=%s", patient.user_id)
            return
    elif "png" in content_type:
        extension = "png"

    parsed = urlparse(picture_url)
    base_name = parsed.path.rstrip("/").split("/")[-1] or f"google_user_{patient.user_id}"
    filename = f"{base_name}.{extension}"

    patient.profile_picture.save(filename, ContentFile(content_bytes), save=False)


def _sync_google_data_to_user_and_patient(user, extra_data):
    email = (extra_data.get("email") or "").strip()
    first_name = (extra_data.get("given_name") or user.first_name or "").strip()
    last_name = (extra_data.get("family_name") or user.last_name or "").strip()
    picture_url = _normalized_avatar_url(extra_data)
    full_name = _safe_full_name(user, extra_data)

    with transaction.atomic():
        update_fields = []

        if email and not user.email:
            user.email = email
            update_fields.append("email")

        if first_name and not user.first_name:
            user.first_name = first_name
            update_fields.append("first_name")

        if last_name and not user.last_name:
            user.last_name = last_name
            update_fields.append("last_name")

        if update_fields:
            user.save(update_fields=update_fields)

        # Only patient users get profile auto-provisioning from Google data.
        # Clinic users keep account-level data only (email/name on User model).
        if user.user_type != "patient":
            return

        patient, _created = Patient.objects.get_or_create(
            user=user,
            defaults={
                "full_name": full_name,
                "gender": "O",
                "phone": "0000000000",
            },
        )

        patient_changed = False
        if not patient.full_name:
            patient.full_name = full_name
            patient_changed = True

        if picture_url and not patient.profile_picture:
            _download_and_attach_avatar(patient, picture_url)
            if patient.profile_picture:
                patient_changed = True

        if patient_changed:
            patient.save()


def _apply_selected_google_role(user, request):
    """
    Enforce: One Google account = One role (patient or clinic only).
    Prevents the same Google account from connecting to multiple roles.
    """
    if request is None:
        return

    selected_role = request.session.pop('google_selected_role', None)
    if selected_role not in {'patient', 'clinic'}:
        return

    # Check if user already has a role set
    if user.user_type and user.user_type != selected_role:
        # User already has a different role - BLOCK this action
        # Store error in session for display
        request.session['google_role_conflict'] = True
        request.session['existing_role'] = user.user_type
        request.session['attempted_role'] = selected_role
        logger.warning(
            f"Google account role conflict: User {user.id} attempted to connect as '{selected_role}' "
            f"but already has role '{user.user_type}'"
        )
        return

    # First time setup - set the role
    if not user.user_type:
        user.user_type = selected_role
        user.save(update_fields=['user_type'])


@receiver(social_account_added)
@receiver(social_account_updated)
def sync_google_profile(sender, request, sociallogin, **kwargs):
    if sociallogin.account.provider != "google":
        return

    user = sociallogin.user
    extra_data = sociallogin.account.extra_data or {}

    _apply_selected_google_role(user, request)

    _sync_google_data_to_user_and_patient(user, extra_data)


@receiver(user_logged_in)
def sync_google_profile_on_login(sender, request, user, **kwargs):
    # Respect explicit role selection made on login page.
    selected_role = None
    if request is not None:
        selected_role = request.session.get('google_selected_role')

    if selected_role == 'clinic':
        if getattr(user, 'user_type', None) != 'clinic':
            user.user_type = 'clinic'
            user.save(update_fields=['user_type'])
        return

    if selected_role == 'patient' and getattr(user, 'user_type', None) != 'patient':
        user.user_type = 'patient'
        user.save(update_fields=['user_type'])

    # Ensure avatar is filled for patient social users when signal ordering differs.
    if getattr(user, "user_type", None) != "patient":
        return

    if Patient.objects.filter(user=user, profile_picture__isnull=False).exists():
        return

    try:
        from allauth.socialaccount.models import SocialAccount
    except Exception:
        return

    account = SocialAccount.objects.filter(user=user, provider="google").first()
    if not account:
        return

    _sync_google_data_to_user_and_patient(user, account.extra_data or {})
