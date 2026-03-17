import base64
import hashlib

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


def _get_fernet():
    """Build a Fernet instance from settings.ENCRYPTION_KEY or SECRET_KEY."""
    key = getattr(settings, 'ENCRYPTION_KEY', None)
    if key is None:
        key = base64.urlsafe_b64encode(
            hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        )
    elif isinstance(key, str):
        key = key.encode()
    return Fernet(key)


@deconstructible
class EncryptedFileSystemStorage(FileSystemStorage):
    """Local-disk Fernet-encrypted storage.

    Files are encrypted before saving and decrypted on read.
    .url(name) returns the Django secure-proxy URL so files are
    never directly accessible; the view decrypts before streaming.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fernet = _get_fernet()

    def _save(self, name, content):
        content.seek(0)
        data = content.read()
        if not isinstance(data, bytes):
            data = data.encode()
        encrypted = ContentFile(self.fernet.encrypt(data))
        return super()._save(name, encrypted)

    def open(self, name, mode='rb'):
        f = super().open(name, mode)
        encrypted = f.read()
        try:
            data = self.fernet.decrypt(encrypted)
        finally:
            f.close()
        return ContentFile(data)

    def url(self, name):
        """Return the server-side decrypt proxy URL."""
        from django.urls import reverse
        return reverse('secure_encrypted_media', kwargs={'blob_name': name})
