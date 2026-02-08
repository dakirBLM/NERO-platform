
from django.db import models
from accounts.models import User
from patients.models import MedicalRecord, Patient

# ...existing code...

# Place Post and Comment models after Clinic and other models

# ...existing Clinic, ClinicGallery, ClinicService, Appointment definitions...

# Add Post and Comment models at the end

class Post(models.Model):
    clinic = models.ForeignKey('Clinic', on_delete=models.CASCADE, related_name='clinic_posts')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='clinic_post_authors')
    description = models.TextField()
    image = models.ImageField(upload_to='clinic_posts/', blank=True, null=True)
    video = models.FileField(upload_to='clinic_post_videos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Post by {self.author} for {self.clinic.clinic_name}"



class Clinic(models.Model):
    SPECIALIZATION_CHOICES = (
        ('Physical Therapy', 'Physical Therapy'),
        ('Occupational Therapy', 'Occupational Therapy'),
        ('Sports Medicine', 'Sports Medicine'),
        ('Orthopedic Rehabilitation', 'Orthopedic Rehabilitation'),
        ('Neurological Rehabilitation', 'Neurological Rehabilitation'),
        ('Cardiac Rehabilitation', 'Cardiac Rehabilitation'),
        ('Pediatric Rehabilitation', 'Pediatric Rehabilitation'),
        ('Geriatric Rehabilitation', 'Geriatric Rehabilitation'),
        ('Pain Management', 'Pain Management'),
        ('Post-Surgical Rehabilitation', 'Post-Surgical Rehabilitation'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    clinic_name = models.CharField(max_length=200)
    tagline = models.CharField(max_length=300, blank=True, help_text="Brief tagline for your clinic")
    description = models.TextField(help_text="Detailed description of your clinic services and approach")
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    phone_number = models.CharField(max_length=15)
    contact_email = models.EmailField()
    website = models.URLField(blank=True)
    specialization = models.CharField(max_length=50, choices=SPECIALIZATION_CHOICES)
    other_specializations = models.CharField(max_length=200, blank=True, help_text="Other specializations (comma separated)")
    license_number = models.CharField(max_length=50)
    established_date = models.DateField()
    facilities = models.CharField(max_length=500, blank=True, help_text="Available facilities (comma separated)")
    number_of_therapists = models.PositiveIntegerField(default=1)
    languages_spoken = models.CharField(max_length=200, default='English', help_text="Languages spoken (comma separated)")
    hours_of_operation = models.TextField(default='Mon-Fri: 9:00 AM - 6:00 PM\nSat: 9:00 AM - 1:00 PM')
    profile_picture = models.ImageField(upload_to='clinic_profile_pics/', blank=True, null=True, help_text="Main profile picture of your clinic")
    cover_photo = models.ImageField(upload_to='clinic_cover_photos/', blank=True, null=True, help_text="Cover photo for your clinic page")
    last_seen = models.DateTimeField(null=True, blank=True)
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    is_verified = models.BooleanField(default=False)
    # Acceptance flags: whether the clinic accepts certain patient conditions
    accepts_heart_problems = models.BooleanField(default=True, help_text="Accept patients with heart problems")
    accepts_catheter = models.BooleanField(default=True, help_text="Accept patients using a catheter (permanent or intermittent)")
    accepts_wheelchair = models.BooleanField(default=True, help_text="Accept patients who use a wheelchair")
    accepts_walker = models.BooleanField(default=True, help_text="Accept patients who use a walker")
    accepts_crutch = models.BooleanField(default=True, help_text="Accept patients who use crutches")
    accepts_electric_wheelchair = models.BooleanField(default=True, help_text="Accept patients who use an electric wheelchair")
    accepts_bowel_incontinence = models.BooleanField(default=True, help_text="Accept patients with bowel incontinence")
    accepts_urine_incontinence = models.BooleanField(default=True, help_text="Accept patients with urine incontinence")
    accepts_medical_condom = models.BooleanField(default=True, help_text="Accept patients using a medical condom")
    accepts_diapers = models.BooleanField(default=True, help_text="Accept patients using diapers")
    accepts_breathing_issues = models.BooleanField(default=True, help_text="Accept patients with breathing issues")
    accepts_feeding_tube = models.BooleanField(default=True, help_text="Accept patients using a feeding tube")
    accepts_stool_tube = models.BooleanField(default=True, help_text="Accept patients using a stool tube")
    accepts_urine_tube = models.BooleanField(default=True, help_text="Accept patients using a urine tube")
    accepts_bedsores = models.BooleanField(default=True, help_text="Accept patients with bedsores")
    accepts_diabetes = models.BooleanField(default=True, help_text="Accept patients with diabetes")
    accepts_insulin = models.BooleanField(default=True, help_text="Accept patients using insulin")
    accepts_high_blood_pressure = models.BooleanField(default=True, help_text="Accept patients with high blood pressure")
    accepts_infectious_diseases = models.BooleanField(default=True, help_text="Accept patients with infectious diseases")
    accepts_vein_thrombosis = models.BooleanField(default=True, help_text="Accept patients with vein thrombosis")
    accepts_depression = models.BooleanField(default=True, help_text="Accept patients with depression")
    
    def __str__(self):
        return self.clinic_name

    def is_active(self, minutes=5):
        from django.utils import timezone
        from datetime import timedelta
        if not self.last_seen:
            return False
        return timezone.now() - self.last_seen <= timedelta(minutes=minutes)
    
    @property
    def full_address(self):
        return f"{self.address}, {self.city}, {self.state} {self.zip_code}"
    
    @property
    def years_in_operation(self):
        from datetime import date
        return date.today().year - self.established_date.year

class ClinicGallery(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='clinic_gallery/')
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Gallery image for {self.clinic.clinic_name}"

class ClinicService(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='services')
    service_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price_range = models.CharField(max_length=100, blank=True, help_text="e.g., $100-$150 per session")
    
    def __str__(self):
        return f"{self.service_name} - {self.clinic.clinic_name}"
    
class Appointment(models.Model):
     STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
     patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
     clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE)
     medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE)
     appointment_date = models.DateField()
     appointment_time = models.TimeField()
     status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
     notes = models.TextField(blank=True, help_text="Any additional notes for the clinic")
     created_at = models.DateTimeField(auto_now_add=True)
     updated_at = models.DateTimeField(auto_now=True)
    
     class Meta:
        ordering = ['-created_at']
    
     def __str__(self):
        return f"Appointment: {self.patient.full_name} - {self.clinic.clinic_name} - {self.appointment_date}"