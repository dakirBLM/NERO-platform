from django import forms
from django.contrib.auth.forms import UserCreationForm
from patients.models import Patient
from clinics.models import Clinic
from .models import User

class PatientSignUpForm(UserCreationForm):
    profile_picture = forms.ImageField(required=False)
    gender = forms.ChoiceField(
        choices=Patient.GENDER_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    full_name = forms.CharField(
        max_length=100, 
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your full name'
        })
    )
    date_of_birth = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    phone = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your phone number'
        })
    )
    class Meta:
        model = User
        fields = ['username', 'email', 'full_name', 'date_of_birth', 'gender', 'phone', 'profile_picture', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose a username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name not in ['password1', 'password2']:
                field.widget.attrs.update({'class': 'form-control'})
                
            
    
    def save(self, commit=True): 
        user = super().save(commit=False)
        user.user_type = 'patient'
        if commit:
            user.save()
            patient = Patient.objects.create(
                user=user,
                full_name=self.cleaned_data['full_name'],
                date_of_birth=self.cleaned_data['date_of_birth'],
                gender=self.cleaned_data.get('gender'),
                phone=self.cleaned_data['phone'],
                profile_picture=self.cleaned_data.get('profile_picture')
            )
        return user

class ClinicSignUpForm(UserCreationForm):
    # Clinic Basic Information
    clinic_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your clinic name',
            'class': 'form-control'
        })
    )
    tagline = forms.CharField(
        max_length=300,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., "Expert Care for Your Recovery Journey"',
            'class': 'form-control'
        })
    )
    description = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Describe your clinic, your approach to rehabilitation, and what makes you unique...',
            'class': 'form-control'
        })
    )
    
    # Contact Information
    address = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Full street address',
            'class': 'form-control'
        })
    )
    city = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'City',
            'class': 'form-control'
        })
    )
    state = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'State',
            'class': 'form-control'
        })
    )
    zip_code = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'ZIP Code',
            'class': 'form-control'
        })
    )
    phone_number = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Phone number',
            'class': 'form-control'
        })
    )
    contact_email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'Contact email address',
            'class': 'form-control'
        })
    )
    website = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'placeholder': 'Website URL (optional)',
            'class': 'form-control'
        })
    )
    
    # Professional Information
    specialization = forms.ChoiceField(
        choices=Clinic.SPECIALIZATION_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    other_specializations = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., Sports Injuries, Post-Surgical Rehab, Pain Management',
            'class': 'form-control'
        })
    )
    license_number = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Clinic license number',
            'class': 'form-control'
        })
    )
    established_date = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    # Clinic Details
    facilities = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., Therapy Pool, Modern Gym, Electrotherapy, Ultrasound',
            'class': 'form-control'
        })
    )
    number_of_therapists = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control'
        })
    )
    languages_spoken = forms.CharField(
        max_length=200,
        initial='English',
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g., English, Spanish, French',
            'class': 'form-control'
        })
    )
    hours_of_operation = forms.CharField(
        required=True,
        initial='Mon-Fri: 9:00 AM - 6:00 PM\nSat: 9:00 AM - 1:00 PM\nSun: Closed',
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control'
        })
    )
    
    # Images
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )
    cover_photo = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )
    
    # Social Media
    facebook_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'placeholder': 'Facebook page URL (optional)',
            'class': 'form-control'
        })
    )
    instagram_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'placeholder': 'Instagram profile URL (optional)',
            'class': 'form-control'
        })
    )
    linkedin_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'placeholder': 'LinkedIn page URL (optional)',
            'class': 'form-control'
        })
    )

    # Acceptance flags (clinic capabilities)
    accepts_heart_problems = forms.BooleanField(
        required=False,
        initial=True,
        label='Accept patients with heart problems',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    accepts_catheter = forms.BooleanField(
        required=False,
        initial=True,
        label='Accept patients using a catheter',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    accepts_wheelchair = forms.BooleanField(required=False, initial=True, label='Accept patients using a wheelchair', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    accepts_walker = forms.BooleanField(required=False, initial=True, label='Accept patients using a walker', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    accepts_crutch = forms.BooleanField(required=False, initial=True, label='Accept patients using crutches', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    accepts_electric_wheelchair = forms.BooleanField(required=False, initial=True, label='Accept patients using an electric wheelchair', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    accepts_bowel_incontinence = forms.BooleanField(required=False, initial=True, label='Accept patients with bowel incontinence', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    accepts_urine_incontinence = forms.BooleanField(required=False, initial=True, label='Accept patients with urine incontinence', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    accepts_medical_condom = forms.BooleanField(required=False, initial=True, label='Accept patients using a medical condom', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    accepts_diapers = forms.BooleanField(required=False, initial=True, label='Accept patients using diapers', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    accepts_breathing_issues = forms.BooleanField(required=False, initial=True, label='Accept patients with breathing issues', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    accepts_feeding_tube = forms.BooleanField(required=False, initial=True, label='Accept patients using a feeding tube', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    accepts_stool_tube = forms.BooleanField(required=False, initial=True, label='Accept patients using a stool tube', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    accepts_urine_tube = forms.BooleanField(required=False, initial=True, label='Accept patients using a urine tube', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    accepts_bedsores = forms.BooleanField(required=False, initial=True, label='Accept patients with bedsores', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    accepts_diabetes = forms.BooleanField(required=False, initial=True, label='Accept patients with diabetes', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    accepts_insulin = forms.BooleanField(required=False, initial=True, label='Accept patients using insulin', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    accepts_high_blood_pressure = forms.BooleanField(required=False, initial=True, label='Accept patients with high blood pressure', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    accepts_infectious_diseases = forms.BooleanField(required=False, initial=True, label='Accept patients with infectious diseases', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    accepts_vein_thrombosis = forms.BooleanField(required=False, initial=True, label='Accept patients with vein thrombosis', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    accepts_depression = forms.BooleanField(required=False, initial=True, label='Accept patients with depression', widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to default fields
        for field_name in ['username', 'email', 'password1', 'password2']:
            self.fields[field_name].widget.attrs.update({'class': 'form-control'})

    def save(self, commit=True):
    # First create the user
     user = super().save(commit=False)
     user.user_type = 'clinic'
    
     if commit:
        user.save()
        
        # Now create the clinic profile
        clinic_data = {
            'user': user,
            'clinic_name': self.cleaned_data['clinic_name'],
            'tagline': self.cleaned_data.get('tagline', ''),
            'description': self.cleaned_data.get('description', ''),
            'address': self.cleaned_data['address'],
            'city': self.cleaned_data['city'],
            'state': self.cleaned_data['state'],
            'zip_code': self.cleaned_data['zip_code'],
            'phone_number': self.cleaned_data['phone_number'],
            'contact_email': self.cleaned_data['contact_email'],
            'website': self.cleaned_data.get('website', ''),
            'specialization': self.cleaned_data['specialization'],
            'other_specializations': self.cleaned_data.get('other_specializations', ''),
            'license_number': self.cleaned_data['license_number'],
            'established_date': self.cleaned_data['established_date'],
            'facilities': self.cleaned_data.get('facilities', ''),
            'number_of_therapists': self.cleaned_data['number_of_therapists'],
            'languages_spoken': self.cleaned_data.get('languages_spoken', 'English'),
            'hours_of_operation': self.cleaned_data.get('hours_of_operation', 'Mon-Fri: 9:00 AM - 6:00 PM'),
        }
        
        # Handle file uploads
        if self.cleaned_data.get('profile_picture'):
            clinic_data['profile_picture'] = self.cleaned_data['profile_picture']
        if self.cleaned_data.get('cover_photo'):
            clinic_data['cover_photo'] = self.cleaned_data['cover_photo']
            
        # Handle social media URLs
        if self.cleaned_data.get('facebook_url'):
            clinic_data['facebook_url'] = self.cleaned_data['facebook_url']
        if self.cleaned_data.get('instagram_url'):
            clinic_data['instagram_url'] = self.cleaned_data['instagram_url']
        if self.cleaned_data.get('linkedin_url'):
            clinic_data['linkedin_url'] = self.cleaned_data['linkedin_url']
            
        # Create the clinic object
        # Acceptance fields
        for field in [
            'accepts_heart_problems', 'accepts_catheter', 'accepts_wheelchair', 'accepts_walker', 'accepts_crutch',
            'accepts_electric_wheelchair', 'accepts_bowel_incontinence', 'accepts_urine_incontinence',
            'accepts_medical_condom', 'accepts_diapers', 'accepts_breathing_issues', 'accepts_feeding_tube',
            'accepts_stool_tube', 'accepts_urine_tube', 'accepts_bedsores', 'accepts_diabetes', 'accepts_insulin',
            'accepts_high_blood_pressure', 'accepts_infectious_diseases', 'accepts_vein_thrombosis', 'accepts_depression']:
            clinic_data[field] = self.cleaned_data.get(field, True)
        clinic = Clinic.objects.create(**clinic_data)
    
     return user
 # Return the user object, not clinic
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken. Please choose a different one.")
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered. Please use a different email.")
        return email
    
    def clean_contact_email(self):
        contact_email = self.cleaned_data.get('contact_email')
        if Clinic.objects.filter(contact_email=contact_email).exists():
            raise forms.ValidationError("A clinic with this contact email already exists.")
        return contact_email
    
    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        # Remove all non-digit characters
        clean_phone = ''.join(filter(str.isdigit, phone_number))
        
        if len(clean_phone) < 10:
            raise forms.ValidationError("Please enter a valid phone number with at least 10 digits.")
        
        return phone_number
    
    def clean_established_date(self):
        established_date = self.cleaned_data.get('established_date')
        from datetime import date
        if established_date > date.today():
            raise forms.ValidationError("Established date cannot be in the future.")
        return established_date
    
    def clean_license_number(self):
        license_number = self.cleaned_data.get('license_number')
        if Clinic.objects.filter(license_number=license_number).exists():
            raise forms.ValidationError("A clinic with this license number already exists.")
        return license_number
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match. Please enter the same password in both fields.")
        
        return cleaned_data
   