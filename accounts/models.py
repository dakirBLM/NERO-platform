from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('patient', 'Patient'),
        ('clinic', 'Clinic'),
    )
    
    user_type = models.CharField(
        max_length=10, 
        choices=USER_TYPE_CHOICES,
        default='patient'
    )
    def __str__(self):
        return f"{self.username} ({self.user_type})"