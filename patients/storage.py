import base64
import hashlib
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from cryptography.fernet import Fernet


class EncryptedFileSystemStorage(FileSystemStorage):
    """A FileSystemStorage that encrypts files with Fernet before saving
    and decrypts them when opened. Uses settings.ENCRYPTION_KEY if provided,
    otherwise derives a key from settings.SECRET_KEY.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        key = getattr(settings, 'ENCRYPTION_KEY', None)
        if key is None:
            # derive consistent key from SECRET_KEY
            key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
        else:
            if isinstance(key, str):
                key = key.encode()
        self.fernet = Fernet(key)

    def _save(self, name, content):
        # read raw bytes
        content.seek(0)
        data = content.read()
        if not isinstance(data, bytes):
            data = data.encode()
        token = self.fernet.encrypt(data)
        from django.core.files.base import ContentFile
        encrypted = ContentFile(token)
        return super()._save(name, encrypted)

    def open(self, name, mode='rb'):
        f = super().open(name, mode)
        encrypted = f.read()
        try:
            data = self.fernet.decrypt(encrypted)
        finally:
            f.close()
        from django.core.files.base import ContentFile
        return ContentFile(data)
