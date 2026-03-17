
from django.db import models
from accounts.models import User
from clinics.models import Clinic

class Post(models.Model):
	clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='posts')
	author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
	description = models.TextField()
	image = models.ImageField(upload_to='clinic_posts/', blank=True, null=True)
	video = models.FileField(upload_to='clinic_post_videos/', blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"Post by {self.author} for {self.clinic.clinic_name}"

